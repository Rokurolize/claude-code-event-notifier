# Claude Code Hook JSON Event Specification

**Date**: 2025-07-21-03-09-00  
**Author**: Specification Astolfo  
**Version**: 1.0

## 1. 概要

Claude Code Hookシステムは、様々なイベントをJSON形式で送信します。本仕様書は、各イベントタイプのデータ構造を詳細に文書化し、Discord通知システムの改善提案を示します。

## 2. 共通フィールド

すべてのイベントに含まれる共通フィールド：

```typescript
interface CommonEventData {
  session_id: string;          // セッションの一意識別子
  transcript_path: string;     // トランスクリプトファイルのパス
  cwd: string;                 // 現在の作業ディレクトリ
  hook_event_name: string;     // イベントタイプ名
}
```

## 3. イベントタイプ別仕様

### 3.1 PreToolUse

ツール実行前に発生するイベント。

```typescript
interface PreToolUseEvent extends CommonEventData {
  hook_event_name: "PreToolUse";
  tool_name: string;           // 実行されるツール名
  tool_input: {                // ツール固有の入力データ
    [key: string]: any;
  };
}
```

#### ツール別tool_inputの例

**Task**:
```json
{
  "description": "Calculate 1+1",
  "prompt": "Calculate 1+1 and provide the answer."
}
```

**Edit**:
```json
{
  "file_path": "/path/to/file.md",
  "old_string": "old content",
  "new_string": "new content"
}
```

**Bash**:
```json
{
  "command": "ls -la"
}
```

### 3.2 PostToolUse

ツール実行後に発生するイベント。

```typescript
interface PostToolUseEvent extends CommonEventData {
  hook_event_name: "PostToolUse";
  tool_name: string;
  tool_input: {
    [key: string]: any;
  };
  tool_response: {
    content?: Array<{
      type: "text";
      text: string;
    }>;
    error?: string;
    totalDurationMs?: number;
    totalTokens?: string;        // マスクされる
    totalToolUseCount?: number;
    usage?: {
      input_tokens: string;      // マスクされる
      output_tokens: string;     // マスクされる
      [key: string]: any;
    };
    wasInterrupted?: boolean;
  };
}
```

### 3.3 Notification

システム通知イベント。

```typescript
interface NotificationEvent extends CommonEventData {
  hook_event_name: "Notification";
  message: string;               // 通知メッセージ
}
```

例：
```json
{
  "message": "Claude is waiting for your input"
}
```

### 3.4 Stop

セッション終了イベント。

```typescript
interface StopEvent extends CommonEventData {
  hook_event_name: "Stop";
  // 追加フィールドなし
}
```

### 3.5 SubagentStop

サブエージェント終了イベント。

```typescript
interface SubagentStopEvent extends CommonEventData {
  hook_event_name: "SubagentStop";
  // transcript_pathから詳細情報を読み取る
}
```

## 4. トランスクリプトファイル形式

`transcript_path`で指定されるJSONLファイルの形式：

```typescript
// 各行が1つのメッセージ
interface TranscriptMessage {
  role: "user" | "assistant";
  content: Array<{
    type: "text" | "tool_use" | "tool_result";
    text?: string;
    id?: string;
    name?: string;
    input?: any;
    content?: any;
  }>;
  timestamp?: string;
}
```

## 5. 現在の実装の問題点

### 5.1 イベント間の状態共有不可

**問題**: PreToolUseで生成した情報（task_id等）をPostToolUseで参照できない

**影響**: 
- 並列タスク実行時のマッチング不可
- スレッドへの結果投稿失敗

### 5.2 タスク識別情報の欠如

**問題**: 同一セッション内の複数タスクを区別する手段がない

**影響**:
- Task応答とリクエストの紐付け不可
- SubagentStopでの適切なスレッド選択不可

## 6. 改善提案

### 6.1 短期的改善（現在の制約内）

#### 提案1: コンテンツベースマッチング
```python
# tool_inputの内容でタスクを識別
def match_task_by_content(tool_input):
    key = f"{tool_input.get('description')}:{tool_input.get('prompt')}"
    return hashlib.md5(key.encode()).hexdigest()[:8]
```

#### 提案2: タイムスタンプ活用
- イベント受信時刻を記録
- 時系列での近似マッチング

### 6.2 中期的改善（Claude Code API拡張）

#### 提案1: task_idフィールド追加
```json
{
  "hook_event_name": "PreToolUse",
  "tool_name": "Task",
  "tool_task_id": "task_20250721_030306_8693",  // 新規フィールド
  "tool_input": {...}
}
```

#### 提案2: parent_event_id追加
```json
{
  "hook_event_name": "PostToolUse",
  "parent_event_id": "pretooluse_12345",  // 関連イベントID
  "tool_response": {...}
}
```

### 6.3 長期的改善（アーキテクチャ見直し）

#### 提案1: ステートフルなHookシステム
- セッション内でのコンテキスト保持
- イベント間での情報伝播

#### 提案2: Webhook拡張
- リクエスト/レスポンス型のインタラクション
- Hook側からの情報注入

## 7. Discord通知の改善案

### 7.1 視覚的改善

1. **リッチエンベッド活用**
   - プログレスバー表示
   - 実行時間の視覚化
   - エラー/成功の色分け強化

2. **インタラクティブ要素**
   - ボタンによるアクション
   - リアクションでのフィードバック

### 7.2 情報密度の最適化

1. **折りたたみ可能な詳細**
   - 長いコード/ログの省略表示
   - 「詳細を見る」リンク

2. **要約ビュー**
   - 重要情報のハイライト
   - 実行統計のダッシュボード

### 7.3 スレッド活用の最適化

1. **自動アーカイブ設定**
   - 24時間後の自動アーカイブ
   - 重要スレッドのピン留め

2. **スレッドタグ付け**
   - 成功/失敗/進行中のステータス
   - プロジェクト別の分類

## 8. 実装優先順位

1. **最優先**: タスクマッチング問題の解決
2. **高**: SubagentStop時の適切なスレッド投稿
3. **中**: Discord通知の視覚的改善
4. **低**: インタラクティブ要素の追加

## 9. まとめ

本仕様書は、Claude Code Hookシステムの現状を正確に文書化し、Discord通知システムの改善に向けた具体的な提案を示しました。特に、並列タスク実行時の課題を解決することで、より豊かなユーザー体験を提供できるようになります。