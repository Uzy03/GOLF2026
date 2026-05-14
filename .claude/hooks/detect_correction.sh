#!/bin/bash
# UserPromptSubmit hook: ユーザーの修正・指摘パターンを検知し、lessons.md 更新を促す

INPUT=$(cat)

MESSAGE=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
msg = data.get('prompt') or data.get('message') or data.get('user_message') or ''
print(msg)
" 2>/dev/null)

# 修正・指摘パターン、またはエラーログの貼り付けを検知
if echo "$MESSAGE" | grep -qiE "できてない|できていない|違う|ちがう|おかしい|なぜ|なんで|間違|ダメ|だめ|エラー|動かない|失敗|また同じ|まだ|やり直|直して|修正して|wrong|not working|doesn't work|failed|error|incorrect|broken|Error:|Exception|Traceback|TypeError|SyntaxError|ReferenceError|NullPointer|stack trace|at line [0-9]|undefined is not|cannot read|ENOENT|EACCES|segmentation fault|panic:|fatal error|警告|assertion failed"; then
  python3 -c "
import json
print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'UserPromptSubmit',
        'additionalContext': '⚠️ ユーザーから修正・指摘を受けています。問題を解決した後、必ず tasks/lessons.md に以下フォーマットで追記してください:\n## [YYYY-MM-DD] [カテゴリ] タイトル\n- **問題**: 何が起きたか（症状）\n- **原因**: なぜ起きたか（根本原因）\n- **対策**: 次回どうするか（再発防止パターン）'
    }
}))
"
fi

exit 0
