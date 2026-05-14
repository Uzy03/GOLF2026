#!/bin/bash
# delegate.sh — 上司（Claude）が部下（Copilot）にタスクを委任するスクリプト
# Usage: bash team/delegate.sh [--model <model_id>] "実装してほしい内容"
#
# モデルエイリアス:
#   A / haiku   → claude-haiku-4.5   (デフォルト: 定型コード・テスト・ログ解析)
#   B / mini    → gpt-4.1-mini       (単純作業: ファイル整形・README草案)
#   C / sonnet  → claude-sonnet-4.5  (複雑な実装・深いバグ修正)

set -e

# --model フラグのパース
MODEL_ARG=""
while [[ "$1" == --* ]]; do
  case "$1" in
    --model)
      MODEL_ARG="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

TASK="$1"
if [ -z "$TASK" ]; then
  echo "Usage: bash team/delegate.sh [--model A|B|C|<model_id>] \"task description\""
  exit 1
fi

# モデルエイリアスの解決（省略時はデフォルト: A = haiku）
resolve_model() {
  case "$1" in
    A|haiku|"")  echo "claude-haiku-4.5" ;;
    B|mini|free) echo "gpt-5-mini" ;;
    C|sonnet)    echo "claude-sonnet-4.5" ;;
    D|opus)      echo "claude-opus-4.5" ;;
    *)           echo "$1" ;;  # そのまま渡す（フルIDを直接指定）
  esac
}
MODEL=$(resolve_model "$MODEL_ARG")

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TASK_FILE="$PROJECT_DIR/team/task.md"
REPORT_FILE="$PROJECT_DIR/team/report.md"
RUNNER="$PROJECT_DIR/team/run_copilot.sh"
LOG_FILE="$PROJECT_DIR/team/copilot.log"

TIMEOUT=600        # 最大待機（秒）10分
FAST_INTERVAL=5    # 最初の60秒: 5秒ごとにチェック
FAST_DURATION=60
SLOW_INTERVAL=30   # 以降: 30秒ごと

# タスクファイルに書き込み
cat > "$TASK_FILE" << TASK_EOF
# 🤖 Copilot タスク指示

$TASK

---
## 完了条件
- 指示されたファイルを全て実装すること
- 実装後は必ず team/report.md に成果物一覧と注意事項を記載すること
TASK_EOF

# レポートをリセット
echo "(Copilot 作業中...)" > "$REPORT_FILE"

echo "📋 タスク書き込み完了: team/task.md"
echo "🤖 モデル: ${MODEL}"
echo "🚀 Copilot をバックグラウンドで起動します..."

# バックグラウンドで直接実行（新Terminalなし）
bash "$RUNNER" "$PROJECT_DIR" "$MODEL" > "$LOG_FILE" 2>&1 &
COPILOT_PID=$!

echo "⚙️  PID: ${COPILOT_PID} / ログ: team/copilot.log"
echo "⏳ 完了を待機中... (最大 ${TIMEOUT}秒)"
echo ""

check_report() {
  if grep -q "🚫 Copilot レート制限" "$REPORT_FILE" 2>/dev/null; then
    echo ""
    echo "🚫 Copilotのレート制限です。しばらく待ってから再試行してください。"
    echo "   (team/copilot.log で詳細を確認できます)"
    exit 2
  fi
  if grep -q "✅ Copilot 実装完了" "$REPORT_FILE" 2>/dev/null; then
    echo "✅ Copilot 完了! (${ELAPSED}秒)"
    echo ""
    echo "════════════════════════════════════"
    echo "  📊 team/report.md"
    echo "════════════════════════════════════"
    cat "$REPORT_FILE"
    echo "════════════════════════════════════"
    exit 0
  fi
  if grep -q "❌ Copilot 実行失敗" "$REPORT_FILE" 2>/dev/null; then
    echo "❌ Copilot が失敗しました"
    echo ""
    echo "════════════════════════════════════"
    echo "  📋 team/copilot.log (最後の20行)"
    echo "════════════════════════════════════"
    tail -20 "$LOG_FILE"
    echo "════════════════════════════════════"
    exit 1
  fi
}

ELAPSED=0
while [ "$ELAPSED" -lt "$TIMEOUT" ]; do
  if [ "$ELAPSED" -lt "$FAST_DURATION" ]; then
    sleep "$FAST_INTERVAL"
    ELAPSED=$((ELAPSED + FAST_INTERVAL))
  else
    sleep "$SLOW_INTERVAL"
    ELAPSED=$((ELAPSED + SLOW_INTERVAL))
  fi

  # プロセスが終了していたら即座に確認
  if ! kill -0 "$COPILOT_PID" 2>/dev/null; then
    check_report
    sleep 1
    check_report
    echo "❌ Copilot が予期せず終了しました"
    tail -10 "$LOG_FILE"
    exit 1
  fi

  check_report
  echo "  ... ${ELAPSED}秒経過"
done

kill "$COPILOT_PID" 2>/dev/null || true
echo ""
echo "⚠️  タイムアウト (${TIMEOUT}秒経過) — Copilot を強制終了しました"
echo "team/copilot.log と team/report.md を手動で確認してください。"
exit 1
