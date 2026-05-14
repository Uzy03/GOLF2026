from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass, field
import math
import json

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import onnx
import onnxruntime as ort


# =========================
# Dataclasses
# =========================


@dataclass
class ARCExample:
    input: np.ndarray
    output: np.ndarray


@dataclass
class TTOResult:
    model: nn.Module
    arch_name: str
    train_acc: float
    final_loss: float


@dataclass
class ExportResult:
    onnx_path: Path
    arch_name: str
    num_params: int
    file_bytes: int
    score: float
    is_valid: bool
    errors: list = field(default_factory=list)


# =========================
# Utilities
# =========================


# =========================
# Device Selection
# =========================


def _get_device() -> torch.device:
    """利用可能な最良のデバイスを返す: CUDA > MPS > CPU"""
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def pad_grid(grid: np.ndarray) -> np.ndarray:
    """Pad/crop a (H, W) grid into a fixed (30, 30) grid with zeros."""
    if grid.ndim != 2:
        raise ValueError(f"grid must be 2D (H,W), got shape={grid.shape}")

    h, w = grid.shape
    out = np.zeros((30, 30), dtype=grid.dtype)
    hh = min(h, 30)
    ww = min(w, 30)
    out[:hh, :ww] = grid[:hh, :ww]
    return out


def grid_to_tensor(grid: np.ndarray) -> torch.Tensor:
    """Convert a (H, W) numpy grid to a (1, 1, 30, 30) int64 tensor."""
    padded = pad_grid(grid).astype(np.int64, copy=False)
    t = torch.from_numpy(padded).unsqueeze(0).unsqueeze(0).to(dtype=torch.int64)
    return t


def one_hot_encode(x: torch.Tensor) -> torch.Tensor:
    """(1,1,30,30) int64 -> (1,10,30,30) float32."""
    return (
        F.one_hot(x.squeeze(1).long(), 10)
        .permute(0, 3, 1, 2)
        .float()
    )


def _target_hw(target: np.ndarray) -> tuple[int, int]:
    if target.ndim != 2:
        raise ValueError(f"target must be 2D (H,W), got shape={target.shape}")
    h, w = target.shape
    return min(h, 30), min(w, 30)


def masked_cross_entropy(logits: torch.Tensor, target: np.ndarray) -> torch.Tensor:
    """Cross entropy on the unpadded region only.

    logits: (1, 10, 30, 30) float32
    target: (H, W) numpy
    """
    h, w = _target_hw(target)
    if h == 0 or w == 0:
        return logits.new_tensor(0.0)

    logits_crop = logits[:, :, :h, :w]
    target_t = torch.from_numpy(target[:h, :w].astype(np.int64, copy=False)).unsqueeze(0)
    target_t = target_t.to(device=logits.device, dtype=torch.long)
    return F.cross_entropy(logits_crop, target_t, reduction="mean")


def pixel_accuracy(logits: torch.Tensor, target: np.ndarray) -> float:
    """Return 1.0 if all pixels match on (H,W) region; else 0.0."""
    h, w = _target_hw(target)
    if h == 0 or w == 0:
        return 1.0

    pred = logits.argmax(dim=1)[0, :h, :w].detach().cpu().numpy().astype(np.int64)
    tgt = target[:h, :w].astype(np.int64, copy=False)
    return 1.0 if np.array_equal(pred, tgt) else 0.0


# =========================
# Models
# =========================


class ColorRemapModel(nn.Module):
    """Per-color remapping via embedding: (1,1,30,30) -> (1,10,30,30)."""

    def __init__(self) -> None:
        super().__init__()
        self.emb = nn.Embedding(10, 10)  # 100 params

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (1,1,30,30) int64
        idx = x.squeeze(1).clamp(min=0, max=9).long()  # (1,30,30)
        y = self.emb(idx)  # (1,30,30,10)
        y = y.permute(0, 3, 1, 2).contiguous()  # (1,10,30,30)
        return y.float()


class Conv1x1Model(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.conv = nn.Conv2d(10, 10, kernel_size=1, padding=0, bias=True)  # 110 params

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        oh = one_hot_encode(x)
        return self.conv(oh)


class Conv3x3Model(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.conv = nn.Conv2d(10, 10, kernel_size=3, padding=1, bias=True)  # 910 params

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        oh = one_hot_encode(x)
        return self.conv(oh)


class TwoLayerConvModel(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        # Keep this model lightweight (~414 params) for the search.
        self.conv1 = nn.Conv2d(10, 4, kernel_size=3, padding=1, bias=True)
        self.conv2 = nn.Conv2d(4, 10, kernel_size=1, padding=0, bias=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        oh = one_hot_encode(x)
        y = self.conv1(oh)
        y = F.relu(y)
        y = self.conv2(y)
        return y


ARCH_REGISTRY = [
    ("color_remap", ColorRemapModel),
    ("conv1x1", Conv1x1Model),
    ("conv3x3", Conv3x3Model),
    ("two_layer_conv", TwoLayerConvModel),
]


# =========================
# TTO (Test-Time Optimization)
# =========================


def run_tto(
    model: nn.Module,
    examples: list[ARCExample],
    epochs: int = 1000,
    lr: float = 0.1,
    lambda_p: float = 1e-5,
    patience: int = 100,
    device: torch.device | None = None,
) -> TTOResult:
    if device is None:
        device = _get_device()
    model = model.to(device)

    arch_name = getattr(model, "arch_name", None) or getattr(model, "_arch_name", None) or model.__class__.__name__

    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    total_params = sum(p.numel() for p in model.parameters())
    param_penalty = float(lambda_p) * float(total_params)

    best_loss = math.inf
    best_epoch = -1
    final_loss = math.inf
    train_acc = 0.0

    for epoch in range(int(epochs)):
        model.train()
        optimizer.zero_grad(set_to_none=True)

        if len(examples) == 0:
            final_loss = param_penalty
            train_acc = 1.0
            break

        losses = []
        for ex in examples:
            x = grid_to_tensor(ex.input).to(device)
            logits = model(x)
            losses.append(masked_cross_entropy(logits, ex.output))

        loss = torch.stack(losses).mean() + logits.new_tensor(param_penalty)
        if torch.isnan(loss).item():
            final_loss = float("nan")
            train_acc = 0.0
            break

        loss.backward()
        optimizer.step()

        # Evaluate *after* the update (for accurate early-stopping)
        model.eval()
        with torch.no_grad():
            eval_losses = []
            accs = []
            for ex in examples:
                x = grid_to_tensor(ex.input).to(device)
                logits = model(x)
                eval_losses.append(masked_cross_entropy(logits, ex.output))
                accs.append(pixel_accuracy(logits, ex.output))

            eval_loss = torch.stack(eval_losses).mean() + logits.new_tensor(param_penalty)
            final_loss = float(eval_loss.detach().cpu().item())
            train_acc = float(sum(accs) / len(accs))

        # Early stop: perfect on all examples
        if train_acc >= 1.0:
            break

        # Early stop: no improvement
        if final_loss < best_loss - 1e-9:
            best_loss = final_loss
            best_epoch = epoch
        elif best_epoch >= 0 and (epoch - best_epoch) >= int(patience):
            break

    model.eval()
    return TTOResult(model=model, arch_name=str(arch_name), train_acc=train_acc, final_loss=final_loss)


def solve_with_search(
    examples: list[ARCExample],
    epochs: int = 1000,
    lr: float = 0.1,
    device: torch.device | None = None,
) -> TTOResult | None:
    if device is None:
        device = _get_device()
    for arch_name, arch_cls in ARCH_REGISTRY:
        model = arch_cls()
        setattr(model, "_arch_name", arch_name)
        res = run_tto(model, examples, epochs=epochs, lr=lr, device=device)
        if res.train_acc >= 1.0:
            return res
    return None


# =========================
# ONNX Export / Validation
# =========================


def export_to_onnx(model: nn.Module, output_path: Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    model = model.to(torch.device("cpu"))
    model.eval()

    dummy = torch.zeros((1, 1, 30, 30), dtype=torch.int64)

    import warnings
    import logging
    import io
    import contextlib

    # Suppress torch.onnx verbose logging
    logging.getLogger("torch.onnx").setLevel(logging.ERROR)
    logging.getLogger("onnxscript").setLevel(logging.ERROR)

    # torch._logging internal system produces [torch.onnx] messages to stdout
    # redirect_stdout captures these without affecting tqdm (which uses stderr)
    try:
        import torch._logging as _tl
        _tl.set_logs(onnx=logging.ERROR)
    except Exception:
        pass

    _sink = io.StringIO()
    with warnings.catch_warnings(), contextlib.redirect_stdout(_sink), contextlib.redirect_stderr(_sink):
        warnings.filterwarnings("ignore", category=UserWarning)
        warnings.filterwarnings("ignore", category=FutureWarning)
        torch.onnx.export(
            model,
            dummy,
            str(output_path),
            input_names=["input"],
            output_names=["output"],
            opset_version=17,
            dynamic_axes={},
            do_constant_folding=True,
        )

    return output_path


_FORBIDDEN_OPS = {"Loop", "Scan", "NonZero", "Unique", "Script", "Function"}


def validate_onnx_file(onnx_path: Path) -> tuple[bool, list]:
    errors: list[str] = []

    try:
        model = onnx.load(str(onnx_path))
        onnx.checker.check_model(model)
    except Exception as e:  # noqa: BLE001
        errors.append(f"onnx.checker.check_model failed: {e}")
        return False, errors

    # Forbidden ops / constructs
    try:
        node_ops = [n.op_type for n in model.graph.node]
        for op in node_ops:
            if op in _FORBIDDEN_OPS:
                errors.append(f"forbidden op detected: {op}")

        if getattr(model, "functions", None):
            if len(model.functions) > 0:
                errors.append("forbidden construct detected: Function")
    except Exception as e:  # noqa: BLE001
        errors.append(f"forbidden-op scan failed: {e}")

    # File size limit
    try:
        file_bytes = Path(onnx_path).stat().st_size
        if file_bytes > 1_509_949:
            errors.append(f"file too large: {file_bytes} bytes > 1509949")
    except Exception as e:  # noqa: BLE001
        errors.append(f"file size check failed: {e}")

    # ORT inference test
    try:
        sess = ort.InferenceSession(
            str(onnx_path),
            providers=["CPUExecutionProvider"],
        )
        inp = np.zeros((1, 1, 30, 30), dtype=np.int64)
        out = sess.run(None, {"input": inp})
        if not out or len(out) != 1:
            errors.append("onnxruntime returned no outputs")
        else:
            y = out[0]
            if tuple(y.shape) != (1, 10, 30, 30):
                errors.append(f"unexpected output shape: {y.shape} (expected (1,10,30,30))")
            if y.dtype != np.float32:
                errors.append(f"unexpected output dtype: {y.dtype} (expected float32)")
    except Exception as e:  # noqa: BLE001
        errors.append(f"onnxruntime inference failed: {e}")

    return (len(errors) == 0), errors


# =========================
# Task IO / Solve
# =========================


def load_task_examples(task_json_path: Path) -> list[ARCExample]:
    task_json_path = Path(task_json_path)
    data = json.loads(task_json_path.read_text(encoding="utf-8"))
    train = data.get("train", [])

    examples: list[ARCExample] = []
    for item in train:
        inp = np.array(item["input"], dtype=np.int64)
        out = np.array(item["output"], dtype=np.int64)
        examples.append(ARCExample(input=inp, output=out))
    return examples


def solve_task(
    task_json_path: Path,
    output_dir: Path,
    task_id: str,
    epochs: int = 1000,
) -> ExportResult | None:
    try:
        task_json_path = Path(task_json_path)
        output_dir = Path(output_dir)

        examples = load_task_examples(task_json_path)
        tto = solve_with_search(examples, epochs=epochs, lr=1e-2)
        if tto is None:
            return None

        onnx_path = export_to_onnx(tto.model, output_dir / f"{task_id}.onnx")
        is_valid, errors = validate_onnx_file(onnx_path)

        num_params = sum(p.numel() for p in tto.model.parameters())
        file_bytes = onnx_path.stat().st_size
        cost = num_params + file_bytes
        score = max(1.0, 25.0 - math.log(cost)) if cost > 0 else 1.0

        return ExportResult(
            onnx_path=onnx_path,
            arch_name=tto.arch_name,
            num_params=int(num_params),
            file_bytes=int(file_bytes),
            score=score,
            is_valid=bool(is_valid),
            errors=list(errors),
        )
    except Exception:  # noqa: BLE001
        return None


# =========================
# CLI
# =========================


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Solve ARC (train) with TTO and export to static ONNX")
    parser.add_argument("task_json", type=str, help="Path to ARC task JSON")
    parser.add_argument("--output-dir", type=str, default="outputs/", help="Directory to write ONNX")
    parser.add_argument("--task-id", type=str, default="task000", help="Output ONNX filename prefix")
    parser.add_argument("--epochs", type=int, default=1000, help="TTO epochs")

    args = parser.parse_args()

    res = solve_task(Path(args.task_json), Path(args.output_dir), args.task_id, epochs=int(args.epochs))
    print(res)
