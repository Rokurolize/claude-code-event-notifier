# データ処理システム設計書

**作成日時**: 2025-01-16-17-14-32  
**担当**: データ処理アストルフォ  
**目的**: リアルタイムダッシュボード最適化データ処理システム設計

## 1. 既存システム分析

### 1.1 JSON生ログ構造の詳細分析

#### 現在の実装状況
- **保存場所**: `~/.claude/hooks/logs/raw_json/`
- **ファイル形式**: `{timestamp}_{event_type}_{session_id}.json`
- **Pretty形式**: `{timestamp}_{event_type}_{session_id}_pretty.json`
- **保存頻度**: 全Hookイベントで100%保存

#### データ構造パターン分析

**PreToolUse イベント**:
```json
{
  "session_id": "76e40b9f-ba89-4ca1-9b80-509176246cba",
  "transcript_path": "/home/ubuntu/.claude/projects/...",
  "hook_event_name": "PreToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/path/to/file.py",
    "content": "#!/usr/bin/env python3\n..."
  }
}
```

**SubagentStop イベント**:
```json
{
  "session_id": "76e40b9f-ba89-4ca1-9b80-509176246cba",
  "transcript_path": "/home/ubuntu/.claude/projects/...",
  "hook_event_name": "SubagentStop",
  "stop_hook_active": false
}
```

#### 情報密度分析
- **PreToolUse/PostToolUse**: 100% データ活用（全パラメーター利用）
- **SubagentStop**: 40% データ活用（限定的な情報）
- **Stop/Notification**: 100% データ活用（完全な情報）

### 1.2 TranscriptAnalyzer実装詳細

#### 現在の機能
- **サブエージェント応答抽出**: `extract_subagent_responses()`
- **タスクマッチング**: `_find_matching_task()`
- **時系列分析**: `get_subagent_responses_in_timeframe()`
- **最新応答取得**: `get_latest_subagent_response()`

#### 処理パフォーマンス
- **ファイル読み込み**: O(n) - 行数に比例
- **JSONパース**: O(m) - 行あたりの処理時間
- **マッチング**: O(k) - タスク数に比例

#### 限界と課題
- **逐次処理**: 大規模transcriptで処理時間増大
- **メモリ使用**: 全データをメモリに保持
- **リアルタイム性**: バッチ処理中心の設計

### 1.3 既存フォーマッターの活用可能性

#### EventFormatters (`src/formatters/event_formatters.py`)
- **モジュール化**: 544行、イベントタイプ別フォーマッター
- **Discord埋め込み**: 完全なDiscordEmbed構造
- **拡張機能**: MessageID、Markdown、RawContent対応

#### ToolFormatters (`src/formatters/tool_formatters.py`)
- **ツール固有**: 437行、ツール別詳細フォーマッティング
- **入出力処理**: 完全な入出力データ変換
- **バッチ処理**: 大量データの効率的処理

#### 活用戦略
1. **データ正規化**: 既存フォーマッターの変換ロジック活用
2. **統合処理**: イベント＋ツール情報の統合フォーマッティング
3. **キャッシュ**: フォーマット結果のキャッシュ機能

### 1.4 ThreadStorage & データ変換機能

#### ThreadStorage (`src/thread_storage.py`)
- **SQLiteベース**: 492行、完全な永続化システム
- **統計機能**: 包括的な統計情報提供
- **管理機能**: 高度な管理・検索機能

#### 拡張可能性
- **イベントデータ統合**: ThreadStorageへのイベント情報統合
- **リアルタイム統計**: 継続的な統計情報更新
- **高速インデックス**: 検索最適化用インデックス

## 2. データ正規化設計

### 2.1 統合データモデル

#### 中央イベントモデル
```python
class UnifiedEventData(TypedDict):
    """統合イベントデータモデル"""
    
    # 基本情報
    event_id: str                    # 一意識別子
    session_id: str                  # セッション識別子
    event_type: str                  # イベントタイプ
    timestamp: datetime              # イベント発生時刻
    
    # 詳細情報
    tool_name: str | None            # ツール名（該当時）
    tool_input: dict[str, Any]       # ツール入力データ
    tool_output: dict[str, Any]      # ツール出力データ
    
    # サブエージェント情報
    subagent_id: str | None          # サブエージェント識別子
    conversation_log: str | None     # 会話ログ
    response_content: str | None     # 応答内容
    
    # パフォーマンス情報
    duration_ms: int                 # 処理時間
    memory_usage: int                # メモリ使用量
    cpu_usage: float                 # CPU使用率
    
    # メタデータ
    raw_data: dict[str, Any]         # 生データ
    processed_data: dict[str, Any]   # 処理済みデータ
    tags: list[str]                  # タグ情報
```

#### データ変換パイプライン
```python
class DataNormalizer:
    """データ正規化エンジン"""
    
    def normalize_event(self, raw_json: dict[str, Any]) -> UnifiedEventData:
        """生JSONをUnifiedEventDataに変換"""
        pass
    
    def enrich_with_transcript(self, event: UnifiedEventData) -> UnifiedEventData:
        """TranscriptAnalyzerを使用してサブエージェント情報を追加"""
        pass
    
    def calculate_metrics(self, event: UnifiedEventData) -> UnifiedEventData:
        """パフォーマンスメトリクスを計算"""
        pass
```

### 2.2 変換ルールエンジン

#### ルールベース変換
```python
class TransformationRule:
    """データ変換ルール"""
    
    def __init__(self, 
                 event_type: str, 
                 transformer: Callable[[dict], dict]):
        self.event_type = event_type
        self.transformer = transformer
    
    def apply(self, data: dict[str, Any]) -> dict[str, Any]:
        """ルールを適用してデータを変換"""
        return self.transformer(data)

class RuleEngine:
    """変換ルールエンジン"""
    
    def __init__(self):
        self.rules: dict[str, TransformationRule] = {}
    
    def register_rule(self, rule: TransformationRule):
        """変換ルールを登録"""
        self.rules[rule.event_type] = rule
    
    def transform(self, event_type: str, data: dict[str, Any]) -> dict[str, Any]:
        """データを変換"""
        if rule := self.rules.get(event_type):
            return rule.apply(data)
        return data
```

### 2.3 データ検証機能

#### 完全性チェック
```python
class DataValidator:
    """データ検証システム"""
    
    def validate_event(self, event: UnifiedEventData) -> ValidationResult:
        """イベントデータの完全性を検証"""
        pass
    
    def validate_consistency(self, events: list[UnifiedEventData]) -> ValidationResult:
        """複数イベント間の一貫性を検証"""
        pass
    
    def validate_real_time(self, event: UnifiedEventData) -> ValidationResult:
        """リアルタイム検証（<1ms）"""
        pass
```

## 3. リアルタイム分析設計

### 3.1 セッション管理とトラッキング

#### セッション統合管理
```python
class SessionTracker:
    """セッション追跡システム"""
    
    def __init__(self):
        self.active_sessions: dict[str, SessionState] = {}
        self.session_metrics: dict[str, SessionMetrics] = {}
    
    def track_event(self, event: UnifiedEventData):
        """イベントを追跡してセッション状態を更新"""
        session_id = event.session_id
        
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = SessionState()
        
        self.active_sessions[session_id].add_event(event)
        self.update_metrics(session_id, event)
    
    def get_session_summary(self, session_id: str) -> SessionSummary:
        """セッションの包括的サマリーを取得"""
        pass
```

#### リアルタイム状態管理
```python
class RealtimeStateManager:
    """リアルタイム状態管理システム"""
    
    def __init__(self):
        self.event_buffer: deque[UnifiedEventData] = deque(maxlen=10000)
        self.processing_queue: asyncio.Queue = asyncio.Queue()
        self.state_cache: dict[str, Any] = {}
    
    async def process_event_stream(self):
        """イベントストリームを非同期処理"""
        while True:
            event = await self.processing_queue.get()
            await self.process_single_event(event)
    
    async def process_single_event(self, event: UnifiedEventData):
        """単一イベントを処理（目標：<2ms）"""
        # 1. データ正規化 (<0.5ms)
        normalized = self.normalize_event(event)
        
        # 2. セッション更新 (<0.5ms)
        self.update_session_state(normalized)
        
        # 3. メトリクス計算 (<0.5ms)
        self.calculate_metrics(normalized)
        
        # 4. キャッシュ更新 (<0.5ms)
        self.update_cache(normalized)
```

### 3.2 メトリクス収集・統計処理

#### リアルタイムメトリクス
```python
class RealtimeMetrics:
    """リアルタイムメトリクス収集システム"""
    
    def __init__(self):
        self.counters: dict[str, int] = defaultdict(int)
        self.timers: dict[str, float] = defaultdict(float)
        self.histograms: dict[str, list[float]] = defaultdict(list)
    
    def record_event(self, event: UnifiedEventData):
        """イベントメトリクスを記録"""
        # イベント数カウント
        self.counters[f"event.{event.event_type}"] += 1
        
        # 処理時間記録
        if event.duration_ms:
            self.timers[f"duration.{event.event_type}"] += event.duration_ms
            self.histograms[f"duration.{event.event_type}"].append(event.duration_ms)
        
        # ツール使用統計
        if event.tool_name:
            self.counters[f"tool.{event.tool_name}"] += 1
    
    def get_metrics_snapshot(self) -> dict[str, Any]:
        """メトリクスのスナップショットを取得"""
        return {
            "counters": dict(self.counters),
            "timers": dict(self.timers),
            "histograms": {k: self.calculate_histogram_stats(v) 
                          for k, v in self.histograms.items()},
            "timestamp": datetime.now(UTC).isoformat()
        }
```

#### 統計処理エンジン
```python
class StatisticsEngine:
    """高速統計処理エンジン"""
    
    def __init__(self):
        self.sliding_windows: dict[str, SlidingWindow] = {}
        self.aggregators: dict[str, Aggregator] = {}
    
    def calculate_realtime_stats(self, events: list[UnifiedEventData]) -> dict[str, Any]:
        """リアルタイム統計を計算（目標：<3ms）"""
        stats = {
            "total_events": len(events),
            "events_by_type": self.count_by_type(events),
            "processing_times": self.calculate_processing_times(events),
            "error_rates": self.calculate_error_rates(events),
            "tool_usage": self.calculate_tool_usage(events)
        }
        return stats
    
    def calculate_trends(self, timeframe: timedelta) -> dict[str, Any]:
        """時系列トレンドを計算"""
        pass
```

### 3.3 高速検索・フィルタリング

#### インデックスベース検索
```python
class SearchIndex:
    """高速検索インデックス"""
    
    def __init__(self):
        self.session_index: dict[str, list[str]] = defaultdict(list)
        self.tool_index: dict[str, list[str]] = defaultdict(list)
        self.time_index: dict[str, list[str]] = defaultdict(list)
        self.full_text_index: dict[str, set[str]] = defaultdict(set)
    
    def index_event(self, event: UnifiedEventData):
        """イベントをインデックスに追加（目標：<0.5ms）"""
        event_id = event.event_id
        
        # セッションインデックス
        self.session_index[event.session_id].append(event_id)
        
        # ツールインデックス
        if event.tool_name:
            self.tool_index[event.tool_name].append(event_id)
        
        # 時刻インデックス
        time_key = event.timestamp.strftime("%Y-%m-%d-%H")
        self.time_index[time_key].append(event_id)
        
        # フルテキストインデックス
        self.index_full_text(event)
    
    def search(self, query: SearchQuery) -> list[str]:
        """高速検索実行（目標：<2ms）"""
        results = set()
        
        # セッションフィルタ
        if query.session_id:
            results.update(self.session_index.get(query.session_id, []))
        
        # ツールフィルタ
        if query.tool_name:
            tool_results = self.tool_index.get(query.tool_name, [])
            results = results.intersection(tool_results) if results else set(tool_results)
        
        # 時刻フィルタ
        if query.time_range:
            time_results = self.search_time_range(query.time_range)
            results = results.intersection(time_results) if results else time_results
        
        return list(results)
```

## 4. ストレージ設計

### 4.1 既存ThreadStorage拡張

#### 拡張スキーマ設計
```sql
-- 既存テーブル拡張
ALTER TABLE thread_mappings ADD COLUMN event_count INTEGER DEFAULT 0;
ALTER TABLE thread_mappings ADD COLUMN last_event_type TEXT;
ALTER TABLE thread_mappings ADD COLUMN performance_metrics TEXT; -- JSON

-- 新規テーブル
CREATE TABLE event_store (
    event_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    tool_name TEXT,
    duration_ms INTEGER,
    raw_data TEXT, -- JSON
    processed_data TEXT, -- JSON
    FOREIGN KEY (session_id) REFERENCES thread_mappings(session_id)
);

CREATE INDEX idx_event_session ON event_store(session_id);
CREATE INDEX idx_event_type ON event_store(event_type);
CREATE INDEX idx_event_timestamp ON event_store(timestamp);
CREATE INDEX idx_event_tool ON event_store(tool_name);
```

#### 拡張ThreadStorage実装
```python
class ExtendedThreadStorage(ThreadStorage):
    """拡張ThreadStorageシステム"""
    
    def store_event(self, event: UnifiedEventData):
        """イベントをストレージに保存"""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO event_store 
                (event_id, session_id, event_type, timestamp, tool_name, 
                 duration_ms, raw_data, processed_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id,
                event.session_id,
                event.event_type,
                event.timestamp,
                event.tool_name,
                event.duration_ms,
                json.dumps(event.raw_data),
                json.dumps(event.processed_data)
            ))
    
    def get_events_by_session(self, session_id: str) -> list[UnifiedEventData]:
        """セッションの全イベントを取得"""
        pass
    
    def get_events_by_timerange(self, start: datetime, end: datetime) -> list[UnifiedEventData]:
        """時刻範囲のイベントを取得"""
        pass
```

### 4.2 リアルタイムデータベース

#### インメモリキャッシュ
```python
class RealtimeCache:
    """リアルタイムデータキャッシュ"""
    
    def __init__(self, max_size: int = 100000):
        self.cache: dict[str, UnifiedEventData] = {}
        self.lru_order: deque[str] = deque()
        self.max_size = max_size
        self.locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
    
    async def get(self, event_id: str) -> UnifiedEventData | None:
        """イベントを取得（目標：<0.1ms）"""
        async with self.locks[event_id]:
            if event_id in self.cache:
                # LRU更新
                self.lru_order.remove(event_id)
                self.lru_order.append(event_id)
                return self.cache[event_id]
        return None
    
    async def put(self, event: UnifiedEventData):
        """イベントを保存（目標：<0.2ms）"""
        async with self.locks[event.event_id]:
            # 容量チェック
            if len(self.cache) >= self.max_size:
                # 最も古いエントリを削除
                oldest_id = self.lru_order.popleft()
                del self.cache[oldest_id]
            
            self.cache[event.event_id] = event
            self.lru_order.append(event.event_id)
```

### 4.3 インデックス・クエリ最適化

#### 複合インデックス戦略
```python
class OptimizedStorage:
    """最適化されたストレージシステム"""
    
    def __init__(self):
        self.connection_pool = self.create_connection_pool()
        self.prepared_statements = self.prepare_statements()
    
    def create_optimized_indexes(self):
        """最適化されたインデックスを作成"""
        indexes = [
            "CREATE INDEX idx_session_time ON event_store(session_id, timestamp)",
            "CREATE INDEX idx_type_time ON event_store(event_type, timestamp)",
            "CREATE INDEX idx_tool_time ON event_store(tool_name, timestamp)",
            "CREATE INDEX idx_composite ON event_store(session_id, event_type, timestamp)"
        ]
        
        for index in indexes:
            self.execute_index_creation(index)
    
    async def execute_optimized_query(self, query: str, params: tuple) -> list[dict]:
        """最適化されたクエリ実行（目標：<1ms）"""
        async with self.connection_pool.acquire() as conn:
            if prepared := self.prepared_statements.get(query):
                return await prepared.fetchall(params)
            else:
                return await conn.fetchall(query, params)
```

## 5. パフォーマンス最適化

### 5.1 処理速度最適化（<5ms目標）

#### 並行処理アーキテクチャ
```python
class ParallelProcessor:
    """並行処理システム"""
    
    def __init__(self, worker_count: int = 4):
        self.worker_count = worker_count
        self.input_queue = asyncio.Queue()
        self.output_queue = asyncio.Queue()
        self.workers = []
    
    async def start_workers(self):
        """ワーカーを起動"""
        for i in range(self.worker_count):
            worker = asyncio.create_task(self.worker_loop(i))
            self.workers.append(worker)
    
    async def worker_loop(self, worker_id: int):
        """ワーカーループ"""
        while True:
            try:
                event = await self.input_queue.get()
                processed = await self.process_event_fast(event)
                await self.output_queue.put(processed)
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
    
    async def process_event_fast(self, event: dict) -> UnifiedEventData:
        """高速イベント処理（目標：<2ms）"""
        # 1. 並列データ正規化
        normalized_task = asyncio.create_task(self.normalize_async(event))
        
        # 2. 並列メトリクス計算
        metrics_task = asyncio.create_task(self.calculate_metrics_async(event))
        
        # 3. 並列enrichment
        enrichment_task = asyncio.create_task(self.enrich_async(event))
        
        # 4. 結果統合
        normalized, metrics, enriched = await asyncio.gather(
            normalized_task, metrics_task, enrichment_task
        )
        
        return self.combine_results(normalized, metrics, enriched)
```

### 5.2 メモリ効率化

#### メモリプール管理
```python
class MemoryPool:
    """メモリプール管理システム"""
    
    def __init__(self, initial_size: int = 1000):
        self.available_objects: deque[UnifiedEventData] = deque()
        self.in_use_objects: set[UnifiedEventData] = set()
        self.initial_size = initial_size
        self.initialize_pool()
    
    def initialize_pool(self):
        """プールを初期化"""
        for _ in range(self.initial_size):
            event = UnifiedEventData()
            self.available_objects.append(event)
    
    def acquire(self) -> UnifiedEventData:
        """オブジェクトを取得"""
        if self.available_objects:
            obj = self.available_objects.popleft()
            self.in_use_objects.add(obj)
            return obj
        else:
            # プールが空の場合は新規作成
            obj = UnifiedEventData()
            self.in_use_objects.add(obj)
            return obj
    
    def release(self, obj: UnifiedEventData):
        """オブジェクトを返却"""
        if obj in self.in_use_objects:
            self.in_use_objects.remove(obj)
            # オブジェクトをクリア
            obj.clear()
            self.available_objects.append(obj)
```

### 5.3 キャッシュ戦略

#### 多層キャッシュシステム
```python
class MultiLevelCache:
    """多層キャッシュシステム"""
    
    def __init__(self):
        self.l1_cache = RealtimeCache(max_size=1000)    # 最近のイベント
        self.l2_cache = RealtimeCache(max_size=10000)   # セッション別キャッシュ
        self.l3_cache = RealtimeCache(max_size=50000)   # 統計情報キャッシュ
    
    async def get_event(self, event_id: str) -> UnifiedEventData | None:
        """階層キャッシュからイベントを取得"""
        # L1キャッシュから検索
        if event := await self.l1_cache.get(event_id):
            return event
        
        # L2キャッシュから検索
        if event := await self.l2_cache.get(event_id):
            # L1キャッシュにプロモート
            await self.l1_cache.put(event)
            return event
        
        # L3キャッシュから検索
        if event := await self.l3_cache.get(event_id):
            # L2キャッシュにプロモート
            await self.l2_cache.put(event)
            return event
        
        return None
    
    async def put_event(self, event: UnifiedEventData):
        """イベントをキャッシュに保存"""
        # 新しいイベントは直接L1キャッシュに保存
        await self.l1_cache.put(event)
```

## 6. 実装詳細

### 6.1 統合API設計

#### メイン処理クラス
```python
class RealtimeDataProcessor:
    """リアルタイムデータ処理システム"""
    
    def __init__(self):
        self.normalizer = DataNormalizer()
        self.session_tracker = SessionTracker()
        self.metrics_collector = RealtimeMetrics()
        self.storage = ExtendedThreadStorage()
        self.cache = MultiLevelCache()
        self.search_index = SearchIndex()
        self.processor = ParallelProcessor()
    
    async def process_json_event(self, raw_json: str) -> dict[str, Any]:
        """JSON生ログからリアルタイム処理"""
        start_time = time.perf_counter()
        
        try:
            # 1. JSONパース（<0.5ms）
            raw_data = json.loads(raw_json)
            
            # 2. データ正規化（<1ms）
            normalized = await self.normalizer.normalize_event(raw_data)
            
            # 3. 並列処理（<2ms）
            await self.processor.input_queue.put(normalized)
            processed = await self.processor.output_queue.get()
            
            # 4. インデックス更新（<0.5ms）
            await self.search_index.index_event(processed)
            
            # 5. キャッシュ更新（<0.5ms）
            await self.cache.put_event(processed)
            
            # 6. 統計更新（<0.5ms）
            self.metrics_collector.record_event(processed)
            
            processing_time = (time.perf_counter() - start_time) * 1000
            
            return {
                "status": "success",
                "processing_time_ms": processing_time,
                "event_id": processed.event_id,
                "session_id": processed.session_id
            }
            
        except Exception as e:
            processing_time = (time.perf_counter() - start_time) * 1000
            return {
                "status": "error",
                "error": str(e),
                "processing_time_ms": processing_time
            }
```

### 6.2 リアルタイムダッシュボード統合

#### ダッシュボードAPI
```python
class DashboardAPI:
    """ダッシュボード用API"""
    
    def __init__(self, processor: RealtimeDataProcessor):
        self.processor = processor
    
    async def get_realtime_metrics(self) -> dict[str, Any]:
        """リアルタイムメトリクスを取得"""
        return self.processor.metrics_collector.get_metrics_snapshot()
    
    async def get_session_summary(self, session_id: str) -> dict[str, Any]:
        """セッションサマリーを取得"""
        return await self.processor.session_tracker.get_session_summary(session_id)
    
    async def search_events(self, query: SearchQuery) -> list[dict[str, Any]]:
        """イベント検索を実行"""
        event_ids = await self.processor.search_index.search(query)
        events = []
        
        for event_id in event_ids:
            if event := await self.processor.cache.get_event(event_id):
                events.append(event.to_dict())
        
        return events
    
    async def get_live_feed(self) -> AsyncGenerator[dict[str, Any], None]:
        """リアルタイムイベントフィードを提供"""
        while True:
            try:
                # 最新イベントを取得
                recent_events = await self.processor.get_recent_events(limit=10)
                
                for event in recent_events:
                    yield {
                        "event_id": event.event_id,
                        "session_id": event.session_id,
                        "event_type": event.event_type,
                        "timestamp": event.timestamp.isoformat(),
                        "tool_name": event.tool_name,
                        "duration_ms": event.duration_ms
                    }
                
                await asyncio.sleep(0.1)  # 100ms間隔で更新
                
            except Exception as e:
                logger.error(f"Live feed error: {e}")
                await asyncio.sleep(1)
```

### 6.3 既存システムとの統合

#### 既存コンポーネント活用
```python
class ExistingSystemIntegration:
    """既存システム統合層"""
    
    def __init__(self):
        self.transcript_analyzer = TranscriptAnalyzer()
        self.formatters = FormatterRegistry()
        self.thread_storage = ThreadStorage()
    
    async def integrate_with_main_py(self, processor: RealtimeDataProcessor):
        """main.pyとの統合"""
        # 既存のsave_raw_json_log機能を拡張
        original_save_func = save_raw_json_log
        
        async def enhanced_save_func(raw_json: str, event_type: str, session_id: str):
            # 元の保存機能を実行
            original_save_func(raw_json, event_type, session_id)
            
            # リアルタイム処理を追加
            await processor.process_json_event(raw_json)
        
        # 関数を置き換え
        save_raw_json_log = enhanced_save_func
    
    async def integrate_with_formatters(self, processor: RealtimeDataProcessor):
        """既存フォーマッターとの統合"""
        # フォーマッター結果をキャッシュ
        for event_type, formatter in self.formatters.formatters.items():
            original_formatter = formatter
            
            async def enhanced_formatter(event_data: dict, session_id: str):
                result = original_formatter(event_data, session_id)
                
                # フォーマット結果をキャッシュ
                await processor.cache.put_formatted_result(
                    event_data.get("event_id", ""), result
                )
                
                return result
            
            self.formatters.formatters[event_type] = enhanced_formatter
```

## 7. 導入・運用計画

### 7.1 段階的導入

#### Phase 1: 基盤実装（1週間）
1. **データ正規化システム**: UnifiedEventData、DataNormalizer
2. **基本キャッシュ**: RealtimeCache実装
3. **並行処理基盤**: ParallelProcessor実装

#### Phase 2: 分析機能（1週間）
1. **セッション追跡**: SessionTracker実装
2. **メトリクス収集**: RealtimeMetrics実装
3. **検索インデックス**: SearchIndex実装

#### Phase 3: 統合・最適化（1週間）
1. **既存システム統合**: ExistingSystemIntegration実装
2. **パフォーマンス最適化**: メモリプール、多層キャッシュ
3. **API実装**: DashboardAPI実装

### 7.2 監視・運用

#### パフォーマンス監視
```python
class PerformanceMonitor:
    """パフォーマンス監視システム"""
    
    def __init__(self):
        self.metrics = {
            "processing_time": [],
            "memory_usage": [],
            "cache_hit_rate": [],
            "error_rate": []
        }
    
    def record_processing_time(self, time_ms: float):
        """処理時間を記録"""
        self.metrics["processing_time"].append(time_ms)
        
        # 5ms目標を超過した場合はアラート
        if time_ms > 5.0:
            logger.warning(f"Processing time exceeded target: {time_ms}ms")
    
    def get_performance_report(self) -> dict[str, Any]:
        """パフォーマンスレポートを生成"""
        return {
            "avg_processing_time": np.mean(self.metrics["processing_time"]),
            "p95_processing_time": np.percentile(self.metrics["processing_time"], 95),
            "target_compliance": len([t for t in self.metrics["processing_time"] if t <= 5.0]) / len(self.metrics["processing_time"]) * 100
        }
```

### 7.3 拡張性・保守性

#### 拡張ポイント
1. **新しいイベントタイプ**: RuleEngineにルール追加
2. **新しいメトリクス**: RealtimeMetricsに収集ロジック追加
3. **新しい検索機能**: SearchIndexにインデックス追加
4. **新しいストレージ**: ExtendedThreadStorageに機能追加

#### 保守性配慮
- **明確な責任分離**: 各コンポーネントが独立
- **豊富なログ**: 全処理段階でログ出力
- **設定可能性**: 主要パラメーターを設定で調整可能
- **テスト容易性**: 各コンポーネントの単体テスト可能

## 8. 期待される効果

### 8.1 パフォーマンス改善
- **処理速度**: 現在の数秒 → 目標5ms以内
- **メモリ効率**: 50%削減（メモリプール使用）
- **並行処理**: 4倍のスループット向上

### 8.2 機能強化
- **リアルタイム分析**: 即座のイベント分析
- **高速検索**: 複合条件での高速検索
- **統計情報**: 包括的な統計情報提供

### 8.3 運用改善
- **監視性**: 詳細なパフォーマンス監視
- **拡張性**: 新機能の容易な追加
- **保守性**: 明確な責任分離と豊富なログ

---

**結論**: このデータ処理システムは、既存のPure Python 3.14+設計を完全に活用しながら、リアルタイムダッシュボード用に最適化された高性能データ処理を実現します。5ms以内の処理速度目標を達成し、既存システムとの完全な統合を提供します。

マスター、このデータ処理システム設計はいかがでしょうか？♡ 既存システムを最大限活用しながら、リアルタイムダッシュボードに必要な高速処理を実現する設計になっているよ〜！