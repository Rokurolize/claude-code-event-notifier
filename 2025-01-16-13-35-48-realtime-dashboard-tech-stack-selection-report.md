# 技術スタック選定レポート - リアルタイムダッシュボード

**調査者**: 技術スタック調査アストルフォ  
**調査日時**: 2025-01-16 13:35:48  
**目的**: Claude Code Event Notifier のリアルタイムダッシュボード構築に最適な技術スタックの選定  

## 1. バックエンド技術選定

### Python Web フレームワーク比較

#### 🏆 **FastAPI** (推奨)
**優位点**:
- **Pure Python 3.14+との親和性**: 型ヒント完全活用、既存のTypedDictをそのまま使用可能
- **WebSocket標準サポート**: リアルタイム通信がネイティブ実装
- **非同期処理**: 既存のHTTPクライアントをasyncioで拡張可能
- **Auto-Documentation**: OpenAPI/Swagger自動生成
- **軽量**: 必要最小限の依存関係

**既存システムとの統合**:
```python
# 既存のTypedDictをそのまま活用
from pydantic import BaseModel
from src.core.config import DiscordConfiguration

class DashboardConfig(BaseModel):
    discord_config: DiscordConfiguration
    websocket_port: int = 8000
```

#### 🥈 **Flask + Flask-SocketIO** (代替案)
**優位点**:
- **既存HTTPクライアントとの親和性**: 同期処理ベースで統合が容易
- **シンプル**: 学習コストが低い
- **WebSocket対応**: Flask-SocketIOで実現

**制約**:
- 非同期処理のためのWorker設定が必要
- 型ヒント活用が限定的

#### ❌ **Django** (非推奨)
**理由**: Zero Dependencies理念に反する重量級フレームワーク

### リアルタイム通信方式比較

#### 🏆 **WebSocket** (推奨)
**優位点**:
- **双方向通信**: サーバー → クライアント、クライアント → サーバー
- **低レイテンシ**: 500ms以内の要求を満たす
- **FastAPI標準サポート**: 追加依存関係なし

**実装例**:
```python
# FastAPI WebSocket実装
from fastapi import WebSocket
from src.core.config import ConfigLoader

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # 既存のThreadStorageからリアルタイムデータを送信
    while True:
        data = await get_realtime_data()
        await websocket.send_json(data)
```

#### 🥈 **Server-Sent Events (SSE)** (代替案)
**優位点**:
- **標準HTTP**: 追加プロトコル不要
- **サーバー → クライアント**: ダッシュボード用途に適している
- **自動再接続**: ブラウザ標準機能

**制約**:
- 単方向通信のみ

#### ❌ **Polling** (非推奨)
**理由**: 500ms以内の要求を満たすには非効率

### 非同期処理戦略

#### 🏆 **asyncio + 既存ThreadStorage拡張** (推奨)
```python
import asyncio
from src.thread_storage import ThreadStorage

class AsyncThreadStorage(ThreadStorage):
    async def get_realtime_metrics(self) -> dict:
        # 既存のSQLiteベースをasyncioで拡張
        return await asyncio.to_thread(self.get_stats)
```

## 2. フロントエンド技術選定

### JavaScript フレームワーク比較

#### 🏆 **Vanilla JavaScript + Web Components** (推奨)
**優位点**:
- **Zero Dependencies理念**: 外部フレームワーク不要
- **Web標準**: 長期的安定性
- **軽量**: 最小限のJavaScript
- **TypeScript対応**: 型安全性確保

**実装例**:
```javascript
// WebSocket接続とリアルタイム更新
class RealtimeDashboard extends HTMLElement {
    constructor() {
        super();
        this.websocket = new WebSocket('ws://localhost:8000/ws');
        this.websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.updateMetrics(data);
        };
    }
    
    updateMetrics(data) {
        // メトリクス表示の更新
        this.querySelector('#active-threads').textContent = data.active_threads;
        this.querySelector('#message-count').textContent = data.message_count;
    }
}
```

#### 🥈 **Vue.js** (軽量代替案)
**優位点**:
- **学習コスト低**: 直感的なAPI
- **WebSocket統合**: 容易な実装
- **TypeScript対応**: 型安全性

**制約**:
- 外部依存関係が発生（Zero Dependencies理念に反する）

#### ❌ **React** (非推奨)
**理由**: 重量級で今回の用途にはオーバースペック

### UI/UX ライブラリ選定

#### 🏆 **CSS Grid + Flexbox + CSS Variables** (推奨)
**優位点**:
- **Web標準**: 外部依存なし
- **レスポンシブ**: モバイル対応
- **カスタマイズ性**: 完全制御可能

**実装例**:
```css
/* ダッシュボードレイアウト */
.dashboard {
    display: grid;
    grid-template-columns: 1fr 2fr 1fr;
    gap: 1rem;
    padding: 1rem;
}

.metrics-card {
    background: var(--card-bg);
    border-radius: 8px;
    padding: 1rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
```

#### 🥈 **Tailwind CSS** (代替案)
**優位点**: 高速開発、一貫性
**制約**: 外部依存関係

## 3. データ処理・ストレージ

### リアルタイムデータストレージ

#### 🏆 **SQLite + 既存ThreadStorage拡張** (推奨)
**優位点**:
- **既存資産活用**: ThreadStorage.pyをそのまま拡張
- **Zero Dependencies**: 標準ライブラリのみ
- **高パフォーマンス**: インメモリ処理

**拡張実装**:
```python
# 既存ThreadStorageの拡張
class RealtimeMetricsStorage(ThreadStorage):
    def get_realtime_metrics(self) -> dict:
        return {
            'active_threads': self.get_active_thread_count(),
            'message_count': self.get_message_count_last_hour(),
            'error_rate': self.get_error_rate(),
            'response_time': self.get_avg_response_time()
        }
```

#### 🥈 **In-Memory Cache + SQLite** (代替案)
**優位点**: 高速アクセス
**制約**: メモリ使用量増加

### メトリクス処理

#### 🏆 **既存JSON生ログ + SQLite集計** (推奨)
```python
# 既存のJSON生ログを活用
import json
from pathlib import Path

class MetricsProcessor:
    def __init__(self, raw_json_path: Path):
        self.raw_json_path = raw_json_path
    
    def process_realtime_metrics(self) -> dict:
        # ~/.claude/hooks/logs/raw_json/ からリアルタイム分析
        recent_files = self.get_recent_json_files()
        return self.aggregate_metrics(recent_files)
```

## 4. 開発環境・ツール

### 開発環境構築

#### 🏆 **uv + Python 3.14+ + 既存設定活用** (推奨)
```bash
# 既存プロジェクトの拡張
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix

# ダッシュボード開発用依存関係追加
uv add fastapi uvicorn websockets --dev

# 既存のmypy/ruff設定をそのまま活用
uv run --python 3.14 python -m mypy src/
uv run --python 3.14 python -m ruff check src/
```

### ビルド・テスト環境

#### 🏆 **既存pytest + 新規統合テスト** (推奨)
```python
# tests/integration/test_realtime_dashboard.py
import pytest
from fastapi.testclient import TestClient
from src.dashboard.app import app

@pytest.mark.integration
def test_websocket_connection():
    client = TestClient(app)
    with client.websocket_connect("/ws") as websocket:
        data = websocket.receive_json()
        assert "active_threads" in data
```

### デプロイメント戦略

#### 🏆 **ローカル開発サーバー** (推奨)
```bash
# 開発サーバー起動
uv run --python 3.14 python -m uvicorn src.dashboard.app:app --reload --port 8000

# バックグラウンド実行
uv run --python 3.14 python -m uvicorn src.dashboard.app:app --port 8000 &
```

## 5. 推奨技術スタック

### 🏆 **最終推奨構成**

```
【バックエンド】
- FastAPI (WebSocket + REST API)
- asyncio (非同期処理)
- SQLite + ThreadStorage拡張 (データ永続化)
- 既存HTTPクライアント拡張 (Discord API)

【フロントエンド】
- Vanilla JavaScript + Web Components
- CSS Grid + Flexbox (レイアウト)
- WebSocket API (リアルタイム通信)
- TypeScript (型安全性)

【データ処理】
- 既存JSON生ログ活用
- SQLiteベースのメトリクス集計
- In-Memory Cache (高速アクセス)

【開発環境】
- uv + Python 3.14+
- 既存mypy/ruff設定活用
- pytest + 統合テスト拡張
```

### 技術選定の理由

1. **Pure Python 3.14+設計との整合性**: 既存のTypedDict、ReadOnly、TypeIsを最大活用
2. **Zero Dependencies理念**: 標準ライブラリ + 最小限の追加依存
3. **既存資産活用**: ThreadStorage、HTTPクライアント、設定管理の拡張
4. **リアルタイム性**: WebSocket + asyncioで500ms以内のレスポンス
5. **保守性**: 既存のコード品質基準を維持

## 6. 実装考慮事項

### パフォーマンス最適化

#### リアルタイム更新の効率化
```python
# 効率的なデータ更新
class RealtimeDataManager:
    def __init__(self):
        self.last_update = 0
        self.cache = {}
    
    async def get_updated_data(self):
        if time.time() - self.last_update > 1.0:  # 1秒キャッシュ
            self.cache = await self.fetch_fresh_data()
            self.last_update = time.time()
        return self.cache
```

### セキュリティ対策

#### WebSocket認証
```python
# 既存Discord認証を活用
async def authenticate_websocket(websocket: WebSocket):
    # 既存のDiscord認証システムを流用
    token = websocket.headers.get("Authorization")
    if not validate_discord_token(token):
        await websocket.close(code=4001)
        return False
    return True
```

### 保守性確保

#### 型安全性の維持
```python
# 既存の型定義を活用
from src.core.config import DiscordConfiguration
from typing import ReadOnly

class DashboardMetrics(TypedDict):
    active_threads: ReadOnly[int]
    message_count: ReadOnly[int]
    error_rate: ReadOnly[float]
    response_time: ReadOnly[float]
```

#### モジュール化設計
```
src/dashboard/
├── __init__.py
├── app.py              # FastAPI アプリケーション
├── websocket.py        # WebSocket エンドポイント
├── metrics.py          # メトリクス処理
├── static/
│   ├── index.html      # ダッシュボード UI
│   ├── dashboard.js    # フロントエンド ロジック
│   └── styles.css      # スタイル定義
└── templates/
    └── dashboard.html  # テンプレート
```

## 7. 実装スケジュール

### Phase 1: 基盤構築 (1-2日)
- [ ] FastAPI プロジェクト設定
- [ ] WebSocket エンドポイント実装
- [ ] 基本的なメトリクス収集

### Phase 2: フロントエンド開発 (2-3日)
- [ ] Vanilla JavaScript ダッシュボード
- [ ] リアルタイム更新機能
- [ ] レスポンシブデザイン

### Phase 3: データ統合 (1-2日)
- [ ] 既存ThreadStorage拡張
- [ ] JSON生ログ分析機能
- [ ] メトリクス集計システム

### Phase 4: 最適化・テスト (1-2日)
- [ ] パフォーマンス調整
- [ ] 統合テスト追加
- [ ] エラーハンドリング強化

## 8. 結論

**選定した技術スタックの特徴**:
- **Pure Python 3.14+設計完全準拠**: 既存の型安全性基盤を最大活用
- **Zero Dependencies理念維持**: 標準ライブラリ + 最小限の追加依存
- **既存資産の完全活用**: ThreadStorage、HTTPクライアント、設定管理を拡張
- **高パフォーマンス**: WebSocket + asyncioで500ms以内の応答
- **保守性重視**: 既存のコード品質基準を維持・拡張

この技術スタックにより、Claude Code Event Notifierの設計思想を損なうことなく、効率的なリアルタイムダッシュボードを構築できます。

---

*"In Pure Python 3.14+ We Trust"*  
*— 技術スタック調査アストルフォ*