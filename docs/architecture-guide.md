# Discord Event Notifier - アーキテクチャガイド

このドキュメントでは、Discord Event Notifierの技術的アーキテクチャ、設定管理、検証システムについて説明します。

---

## 🏗️ Architecture Overview

### Core Structure

新アーキテクチャは完全にモジュール化されており、約8,000行のコードが以下の構造で整理されています：

```
src/
├── main.py               # 【実装済み・使用中】新アーキテクチャ用エントリーポイント (289行)
├── thread_storage.py       # SQLiteベースのスレッド永続化機能
├── type_guards.py          # TypeGuard/TypeIsを使用した実行時型検証
└── settings_types.py       # Claude Code設定用のTypedDict定義

src/core/                 # 新アーキテクチャ（完成済み、使用中）
├── config.py              # 設定の読み込みと検証機能 (1,153行)
├── constants.py           # 定数と設定のデフォルト値
├── exceptions.py          # カスタム例外階層
└── http_client.py         # Discord API クライアント実装 (762行)

src/handlers/             # 新アーキテクチャ（完成済み、使用中）
├── discord_sender.py      # メッセージ送信ロジック (246行)
├── event_registry.py      # イベント型の登録と振り分け
└── thread_manager.py      # スレッドの検索と管理 (524行)

src/formatters/           # 新アーキテクチャ（完成済み、使用中）
├── base.py                # ベースフォーマッタープロトコル
├── event_formatters.py    # イベント固有のフォーマッター (544行)
└── tool_formatters.py     # ツール固有のフォーマッター (437行)
```

### 実際のコードパスと各コンポーネントの役割

#### エントリーポイント
- **`src/main.py`** (289行): Hookイベントの受信とメイン処理フロー
  - JSONデータの読み込みと解析
  - 設定の読み込みとバリデーション
  - フォーマッターレジストリの初期化
  - Discord送信の実行

#### コア機能（`src/core/`）
- **`config.py`** (1,153行): 設定管理の中核
  - `ConfigLoader`: 設定ファイルの読み込みと環境変数の処理
  - `ConfigValidator`: 設定値の検証とバリデーション
  - `ConfigFileWatcher`: 設定ファイルの監視とホットリロード
  - ログ設定とイベント/ツールフィルタリング
- **`http_client.py`** (762行): Discord API通信
  - HTTP リクエストの送信と再試行ロジック
  - エラーハンドリングと接続管理
  - レート制限対応
- **`constants.py`** (166行): システム定数とデフォルト値
- **`exceptions.py`** (168行): カスタム例外クラス群

#### ハンドラー（`src/handlers/`）
- **`discord_sender.py`** (246行): Discord メッセージ送信の実装
  - `send_to_discord()`: メイン送信関数
  - `DiscordContext`: 送信コンテキストの管理
- **`thread_manager.py`** (524行): Discord スレッド管理
  - スレッドの検索、作成、キャッシュ管理
  - セッションベースのスレッド組織化
- **`event_registry.py`** (104行): イベントタイプの登録とフォーマッター管理

#### フォーマッター（`src/formatters/`）
- **`event_formatters.py`** (544行): イベント固有のフォーマッター
  - 各イベントタイプ用のDiscord埋め込み生成
  - バージョン情報とフッター生成
- **`tool_formatters.py`** (437行): ツール固有のフォーマッター
  - 各ツールタイプ用の詳細情報フォーマッティング
  - 入出力データの整形
- **`base.py`** (194行): 基底フォーマッター機能とユーティリティ

#### その他の重要なコンポーネント
- **`type_guards.py`** (1,093行): 型安全性を保証するTypeGuard/TypeIs実装
- **`thread_storage.py`** (492行): SQLite ベースのスレッド永続化
- **`settings_types.py`** (240行): Claude Code設定用TypedDict定義

### Configuration Management

設定管理は以下の優先順位階層に従って実行されます：

1. **環境変数**（最高優先度）
2. **`~/.claude/hooks/` ディレクトリの `.env` ファイル**
3. **デフォルト値**（最低優先度）

重要な設定オプション：
- `DISCORD_WEBHOOK_URL` または `DISCORD_TOKEN` + `DISCORD_CHANNEL_ID`
- `DISCORD_USE_THREADS` - スレッド機能の有効化
- `DISCORD_ENABLED_EVENTS` / `DISCORD_DISABLED_EVENTS` - イベントフィルタリング
- `DISCORD_DEBUG` - 詳細ログの有効化

### Hook Integration

**現在の設定状況**
```json
"hooks": {
    "PreToolUse": [{
        "hooks": [{
            "type": "command",
            "command": "CLAUDE_HOOK_EVENT=PreToolUse cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python /home/ubuntu/workbench/projects/claude-code-event-notifier/src/main.py"
        }]
    }]
}
```

**新アーキテクチャの使用状況**
新しいアーキテクチャは既に完全実装され、すべてのHookイベント（PreToolUse、PostToolUse、Notification、Stop、SubagentStop）で `src/main.py` をエントリーポイントとして使用しています。モジュール化された新しいアーキテクチャが正常に動作し、完全に実用化されています。

---

## 🔧 Discord Notification Configuration

### 📱 Available Message Types

The Discord notifier supports 5 main event types with distinct visual styling:

1. **PreToolUse** (🔵 Blue) - Triggered before any tool executes
2. **PostToolUse** (🟢 Green) - Triggered after tool execution completes
3. **Notification** (🟠 Orange) - System notifications and important messages
4. **Stop** (⚫ Gray) - Session end notifications
5. **SubagentStop** (🟣 Purple) - Subagent completion notifications

### ⚙️ Configuration Methods

#### Event-Level Filtering

**Enable specific events only (whitelist approach):**
```bash
# Only send Stop and Notification events
DISCORD_ENABLED_EVENTS=Stop,Notification

# Only send tool execution events
DISCORD_ENABLED_EVENTS=PreToolUse,PostToolUse
```

**Disable specific events (blacklist approach):**
```bash
# Send all events except PreToolUse and PostToolUse
DISCORD_DISABLED_EVENTS=PreToolUse,PostToolUse

# Disable only session end notifications
DISCORD_DISABLED_EVENTS=Stop,SubagentStop
```

#### Tool-Level Filtering

**Disable notifications for specific tools:**
```bash
# Don't send notifications for Read, Edit, TodoWrite, and Grep tools
DISCORD_DISABLED_TOOLS=Read,Edit,TodoWrite,Grep

# Common development setup - exclude file operations
DISCORD_DISABLED_TOOLS=Read,Write,Edit,MultiEdit,LS
```

**Available tools include:** Bash, Read, Write, Edit, MultiEdit, Glob, Grep, LS, Task, WebFetch, TodoWrite, and others.

### 📁 Configuration File Location

**Primary configuration file:** `~/.claude/.env`

**Current configuration:**
@/home/ubuntu/.claude/.env

### 🔄 Configuration Precedence

The system follows this hierarchy (highest to lowest priority):

1. **Environment variables** (highest priority)
2. **`.env` file values**
3. **Built-in defaults** (all events enabled)

### 💡 Configuration Examples

For complete configuration options and current settings, see:
@/home/ubuntu/.claude/.env

**Key configuration patterns:**
- **Minimal**: Enable only `DISCORD_EVENT_NOTIFICATION=1` and `DISCORD_EVENT_STOP=1`
- **Development**: Disable file operations with `DISCORD_TOOL_READ=0`, `DISCORD_TOOL_EDIT=0`
- **Production**: Enable all events and set `DISCORD_MENTION_USER_ID`
- **Focus**: Enable only `DISCORD_EVENT_PRETOOLUSE=1` and `DISCORD_EVENT_POSTTOOLUSE=1`

### 🔥 Hot Reload Support

The new architecture includes `ConfigFileWatcher` that automatically detects changes to the configuration file:

```bash
# Test configuration changes without restart
echo 'DISCORD_DISABLED_TOOLS=Read,Edit' >> ~/.claude/.env

# Configuration is automatically reloaded
# No Claude Code restart required
```

### 📊 Configuration Validation

The system includes comprehensive validation:

```bash
# Test configuration validity
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python configure_hooks.py --reload

# Validate end-to-end functionality
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python configure_hooks.py --validate-end-to-end
```

### 🛠️ Advanced Configuration Options

#### User Mentions
```bash
# Automatic user mentions for important events
DISCORD_MENTION_USER_ID=your_discord_user_id
```

#### Thread Support
```bash
# Create Discord threads for session organization
DISCORD_USE_THREADS=true
```

#### Debug Logging
```bash
# Enable detailed logging for troubleshooting
DISCORD_DEBUG=1
```

### 🚨 Important Notes

- **Graceful Degradation**: Invalid configurations never block Claude Code operation
- **Error Reporting**: Configuration errors are logged but don't prevent execution
- **Performance**: Filtering happens before message formatting for optimal performance
- **Thread Safety**: Configuration changes are safely applied during runtime

---

## 🎯 End-to-End Validation System

### 🚀 完全統合テストコマンド（自律実行可能）

**基本実行 - 即座に完全テスト開始**
```bash
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python configure_hooks.py --validate-end-to-end
```

このコマンドは、Discord API使って自分でメッセージ受信して検証する完全な統合テストを実行します。

### 📋 End-to-End Validation の実行内容

#### Step 1: Configuration Loading and Validation
- 設定ファイルの存在確認と有効性検証
- Discord認証情報の検証（Webhook URL または Bot Token）
- Channel ID の設定確認

#### Step 2: Authentication Method Detection
- **Webhook-only Mode**: Bot Token未設定時の検証方式
- **Bot Token + API Mode**: 完全なDiscord API検証が可能

#### Step 3: Hook Execution with Test Event
- 実際のHookシステムを使用したテストイベント送信
- 新アーキテクチャ（main.py）またはレガシー実装の自動検出
- 設定に応じた適切なPython実行環境の使用

#### Step 4: Real-Time Discord Verification
- **Webhook Mode**: Hook実行成功の確認
- **API Mode**: 3秒待機後のDiscord API経由でのメッセージ受信確認

#### Step 5: Complete Results Analysis
- 実行結果の包括的分析と報告
- エラー発生時の詳細な診断情報提供

### 🔧 認証モード別動作

#### 🔗 Webhook-only Mode（現在の標準設定）
```bash
# 設定確認
ls -la ~/.claude/.env
grep DISCORD_WEBHOOK_URL ~/.claude/.env

# 実行結果例
🔗 Webhook-only mode detected (no bot token for reading)
✅ Hook executed successfully with webhook configuration
📤 Discord notification should have been sent via webhook
🎉 END-TO-END VALIDATION: SUCCESS!
```

#### 🤖 Bot Token + API Mode（完全検証）
```bash
# Bot Token追加でフル機能有効化
echo 'DISCORD_BOT_TOKEN=your_bot_token_here' >> ~/.claude/.env

# 実行結果例
🤖 Bot token authentication detected
✅ Discord API access verified  
📊 Baseline: 5 total messages, 2 notifier messages
🎉 END-TO-END VALIDATION: SUCCESS!
✅ New Discord Notifier message detected!
📈 Message count: 2 → 3
```

### 🛠️ トラブルシューティング実行手順

#### 問題発生時の系統的診断
```bash
# 1. 基本動作確認
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python configure_hooks.py --validate-end-to-end

# 2. 失敗時: 個別コンポーネント確認
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python configure_hooks.py --reload  # 設定読み込み確認
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python utils/check_discord_access.py  # Discord API アクセス確認

# 3. Hook単体実行テスト
echo '{"session_id":"test","tool_name":"Test"}' | CLAUDE_HOOK_EVENT=PreToolUse cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python src/main.py

# 4. 詳細ログ確認
tail -f ~/.claude/hooks/logs/discord_notifier_*.log
```

### 💡 期待される実行結果とエラー対応

#### ✅ 成功時の典型的出力
```
🚀 Starting Complete End-to-End Validation...
📋 Step 1: Configuration Loading and Validation
✅ Discord channel ID: 1391964875600822366
✅ Configuration validation: Passed

📡 Step 2: Authentication Method Detection  
🔗 Webhook-only mode detected

🔥 Step 3: Hook Execution with Test Event
🔧 Using new modular architecture (main.py)
✅ Hook execution successful

🔍 Step 4: Validation Method
🎉 END-TO-END VALIDATION: SUCCESS!

📊 Step 5: End-to-End Results Analysis
Overall Result: 🎉 PASSED
```

#### ❌ 失敗時の診断ガイド

**設定エラー**: 
```
❌ Discord credentials invalid or missing
→ ~/.claude/.env を確認・設定
```

**Hook実行エラー**:
```
❌ Hook execution failed
→ Python 3.14環境確認: uv run --python 3.14 python --version
→ src/main.py または src/discord_notifier.py の存在確認
```

**Discord API エラー**:
```
❌ Discord API access failed: Bot may not have access
→ Bot権限確認またはWebhook URL検証
→ utils/check_discord_access.py で詳細診断
```

### 🎯 Hot Reload機能の完全検証手順

#### リアルタイム設定変更テスト
```bash
# 1. ベースライン確認
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python configure_hooks.py --reload

# 2. 設定変更（例：無効化ツール変更）
echo 'DISCORD_DISABLED_TOOLS=Write,Edit' >> ~/.claude/.env

# 3. 変更の即座反映確認
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python configure_hooks.py --reload

# 4. 実際のHook動作での設定反映確認
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python configure_hooks.py --validate-end-to-end
```

### 📊 既存Discord API Validator統合

**`src/utils/discord_api_validator.py` 活用機能**:
- `fetch_channel_messages()`: Discord APIからのメッセージ取得
- `verify_channel_repeatedly()`: 複数回検証による信頼性向上  
- `analyze_channel_health()`: チャンネル健全性の包括的分析

**使用例 - 直接API検証**:
```bash
# 単体でDiscord API検証実行
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python src/utils/discord_api_validator.py

# 実行結果例
🚀 Starting Discord API validation for channel 1391964875600822366
🔍 Verification attempt 1/3...
✅ Success: Found 47 messages
📢 15 Discord Notifier messages detected

📊 Analysis Results:
Status: healthy
Success Rate: 100.0%
Discord Notifier Messages Found: True
```

### 🔄 継続的検証のための自動化

#### CI/CD パイプライン統合
```bash
# 基本検証スクリプト
#!/bin/bash
set -e

echo "🔄 Running Discord Notifier End-to-End Validation..."
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python configure_hooks.py --validate-end-to-end

if [ $? -eq 0 ]; then
    echo "✅ All validation tests passed!"
else
    echo "❌ Validation failed - check Discord configuration"
    exit 1
fi
```

#### 定期実行設定例
```bash
# crontab設定例（毎時実行）
0 * * * * cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python configure_hooks.py --validate-end-to-end >> /tmp/discord-validation.log 2>&1
```

---

## 📊 Discord送信検証システム完全ガイド

### 🔗 DiscordメッセージURL確認方法（重要）

**ユーザーがDiscordメッセージURLを貼った場合の確認手順**

DiscordメッセージURL（例：`https://discord.com/channels/1141224103580274760/1391964875600822366/1395107298451390567`）を確認する際は、以下の手順を実行：

#### 0. 設定確認（最重要）
```bash
# 通知が表示されない場合、まず設定を確認
# イベントタイプ別の有効/無効設定を確認
grep -E "DISCORD_EVENT_|DISCORD_TOOL_" ~/.claude/.env | grep -v "^#"

# 特定のツールが無効化されていないか確認
grep "DISCORD_DISABLED_TOOLS" ~/.claude/.env

# PreToolUse/PostToolUseが無効の場合、Taskツールの実行前後通知は送信されない
# SubagentStopイベントのみが送信される
```

#### 1. Discord API経由での確認（推奨）
```bash
# 既存のdiscord_api_validatorを使用
uv run --python 3.14 python src/utils/discord_api_validator.py

# 最新メッセージを確認
uv run --python 3.14 python -c "
import sys
sys.path.insert(0, '.')
from src.utils.discord_api_validator import fetch_channel_messages
from src.core.config import ConfigLoader

config = ConfigLoader.load()
messages = fetch_channel_messages(config['channel_id'], config['bot_token'])

for i, msg in enumerate(messages[:3]):
    print(f'Message {i+1}:')
    print(f'  Timestamp: {msg[\"timestamp\"]}')
    print(f'  Author: {msg[\"author\"][\"username\"]}')
    if msg.get('embeds'):
        embed = msg['embeds'][0]
        print(f'  Title: {embed.get(\"title\", \"\")}')
        print(f'  Footer: {embed.get(\"footer\", {}).get(\"text\", \"\")}')
"
```

#### 2. URLからの情報抽出
```bash
# URLから channel_id と message_id を抽出
url="https://discord.com/channels/1141224103580274760/1391964875600822366/1395107298451390567"
channel_id=$(echo $url | cut -d'/' -f6)
message_id=$(echo $url | cut -d'/' -f7)
echo "Channel: $channel_id, Message: $message_id"
```

#### 3. 通知の詳細分析
- **Event Type**: フッターの「Event: 」の後の文字列
- **Tool Name**: タイトルの「execute: 」または「Completed: 」の後の文字列
- **Session ID**: フッターの「Session: 」の後の文字列
- **Timestamp**: メッセージの作成時間

**⚠️ 重要**: Bot tokenが必要。403 Forbiddenエラーが発生する場合は、既存のdiscord_api_validatorを使用する。

### 🆔 メッセージID検証機能（新機能）

**送信時にメッセージIDを取得し、後で検証する方法**

#### 1. メッセージIDを取得して送信
```bash
# メッセージID付きテスト送信
uv run --python 3.14 python -c "
import sys
sys.path.insert(0, '.')
from src.core.config import ConfigLoader
from src.core.http_client import HTTPClient
from src.handlers.discord_sender import DiscordContext, send_to_discord_with_id
import logging

config = ConfigLoader.load()
logger = logging.getLogger(__name__)
http_client = HTTPClient(logger=logger)
ctx = DiscordContext(config=config, logger=logger, http_client=http_client)

test_message = {
    'embeds': [{
        'title': '🧪 Message ID Test',
        'description': 'Testing message ID capture functionality',
        'color': 0x00FF00
    }]
}

message_id = send_to_discord_with_id(test_message, ctx, 'test_session', 'PreToolUse')
print(f'Message ID: {message_id}')
"
```

#### 2. 取得したメッセージIDで検証
```bash
# 特定のメッセージIDで検証
MESSAGE_ID="1395109592484286679"  # 実際のメッセージID
uv run --python 3.14 python -c "
import sys
sys.path.insert(0, '.')
from src.core.config import ConfigLoader
import urllib.request, json

config = ConfigLoader.load()
channel_id = config['channel_id']
bot_token = config['bot_token']

# 特定のメッセージを取得
url = f'https://discord.com/api/v10/channels/{channel_id}/messages/${MESSAGE_ID}'
headers = {'Authorization': f'Bot {bot_token}'}
req = urllib.request.Request(url, headers=headers)

try:
    with urllib.request.urlopen(req) as response:
        message = json.loads(response.read().decode())
        print(f'Message ID: {message[\"id\"]}')
        print(f'Timestamp: {message[\"timestamp\"]}')
        print(f'Author: {message[\"author\"][\"username\"]}')
        if message.get('embeds'):
            embed = message['embeds'][0]
            print(f'Title: {embed.get(\"title\", \"\")}')
            print(f'Description: {embed.get(\"description\", \"\")}')
except Exception as e:
    print(f'Error: {e}')
"
```

#### 3. 実際のHook動作での検証
```bash
# 実際のHook実行でメッセージIDを記録
# ログにメッセージIDが記録される
tail -f ~/.claude/hooks/logs/discord_notifier_*.log | grep "Message ID"
```

**メッセージIDの利点**:
- 送信したメッセージを確実に特定可能
- 後で詳細な検証が可能
- Discord APIで直接メッセージ内容を確認可能
- 問題発生時のデバッグが容易

#### 4. メッセージIDを直接指定して取得（新方法）
```bash
# ユーザーから提供されたメッセージIDを直接取得
MESSAGE_IDS="1395920855741104128,1395920856018063471,1395920857842454529"
CHANNEL_ID="1391964875600822366"

uv run --python 3.14 python -c "
from pathlib import Path
import urllib.request
import json

# Read bot token
config_path = Path.home() / '.claude' / '.env'
bot_token = None
with open(config_path, 'r') as f:
    for line in f:
        if line.startswith('DISCORD_BOT_TOKEN='):
            bot_token = line.split('=', 1)[1].strip()
            break

# Fetch specific messages
message_ids = '$MESSAGE_IDS'.split(',')
channel_id = '$CHANNEL_ID'

for msg_id in message_ids:
    url = f'https://discord.com/api/v10/channels/{channel_id}/messages/{msg_id}'
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'Bot {bot_token}')
    req.add_header('User-Agent', 'DiscordBot (discord-notifier, 1.0)')
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            msg = json.loads(response.read().decode())
            if msg.get('embeds'):
                embed = msg['embeds'][0]
                footer = embed.get('footer', {}).get('text', '')
                event_type = footer.split('Event: ')[1].split(' |')[0] if 'Event: ' in footer else 'Unknown'
                print(f'ID: {msg_id} - Event: {event_type} - Title: {embed.get(\"title\", \"\")}')
    except Exception as e:
        print(f'Error fetching {msg_id}: {e}')
"
```

---

## 💎 デッドコード活用完全ガイド - Advanced Features Integration

### 🚀 概要：発見された高度機能の完全活用

調査により、以下の高度な機能が既に実装されているが十分に活用されていないことが判明しました：

1. **ThreadStorage** - SQLiteベースの持続的スレッド管理システム
2. **MarkdownExporter** - Discord埋め込みのMarkdown変換システム  
3. **MessageIDGenerator** - 一意メッセージID生成システム
4. **Thread Management Tools** - 高度なスレッド管理機能

### 🔧 ThreadStorage 完全活用ガイド

#### 基本統合状況
ThreadStorageは既に `src/handlers/thread_manager.py` で完全統合されており、以下の機能が利用可能です：

```python
# 基本的な使用（既に統合済み）
thread_id = get_or_create_thread(session_id, config, http_client, logger)
```

#### 高度な管理機能

**ThreadStorage Manager 使用例**
```bash
# 統計情報の取得
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python src/utils/thread_storage_manager.py stats

# 古いスレッドのクリーンアップ
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python src/utils/thread_storage_manager.py cleanup

# 健全性レポート
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python src/utils/thread_storage_manager.py health

# チャンネル内の全スレッド検索
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python src/utils/thread_storage_manager.py find-channel 1391964875600822366

# 名前によるスレッド検索
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python src/utils/thread_storage_manager.py find-name 1391964875600822366 "Session abc123"

# セッションIDによるスレッド取得
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python src/utils/thread_storage_manager.py get-session "abc123def456"
```

#### 設定オプション

**環境変数による設定**
```bash
# ThreadStorage設定
DISCORD_THREAD_STORAGE_PATH=/custom/path/threads.db  # カスタムデータベースパス
DISCORD_THREAD_CLEANUP_DAYS=30                       # 古いスレッドの保持期間
DISCORD_USE_THREADS=true                             # スレッド機能の有効化
```

### 📝 MarkdownExporter 完全活用ガイド

#### 統合状況
MarkdownExporterは既に `src/formatters/event_formatters.py` の `format_subagent_stop` 関数で完全統合されています。

#### 機能概要
```python
# 自動的にMarkdownコンテンツが生成される（既に統合済み）
markdown_content = generate_markdown_content(raw_content, message_id)

# Discord埋め込みに含まれるフィールド
embed["markdown_content"] = markdown_content  # 完全なMarkdown形式
embed["message_id"] = message_id              # 一意メッセージID
embed["raw_content"] = raw_content            # 生データ
```

#### 生成されるMarkdown形式
```markdown
# 🤖 Subagent Completed

**Message ID**: `SubagentStop_abc123def456_20250716142000_a1b2c3d4`

**Subagent ID**: subagent_001
**Task**: Calculate 2+2 and provide explanation

## Conversation Log
```
User: What is 2+2?
Assistant: 2+2 equals 4. This is basic arithmetic addition.
```

## Response Content
```
The answer is 4. This is calculated by adding 2 and 2 together.
```

## Result
```
{"answer": 4, "explanation": "Basic arithmetic addition"}
```

## Metrics
- **Duration**: 1.5 seconds
- **Tools Used**: 0

---
*Generated at: 2025-07-16T14:20:00.000Z*
```

### 🆔 MessageIDGenerator 完全活用ガイド

#### 統合状況
MessageIDGeneratorは既に `src/formatters/event_formatters.py` で完全統合されています。

#### 生成されるID形式
```python
# 自動生成される一意ID（既に統合済み）
# 形式: {event_type}_{session_id}_{timestamp}_{uuid}
"SubagentStop_abc123def456_20250716142000_a1b2c3d4"
```

---

## 🔧 Commands

```bash
# 現在の実装をテストする
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python configure_hooks.py

# Hookを削除する
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python configure_hooks.py --remove

# すべてのテストを実行する
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python -m unittest discover -s tests -p "test_*.py"

# 型チェックとリンティングを実行する
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python -m mypy src/ configure_hooks.py
ruff check src/ configure_hooks.py utils/
ruff format src/ configure_hooks.py utils/

# デバッグログを表示する（DISCORD_DEBUG=1が必要）
tail -f ~/.claude/hooks/logs/discord_notifier_*.log

# 新アーキテクチャ用コマンド
# 新アーキテクチャでのHook設定（main.py使用）
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python configure_hooks.py

# 新アーキテクチャの動作テスト
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python src/main.py < test_event.json

# 🚀 END-TO-END VALIDATION SYSTEM (完全統合テスト)
# エンドツーエンド検証 - Hot Reload + Discord API 統合テスト
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python configure_hooks.py --validate-end-to-end

# 設定ホットリロード機能テスト
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python configure_hooks.py --reload

# 既存Discord API検証ツール単体実行
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python src/utils/discord_api_validator.py
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python utils/check_discord_access.py
```

---

*"Beautiful architecture is not about complexity, but about clarity."*
*— The Sacred Code Keepers*