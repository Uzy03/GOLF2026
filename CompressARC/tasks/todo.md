# NeuroGolf 2026 — タスクリスト

## 完了
- [x] CompressARC リポジトリクローン
- [x] pyproject.toml + .python-version 作成
- [x] uv sync 完了 (torch 2.11, onnx, onnxruntime, kagglehub 等)
- [x] tasks/todo.md + outputs/ ディレクトリ作成
- [x] neurogolf_scorer.py (Copilot A) — ONNX検証・スコア計算
- [x] download_competition_data.py (Copilot A) — Kaggleデータダウンロード
- [x] onnx_export.py (Copilot gpt-5.2) — TTO + ONNX export
  - ✅ 動作確認: ColorRemapModel, Conv3x3等のモデルがimport可能
  - ✅ 0d3d703e タスク: lr=0.1, epochs=2000 で正答

## 進行中
- [ ] onnx_export.py の lr バグ修正 (Copilot レート制限中)
  - run_tto と solve_with_search のデフォルト lr: 1e-2 → 0.1 に変更
  - solve_task の score 計算: train_acc → max(1.0, 25.0 - ln(cost)) に変更

## 次のステップ
- [ ] run_all_onnx.py 作成 (Copilot A) — 400タスク並列実行
- [ ] solve_task_onnx.py 作成 (Copilot A) — シングルタスクCLI (run_all用)
- [ ] Kaggle競合データダウンロード確認 (GPUサーバにデプロイ後)

## メモ
- デプロイ先: リモートSSH GPUサーバ (Linux)
- uv で環境管理 (`uv sync` → `uv run python script.py`)
- Kaggle competition: neurogolf-2026
- スコア = max(1, 25 - ln(params + file_bytes))
- ColorRemapModel (100 params) が最軽量。色変換タスクに有効。
- 0d3d703e (color remap task) は ColorRemapModel で解ける (lr=0.1, epochs=2000)
