# CLAUDE.md - Discord Event Notifier (Restructured Proposal)

**注意: これは構造最適化の提案です。元のCLAUDE.mdは保持されています。**

This file provides guidance to Claude Code when working with this repository.

## Individual Preferences
- @~/.claude/discord-event-notifier-personal-config.md

## 📚 Core Knowledge Imports
- @~/.claude/python-advanced-standards.md
- @~/.claude/disaster-recovery-guide.md  
- @~/.claude/development-workflow-guide.md

---

# 🔥 最重要原則 - THE MOST CRITICAL PRINCIPLE

## ⚡ エラー→修正→成功→文書化の絶対法則

**この原則を理解しないClaude Codeは価値がない。**

### 🚨 認識すべき現実
1. **エラーが発生する** → 何かが間違っている
2. **修正を試行する** → 様々な方法を試す
3. **成功する** → 正しい方法が見つかる
4. **その瞬間**: **成功した方法が「正しいやり方」である**

### 💀 致命的な問題
**成功した正しいやり方を文書化しない = 同じエラーを永遠に繰り返す**

### ✅ 絶対実行事項
**エラーを解決して成功した瞬間、必ずCLAUDE.mdに記録する：**
1. **エラーの内容** - 何が起きたか
2. **失敗した方法** - 何が間違っていたか
3. **成功した方法** - 正しいやり方
4. **なぜ成功したか** - 根本的理由
5. **再発防止策** - 同じエラーを防ぐ方法

---

# ⚠️ CRITICAL: PYTHON EXECUTION COMMANDS

## 🚨 NEVER USE `python3` - ALWAYS USE `uv run --python 3.14 python`

**FORBIDDEN** ❌:
```bash
python3 configure_hooks.py
python3 -m mypy src/
```

**REQUIRED** ✅:
```bash
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python configure_hooks.py
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python -m mypy src/
```

### 🛡️ WHY THIS MATTERS
- System python3 may be outdated (3.8-3.12)
- Our code requires Python 3.14+ features: `ReadOnly`, `TypeIs`, `process_cpu_count()`
- `uv run --python 3.14 python` guarantees correct environment

---

# 🚨 現在の実装状況（最終更新：2025-07-17-03-54-59）

## ✅ 新アーキテクチャ完全実装・正常動作中
- **実装**: 新アーキテクチャ（約8,000行）が正常動作中
- **Hook統合**: 全イベントタイプで新アーキテクチャを使用
- **設計**: Pure Python 3.14+設計原則維持、typing_extensions依存完全除去

## ✅ Stop イベント通知改善完了
- **機能**: 複数プロジェクト並行作業で「cd （ディレクトリのパス）」で即座に移動可能
- **実装**: `src/utils/path_utils.py` + `format_stop`関数拡張完了

---

# 🔧 Essential Commands

## Core Operations
```bash
# 基本テスト・設定
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python configure_hooks.py

# エンドツーエンド検証（推奨）
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python configure_hooks.py --validate-end-to-end

# 設定リロード
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python configure_hooks.py --reload
```

## Environment Verification
```bash
# Python環境確認（必須）
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python --version

# 機能確認
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python -c "from typing import ReadOnly, TypeIs; import os; print(f'ReadOnly: OK, TypeIs: OK, CPU: {os.process_cpu_count()}')"
```

---

# 📁 Project Information

- **作業ディレクトリ**: `/home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix/`
- **最終更新**: 2025-07-17-03-54-59
- **実装状況**: ✅ 新アーキテクチャ完全実装・Stop イベント通知改善完了・正常動作中
- **設計原則**: Pure Python 3.14+ maintained, zero external dependencies
- **次の作業**: 他のイベントタイプへの作業ディレクトリ表示機能の拡張検討

---

## 📋 構造最適化の提案

### 🎯 分離戦略
1. **メインCLAUDE.md** (この提案ファイル) - 日常的核心情報のみ (111行)
2. **python-advanced-standards.md** - Python 3.14+設計哲学・技術標準
3. **disaster-recovery-guide.md** - 災害記録・トラブルシューティング
4. **development-workflow-guide.md** - 開発プロセス・詳細仕様

### 📊 分離効果
- **コンテキスト効率**: 75%削減（3,100行→111行）
- **保守性向上**: 用途別モジュール化
- **参照効率**: 必要な情報に即座アクセス
- **Claude Codeインポート機能活用**: @パス指定で必要時参照

### 🔄 導入手順（提案）
1. 元のCLAUDE.mdをバックアップ保持
2. 提案構造をレビュー・承認
3. 段階的移行実施
4. 動作検証とフィードバック収集

---

*"In Pure Python 3.14+ We Trust"*
*— Proposed Restructured Architecture*