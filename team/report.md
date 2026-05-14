# 修正レポート: torch.onnx 冗長ログ抑制

## 成果物

### 修正ファイル
- **`CompressARC/onnx_export.py`** - `export_to_onnx` 関数 (Lines 296-327)

## 修正内容

修正前の `torch.onnx.export()` 呼び出しに以下のログ抑制メカニズムを追加:

### 3つのログ抑制メカニズム

1. **ロギングレベル調整**
   ```python
   logging.getLogger("torch.onnx").setLevel(logging.ERROR)
   ```
   - `torch.onnx` ロガーの出力を ERROR 以上のみに限定

2. **環境変数設定**
   ```python
   os.environ.setdefault("TORCH_LOGS", "")
   ```
   - `TORCH_LOGS` を空文字に設定して torch の詳細ログを抑制

3. **警告フィルタリング**
   ```python
   with warnings.catch_warnings():
       warnings.filterwarnings("ignore", category=UserWarning)
       warnings.filterwarnings("ignore", category=FutureWarning)
       torch.onnx.export(...)
   ```
   - UserWarning と FutureWarning を局所的に無視

## 影響範囲

- **修正関数**: `export_to_onnx` のみ
- **他の関数**: 変更なし
- **機能動作**: 完全に互換性あり（ロジック変更なし）

## 品質保証

✅ **構文チェック**: Python コンパイルエラーなし
✅ **スコープ**: 指定されたファイルのみ修正
✅ **後方互換性**: API・動作は同じ

## 注意事項

- 警告フィルタリングは `torch.onnx.export()` 呼び出し範囲内に局所化（他の処理に影響しない）
- `os.environ.setdefault()` を使用しているため、既に `TORCH_LOGS` が設定されている場合は上書きしない
- logging レベルは global に設定されるため、複数スレッド環境では注意が必要

✅ Copilot 実装完了 (2026-05-14 14:13:59)

---

# 追加修正レポート: onnxscript ログ抑制

## 成果物一覧

- **`/Users/udy03/Desktop/Development/2026/GOLF/CompressARC/onnx_export.py`**
  - `export_to_onnx` 内に `logging.getLogger("onnxscript").setLevel(logging.ERROR)` を1行追加

## 注意事項

- 変更は指定どおり1行追加のみで、既存ロジックや他の処理には影響しない
- `onnxscript` ロガーのレベル変更はプロセス内で有効なため、同一プロセス内の他処理にも適用される

✅ Copilot 実装完了 (2026-05-14 14:20:46)

---

# 追加修正レポート: torch._logging 経由の ONNX verbose 抑制

## 成果物一覧

- **`/Users/udy03/Desktop/Development/2026/GOLF/CompressARC/onnx_export.py`**
  - `export_to_onnx` の `torch.onnx.export()` 呼び出し部分を指定どおり置換
  - `io` / `contextlib` の import を関数内 import 群へ追加
  - `torch._logging.set_logs(onnx=logging.ERROR)` のベストエフォート設定を追加
  - `contextlib.redirect_stdout(io.StringIO())` で `[torch.onnx]` stdout 出力を捕捉

## 注意事項

- `torch._logging` は PyTorch バージョン差で利用不可の場合があるため、`try/except` で安全にフォールバック
- `redirect_stdout` は `export_to_onnx` 実行区間のみ有効で、`stderr` 出力（例: tqdm）は抑制しない
- 修正対象は `export_to_onnx` 関数のみで、他の関数ロジックには変更なし

✅ Copilot 実装完了 (2026-05-14 14:22:27)

✅ Copilot 実装完了 (2026-05-14 14:23:00)

---

# 追加修正レポート: TORCH_LOGS 警告抑制の調整

## 成果物一覧

- **`/Users/udy03/Desktop/Development/2026/GOLF/CompressARC/onnx_export.py`**
  - `export_to_onnx` 内の `os.environ.setdefault("TORCH_LOGS", "")` を削除
  - 関数内 `import os` を削除
  - `with warnings.catch_warnings(), contextlib.redirect_stdout(_sink):` を  
    `with warnings.catch_warnings(), contextlib.redirect_stdout(_sink), contextlib.redirect_stderr(_sink):` に変更

## 注意事項

- `TORCH_LOGS` を空文字で設定しないため、`torch._logging` の `set_logs()` が環境変数設定により無視される警告を回避できる
- `stdout` と `stderr` の両方を局所的に `StringIO` へリダイレクトするため、ONNX export 時の `[torch.onnx]` 出力と glog 警告を同時に抑制する
- 修正対象は `export_to_onnx` 関数のみで、他の関数・処理フローには変更なし

✅ Copilot 実装完了 (2026-05-14 14:25:03)

✅ Copilot 実装完了 (2026-05-14 14:25:35)
