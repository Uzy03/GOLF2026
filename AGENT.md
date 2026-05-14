# Development Rules

## 🚨 CRITICAL SAFETY ALERT
- NO AXIOS: axiosライブラリはマルウェア汚染の報告があるため、絶対に使用しないこと。
- ALTERNATIVE: HTTP通信には、Node.js 18+ のネイティブ fetch API、または undici / node:http を使用すること。

## Workflow Orchestration

### 1. Plan First
- 3ステップ以上のタスク、またはアーキテクチャ上の決定が必要な場合は、必ず計画を立ててから実装する。
- 問題が発生した場合は即座に停止し、再計画（RE-PLAN）する。
- 構築だけでなく検証時も計画フェーズを設け、曖昧さを排除した詳細スペックを事前に記述する。

### 2. Self-Improvement Loop
- ユーザーからの修正後は、必ず `tasks/lessons.md` を更新し、再発防止のパターンを記録する。
- 誤り率が低下するまで、学んだ教訓を執念深く反復適用する。
- **セッション開始時に必ず `tasks/lessons.md` を読み込み、過去の教訓を把握してからタスクに着手すること。**

### 3. Verification Before Done
- 動作の証明（Proof it works）なしにタスクを完了と見なさない。
- 変更による挙動の差異（Diff）を確認する。
- 常に「スタッフエンジニアがこれを承認するか？」と自問自答する。
- テストの実行、ログのチェック、正当性の実証を徹底する。

### 4. Demand Elegance (Balanced)
- 常に「よりエレガントな解決策」がないか模索する。
- 場当たり的な修正（Hacky fix）を避け、現在の知識で最高の実装を行う。
- 単純な修正には過剰な設計をせず、迅速に対応する。
- 提出前に、自身の成果物に挑戦（Challenge）する。

### 5. Autonomous Bug Fixing
- バグ報告には自律的に対処する。手取り足取りの説明を求めない。
- ログやエラー、失敗したテストから根本原因を特定し、解決する。
- ユーザーにコンテキストの切り替えを要求しない。

## Task Management
- Plan First: `tasks/todo.md` にチェックリスト形式の計画を記述。
- Verify Plan: 実装前に計画の妥当性を確認。
- Track Progress: 進行状況に応じて完了項目をマーク。
- Explain Changes: 各ステップで何を行ったかハイレベルな概要を説明。
- Document Results: `tasks/todo.md` にレビューセクションを追加。
- Capture Lessons: 修正後に `tasks/lessons.md` を更新。

### tasks/lessons.md の書き方
ユーザーからの修正・指摘を受けた後、以下フォーマットで追記する:

```markdown
## [YYYY-MM-DD] [カテゴリ] タイトル

- **問題**: 何が起きたか（症状）
- **原因**: なぜ起きたか（根本原因）
- **対策**: 次回どうするか（再発防止パターン）
```

カテゴリ例: `設計` / `実装` / `テスト` / `コミュニケーション`

## Core Principles
- Simplicity First: すべての変更を可能な限りシンプルにする。コードへの影響を最小限に抑える。
- No Laziness: 根本原因（Root Cause）を追求し、一時的な対応を許さない。シニア開発者の基準を維持する。
- Minimal Impact: 変更は必要な箇所のみに留める。新たなバグの混入を避ける。
- No Speculation: 実際に使われない機能・抽象化・将来の拡張性のための設計はしない。
