#!/bin/bash
# enforce_delegation.sh
# コードファイルへの直接書き込みをブロックし、Copilotへの委任を強制する。
# 許可: .json / .yaml / .yml / .md / .toml / .sh / .txt / .gitignore 等の設定・ドキュメント類
# ブロック: .cs / .ts / .tsx / .js / .jsx / .py 等のコードファイル

INPUT=$(cat)
TOOL=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null)
FILE=$(echo "$INPUT"  | python3 -c "import sys,json; d=json.load(sys.stdin).get('tool_input',{}); print(d.get('file_path',''))" 2>/dev/null)

# ブロック対象の拡張子: cs / ts / tsx / js / jsx / py
if [[ "$FILE" =~ \.(cs|ts|tsx|js|jsx|py)$ ]]; then
    echo "" >&2
    echo "╔══════════════════════════════════════════════════════════╗" >&2
    echo "║  🚫  DELEGATION REQUIRED — 直接実装は禁止               ║" >&2
    echo "╠══════════════════════════════════════════════════════════╣" >&2
    echo "║  対象ファイル: $FILE" >&2
    echo "║                                                          ║" >&2
    echo "║  CLAUDE.md チームワークフロー違反:                       ║" >&2
    echo "║  コードファイルは Copilot（部下）が実装します。          ║" >&2
    echo "║                                                          ║" >&2
    echo "║  ✅ 正しい手順:                                          ║" >&2
    echo "║     bash team/delegate.sh \"実装仕様をここに書く\"         ║" >&2
    echo "╚══════════════════════════════════════════════════════════╝" >&2
    echo "" >&2
    exit 2
fi

exit 0
