# Phase 1 実装ガイド - バックエンド基盤構築

**作成日時**: 2025-01-16-20-30-00  
**Phase**: 1/3 - バックエンド基盤構築  
**目的**: Pure Python 3.14+ 標準ライブラリのみでリアルタイムダッシュボードバックエンドを実装  
**設計原則**: Zero Dependencies + Pure Python 3.14+ 完全遵守

## 🎯 Phase 1 実装目標

### 実装完了判定基準
- ✅ Pure Python 3.14+ HTTPサーバーが正常動作する
- ✅ WebSocketライクなリアルタイム通信が実装される（標準ライブラリのみ使用）
- ✅ 既存 `src/main.py` との統合が完了している
- ✅ ExtendedThreadStorage が実装され、データが永続化される
- ✅ RealtimeDataProcessor が <5ms で処理完了する
- ✅ JSON生ログ監視システムが正常動作する
- ✅ **全機能が Pure Python 3.14+ 標準ライブラリのみで実装されている**

## 📋 前提条件確認

### 必須環境チェック
```bash
# Python 3.14+ 環境確認（必須）
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python --version

# 期待結果: Python 3.14.x
# 3.13以下の場合は作業停止

# Pure Python 3.14+ 機能確認（設計純粋性チェック）
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python -c "from typing import ReadOnly, TypeIs; import os; print(f'ReadOnly: OK, TypeIs: OK, CPU: {os.process_cpu_count()}')"

# 期待結果: "ReadOnly: OK, TypeIs: OK, CPU: X"
# ImportError発生時 → DESIGN VIOLATION - 作業停止

# 現在のプロジェクト構造確認
ls -la src/
ls -la src/core/
ls -la ~/.claude/hooks/.env.discord

# 既存システムの動作確認
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python configure_hooks.py --validate-end-to-end
```

## 🏗️ Step 1: プロジェクト構造準備

### 1.1 ダッシュボード用ディレクトリ構造作成
```bash
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix

# ダッシュボード専用ディレクトリ作成
mkdir -p src/dashboard
mkdir -p src/dashboard/core
mkdir -p src/dashboard/handlers
mkdir -p src/dashboard/static
mkdir -p src/dashboard/templates

# ダッシュボードログディレクトリ
mkdir -p ~/.claude/hooks/dashboard

# 作成確認
ls -la src/dashboard/
```

### 1.2 __init__.py ファイル作成
```bash
# 必要な __init__.py ファイルを作成
touch src/dashboard/__init__.py
touch src/dashboard/core/__init__.py
touch src/dashboard/handlers/__init__.py
```

## 🔧 Step 2: Pure Python 3.14+ HTTP/WebSocketサーバー実装

### 2.1 HTTPサーバー基盤実装
```bash
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix
```

**`src/dashboard/core/http_server.py` 作成:**
```python
#!/usr/bin/env python3
"""
Pure Python 3.14+ HTTPサーバー - Zero Dependencies

http.server + socketserver + asyncio のみ使用
WebSocketライクなSSE（Server-Sent Events）でリアルタイム通信実現
"""

from __future__ import annotations

import json
import threading
import time
import queue
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Dict, Any, Optional, List, Callable, TypeIs
from urllib.parse import urlparse, parse_qs
import logging
from pathlib import Path

# 既存システム統合
import sys
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class SSEConnection:
    """Server-Sent Events 接続管理"""
    
    def __init__(self, handler: BaseHTTPRequestHandler) -> None:
        self.handler = handler
        self.active = True
        self._lock = threading.Lock()
    
    def send_event(self, data: Dict[str, Any], event_type: str = "message") -> bool:
        """SSEイベント送信"""
        if not self.active:
            return False
        
        try:
            with self._lock:
                # SSE形式でデータ送信
                message = f"event: {event_type}\n"
                message += f"data: {json.dumps(data)}\n\n"
                
                self.handler.wfile.write(message.encode('utf-8'))
                self.handler.wfile.flush()
                return True
        except (BrokenPipeError, ConnectionResetError):
            self.active = False
            return False
    
    def close(self) -> None:
        """接続クローズ"""
        self.active = False


class RealtimeDashboardHandler(BaseHTTPRequestHandler):
    """リアルタイムダッシュボード HTTPハンドラー"""
    
    # クラス変数でSSE接続を管理
    sse_connections: List[SSEConnection] = []
    _connections_lock = threading.Lock()
    
    def do_GET(self) -> None:
        """GET リクエスト処理"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == "/api/events":
            self._handle_sse_connection()
        elif parsed_path.path == "/api/metrics":
            self._handle_metrics_request()
        elif parsed_path.path == "/api/sessions":
            self._handle_sessions_request()
        elif parsed_path.path == "/":
            self._serve_dashboard_html()
        elif parsed_path.path.startswith("/static/"):
            self._serve_static_file(parsed_path.path)
        else:
            self._send_404()
    
    def _handle_sse_connection(self) -> None:
        """SSE接続処理"""
        # SSEヘッダー送信
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # 接続を管理リストに追加
        connection = SSEConnection(self)
        with self._connections_lock:
            self.sse_connections.append(connection)
        
        try:
            # 初期データ送信
            connection.send_event({"type": "connected", "timestamp": time.time()})
            
            # 接続維持（クライアントが切断するまで）
            while connection.active:
                time.sleep(1)  # 1秒間隔でハートビート
                if not connection.send_event({"type": "heartbeat", "timestamp": time.time()}):
                    break
                    
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            # 接続をリストから削除
            with self._connections_lock:
                if connection in self.sse_connections:
                    self.sse_connections.remove(connection)
            connection.close()
    
    def _handle_metrics_request(self) -> None:
        """メトリクス API 処理"""
        try:
            # ExtendedThreadStorage からメトリクス取得
            from src.dashboard.core.extended_storage import get_realtime_metrics
            
            metrics = get_realtime_metrics()
            response_data = json.dumps(metrics)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response_data.encode('utf-8'))
            
        except Exception as e:
            self._send_error(500, f"Internal Server Error: {e}")
    
    def _handle_sessions_request(self) -> None:
        """セッション一覧 API 処理"""
        try:
            # ExtendedThreadStorage からセッション一覧取得
            from src.dashboard.core.extended_storage import get_recent_sessions
            
            sessions = get_recent_sessions(limit=50)
            response_data = json.dumps(sessions)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response_data.encode('utf-8'))
            
        except Exception as e:
            self._send_error(500, f"Internal Server Error: {e}")
    
    def _serve_dashboard_html(self) -> None:
        """ダッシュボード HTML 配信"""
        html_content = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude Code Event Notifier - リアルタイムダッシュボード</title>
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0; padding: 20px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
        }
        .container { 
            max-width: 1200px; margin: 0 auto; 
            background: rgba(255,255,255,0.95);
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }
        .header { 
            text-align: center; margin-bottom: 30px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 20px;
        }
        .header h1 { 
            color: #667eea; margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }
        .metrics-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
            gap: 20px; 
            margin-bottom: 30px; 
        }
        .metric-card { 
            background: white; 
            padding: 20px; 
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.08);
            border-left: 4px solid #667eea;
            transition: transform 0.2s;
        }
        .metric-card:hover {
            transform: translateY(-5px);
        }
        .metric-value { 
            font-size: 2em; 
            font-weight: bold; 
            color: #667eea; 
            margin: 10px 0;
        }
        .metric-label { 
            color: #666; 
            font-size: 0.9em; 
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .sessions-container {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.08);
        }
        .session-item {
            padding: 15px;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .session-item:last-child {
            border-bottom: none;
        }
        .status { 
            padding: 5px 12px; 
            border-radius: 20px; 
            font-size: 0.8em; 
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .status.connected { background: #4CAF50; color: white; }
        .status.disconnected { background: #f44336; color: white; }
        #connectionStatus {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px 20px;
            border-radius: 25px;
            font-weight: bold;
            z-index: 1000;
        }
    </style>
</head>
<body>
    <div id="connectionStatus" class="status disconnected">接続中...</div>
    
    <div class="container">
        <div class="header">
            <h1>🚀 Claude Code Event Notifier</h1>
            <p>リアルタイムダッシュボード - Pure Python 3.14+</p>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">アクティブセッション</div>
                <div class="metric-value" id="activeSessions">-</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">総スレッド数</div>
                <div class="metric-value" id="totalThreads">-</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">直近1時間のメッセージ</div>
                <div class="metric-value" id="messagesLastHour">-</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">平均セッション時間</div>
                <div class="metric-value" id="avgSessionDuration">-</div>
            </div>
        </div>
        
        <div class="sessions-container">
            <h2>最近のセッション</h2>
            <div id="sessionsList">読み込み中...</div>
        </div>
    </div>
    
    <script>
        // SSE接続とリアルタイム更新
        const eventSource = new EventSource('/api/events');
        const connectionStatus = document.getElementById('connectionStatus');
        
        eventSource.onopen = function() {
            connectionStatus.textContent = '接続済み';
            connectionStatus.className = 'status connected';
        };
        
        eventSource.onerror = function() {
            connectionStatus.textContent = '接続エラー';
            connectionStatus.className = 'status disconnected';
        };
        
        eventSource.onmessage = function(event) {
            const data = JSON.parse(event.data);
            if (data.type === 'metrics_update') {
                updateMetrics(data.metrics);
            }
        };
        
        // メトリクス更新
        function updateMetrics(metrics) {
            document.getElementById('activeSessions').textContent = metrics.active_sessions;
            document.getElementById('totalThreads').textContent = metrics.total_threads;
            document.getElementById('messagesLastHour').textContent = metrics.messages_last_hour;
            document.getElementById('avgSessionDuration').textContent = 
                Math.round(metrics.session_duration_avg) + 's';
        }
        
        // 定期的にメトリクス取得
        async function fetchMetrics() {
            try {
                const response = await fetch('/api/metrics');
                const metrics = await response.json();
                updateMetrics(metrics);
            } catch (error) {
                console.error('メトリクス取得エラー:', error);
            }
        }
        
        // 初回ロード時とその後5秒間隔で更新
        fetchMetrics();
        setInterval(fetchMetrics, 5000);
        
        // セッション一覧取得
        async function fetchSessions() {
            try {
                const response = await fetch('/api/sessions');
                const sessions = await response.json();
                updateSessionsList(sessions);
            } catch (error) {
                console.error('セッション取得エラー:', error);
            }
        }
        
        function updateSessionsList(sessions) {
            const container = document.getElementById('sessionsList');
            if (sessions.length === 0) {
                container.innerHTML = '<p>セッションがありません</p>';
                return;
            }
            
            container.innerHTML = sessions.map(session => `
                <div class="session-item">
                    <div>
                        <strong>${session.session_id.substring(0, 8)}...</strong><br>
                        <small>${session.last_event_type || 'Unknown'} - ${session.project_name || 'No project'}</small>
                    </div>
                    <div>
                        <span class="status ${session.is_active ? 'connected' : 'disconnected'}">
                            ${session.is_active ? 'アクティブ' : '非アクティブ'}
                        </span>
                    </div>
                </div>
            `).join('');
        }
        
        // 初回セッション取得
        fetchSessions();
        setInterval(fetchSessions, 10000);
    </script>
</body>
</html>"""
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def _serve_static_file(self, path: str) -> None:
        """静的ファイル配信"""
        self._send_404()  # 今回は静的ファイルなし
    
    def _send_404(self) -> None:
        """404エラー送信"""
        self.send_response(404)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Not Found')
    
    def _send_error(self, code: int, message: str) -> None:
        """エラーレスポンス送信"""
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        error_response = json.dumps({"error": message})
        self.wfile.write(error_response.encode('utf-8'))
    
    def log_message(self, format: str, *args: Any) -> None:
        """ログメッセージ（標準出力への出力を抑制）"""
        pass  # サイレントモード
    
    @classmethod
    def broadcast_to_all_connections(cls, data: Dict[str, Any], event_type: str = "message") -> int:
        """全SSE接続にブロードキャスト"""
        sent_count = 0
        with cls._connections_lock:
            active_connections = []
            for connection in cls.sse_connections:
                if connection.send_event(data, event_type):
                    active_connections.append(connection)
                    sent_count += 1
            cls.sse_connections = active_connections
        return sent_count


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """スレッド対応HTTPサーバー"""
    daemon_threads = True
    allow_reuse_address = True


class DashboardServer:
    """リアルタイムダッシュボードサーバー"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8000) -> None:
        self.host = host
        self.port = port
        self.server: Optional[ThreadingHTTPServer] = None
        self.running = False
        self._server_thread: Optional[threading.Thread] = None
    
    def start(self) -> bool:
        """サーバー開始"""
        if self.running:
            return False
        
        try:
            self.server = ThreadingHTTPServer((self.host, self.port), RealtimeDashboardHandler)
            self.running = True
            
            # 別スレッドでサーバー実行
            self._server_thread = threading.Thread(target=self._run_server, daemon=True)
            self._server_thread.start()
            
            return True
        except Exception:
            return False
    
    def _run_server(self) -> None:
        """サーバー実行（内部用）"""
        if self.server:
            self.server.serve_forever()
    
    def stop(self) -> None:
        """サーバー停止"""
        if self.server and self.running:
            self.server.shutdown()
            self.server.server_close()
            self.running = False
            if self._server_thread:
                self._server_thread.join(timeout=5.0)
    
    def broadcast_metrics_update(self, metrics: Dict[str, Any]) -> int:
        """メトリクス更新をブロードキャスト"""
        return RealtimeDashboardHandler.broadcast_to_all_connections(
            {"type": "metrics_update", "metrics": metrics},
            "message"
        )
    
    def broadcast_event(self, event_data: Dict[str, Any]) -> int:
        """イベントをブロードキャスト"""
        return RealtimeDashboardHandler.broadcast_to_all_connections(
            {"type": "event", "data": event_data},
            "event"
        )


# モジュールレベル関数
def create_dashboard_server(host: str = "127.0.0.1", port: int = 8000) -> DashboardServer:
    """ダッシュボードサーバー作成"""
    return DashboardServer(host, port)


def is_server_running(server: DashboardServer) -> TypeIs[bool]:
    """サーバー実行状態チェック"""
    return isinstance(server.running, bool) and server.running
```

### 2.2 HTTPサーバー実装手順
```bash
# ファイル作成
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix

# 上記コードを src/dashboard/core/http_server.py に保存
# (上記のPythonコードをコピーしてファイル作成)

# 構文チェック
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python -m py_compile src/dashboard/core/http_server.py

# 期待結果: エラーなし
# エラーが発生した場合は構文を修正
```

## 🗄️ Step 3: ExtendedThreadStorage 実装

### 3.1 拡張ストレージ実装
**`src/dashboard/core/extended_storage.py` 作成:**