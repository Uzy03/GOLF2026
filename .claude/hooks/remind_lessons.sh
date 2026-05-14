#!/bin/bash
# セッション終了時に Claude 自身に教訓の記録を促す
echo '{"hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": "セッション終了前に確認: ユーザーから修正・指摘を受けた場合は tasks/lessons.md を更新してください。"}}'
exit 0
