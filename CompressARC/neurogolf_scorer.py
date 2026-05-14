from pathlib import Path
from dataclasses import dataclass, field
import math
import os
import onnx
import onnxruntime as ort
import numpy as np

FORBIDDEN_OPS = frozenset(['Loop', 'Scan', 'NonZero', 'Unique', 'Script', 'Function'])
MAX_FILE_BYTES = 1_509_949  # 1.44 MB

@dataclass
class ScoringResult:
    onnx_path: Path
    num_params: int
    file_bytes: int
    cost: float
    score: float
    is_valid: bool
    errors: list = field(default_factory=list)

def count_onnx_params(onnx_path: Path) -> int:
    """ONNXモデルの全initializer tensorの要素数合計を返す (= パラメータ数)"""
    model = onnx.load(str(onnx_path))
    total_params = 0
    for initializer in model.graph.initializer:
        if initializer.dims:
            num_elements = int(np.prod(initializer.dims))
            total_params += num_elements
    return total_params

def _collect_nodes(graph) -> list:
    """graphの全ノードを再帰的に収集 (If/Loop等のサブグラフも含む)"""
    nodes = list(graph.node)
    for node in graph.node:
        for attr in node.attribute:
            if attr.HasField('g'):
                nodes.extend(_collect_nodes(attr.g))
            for subgraph in attr.graphs:
                nodes.extend(_collect_nodes(subgraph))
    return nodes

def check_forbidden_ops(model_proto: onnx.ModelProto) -> list:
    """FORBIDDEN_OPS に含まれるop名をリストで返す"""
    forbidden_found = []
    nodes = _collect_nodes(model_proto.graph)
    for node in nodes:
        if node.op_type in FORBIDDEN_OPS:
            forbidden_found.append(node.op_type)
    return forbidden_found

def validate_onnx(onnx_path: Path) -> tuple:
    """
    (is_valid: bool, errors: list[str]) を返す。
    検証項目:
    1. onnx.checker.check_model(model)
    2. check_forbidden_ops() で禁止opがないか
    3. 全入出力のshapeが静的か (value_info の dim.HasField('dim_value') で判定)
    4. ファイルサイズ <= MAX_FILE_BYTES
    5. ort.InferenceSession で zeros(shape=(1,1,30,30), dtype=int64) で推論テスト
    エラー発生時も is_valid=False でエラーメッセージを errors に追加すること
    """
    errors = []
    
    try:
        model = onnx.load(str(onnx_path))
    except Exception as e:
        return False, [f'Failed to load ONNX model: {str(e)}']
    
    # 1. Check model structure
    try:
        onnx.checker.check_model(model)
    except Exception as e:
        errors.append(f'Model check failed: {str(e)}')
        return False, errors
    
    # 2. Check for forbidden ops
    forbidden_ops = check_forbidden_ops(model)
    if forbidden_ops:
        unique_ops = list(set(forbidden_ops))
        errors.append(f'Forbidden ops found: {unique_ops}')
        return False, errors
    
    # 3. Check all inputs and outputs have static shapes
    all_value_infos = list(model.graph.input) + list(model.graph.output)
    for value_info in all_value_infos:
        if value_info.HasField('type'):
            tensor_type = value_info.type
            if tensor_type.HasField('tensor_type'):
                shape = tensor_type.tensor_type.shape
                for dim in shape.dim:
                    if dim.WhichOneof('value') == 'dim_param':
                        errors.append(f'Dynamic shape (dim_param="{dim.dim_param}") found in {value_info.name}')
                        return False, errors
    
    # 4. Check file size
    file_bytes = os.path.getsize(onnx_path)
    if file_bytes > MAX_FILE_BYTES:
        errors.append(f'File size {file_bytes} exceeds MAX_FILE_BYTES {MAX_FILE_BYTES}')
        return False, errors
    
    # 5. Inference test with dummy input
    try:
        session = ort.InferenceSession(str(onnx_path), providers=['CPUExecutionProvider'])
        input_shape = (1, 1, 30, 30)
        dummy_input = np.zeros(input_shape, dtype=np.int64)
        input_name = session.get_inputs()[0].name
        session.run(None, {input_name: dummy_input})
    except Exception as e:
        errors.append(f'Inference test failed: {str(e)}')
        return False, errors
    
    return True, errors

def compute_cost(onnx_path: Path) -> float:
    """Cost = count_onnx_params(path) + os.path.getsize(path)"""
    num_params = count_onnx_params(onnx_path)
    file_bytes = os.path.getsize(onnx_path)
    return float(num_params + file_bytes)

def compute_score(cost: float) -> float:
    """Score = max(1.0, 25.0 - math.log(cost))"""
    return max(1.0, 25.0 - math.log(cost))

def score_onnx_file(onnx_path: Path) -> ScoringResult:
    """
    score_onnx_file を呼ぶだけで ScoringResult が返る。
    ファイルが存在しない場合は errors=['File not found'] で is_valid=False を返す。
    """
    onnx_path = Path(onnx_path)
    
    if not onnx_path.exists():
        return ScoringResult(
            onnx_path=onnx_path,
            num_params=0,
            file_bytes=0,
            cost=0.0,
            score=0.0,
            is_valid=False,
            errors=['File not found']
        )
    
    # Validate
    is_valid, errors = validate_onnx(onnx_path)
    
    # Count params and file size
    try:
        num_params = count_onnx_params(onnx_path)
        file_bytes = os.path.getsize(onnx_path)
    except Exception as e:
        return ScoringResult(
            onnx_path=onnx_path,
            num_params=0,
            file_bytes=0,
            cost=0.0,
            score=0.0,
            is_valid=False,
            errors=errors + [f'Failed to count params: {str(e)}']
        )
    
    # Compute cost and score
    cost = compute_cost(onnx_path)
    score = compute_score(cost)
    
    return ScoringResult(
        onnx_path=onnx_path,
        num_params=num_params,
        file_bytes=file_bytes,
        cost=cost,
        score=score,
        is_valid=is_valid,
        errors=errors
    )

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Usage: python neurogolf_scorer.py <path/to/model.onnx>')
        sys.exit(1)
    result = score_onnx_file(Path(sys.argv[1]))
    print(f'Params: {result.num_params}')
    print(f'Bytes:  {result.file_bytes}')
    print(f'Cost:   {result.cost:.1f}')
    print(f'Score:  {result.score:.4f}')
    print(f'Valid:  {result.is_valid}')
    if result.errors:
        for e in result.errors:
            print(f'  ERROR: {e}')
