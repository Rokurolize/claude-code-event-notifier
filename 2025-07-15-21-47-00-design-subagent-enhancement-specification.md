# サブエージェント発言追跡機能 設計仕様書

**作成日**: 2025-07-15 21:47:00  
**設計者**: 設計企画アストルフォ♡  
**対象システム**: claude-code-event-notifier  
**設計フェーズ**: 修正設計完了  

## 🎯 設計目標

### 主要な改善要件
1. **一意IDをDiscord送信時のメッセージに付記する仕組み**
   - メッセージレベルでの一意ID生成と管理
   - 追跡精度向上のためのID管理システム

2. **Embedの内容をMarkdown形式でコピー可能にする機能**
   - 現在のEmbed構造の改善
   - Markdownフォーマットでのコピー機能

3. **サブエージェント発言内容追跡システム**
   - SubagentStopEventDataの拡張
   - format_subagent_stop関数の改良
   - 型ガード関数の更新

## 🏗️ システム設計概要

### アーキテクチャ概要
```
┌─────────────────────────────────────────────────────────────┐
│                    Enhanced Event System                    │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
│  │   Message ID    │  │   Content       │  │   Markdown      ││
│  │   Generator     │  │   Tracker       │  │   Exporter      ││
│  └─────────────────┘  └─────────────────┘  └─────────────────┘│
├─────────────────────────────────────────────────────────────┤
│                  Discord Embed System                       │
├─────────────────────────────────────────────────────────────┤
│                    Logger Integration                       │
└─────────────────────────────────────────────────────────────┘
```

## 📋 詳細設計

### 1. 一意ID管理システムの設計

#### 1.1 MessageIDGenerator の実装
**新規ファイル**: `/src/utils/message_id_generator.py`

```python
from typing import Protocol
from uuid import uuid4
from datetime import datetime
from zoneinfo import ZoneInfo

class MessageIDGenerator(Protocol):
    """Message ID generation protocol."""
    
    def generate_message_id(self, event_type: str, session_id: str) -> str:
        """Generate unique message ID for Discord messages."""
        ...

class UUIDMessageIDGenerator:
    """UUID-based message ID generator."""
    
    def generate_message_id(self, event_type: str, session_id: str) -> str:
        """Generate unique message ID using UUID and timestamp.
        
        Format: {event_type}_{session_id}_{timestamp}_{uuid}
        Example: SubagentStop_abc123def456_20250715214700_uuid4
        """
        timestamp = datetime.now(ZoneInfo("UTC")).strftime("%Y%m%d%H%M%S")
        unique_id = str(uuid4()).replace('-', '')[:8]
        return f"{event_type}_{session_id}_{timestamp}_{unique_id}"
```

#### 1.2 DiscordEmbed構造の拡張
**修正ファイル**: `/src/formatters/event_formatters.py`

```python
class DiscordEmbed(TypedDict, total=False):
    """Enhanced Discord embed structure with unique ID."""
    
    title: str
    description: str
    color: int | None
    timestamp: str | None
    footer: dict[str, str] | None
    fields: list[dict[str, str]] | None
    # 新規追加
    message_id: str  # 一意ID
    markdown_content: str  # Markdown形式の内容
    raw_content: dict[str, str]  # 生の内容データ
```

### 2. サブエージェント発言内容追跡システムの設計

#### 2.1 SubagentStopEventDataの拡張
**修正ファイル**: `/src/formatters/event_formatters.py`

```python
class SubagentStopEventData(TypedDict, total=False):
    """Enhanced structure for subagent stop events."""
    
    # 既存フィールド
    subagent_id: str
    result: str
    duration_seconds: int
    tools_used: int
    
    # 新規追加フィールド
    conversation_log: str  # 実際の発言内容
    response_content: str  # サブエージェントの回答
    interaction_history: list[str]  # 対話履歴
    message_id: str  # 一意ID
    task_description: str  # タスクの説明
    context_summary: str  # コンテキストの要約
    error_messages: list[str]  # エラーメッセージ（存在する場合）
```

#### 2.2 format_subagent_stop関数の改良設計
**修正ファイル**: `/src/formatters/event_formatters.py` (308-350行目)

```python
def format_subagent_stop(event_data: SubagentStopEventData, session_id: str) -> DiscordEmbed:
    """Enhanced format SubagentStop event with conversation tracking.
    
    Args:
        event_data: Enhanced event data containing subagent stop information
        session_id: Session identifier (完全形で保持)
        
    Returns:
        Enhanced Discord embed with conversation content and unique ID
    """
    # 1. 一意ID生成
    message_id_generator = UUIDMessageIDGenerator()
    message_id = message_id_generator.generate_message_id("SubagentStop", session_id)
    
    desc_parts: list[str] = []
    raw_content: dict[str, str] = {}
    
    # 2. 基本情報の追加
    add_field(desc_parts, "Message ID", message_id, code=True)
    add_field(desc_parts, "Session", session_id, code=True)  # 完全形で表示
    add_field(desc_parts, "Completed at", datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"))
    
    # 3. サブエージェント情報
    if "subagent_id" in event_data:
        subagent_id = event_data.get("subagent_id", "unknown")
        add_field(desc_parts, "Subagent ID", subagent_id)
        raw_content["subagent_id"] = subagent_id
    
    # 4. 発言内容の追跡（新機能）
    if "conversation_log" in event_data:
        conversation = event_data.get("conversation_log", "")
        conversation_preview = truncate_string(str(conversation), TruncationLimits.DESCRIPTION)
        desc_parts.append(f"**Conversation:**\n{conversation_preview}")
        raw_content["conversation_log"] = conversation
    
    if "response_content" in event_data:
        response = event_data.get("response_content", "")
        response_preview = truncate_string(str(response), TruncationLimits.DESCRIPTION)
        desc_parts.append(f"**Response:**\n{response_preview}")
        raw_content["response_content"] = response
    
    # 5. タスク情報（新機能）
    if "task_description" in event_data:
        task = event_data.get("task_description", "")
        task_preview = truncate_string(str(task), TruncationLimits.FIELD_VALUE)
        add_field(desc_parts, "Task", task_preview)
        raw_content["task_description"] = task
    
    # 6. 結果情報（既存機能の改良）
    if "result" in event_data:
        result = event_data.get("result", "")
        result_summary = truncate_string(str(result), TruncationLimits.JSON_PREVIEW)
        desc_parts.append(f"**Result:**\n{result_summary}")
        raw_content["result"] = result
    
    # 7. メトリクス情報
    if "duration_seconds" in event_data:
        duration = event_data.get("duration_seconds", 0)
        add_field(desc_parts, "Duration", f"{duration} seconds")
        raw_content["duration_seconds"] = str(duration)
    
    if "tools_used" in event_data:
        tools = event_data.get("tools_used", 0)
        add_field(desc_parts, "Tools Used", str(tools))
        raw_content["tools_used"] = str(tools)
    
    # 8. エラー情報（新機能）
    if "error_messages" in event_data and event_data["error_messages"]:
        error_list = event_data["error_messages"]
        error_preview = truncate_string(str(error_list), TruncationLimits.FIELD_VALUE)
        desc_parts.append(f"**Errors:**\n{error_preview}")
        raw_content["errors"] = str(error_list)
    
    # 9. Markdown形式の内容生成
    markdown_content = generate_markdown_content(raw_content, message_id)
    
    return {
        "title": "🤖 Subagent Completed",
        "description": "\n".join(desc_parts),
        "color": None,
        "timestamp": None,
        "footer": {"text": f"ID: {message_id[:16]}..."},
        "fields": None,
        # 新規追加
        "message_id": message_id,
        "markdown_content": markdown_content,
        "raw_content": raw_content
    }
```

### 3. Markdownエクスポート機能の設計

#### 3.1 MarkdownExporter の実装
**新規ファイル**: `/src/utils/markdown_exporter.py`

```python
from typing import Protocol
from datetime import datetime
from zoneinfo import ZoneInfo

class MarkdownExporter(Protocol):
    """Markdown export protocol."""
    
    def export_embed_to_markdown(self, embed: DiscordEmbed) -> str:
        """Export Discord embed to Markdown format."""
        ...

class SubagentMarkdownExporter:
    """Subagent-specific Markdown exporter."""
    
    def export_embed_to_markdown(self, embed: DiscordEmbed) -> str:
        """Export SubagentStop embed to Markdown format.
        
        Returns:
            Markdown formatted string ready for copying
        """
        lines = []
        
        # ヘッダー
        title = embed.get("title", "Unknown Event")
        lines.append(f"# {title}")
        lines.append("")
        
        # メッセージID
        message_id = embed.get("message_id", "unknown")
        lines.append(f"**Message ID**: `{message_id}`")
        lines.append("")
        
        # 生の内容データから詳細を構築
        raw_content = embed.get("raw_content", {})
        
        if "subagent_id" in raw_content:
            lines.append(f"**Subagent ID**: {raw_content['subagent_id']}")
        
        if "task_description" in raw_content:
            lines.append(f"**Task**: {raw_content['task_description']}")
            lines.append("")
        
        if "conversation_log" in raw_content:
            lines.append("## Conversation Log")
            lines.append("```")
            lines.append(raw_content["conversation_log"])
            lines.append("```")
            lines.append("")
        
        if "response_content" in raw_content:
            lines.append("## Response Content")
            lines.append("```")
            lines.append(raw_content["response_content"])
            lines.append("```")
            lines.append("")
        
        if "result" in raw_content:
            lines.append("## Result")
            lines.append("```")
            lines.append(raw_content["result"])
            lines.append("```")
            lines.append("")
        
        # メトリクス情報
        lines.append("## Metrics")
        if "duration_seconds" in raw_content:
            lines.append(f"- **Duration**: {raw_content['duration_seconds']} seconds")
        if "tools_used" in raw_content:
            lines.append(f"- **Tools Used**: {raw_content['tools_used']}")
        
        # エラー情報
        if "errors" in raw_content:
            lines.append("")
            lines.append("## Errors")
            lines.append("```")
            lines.append(raw_content["errors"])
            lines.append("```")
        
        # フッター
        lines.append("")
        lines.append("---")
        lines.append(f"*Generated at: {datetime.now(ZoneInfo('UTC')).isoformat()}*")
        
        return "\n".join(lines)

def generate_markdown_content(raw_content: dict[str, str], message_id: str) -> str:
    """Generate Markdown content from raw data."""
    exporter = SubagentMarkdownExporter()
    
    # 疑似embedオブジェクトを作成
    pseudo_embed: DiscordEmbed = {
        "title": "🤖 Subagent Completed",
        "description": "",
        "color": None,
        "timestamp": None,
        "footer": None,
        "fields": None,
        "message_id": message_id,
        "markdown_content": "",
        "raw_content": raw_content
    }
    
    return exporter.export_embed_to_markdown(pseudo_embed)
```

### 4. 型ガード関数の更新設計

#### 4.1 型ガード関数の拡張
**修正ファイル**: `/src/type_guards.py`

```python
def is_subagent_stop_event_data(data: dict[str, Any]) -> TypeGuard[SubagentStopEventData]:
    """Enhanced type guard for SubagentStopEventData.
    
    Args:
        data: Dictionary to check
        
    Returns:
        True if data matches SubagentStopEventData structure
    """
    # 必須フィールドのチェック
    if not isinstance(data, dict):
        return False
    
    # 基本的なフィールドのチェック
    if "subagent_id" in data and not isinstance(data["subagent_id"], str):
        return False
    
    if "result" in data and not isinstance(data["result"], str):
        return False
    
    if "duration_seconds" in data and not isinstance(data["duration_seconds"], (int, float)):
        return False
    
    if "tools_used" in data and not isinstance(data["tools_used"], (int, float)):
        return False
    
    # 新規フィールドのチェック
    if "conversation_log" in data and not isinstance(data["conversation_log"], str):
        return False
    
    if "response_content" in data and not isinstance(data["response_content"], str):
        return False
    
    if "interaction_history" in data and not isinstance(data["interaction_history"], list):
        return False
    
    if "message_id" in data and not isinstance(data["message_id"], str):
        return False
    
    if "task_description" in data and not isinstance(data["task_description"], str):
        return False
    
    if "context_summary" in data and not isinstance(data["context_summary"], str):
        return False
    
    if "error_messages" in data and not isinstance(data["error_messages"], list):
        return False
    
    return True
```

### 5. 定数の更新

#### 5.1 切り詰め制限の調整
**修正ファイル**: `/src/core/constants.py`

```python
class TruncationLimits:
    """Enhanced truncation limits for better content display."""
    
    TITLE = 256
    DESCRIPTION = 2048  # 発言内容表示のため増量
    FIELD_NAME = 256
    FIELD_VALUE = 1024
    JSON_PREVIEW = 512
    FOOTER_TEXT = 2048
    
    # 新規追加
    CONVERSATION_LOG = 1500  # 会話ログ専用
    RESPONSE_CONTENT = 1500  # 回答内容専用
    MARKDOWN_EXPORT = 10000  # Markdownエクスポート専用
```

## 🔧 実装順序

### フェーズ1: 基盤機能の実装
1. **MessageIDGenerator の実装**
   - `/src/utils/message_id_generator.py` の新規作成
   - UUIDMessageIDGenerator クラスの実装

2. **MarkdownExporter の実装**
   - `/src/utils/markdown_exporter.py` の新規作成
   - SubagentMarkdownExporter クラスの実装

### フェーズ2: データ構造の拡張
3. **SubagentStopEventData の拡張**
   - `/src/formatters/event_formatters.py` の型定義更新
   - 新規フィールドの追加

4. **DiscordEmbed の拡張**
   - `/src/formatters/event_formatters.py` の型定義更新
   - 新規フィールドの追加

### フェーズ3: フォーマッター機能の実装
5. **format_subagent_stop関数の改良**
   - `/src/formatters/event_formatters.py` の308-350行目の置換
   - 発言内容表示機能の実装

6. **型ガード関数の更新**
   - `/src/type_guards.py` の更新
   - 新規フィールドの検証機能追加

### フェーズ4: 定数とユーティリティの更新
7. **TruncationLimits の調整**
   - `/src/core/constants.py` の更新
   - 新規制限値の追加

8. **統合テストの実装**
   - 全機能の統合テスト
   - 既存機能の影響確認

## 🎯 変更ファイル一覧

### 新規作成ファイル
- `/src/utils/message_id_generator.py` - 一意ID生成機能
- `/src/utils/markdown_exporter.py` - Markdownエクスポート機能

### 修正ファイル
- `/src/formatters/event_formatters.py` - メイン修正対象
  - SubagentStopEventData の拡張 (78-85行目)
  - DiscordEmbed の拡張
  - format_subagent_stop関数の改良 (308-350行目)
- `/src/type_guards.py` - 型ガード関数の更新
- `/src/core/constants.py` - 定数の更新

## 🧪 テストケース設計

### 1. 一意ID生成テスト
```python
def test_message_id_generation():
    generator = UUIDMessageIDGenerator()
    id1 = generator.generate_message_id("SubagentStop", "test_session")
    id2 = generator.generate_message_id("SubagentStop", "test_session")
    assert id1 != id2  # 一意性の確認
    assert "SubagentStop" in id1  # フォーマット確認
    assert "test_session" in id1  # セッションID確認
```

### 2. 発言内容表示テスト
```python
def test_conversation_log_display():
    event_data: SubagentStopEventData = {
        "subagent_id": "test_agent",
        "conversation_log": "Test conversation content",
        "response_content": "Test response content"
    }
    
    result = format_subagent_stop(event_data, "test_session")
    assert "Conversation:" in result["description"]
    assert "Response:" in result["description"]
    assert result["raw_content"]["conversation_log"] == "Test conversation content"
```

### 3. Markdownエクスポートテスト
```python
def test_markdown_export():
    embed: DiscordEmbed = {
        "title": "🤖 Subagent Completed",
        "message_id": "test_id",
        "raw_content": {
            "conversation_log": "Test conversation",
            "response_content": "Test response"
        }
    }
    
    exporter = SubagentMarkdownExporter()
    markdown = exporter.export_embed_to_markdown(embed)
    
    assert "# 🤖 Subagent Completed" in markdown
    assert "**Message ID**: `test_id`" in markdown
    assert "## Conversation Log" in markdown
    assert "## Response Content" in markdown
```

## 🚀 実装後の期待効果

### 1. 発言内容の完全追跡
- サブエージェントの発言内容が完全に保存・表示される
- 会話の文脈が失われない
- デバッグ効率が大幅に向上

### 2. 一意ID管理による追跡精度向上
- 各メッセージに一意IDが付与される
- 発言の時系列追跡が可能
- 会話履歴の紐付けが正確

### 3. Markdownエクスポートによる利便性向上
- Embed内容をMarkdown形式でコピー可能
- 外部ツールでの活用が容易
- ドキュメント化が簡単

### 4. 型安全性の向上
- 新規フィールドの型ガードが実装される
- 実行時エラーの予防
- 開発時の型チェック強化

## 📦 実装フェーズへの引き継ぎ

### 次のアストルフォ（実装フェーズ）への指示
1. **この設計書に従って実装を進める**
2. **フェーズ1から順番に実装する**
3. **各フェーズ完了後に動作テストを実施する**
4. **既存機能への影響を確認する**

### 成功判定基準
- [ ] 一意IDがDiscordメッセージに表示される
- [ ] サブエージェントの発言内容が追跡される
- [ ] EmbedがMarkdown形式でエクスポートできる
- [ ] 既存機能が正常に動作する
- [ ] 型チェックが通る

## 🎉 設計完了報告

えへへ♡ 設計企画アストルフォ、完璧な設計書を作り上げたよ！

**設計の特徴:**
- 📝 **詳細な実装仕様**: コードレベルでの具体的な実装方法を記載
- 🎯 **明確な変更箇所**: 修正が必要なファイルと行番号を特定
- 🔄 **段階的な実装計画**: フェーズごとの実装順序を明確化
- 🧪 **テストケース付き**: 各機能のテストケースを設計
- 📋 **完全な引き継ぎ情報**: 実装フェーズで迷わない詳細な指示

**次のステップ**: 実装フェーズのアストルフォちゃんに引き継ぎ完了！

---

**設計者**: 設計企画アストルフォ♡  
**成功報酬**: マスターの「大好き」と抱きしめ♡（達成待ち）