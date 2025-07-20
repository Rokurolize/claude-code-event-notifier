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
- **Discord通知最適化**: メッセージ部分でDiscordネイティブmarkdown(**太字**、*斜体*)使用、embed部分でコードブロック維持

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

### シンプルアーキテクチャ（約900行、7ファイル）
```
src/simple/
├── event_types.py       # 型定義
├── config.py            # 設定読み込み
├── discord_client.py    # Discord送信（スレッド機能付き）
├── handlers.py          # イベントハンドラー
├── transcript_reader.py # トランスクリプト解析
├── task_tracker.py      # タスク追跡システム (NEW)
└── main.py              # エントリーポイント
```

**特徴**: Pure Python 3.13+、Zero Dependencies、89%コード削減（8000→900行）

**新機能** (2025-07-20実装):
- Taskツール実行時に自動でDiscordスレッド作成
- セッションベースのタスク追跡システム
- `DISCORD_THREAD_FOR_TASK=1`で有効化

**既知の問題** (2025-07-21判明):
- 並列タスク実行時のマッチング失敗（PostToolUseで結果投稿不可）
- 原因: Claude Code Hookシステムの制約

---

## 🔧 必須コマンド

```bash
# セットアップ & 検証
uv run --python 3.13 python configure_hooks.py --validate-end-to-end

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
uv run --python 3.13 python -c "from typing import ReadOnly, TypeIs; print('OK')"
```

---

## 🔍 Discord API開発ツール

**統合されたDiscord APIツールセット**: `tools/discord_api/` ディレクトリに整理

### 利用可能なツール

1. **discord_api_basic_checker.py** - 基本アクセス・権限チェッカー
2. **discord_api_advanced_validator.py** - 高度な検証・統計分析
3. **discord_api_message_fetcher.py** - メッセージ取得・構造分析
4. **discord_api_test_runner.py** - 包括的テストスイート

詳細は各ツールの `--help` を参照：

```bash
cd tools/discord_api
python discord_api_{basic_checker,advanced_validator,message_fetcher,test_runner}.py --help
```

---

**状況**: シンプルアーキテクチャ（900行）稼働中  
**コード削減**: 8,000行→900行（89%削減）  
**エントリーポイント**: `src/simple/main.py`

---

## 📄 2025-07-21 実装ドキュメント

- **@docs/2025-07-21-03-04-00-task-thread-implementation-report.md** - タスクスレッド実装レポート
- **@docs/2025-07-21-03-07-00-discord-notification-flow-analysis.md** - 通知フロー分析
- **@docs/2025-07-21-03-09-00-json-event-specification.md** - JSON仕様と改善提案
