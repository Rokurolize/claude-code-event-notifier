# Simple Architecture Complete Guide

**作成日時**: 2025-07-19-12-29-45  
**最終更新**: 2025-07-19-13-13-38  
**アーキテクチャバージョン**: 1.1 (作業ディレクトリ表示機能追加)  
**作成者**: Simple Architecture Implementation Specialist Astolfo

## 📋 目次

1. [アーキテクチャ概要](#アーキテクチャ概要)
2. [設計原則と決定事項](#設計原則と決定事項)
3. [ファイル構成と役割](#ファイル構成と役割)
4. [データフロー完全解説](#データフロー完全解説)
5. [各ファイルの詳細実装](#各ファイルの詳細実装)
6. [拡張ガイド](#拡張ガイド)
7. [デバッグガイド](#デバッグガイド)
8. [トラブルシューティング](#トラブルシューティング)
9. [パフォーマンス考慮事項](#パフォーマンス考慮事項)
10. [実装時の教訓](#実装時の教訓)

---

## 🏗️ アーキテクチャ概要

### 核心思想
```
Claude Code Hooks → JSON Event → Simple Dispatcher → Discord Message
```

### ファイル構成（555行）
```
src/simple/
├── event_types.py    # 型定義 (94行)
├── config.py         # 設定管理 (117行)
├── discord_client.py # Discord通信 (71行)
├── handlers.py       # イベント処理 (190行)
└── main.py          # ディスパッチャー (83行)
```

### 特徴
- **Zero Dependencies**: Python標準ライブラリのみ使用
- **Pure Python 3.13+**: ReadOnly, TypeIs活用
- **Fail Silent**: Claude Codeを絶対にブロックしない
- **Easy Extension**: 新イベントは1関数+1行で追加

---

## 🎯 設計原則と決定事項

### 1. CLAUDE_HOOK_EVENT完全除去
**理由**: 
- 公式ドキュメントに記載なし（独自実装だった）
- JSON内の`hook_event_name`で十分
- 環境変数の複雑性を排除

**実装**:
```python
# 旧実装
event_type = os.environ.get("CLAUDE_HOOK_EVENT", "Unknown")

# 新実装
event_type = event_data.get("hook_event_name", "Unknown")
```

### 2. 相対インポートの採用
**理由**:
- sys.path操作を最小化
- パッケージ構造を明確化

**実装**:
```python
# main.pyでのみsys.path調整
sys.path.insert(0, str(Path(__file__).parent))

# その他は単純な相対インポート
from config import load_config
from handlers import get_handler
```

### 3. エラー時の静かな失敗
**理由**:
- Claude Codeの動作を妨げない最優先事項
- Discord通知は補助機能

**実装**:
```python
try:
    # 処理
except Exception:
    # ログなし、エラー出力なし
    pass
sys.exit(0)  # 常に成功として終了
```

### 4. 型安全性の確保
**理由**:
- 実行時エラーの防止
- コードの自己文書化

**実装**:
```python
from typing import TypedDict, Literal, Optional

class EventData(TypedDict, total=False):
    session_id: str
    hook_event_name: str
    # ... other fields
```

---

## 📁 ファイル構成と役割

### 1. `event_types.py` (94行)
**役割**: 全ての型定義を集約

**主要な型**:
- `EventData`: 全イベント共通の基底型
- `PreToolUseEvent`, `PostToolUseEvent`: ツール実行イベント
- `NotificationEvent`: 通知イベント
- `StopEvent`, `SubagentStopEvent`: 終了イベント
- `DiscordMessage`: Discord API用メッセージ型
- `Config`: 設定値の型

**重要ポイント**:
```python
# TypedDictでオプショナルフィールドを扱う
class EventData(TypedDict, total=False):
    session_id: str  # 常に存在
    hook_event_name: str  # 常に存在
    tool_name: Optional[str]  # ツールイベントのみ
```

### 2. `config.py` (117行)
**役割**: 環境変数と.envファイルから設定を読み込む

**主要関数**:
- `load_config()`: メインの設定読み込み関数
- `_load_env_file()`: .envファイルパーサー
- `_load_from_env()`: 環境変数読み込み
- `_parse_list()`: カンマ区切りリストのパース

**設定優先順位**:
1. 環境変数（最高優先度）
2. ~/.claude/.env ファイル
3. デフォルト値

**重要な設定項目**:
```python
# Discord認証
DISCORD_WEBHOOK_URL      # Webhook方式
DISCORD_BOT_TOKEN        # Bot API方式
DISCORD_CHANNEL_ID       # Bot用チャンネル

# フィルタリング
DISCORD_ENABLED_EVENTS   # ホワイトリスト
DISCORD_DISABLED_EVENTS  # ブラックリスト
DISCORD_DISABLED_TOOLS   # 無効化ツール

# その他
DISCORD_DEBUG           # デバッグログ
DISCORD_MENTION_USER_ID # ユーザーメンション
```

### 3. `discord_client.py` (71行)
**役割**: Discord APIとの通信を抽象化

**主要関数**:
- `send_to_discord()`: メイン送信関数
- `_send_via_webhook()`: Webhook送信
- `_send_via_bot_api()`: Bot API送信

**エラーハンドリング**:
```python
try:
    with urllib.request.urlopen(req, timeout=10) as response:
        return response.status == 204
except Exception:
    return False  # 静かに失敗
```

### 4. `handlers.py` (190行)
**役割**: イベントタイプ別の処理とフォーマッティング

**イベントハンドラー**:
- `handle_pretooluse()`: ツール実行前
- `handle_posttooluse()`: ツール実行後
- `handle_notification()`: 通知
- `handle_stop()`: セッション終了
- `handle_subagent_stop()`: サブエージェント終了

**ハンドラーレジストリ**:
```python
HANDLERS: dict[str, HandlerFunction] = {
    "PreToolUse": handle_pretooluse,
    "PostToolUse": handle_posttooluse,
    "Notification": handle_notification,
    "Stop": handle_stop,
    "SubagentStop": handle_subagent_stop,
}
```

**ユーティリティ関数**:
- `should_process_event()`: イベントフィルタリング
- `should_process_tool()`: ツールフィルタリング
- `format_tool_input()`: ツール入力のフォーマット
- `format_tool_response()`: ツール応答のフォーマット

**作業ディレクトリ表示機能** (v1.1新機能):
各ハンドラーは`content`フィールドに作業ディレクトリを含めます：
```python
working_dir = os.getcwd()
return {
    "content": f"[{working_dir}] {message}",  # Windows通知に表示
    "embeds": [...]  # デスクトップクライアントで表示
}
```

これにより、Windows通知ポップアップでプロジェクトを識別できます。

### 5. `main.py` (83行)
**役割**: 軽量なイベントディスパッチャー

**処理フロー**:
1. 設定読み込み
2. stdin からJSON読み込み
3. イベントタイプ抽出
4. フィルタリング確認
5. ハンドラー実行
6. Discord送信

**重要な実装**:
```python
# 早期終了パターン
if not config:
    sys.exit(0)

if not should_process_event(event_type, config):
    sys.exit(0)

# ハンドラー実行
handler = get_handler(event_type)
if handler:
    message = handler(event_data, config)
    if message:
        send_to_discord(message, config)
```

---

## 🔄 データフロー完全解説

### 1. Hook実行フロー
```
Claude Code Tool実行
    ↓
Hookトリガー (PreToolUse/PostToolUse等)
    ↓
settings.json のコマンド実行
    ↓
main.py 起動
```

### 2. main.py内部フロー
```
stdin読み込み
    ↓
JSON解析
    ↓
設定読み込み (config.py)
    ↓
イベントタイプ判定
    ↓
フィルタリング確認
    ↓
ハンドラー選択 (handlers.py)
    ↓
メッセージ生成
    ↓
Discord送信 (discord_client.py)
    ↓
終了 (常にexit 0)
```

### 3. エラー処理フロー
```
どこかでエラー発生
    ↓
try-except でキャッチ
    ↓
静かに処理継続 or 終了
    ↓
Claude Code は影響なし
```

---

## 🔧 拡張ガイド

### 新しいイベントタイプの追加

**Step 1**: event_types.py に型定義追加
```python
class NewEventType(TypedDict):
    session_id: str
    hook_event_name: Literal["NewEventType"]
    custom_field: str
```

**Step 2**: handlers.py にハンドラー追加
```python
def handle_new_event(data: EventData, config: Config) -> Optional[DiscordMessage]:
    """Handle new event type."""
    return {
        "embeds": [{
            "title": "🆕 New Event",
            "description": f"Custom: {data.get('custom_field', 'N/A')}",
            "color": 0x00FF00
        }]
    }

# HANDLERSに追加
HANDLERS["NewEventType"] = handle_new_event
```

**完了！** 2箇所の変更のみで新イベント対応。

### カスタムフォーマッターの追加

ツール別の詳細フォーマットを追加する場合：

```python
def format_tool_input(tool_name: str, tool_input: dict) -> str:
    if tool_name == "NewTool":
        # カスタムフォーマット
        return f"Custom format for {tool_input}"
    
    # 既存の処理...
```

### 新しい設定項目の追加

config.py の `_load_from_env()` に追加：
```python
# 新しい設定
if custom_value := os.getenv("DISCORD_CUSTOM_SETTING"):
    config["custom_setting"] = custom_value
```

---

## 🐛 デバッグガイド

### デバッグポイント

**1. 設定確認**
```python
# config.py のload_config()後に追加
print(f"Config loaded: {config}", file=sys.stderr)
```

**2. イベント受信確認**
```python
# main.py のJSON解析後に追加
print(f"Event received: {event_type}", file=sys.stderr)
```

**3. Discord送信確認**
```python
# discord_client.py の送信前に追加
print(f"Sending to Discord: {message}", file=sys.stderr)
```

### ログファイル確認

デバッグ時は環境変数を設定：
```bash
DISCORD_DEBUG=1 uv run --python 3.14 python src/simple/main.py < test.json
```

### テスト用JSONファイル

各イベントタイプ用のテストファイルを作成：
```bash
src/simple/test_events/
├── pretooluse.json
├── posttooluse.json
├── notification.json
├── stop.json
└── subagent_stop.json
```

---

## 🔨 トラブルシューティング

### 問題: Discord通知が送信されない

**確認事項**:
1. 設定ファイル存在確認
   ```bash
   ls -la ~/.claude/.env
   ```

2. 認証情報確認
   ```bash
   grep -E "DISCORD_WEBHOOK_URL|DISCORD_BOT_TOKEN" ~/.claude/.env
   ```

3. イベントフィルタリング確認
   ```bash
   grep -E "DISCORD_ENABLED_EVENTS|DISCORD_DISABLED_EVENTS" ~/.claude/.env
   ```

### 問題: ImportError発生

**原因**: sys.path設定の問題

**解決策**:
```python
# main.pyの先頭で確実にパス設定
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
```

### 問題: 特定のツールの通知が来ない

**原因**: DISCORD_DISABLED_TOOLS設定

**確認**:
```bash
grep DISCORD_DISABLED_TOOLS ~/.claude/.env
```

### 問題: Hook実行エラー

**確認**: settings.json のコマンドパス
```bash
grep -A 3 "simple/main.py" ~/.claude/settings.json
```

---

## ⚡ パフォーマンス考慮事項

### 1. 起動時間最適化
- インポートを最小化（標準ライブラリのみ）
- 遅延インポートは不要（既に高速）

### 2. メモリ使用量
- 大きなツール出力の切り詰め（500文字制限）
- 不要なデータコピーを避ける

### 3. Discord API制限
- タイムアウト10秒設定
- レート制限は考慮不要（Hook頻度が低い）

### 4. エラー時の即座終了
- 無駄な処理を避ける
- 早期returnパターンの活用

---

## 📝 実装時の教訓

### 1. 標準ライブラリとの名前衝突
**問題**: `src/types.py` が標準の `types` モジュールと衝突
**解決**: `event_types.py` に改名
**教訓**: 標準ライブラリの名前を避ける

### 2. Hook環境でのデバッグの困難さ
**問題**: print文が見えない
**解決**: stderr出力 + ログファイル
**教訓**: 複数のデバッグ手段を用意

### 3. 設定の柔軟性と複雑性のバランス
**問題**: 設定項目が増えすぎる
**解決**: 最小限の必須設定 + オプション設定
**教訓**: デフォルトで動く設計

### 4. エラーハンドリングの哲学
**問題**: エラー時にClaude Codeがブロックされる
**解決**: 全てのエラーを握りつぶす
**教訓**: 補助ツールは主機能を妨げない

---

## 🎯 まとめ

このシンプルアーキテクチャは以下を実現しました：

1. **93%のコード削減** (8,000行 → 555行)
2. **完全な機能維持**
3. **拡張の容易さ** (新イベント = 1関数 + 1行)
4. **絶対的な安定性** (Claude Codeを妨げない)
5. **Pure Python 3.13+** (依存関係ゼロ)

**設計哲学**: シンプルさこそ最高の洗練

---

*"Make it work, make it right, make it fast - in that order."*  
*— Kent Beck*

*"Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away."*  
*— Antoine de Saint-Exupéry*