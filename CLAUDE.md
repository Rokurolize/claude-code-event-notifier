# CLAUDE.md - Discord Event Notifier

シンプルアーキテクチャ（555行）のDiscord通知システム設定ガイド。

## 📚 主要ドキュメント

- **@docs/simple-architecture-complete-guide.md** - 技術仕様
- **@docs/troubleshooting.md** - トラブルシューティング
- **@~/.claude/discord-event-notifier-personal-config.md** - 個人設定

## ⚡ エラー文書化の鉄則

**エラー解決後は即座にCLAUDE.mdに記録する。これを怠る = 同じエラーの無限ループ。**

### 📝 重要な教訓

- **モジュール名衝突**: `src/types.py`→`src/simple/event_types.py` (標準ライブラリ回避)
- **Hook環境隔離**: `uv run --python 3.13 --no-project` (依存関係干渉防止)
- **タイムスタンプ**: `date +"%Y-%m-%d-%H-%M-%S"` (手動入力禁止)

---

## ⚠️ Python実行規則

**必須**: `cd project_root && uv run --python 3.13 python script.py`  
**Hook時**: `uv run --python 3.13 --no-project python /path/to/script.py`  
**禁止**: `python3` の直接使用

### 設計原則
- **Pure Python 3.13+**: 標準ライブラリのみ、typing_extensions禁止
- **Fail Silent**: Claude Codeをブロックしない
- **Type Safety**: TypedDict、TypeIs使用

---

## 🚨 現在の実装状況

### シンプルアーキテクチャ（555行、5ファイル）
```
src/simple/
├── event_types.py    # 型定義（94行）
├── config.py         # 設定読み込み（117行）
├── discord_client.py # Discord送信（71行）
├── handlers.py       # イベントハンドラー（190行）
└── main.py          # エントリーポイント（83行）
```

**特徴**: Pure Python 3.13+、Zero Dependencies、93%コード削減（8000→555行）

---

## 🔧 必須コマンド

```bash
# セットアップ
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.13 python configure_hooks_simple.py

# 検証
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.13 python configure_hooks.py --validate-end-to-end

# ログ確認
tail -f ~/.claude/hooks/logs/simple_notifier_*.log
```

---

## 📁 設定ファイル

- **@/home/ubuntu/.claude/.env** - Discord通知設定
- **@/home/ubuntu/.claude/settings.json** - Hook設定

---

## ⚠️ セッション開始時チェック

```bash
# アーキテクチャ確認  
ls src/simple/*.py

# Python 3.13+確認
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.13 python -c "from typing import ReadOnly, TypeIs; print('OK')"
```

---

---

**状況**: シンプルアーキテクチャ（555行）稼働中  
**コード削減**: 8,000行→555行（93%削減）  
**エントリーポイント**: `src/simple/main.py`

*"Simplicity is the ultimate sophistication."*
