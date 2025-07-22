# Discord Channel Segmentation Plan
## チャンネル分離によるDiscord通知最適化計画

### 問題の定義
現在、すべての通知が単一チャンネルに送信されるため、ユーザーにメンションが飛んでも追跡が困難。異なる種類の通知を適切に分離し、目的別のチャンネルに送信する必要がある。

### 通知タイプの粒度分析

#### 1. **イベントベースの分類** (Event-Based Classification)
Claude Codeの基本イベント種類：
- **PreToolUse** - ツール実行前通知
- **PostToolUse** - ツール実行後通知  
- **Notification** - システム通知
- **Stop** - メインエージェント終了
- **SubagentStop** - サブエージェント終了

#### 2. **ツールベースの分類** (Tool-Based Classification)
実際の使用頻度順：
- **Read** (4回) - ファイル読み取り
- **Bash** (3回) - コマンド実行
- **Edit** (2回) - ファイル編集
- **Grep** (1回) - 検索

#### 3. **重要度ベースの分類** (Criticality-Based Classification)
- **Critical** - エラー、セキュリティアラート
- **Important** - タスク完了、重要な変更
- **Informational** - 進行状況、デバッグ情報
- **Low Priority** - 詳細ログ、統計情報

#### 4. **プロジェクトベースの分類** (Project-Based Classification)
- 各プロジェクトディレクトリ別の通知
- 個人用 vs チーム用プロジェクト

### 推奨粒度 (Recommended Granularity)

**レベル1: イベント + 重要度の組み合わせ**
```
1. 🔧 tool-activity     - PreToolUse/PostToolUse (作業進行)
2. 📢 notifications     - Notification (システム通知)  
3. ✅ completion        - Stop/SubagentStop (完了通知)
4. 🚨 alerts           - エラー・警告 (緊急対応)
5. 📊 analytics        - 統計・ログ (分析用)
```

**レベル2: 詳細セグメンテーション**
```
1. 🔧 bash-commands    - Bashツール専用
2. 📝 file-operations  - Read/Edit/Write専用
3. 🔍 search-grep      - 検索関連
4. 🤖 ai-interactions  - Task/LLM関連
5. 📢 system-notices   - Claude Code システム通知
6. ✅ task-completion  - 作業完了
7. 🚨 error-alerts     - エラー・例外
8. 📊 usage-stats      - 使用統計
```

### 設定システム設計

#### 環境変数ベース設定
```bash
# レベル1: 基本分離
DISCORD_CHANNEL_TOOL_ACTIVITY="123456789"
DISCORD_CHANNEL_NOTIFICATIONS="234567890" 
DISCORD_CHANNEL_COMPLETION="345678901"
DISCORD_CHANNEL_ALERTS="456789012"
DISCORD_CHANNEL_ANALYTICS="567890123"

# レベル2: 詳細分離
DISCORD_CHANNEL_BASH_COMMANDS="123456789"
DISCORD_CHANNEL_FILE_OPERATIONS="234567890"
DISCORD_CHANNEL_SEARCH_GREP="345678901"
DISCORD_CHANNEL_AI_INTERACTIONS="456789012"
DISCORD_CHANNEL_SYSTEM_NOTICES="567890123"
DISCORD_CHANNEL_TASK_COMPLETION="678901234"
DISCORD_CHANNEL_ERROR_ALERTS="789012345"
DISCORD_CHANNEL_USAGE_STATS="890123456"

# フォールバック
DISCORD_CHANNEL_DEFAULT="999999999"  # 未分類の通知
```

#### JSON設定ファイル
```json
{
  "discord_channels": {
    "default": "999999999",
    "event_routing": {
      "PreToolUse": {
        "default": "tool-activity",
        "tools": {
          "Bash": "bash-commands",
          "Read": "file-operations", 
          "Edit": "file-operations",
          "Write": "file-operations",
          "Grep": "search-grep",
          "Task": "ai-interactions"
        }
      },
      "PostToolUse": {
        "default": "tool-activity",
        "tools": {
          "Bash": "bash-commands",
          "Read": "file-operations",
          "Edit": "file-operations", 
          "Write": "file-operations",
          "Grep": "search-grep",
          "Task": "ai-interactions"
        }
      },
      "Notification": "system-notices",
      "Stop": "task-completion",
      "SubagentStop": "task-completion"
    },
    "channels": {
      "tool-activity": "123456789",
      "bash-commands": "234567890",
      "file-operations": "345678901",
      "search-grep": "456789012",
      "ai-interactions": "567890123",
      "system-notices": "678901234",
      "task-completion": "789012345",
      "error-alerts": "890123456",
      "usage-stats": "901234567"
    }
  }
}
```

### 実装戦略

#### Phase 1: 基本分離 (2-3 channels)
1. **作業チャンネル** - PreToolUse/PostToolUse
2. **完了チャンネル** - Stop/SubagentStop + 重要なNotification
3. **アラートチャンネル** - エラー・警告

#### Phase 2: 詳細分離 (5-8 channels)
1. ツール別ルーティング実装
2. 重要度判定ロジック追加
3. プロジェクト別オプション

#### Phase 3: 高度な機能
1. 動的チャンネル作成
2. メンション制御
3. スレッド活用
4. 時間帯フィルタリング

### 技術実装計画

#### 1. 設定拡張 (`config.py`)
```python
def get_channel_for_event(event_name: str, tool_name: str = None) -> str:
    """イベントとツールに基づいてチャンネルIDを決定"""
    
def load_channel_config() -> dict:
    """チャンネル設定を環境変数またはJSONから読み込み"""
```

#### 2. ルーティングロジック (`discord_client.py`)
```python
def route_to_channel(event_data: dict, message: dict) -> str:
    """メッセージを適切なチャンネルにルーティング"""
    
def send_to_specific_channel(channel_id: str, message: dict) -> bool:
    """指定チャンネルにメッセージ送信"""
```

#### 3. ハンドラー更新 (`handlers.py`)
```python
def handle_with_routing(event: dict, config: dict) -> dict:
    """ルーティング情報付きでメッセージを返す"""
```

### 移行戦略

#### 段階的移行
1. **既存機能維持** - デフォルトチャンネルで動作継続
2. **オプトイン** - 新設定があれば新機能有効
3. **段階的有効化** - チャンネルごとに個別設定可能

#### 後方互換性
- 既存の`DISCORD_CHANNEL_ID`設定は継続サポート
- 新設定がない場合は従来通り単一チャンネル使用
- 設定エラー時は安全にフォールバック

### テスト計画

#### 1. ユニットテスト
- チャンネルルーティングロジック
- 設定読み込み・検証
- フォールバック動作

#### 2. 統合テスト  
- 各イベントタイプの正しいルーティング
- 複数チャンネルへの同時送信
- エラー状況での動作

#### 3. 本番テスト
- 段階的ロールアウト
- メンション動作確認
- パフォーマンス監視

### 期待される効果

#### ユーザビリティ向上
- **メンション追跡容易** - 関心事別にチャンネル分離
- **ノイズ削減** - 重要な通知が埋もれない
- **コンテキスト保持** - 関連する通知が同じ場所に

#### 運用効率化
- **チーム分担** - チャンネルごとに担当者設定可能
- **アラート最適化** - 緊急度に応じた通知方法
- **分析改善** - 用途別の統計取得

#### 拡張性
- **プロジェクト対応** - 新しいプロジェクトで独立設定
- **カスタマイズ** - ユーザー固有のルーティングルール
- **統合** - 他のツールとの連携可能

### リスク評価

#### 技術リスク
- **設定複雑化** - ユーザーに適切なドキュメント提供必要
- **パフォーマンス** - 複数チャンネル送信時の負荷
- **障害波及** - 一部チャンネル障害時の影響

#### 運用リスク
- **チャンネル作成** - Discord側での適切なチャンネル設定
- **権限管理** - Bot権限の適切な設定
- **メンテナンス** - 設定変更時の影響範囲

### 成功指標

#### 定量指標
- メンション応答時間の短縮
- 重要通知の見落とし減少
- ユーザー満足度向上

#### 定性指標
- チャンネル分離によるコンテキスト改善
- チーム協力の効率化
- システム監視の向上

---

**実装優先度: High**
**実装期間見積もり: 2-3日 (Phase 1), 1週間 (Phase 2)**
**影響範囲: Medium (設定とルーティングロジックのみ)**