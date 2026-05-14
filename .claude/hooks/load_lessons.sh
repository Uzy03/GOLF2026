#!/bin/bash
# セッション開始時に tasks/lessons.md をモデルのコンテキストに注入する
if [ -f "tasks/lessons.md" ]; then
  python3 -c "
import json
content = open('tasks/lessons.md').read()
print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'SessionStart',
        'additionalContext': '=== 過去の教訓 (tasks/lessons.md) ===\n' + content
    }
}))
"
fi
exit 0
