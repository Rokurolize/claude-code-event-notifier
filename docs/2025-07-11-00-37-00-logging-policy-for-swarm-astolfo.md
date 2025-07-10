# 群体アストルフォ向けロギング方針

## 概要

このドキュメントは、Discord Notifierプロジェクトにおける群体アストルフォ向けのロギング方針を定義します。vibe-loggerの設計思想を参考に、AI（アストルフォ）が効率的にデバッグ・開発を進められるようなロギングシステムを目指します。

## 基本原則

### 1. AIファーストのログ設計

従来の人間向けログ: 
```
ERROR: Failed to send message
```

群体アストルフォ向けログ:
```json
{
  "timestamp": "2025-07-11T00:37:00Z",
  "level": "ERROR",
  "event": "discord_send_failed",
  "session_id": "a6a0ce89",
  "correlation_id": "msg-001",
  "context": {
    "tool_name": "Task",
    "prompt_length": 5432,
    "truncated_to": 200,
    "discord_limit": 4096,
    "attempted_split": false
  },
  "error": {
    "type": "MessageTooLong",
    "message": "Embed description exceeds Discord limit",
    "stack_trace": "..."
  },
  "ai_todo": "プロンプトが長すぎて送信に失敗。分割送信機能の実装が必要",
  "human_note": "このエラーは頻繁に発生。優先度高"
}
```

### 2. 詳細なコンテキスト情報

各ログエントリには以下を含める：
- **イベントの完全なコンテキスト**: 入力パラメータ、環境変数、設定値
- **処理の流れ**: どの関数から呼ばれたか、次に何が起きるか
- **関連するデータ**: セッションID、トランスクリプトパス、Discord情報
- **デバッグヒント**: 問題の原因と解決方法の提案

### 3. 開発時の冗長性

開発時（`DISCORD_DEBUG=1`）には：
- すべての関数の入出力をログ
- Discord APIのリクエスト/レスポンスの完全なダンプ
- トランスクリプトファイルの読み取り結果
- 各処理ステップの詳細な状態

### 4. 群体間の引き継ぎ情報

各アストルフォが作業を引き継げるように：
- 現在の作業状態
- 未解決の問題
- 試行した解決策とその結果
- 次のアストルフォへの申し送り

## 実装提案

### 1. 構造化ログクラス

```python
from dataclasses import dataclass, field
from typing import Any, Optional
import json
from datetime import datetime

@dataclass
class AstolfoLog:
    """群体アストルフォ向けの構造化ログエントリ"""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    level: str = "INFO"
    event: str = ""
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None
    context: dict[str, Any] = field(default_factory=dict)
    error: Optional[dict[str, Any]] = None
    ai_todo: Optional[str] = None
    human_note: Optional[str] = None
    astolfo_note: Optional[str] = None  # アストルフォ間の引き継ぎメモ
    
    def to_json(self) -> str:
        return json.dumps(self.__dict__, indent=2, ensure_ascii=False)
```

### 2. ログ出力例

#### イベント処理開始時
```python
log = AstolfoLog(
    level="INFO",
    event="pre_tool_use_start",
    session_id=session_id,
    context={
        "tool_name": tool_name,
        "input_size": len(str(tool_input)),
        "truncation_limits": {
            "prompt": TruncationLimits.PROMPT_PREVIEW,
            "output": TruncationLimits.OUTPUT_PREVIEW
        },
        "discord_config": {
            "use_threads": config.get("use_threads"),
            "channel_type": config.get("channel_type")
        }
    },
    ai_todo="ツール実行前の通知処理を開始"
)
logger.info(log.to_json())
```

#### エラー発生時
```python
log = AstolfoLog(
    level="ERROR",
    event="transcript_read_failed",
    session_id=session_id,
    correlation_id=f"task-{tool_id}",
    context={
        "transcript_path": transcript_path,
        "file_exists": Path(transcript_path).exists(),
        "file_size": Path(transcript_path).stat().st_size if Path(transcript_path).exists() else 0,
        "attempted_lines": 500,
        "search_pattern": "Task tool prompt"
    },
    error={
        "type": type(e).__name__,
        "message": str(e),
        "stack_trace": traceback.format_exc()
    },
    ai_todo="トランスクリプトファイルの読み取りに失敗。ファイルフォーマットまたはアクセス権限を確認",
    astolfo_note="このエラーは断続的に発生。ファイルロックの可能性あり"
)
logger.error(log.to_json())
```

### 3. デバッグモードの詳細ログ

```python
if debug_mode:
    # Discord API通信の詳細
    log = AstolfoLog(
        level="DEBUG",
        event="discord_api_request",
        correlation_id=request_id,
        context={
            "method": "POST",
            "url": url,
            "headers": headers,
            "body": json.loads(data) if data else None,
            "body_size": len(data) if data else 0
        },
        ai_todo="Discord APIリクエストの詳細。レスポンスは次のログエントリで確認"
    )
    logger.debug(log.to_json())
```

### 4. 引き継ぎログ

作業終了時に自動的に生成：
```python
log = AstolfoLog(
    level="INFO",
    event="astolfo_handover",
    session_id=session_id,
    context={
        "work_summary": {
            "fixed_issues": ["プロンプト200文字制限", "ハードコード除去"],
            "pending_issues": ["Discord分割送信が未実装", "ログ詳細化が必要"],
            "files_modified": ["src/formatters/event_formatters.py", "src/core/constants.py"]
        },
        "test_status": "未実行",
        "next_steps": ["Discord分割送信の実装", "テストの実行"]
    },
    astolfo_note="プロンプトの切り詰め問題は解決したけど、4096文字を超える場合の分割送信はまだ未実装だよ！",
    human_note="マスターは全文が見たいと言っていた。分割送信の実装を優先して！"
)
```

## 実装優先度

1. **高優先度**
   - 基本的な構造化ログクラスの実装
   - エラー時の詳細コンテキスト記録
   - Discord API通信のログ強化

2. **中優先度**
   - デバッグモードでの冗長ログ
   - 引き継ぎログの自動生成
   - パフォーマンス計測ログ

3. **低優先度**
   - ログのビジュアライゼーション
   - ログ分析ツール
   - 自動問題検出

## まとめ

このロギング方針により、群体アストルフォは：
- 前のアストルフォが何をしたか正確に把握できる
- エラーの原因を素早く特定できる
- 効率的に作業を引き継げる
- マスターのために最高の成果を出せる！♡

えへへ、これでみんなが迷子にならないね！♡