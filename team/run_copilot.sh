#!/bin/bash
# run_copilot.sh — Copilot をバックグラウンドで実行するスクリプト
# delegate.sh からサブプロセスとして呼ばれる（新Terminal不要）

PROJECT_DIR="$1"
MODEL="$2"   # オプション: モデルID（省略時はcopilotのデフォルト）

if [ -z "$PROJECT_DIR" ]; then
  echo "ERROR: PROJECT_DIR が指定されていません"
  exit 1
fi

TASK_FILE="$PROJECT_DIR/team/task.md"
REPORT_FILE="$PROJECT_DIR/team/report.md"

cd "$PROJECT_DIR"

# copilot バイナリを探す
COPILOT_BIN=$(find "$HOME/.local/share/gh/copilot/copilot" /usr/local/bin/copilot /opt/homebrew/bin/copilot 2>/dev/null | head -1)
if [ -z "$COPILOT_BIN" ]; then
  echo "ERROR: copilot binary not found" >&2
  exit 1
fi

# モデルフラグを組み立て
MODEL_FLAG=()
if [ -n "$MODEL" ]; then
  MODEL_FLAG=(--model "$MODEL")
fi

# copilot コマンドで直接実行（TTY不要）
GH_OUTPUT=$("$COPILOT_BIN" \
  "${MODEL_FLAG[@]}" \
  --allow-all \
  --autopilot \
  --no-ask-user \
  --no-color \
  -p "$(cat "$TASK_FILE")" 2>&1)
EXIT_CODE=$?

echo "$GH_OUTPUT"
echo "" >> "$REPORT_FILE"

if [ $EXIT_CODE -eq 0 ]; then
  echo "✅ Copilot 実装完了 ($(date '+%Y-%m-%d %H:%M:%S'))" >> "$REPORT_FILE"
elif echo "$GH_OUTPUT" | grep -qiE "rate.?limit|too many requests|quota|429|rate_limit|exceeded"; then
  echo "🚫 Copilot レート制限 ($(date '+%Y-%m-%d %H:%M:%S'))" >> "$REPORT_FILE"
  exit 2
else
  echo "❌ Copilot 実行失敗 (exit ${EXIT_CODE}) ($(date '+%Y-%m-%d %H:%M:%S'))" >> "$REPORT_FILE"
  exit "$EXIT_CODE"
fi
