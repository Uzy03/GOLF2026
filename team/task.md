# 🤖 Copilot タスク指示

/Users/udy03/Desktop/Development/2026/GOLF/CompressARC/onnx_export.py の `export_to_onnx` 関数を修正してください。

## 問題

現在の実装に `os.environ.setdefault("TORCH_LOGS", "")` という行がある。
これが TORCH_LOGS 環境変数を空文字でセットしてしまい、
その結果 torch._logging が「TORCH_LOGS env var を使うので set_logs() 呼び出しを無視する」と判断し、
以下の警告を出す:

```
W0514 14:23:52.176000 89880 torch/_logging/_internal.py:488]
Using TORCH_LOGS environment variable for log settings, ignoring call to set_logs
```

## 修正内容

`export_to_onnx` 関数内の以下の**2点**を変更する:

**変更1: `os.environ.setdefault("TORCH_LOGS", "")` を削除する**

削除対象:
```python
    os.environ.setdefault("TORCH_LOGS", "")
```

この行を完全に削除する（`import os` も不要になるので一緒に削除する）。

**変更2: `redirect_stdout` を `redirect_stderr` も含むように拡張する**

現在:
```python
    _sink = io.StringIO()
    with warnings.catch_warnings(), contextlib.redirect_stdout(_sink):
```

変更後:
```python
    _sink = io.StringIO()
    with warnings.catch_warnings(), contextlib.redirect_stdout(_sink), contextlib.redirect_stderr(_sink):
```

これにより:
- stdout へ出力される `[torch.onnx] Obtain model graph...` 等を抑制
- stderr へ出力される `W0514...` glog 警告も抑制
- tqdm は自分自身の fd を持つので影響なし

この関数1つだけ修正してください。他は変更不要。

---

## 完了条件
- 指示されたファイルを修正すること
- 実装後は必ず team/report.md に成果物一覧と注意事項を記載すること
