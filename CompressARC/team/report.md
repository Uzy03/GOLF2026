# NeuroGolf 2026 実装レポート

## 成果物一覧

### 1. neurogolf_scorer.py
**ファイルパス**: `/Users/udy03/Desktop/Development/2026/GOLF/CompressARC/neurogolf_scorer.py`

NeuroGolf 2026 Kaggleコンペのスコアリングモジュール。ONNXモデルに対して以下の機能を提供します：

#### 主要機能
- **パラメータカウント** (`count_onnx_params`): initializer tensorの全要素数を計算
- **禁止Op検出** (`check_forbidden_ops`): Loop, Scan, NonZero, Unique, Script, Function の検出
- **ノード収集** (`_collect_nodes`): If/Loop等のサブグラフを含む全ノードを再帰的に収集
- **モデル検証** (`validate_onnx`): 5段階の検証（モデルチェック、禁止Op、静的Shape、ファイルサイズ、推論テスト）
- **コスト計算** (`compute_cost`): Cost = パラメータ数 + ファイルサイズ(bytes)
- **スコア計算** (`compute_score`): Score = max(1.0, 25.0 - ln(Cost))
- **統合スコアリング** (`score_onnx_file`): ScoringResultデータクラスで全情報を返却

#### 定数
- `FORBIDDEN_OPS`: 禁止演算子のfrozenset
- `MAX_FILE_BYTES`: 1,509,949 bytes (1.44 MB)

#### 使用方法
```bash
python3 neurogolf_scorer.py <path/to/model.onnx>
```

### 2. download_competition_data.py
**ファイルパス**: `/Users/udy03/Desktop/Development/2026/GOLF/CompressARC/download_competition_data.py`

Kaggleコンペティション「neurogolf-2026」のデータダウンロードスクリプト。

#### 主要機能
- **データダウンロード** (`download_arc_data`): kagglehubを使用してコンペデータを取得
- **ファイルコピー** (`download_arc_data`): JSONファイルをDATASET_DIR/にコピー（重複は スキップ）
- **メイン処理** (`main`): ダウンロード実行と結果出力

#### 定数
- `COMPETITION`: 'neurogolf-2026'
- `DATASET_DIR`: スクリプトと同じディレクトリの 'dataset' フォルダ

#### 使用方法
```bash
python3 download_competition_data.py
```

## 実装の注意事項

### neurogolf_scorer.py
1. **ONNX検証のロバスト性**: エラーが発生してもtry-exceptでキャッチし、エラーメッセージをリストに記録する
2. **サブグラフ処理**: If や Loop ノード内のサブグラフも再帰的に検索し、禁止Opを検出
3. **Shape判定**: protobuf の repeated フィールド（`shape.dim`）には `HasField` を使わず、`WhichOneof('value')` で動的Shape検出。`dim_param` が設定されている場合は動的Shapeと判定
4. **推論テスト**: 入力形状 (1, 1, 30, 30) のint64ダミー入力で推論実行

### download_competition_data.py
1. **Kagglehub依存**: kagglehubライブラリが必要（pip install kagglehub）
2. **ディレクトリ自動作成**: DATASET_DIRが存在しない場合は自動作成
3. **上書き保護**: 既にコピー済みのファイルはスキップ（idempotent）
4. **JSON形式のみ**: rglob('*.json') で JSONファイルのみを対象とする

## 依存ライブラリ

```
onnx
onnxruntime
numpy
kagglehub
```

これらのライブラリは事前にインストール必須です。

## テスト方針
- **neurogolf_scorer.py**: ダミーのONNXモデルを作成して各関数の動作確認
- **download_competition_data.py**: Kaggle APIキー設定後にデータダウンロードテスト

---

### 3. onnx_export.py - デバイス自動選択機能
**ファイルパス**: `/Users/udy03/Desktop/Development/2026/GOLF/CompressARC/onnx_export.py`

#### 修正内容
既存の CPU 固定のデバイス処理を、CUDA・MPS・CPU を自動選択する汎用デバイスシステムに変更しました。

#### 実装詳細

**1. デバイス選択関数 `_get_device()` を追加（行 56-62）**
```python
def _get_device() -> torch.device:
    """利用可能な最良のデバイスを返す: CUDA > MPS > CPU"""
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")
```
- CUDA（GPU サーバ）> MPS（Mac）> CPU の優先順位で自動選択

**2. `run_tto` 関数の修正（行 196-207）**
- シグネチャに `device: torch.device | None = None` を追加
- `device` が `None` 時は `_get_device()` で自動選択
- モデルを指定デバイスに移動

**3. `solve_with_search` 関数の修正（行 274-285）**
- シグネチャに `device: torch.device | None = None` を追加
- `device` が `None` 時は `_get_device()` で自動選択
- `run_tto` 呼び出しに `device=device` を渡す

**4. `export_to_onnx` 関数の確認（行 300-301）**
- ONNX export は CPU のみ対応のため、既に `model.to(torch.device("cpu"))` が実装されているため変更不要

#### 動作環境への対応
- **GPU サーバ（CUDA対応）**: 自動的に CUDA デバイスを選択
- **Mac（M1/M2/M3等）**: 自動的に MPS（Metal Performance Shaders）を選択
- **CPU のみ環境**: CPU を使用

#### 使用例
```python
# デバイスを自動選択（推奨）
tto = solve_with_search(examples)

# 明示的にデバイスを指定
tto = solve_with_search(examples, device=torch.device("cuda"))
tto = solve_with_search(examples, device=torch.device("cpu"))
```

#### 注意事項
- `torch.backends.mps.is_available()` は PyTorch 2.x 以降で使用可能
- 既存の呼び出しコード（`device` 引数を省略）は完全に互換性を保持
- `grid_to_tensor()` の結果が `torch.int64` なので、デバイス移動時に自動的に正しく処理される

---

**実装日時**: 2026-05-14  
**実装者**: Copilot

---

### 4. submit.py - kaggle CLI バイナリ呼び出し修正
**ファイルパス**: `/Users/udy03/Desktop/Development/2026/GOLF/CompressARC/submit.py`

#### 修正内容
`kaggle_submit` 関数を修正し、`python -m kaggle` から直接 `kaggle` バイナリ呼び出しに変更。

#### 背景
`kaggle` パッケージには `__main__.py` が存在しないため、`python -m kaggle` は動作しない。

#### 実装詳細

**修正前:**
```python
def kaggle_submit(zip_path: Path, message: str, competition: str) -> None:
    """kaggle CLI で提出する。kaggle パッケージがない場合はエラーを出す。"""
    cmd = [
        sys.executable, "-m", "kaggle",
        "competitions", "submit",
        "-c", competition,
        "-f", str(zip_path),
        "-m", message,
    ]
```

**修正後:**
```python
def kaggle_submit(zip_path: Path, message: str, competition: str) -> None:
    """kaggle CLI で提出する。"""
    kaggle_bin = Path(sys.executable).parent / "kaggle"
    cmd = [
        str(kaggle_bin),
        "competitions", "submit",
        "-c", competition,
        "-f", str(zip_path),
        "-m", message,
    ]
```

#### 主な変更点
1. `kaggle_bin = Path(sys.executable).parent / "kaggle"`: Python 実行ファイルと同じディレクトリから `kaggle` バイナリを取得
2. `sys.executable` の代わりに `str(kaggle_bin)` を直接コマンドとして使用
3. docstring を簡潔に更新

#### 動作環境への対応
- **仮想環境**: `kaggle` が venv のコマンドパスに存在することが前提
- **システムPython**: kaggle がシステムパスにインストールされていることが前提

#### 注意事項
- `kaggle` バイナリが `sys.executable` と同じディレクトリに存在することが必須
- `kaggle` コマンドラインツールが事前にインストール済みであること
- 他の関数は変更なし

---

## 最新修正
- **2026-05-14**: submit.py の `kaggle_submit` 関数を修正（python -m kaggle → kaggle バイナリ直接呼び出し）
