# CLAUDE.md - Discord Event Notifier (実用版)

## 🔥 最重要原則

### エラー→修正→成功→文書化の絶対法則
1. **エラーが発生する** → 何かが間違っている
2. **修正を試行する** → 様々な方法を試す
3. **成功する** → 正しい方法が見つかる
4. **その瞬間**: **成功した方法が「正しいやり方」である**
5. **必須**: エラー解決した瞬間、必ずCLAUDE.mdに記録する

## 🚨 PYTHON実行コマンド強制事項

### ❌ 絶対使用禁止
```bash
python3 configure_hooks.py                    # ← 設計違反
python3 -m mypy src/                          # ← 設計違反  
```

### ✅ 必須実行形式
```bash
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python configure_hooks.py
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python -m mypy src/
```

## 📋 実装前必須チェックリスト

### STEP 0: Python環境確認（最優先）
```bash
# 必須: Python 3.14確認
uv run --python 3.14 python --version
# 期待結果: Python 3.14.x or higher ONLY

# 機能確認
uv run --python 3.14 python -c "from typing import ReadOnly, TypeIs; import os; print(f'ReadOnly: OK, TypeIs: OK, CPU: {os.process_cpu_count()}')"
```

### STEP 1: セッション状況把握
```bash
# Auto-compactセッションでは必須
@projects/claude-code-event-notifier-bugfix/CLAUDE.md
ls 2025-*-investigation-*.md | head -3
```

### タイムスタンプ取得（手動入力絶対禁止）
```bash
date +"%Y-%m-%d-%H-%M-%S"
```

## 🔧 主要コマンド集

### Discord Notifier基本操作
```bash
# Hook設定/再設定
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python configure_hooks.py

# Hook削除
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python configure_hooks.py --remove

# 完全統合テスト（最重要）
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python configure_hooks.py --validate-end-to-end

# 設定ホットリロード
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python configure_hooks.py --reload
```

### デバッグ・検証ツール
```bash
# Discord API基本確認
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python utils/check_discord_access.py

# 高度Discord API検証
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python src/utils/discord_api_validator.py

# ログ確認
tail -f ~/.claude/hooks/logs/discord_notifier_*.log
```

## ⚙️ Discord設定（重要）

### 設定ファイル場所
`~/.claude/hooks/.env.discord`

### 基本設定例
```bash
# 必須: 接続設定
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123456789/abcdef

# イベントフィルタリング
DISCORD_ENABLED_EVENTS=PreToolUse,PostToolUse,Notification,Stop
DISCORD_DISABLED_TOOLS=Read,Edit,TodoWrite,Grep

# 高度設定
DISCORD_USE_THREADS=true
DISCORD_DEBUG=1
```

### よく使う設定パターン
```bash
# 開発モード（ファイル操作除外）
DISCORD_DISABLED_TOOLS=Read,Write,Edit,MultiEdit,LS,TodoWrite

# 必要最小限
DISCORD_ENABLED_EVENTS=Notification,Stop

# 実行専用モード
DISCORD_ENABLED_EVENTS=PreToolUse,PostToolUse
```

## 🛠️ トラブルシューティング

### 問題発生時の診断手順
```bash
# 1. 基本動作確認
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python configure_hooks.py --validate-end-to-end

# 2. 個別確認
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python configure_hooks.py --reload
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python utils/check_discord_access.py

# 3. Hook単体テスト
echo '{"session_id":"test","tool_name":"Test"}' | CLAUDE_HOOK_EVENT=PreToolUse cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python src/main.py
```

### よくあるエラーと対処

**ReadOnlyインポートエラー**
```bash
# Python 3.14環境確認
uv run --python 3.14 python -c "from typing import ReadOnly; print('ReadOnly: OK')"
```

**Hook動作しない**
```bash
# 設定確認
ls -la ~/.claude/hooks/.env.discord
grep -A 5 "main.py" ~/.claude/settings.json
```

**環境汚染エラー**
```bash
# 正しい実行（コンテキスト独立）
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python configure_hooks.py
```

## 🎯 Subagent活用戦略

### 大規模調査の効率化
1. **ファイル発見** → 関連ファイル網羅
2. **技術分析** → 実装詳細分析  
3. **使用方法調査** → 実際コマンド抽出
4. **統合レビュー** → 最終品質確認

### 委譲テンプレート
```markdown
## [専門分野]への委譲

**指示内容**: [具体的タスク]
**成果物**: [ファイル名・形式]
**制約条件**: [技術制約・時間制約]
```

## 📊 成功指標

### 実装完了チェック
- [ ] `src/main.py`構文チェック通過
- [ ] Hook設定がmain.py指定
- [ ] Discord通知正常送信
- [ ] Claude Code再起動後動作

### 日常運用チェック
- [ ] End-to-End validation成功
- [ ] 設定ホットリロード動作
- [ ] エラーログに問題なし

## 🔄 定期保守タスク

```bash
# 毎日: 健全性確認
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python configure_hooks.py --validate-end-to-end

# 週次: 設定最適化
echo 'DISCORD_DISABLED_TOOLS=Read,Edit' >> ~/.claude/hooks/.env.discord

# 問題時: 完全リセット
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python configure_hooks.py --remove
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python configure_hooks.py
```

---

**プロジェクト基本情報**
- **作業ディレクトリ**: `/home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix/`
- **実装状況**: ✅ 新アーキテクチャ完全実装・正常動作中
- **Python要件**: 3.14+ 必須（typing_extensions使用禁止）
- **エントリーポイント**: `src/main.py`