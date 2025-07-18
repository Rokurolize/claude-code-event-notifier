# CLAUDE.md - Discord Event Notifier (効率版)

## 🔥 最重要原則：エラー→修正→成功→文書化の絶対法則

**エラーが発生した瞬間、解決後に必ずこのファイルに記録せよ。**
同じエラーを繰り返すことは、学習能力の完全放棄である。

成功体験の記録項目：
1. エラー内容と失敗した方法
2. 成功した正確な方法
3. 成功理由と再発防止策

## ⚡ 絶対実行コマンド：Pure Python 3.14+設計の維持

**禁止**: `python3` (システム依存・汚染リスク)
**必須**: `cd project_root && uv run --python 3.14 python`

理由：ReadOnly, TypeIs, process_cpu_count()の完全サポート、環境汚染防止

## 🚨 現在の実装状況（2025-07-17）

**✅ 完了**: 新アーキテクチャ（main.py）完全実装・正常動作中
**✅ 完了**: Discord通知スパム問題解決・Hook重複除去
**✅ 完了**: Python 3.14移行・環境汚染危機解決
**✅ 完了**: Stop イベント作業ディレクトリ表示機能

**実行中**: src/main.py をエントリーポイントとする新アーキテクチャ

## 💀 絶対禁止事項

**typing_extensions追加は設計への冒涜**
```python
# ❌ 絶対禁止
from typing_extensions import ReadOnly
```

Pure Python 3.14+の純粋性を汚すフォールバック・互換性コードは一切作成しない。

## 🔧 必須チェックリスト

### セッション開始時
```bash
# Python 3.14確認（失敗時は作業停止）
uv run --python 3.14 python --version

# ReadOnly機能確認
uv run --python 3.14 python -c "from typing import ReadOnly; print('OK')"

# 現在状況把握
@projects/claude-code-event-notifier-bugfix/CLAUDE.md
```

### タイムスタンプ取得（手動入力絶対禁止）
```bash
date +"%Y-%m-%d-%H-%M-%S"
```

## 🎯 主要コマンド

```bash
# Hook設定・テスト
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python configure_hooks.py

# 完全統合テスト
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python configure_hooks.py --validate-end-to-end

# Hook削除
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python configure_hooks.py --remove
```

## 📊 Discord設定

**設定ファイル**: `~/.claude/hooks/.env.discord`

```bash
# 必須
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123456789/abcdef

# フィルタリング例
DISCORD_DISABLED_TOOLS=Read,Edit,TodoWrite,Grep  # 開発時ノイズ削減
DISCORD_ENABLED_EVENTS=PreToolUse,PostToolUse,Stop  # 重要イベントのみ

# 高度設定
DISCORD_USE_THREADS=true
DISCORD_DEBUG=1  # トラブルシューティング時
```

## 🔍 トラブルシューティング

### よくあるエラーと対処法

**ReadOnlyインポートエラー**
- 原因：Python 3.12以下の環境
- 対処：Python 3.14環境確認、uv run強制実行

**Hook動作しない**
```bash
# 設定確認
ls -la ~/.claude/hooks/.env.discord
grep -A 3 "main.py" ~/.claude/settings.json

# 再設定
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python configure_hooks.py --remove
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python configure_hooks.py
```

## 📋 設計哲学（核心）

**Pure Python 3.14+は妥協なき美の追求**
外部依存関係ゼロ、typing_extensionsフォールバック拒絶、ReadOnly/TypeIs/process_cpu_count()の完全活用による純粋性維持。

## 🚀 アーキテクチャ概要

```
src/main.py           # エントリーポイント（実行中）
src/core/config.py    # 設定管理・ホットリロード
src/handlers/         # Discord送信・スレッド管理
src/formatters/       # イベント・ツール別フォーマッタ
```

**Hook統合**: ~/.claude/settings.json で main.py 指定済み

## 📚 重要ファイル

- `current-work-context.md` - 現在作業状況（必須更新）
- `docs/investigation-index.md` - 調査結果一覧
- `~/.claude/hooks/logs/` - ログ・JSON生データ

## 💡 過去の重大教訓

**2025年7月災害**: 新アーキテクチャ99%完成でも統合なしでは無価値
**解決**: main.py実装でHook統合完了

**スパム問題**: Hook重複設定による10回連続送信
**解決**: should_keep_hook関数修正、重複削除

**環境汚染**: typing_extensions依存による設計破綻
**解決**: Pure Python 3.14+完全移行

## ✅ 成功確認基準

- [ ] `uv run --python 3.14 python src/main.py` が正常実行
- [ ] configure_hooks.py がエラーなく完了
- [ ] Discord通知が実際に送信される
- [ ] Claude Code再起動後も正常動作

## 🔄 セッション終了時更新事項

- [ ] 実装状況の現実を記録
- [ ] 次回具体的アクションを明記
- [ ] 最終更新日時を現在時刻に変更
- [ ] git commitで変更を記録

---

**プロジェクト状況**: 新アーキテクチャ完全実装・正常動作中
**最終更新**: 2025-07-17-03-54-59
**次の作業**: 他イベントタイプへの作業ディレクトリ表示機能拡張検討