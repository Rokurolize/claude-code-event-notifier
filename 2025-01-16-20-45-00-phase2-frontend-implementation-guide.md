# Phase 2 実装ガイド - フロントエンド構築

**作成日時**: 2025-01-16-20-45-00  
**Phase**: 2/3 - フロントエンド構築  
**目的**: Vanilla JavaScript + Web Components でリアルタイムUIを実装  
**設計原則**: Zero Dependencies + Pure JavaScript ES2024+ 完全遵守

## 🎯 Phase 2 実装目標

### 実装完了判定基準
- ✅ モダンなWeb Components が実装される
- ✅ CSS Grid + Flexbox による響レスポンシブレイアウトが完成する
- ✅ SSE（Server-Sent Events）によるリアルタイム通信が動作する
- ✅ リアルタイムメトリクス表示が <500ms で更新される
- ✅ セッション詳細ビューが実装される
- ✅ **外部ライブラリ使用ゼロ（Pure JavaScript ES2024+）**

## 📋 前提条件確認

### Phase 1 完了確認
```bash
# Phase 1 バックエンドの動作確認
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix

# ディレクトリ構造確認
ls -la src/dashboard/core/
# 期待結果: http_server.py, extended_storage.py が存在

# HTTPサーバー構文チェック
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix && uv run --python 3.14 python -m py_compile src/dashboard/core/http_server.py

# 期待結果: エラーなし
```

## 🏗️ Step 1: Web Components 基盤実装

### 1.1 コンポーネントディレクトリ構造作成
```bash
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix

# フロントエンド用ディレクトリ作成
mkdir -p src/dashboard/static/js/components
mkdir -p src/dashboard/static/css
mkdir -p src/dashboard/templates

# 作成確認
ls -la src/dashboard/static/
```

### 1.2 ベースWeb Componentクラス実装
**`src/dashboard/static/js/components/base-component.js` 作成:**
```javascript
/**
 * ベースWeb Component - Pure JavaScript ES2024+
 * Zero Dependencies 設計原則完全遵守
 */

class BaseComponent extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this._state = {};
        this._updateQueued = false;
        
        // コンポーネント初期化
        this.init();
        this.render();
    }
    
    /**
     * 初期化処理（サブクラスでオーバーライド）
     */
    init() {
        // サブクラスで実装
    }
    
    /**
     * 状態更新
     * @param {Object} newState 新しい状態
     */
    setState(newState) {
        this._state = { ...this._state, ...newState };
        this.queueUpdate();
    }
    
    /**
     * 状態取得
     * @param {string} key 状態キー
     * @returns {any} 状態値
     */
    getState(key) {
        return this._state[key];
    }
    
    /**
     * 更新をキューに追加（パフォーマンス最適化）
     */
    queueUpdate() {
        if (this._updateQueued) return;
        
        this._updateQueued = true;
        requestAnimationFrame(() => {
            this.render();
            this._updateQueued = false;
        });
    }
    
    /**
     * レンダリング（サブクラスで実装必須）
     */
    render() {
        throw new Error('render() method must be implemented by subclass');
    }
    
    /**
     * CSS スタイル生成
     * @returns {string} CSS文字列
     */
    getStyles() {
        return `
            :host {
                display: block;
                box-sizing: border-box;
            }
            * {
                box-sizing: border-box;
            }
        `;
    }
    
    /**
     * イベントリスナー追加ヘルパー
     * @param {string} selector セレクター
     * @param {string} event イベント名
     * @param {Function} handler ハンドラー
     */
    addEventListeners(selector, event, handler) {
        const elements = this.shadowRoot.querySelectorAll(selector);
        elements.forEach(element => {
            element.addEventListener(event, handler.bind(this));
        });
    }
    
    /**
     * 属性変更監視
     */
    static get observedAttributes() {
        return [];
    }
    
    /**
     * 属性変更時の処理
     */
    attributeChangedCallback(name, oldValue, newValue) {
        if (oldValue !== newValue) {
            this.queueUpdate();
        }
    }
    
    /**
     * DOM接続時の処理
     */
    connectedCallback() {
        this.onConnected();
    }
    
    /**
     * DOM切断時の処理
     */
    disconnectedCallback() {
        this.onDisconnected();
    }
    
    /**
     * 接続時の処理（サブクラスでオーバーライド）
     */
    onConnected() {
        // サブクラスで実装
    }
    
    /**
     * 切断時の処理（サブクラスでオーバーライド）
     */
    onDisconnected() {
        // サブクラスで実装
    }
}

export default BaseComponent;
```

### 1.3 リアルタイムメトリクスコンポーネント実装
**`src/dashboard/static/js/components/metrics-panel.js` 作成:**
```javascript
/**
 * リアルタイムメトリクスパネル - Web Component
 * Pure JavaScript ES2024+ + Zero Dependencies
 */

import BaseComponent from './base-component.js';

class MetricsPanel extends BaseComponent {
    init() {
        this.setState({
            metrics: {
                active_sessions: 0,
                total_threads: 0,
                messages_last_hour: 0,
                events_last_hour: 0,
                session_duration_avg: 0,
                top_tools: []
            },
            loading: true,
            lastUpdate: null
        });
        
        // メトリクス更新タイマー
        this._metricsTimer = null;
    }
    
    render() {
        const metrics = this.getState('metrics');
        const loading = this.getState('loading');
        const lastUpdate = this.getState('lastUpdate');
        
        this.shadowRoot.innerHTML = `
            <style>
                ${this.getStyles()}
                
                .metrics-container {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }
                
                .metric-card {
                    background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
                    border-radius: 12px;
                    padding: 24px;
                    box-shadow: 0 8px 25px rgba(0,0,0,0.1);
                    border-left: 4px solid var(--accent-color, #667eea);
                    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                    position: relative;
                    overflow: hidden;
                }
                
                .metric-card:hover {
                    transform: translateY(-5px);
                    box-shadow: 0 12px 35px rgba(0,0,0,0.15);
                }
                
                .metric-card::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    right: 0;
                    width: 100px;
                    height: 100px;
                    background: var(--accent-color, #667eea);
                    opacity: 0.05;
                    border-radius: 50%;
                    transform: translate(30px, -30px);
                }
                
                .metric-label {
                    font-size: 0.875rem;
                    font-weight: 600;
                    color: #6b7280;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                    margin-bottom: 12px;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }
                
                .metric-icon {
                    width: 18px;
                    height: 18px;
                    border-radius: 50%;
                    background: var(--accent-color, #667eea);
                    display: inline-block;
                }
                
                .metric-value {
                    font-size: 2.5rem;
                    font-weight: 700;
                    color: var(--accent-color, #667eea);
                    line-height: 1;
                    margin-bottom: 8px;
                    transition: all 0.3s ease;
                }
                
                .metric-change {
                    font-size: 0.875rem;
                    font-weight: 500;
                    display: flex;
                    align-items: center;
                    gap: 4px;
                }
                
                .metric-change.positive {
                    color: #10b981;
                }
                
                .metric-change.negative {
                    color: #ef4444;
                }
                
                .metric-change.neutral {
                    color: #6b7280;
                }
                
                .loading-shimmer {
                    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
                    background-size: 200% 100%;
                    animation: shimmer 1.5s infinite;
                }
                
                @keyframes shimmer {
                    0% { background-position: -200% 0; }
                    100% { background-position: 200% 0; }
                }
                
                .update-status {
                    text-align: center;
                    font-size: 0.75rem;
                    color: #6b7280;
                    margin-top: 20px;
                    padding: 8px;
                    background: rgba(0,0,0,0.02);
                    border-radius: 6px;
                }
                
                .tools-list {
                    margin-top: 16px;
                }
                
                .tool-item {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 8px 0;
                    border-bottom: 1px solid #f3f4f6;
                }
                
                .tool-item:last-child {
                    border-bottom: none;
                }
                
                .tool-name {
                    font-weight: 500;
                    color: #374151;
                }
                
                .tool-count {
                    font-weight: 600;
                    color: var(--accent-color, #667eea);
                }
            </style>
            
            <div class="metrics-container">
                <div class="metric-card" style="--accent-color: #3b82f6">
                    <div class="metric-label">
                        <span class="metric-icon"></span>
                        アクティブセッション
                    </div>
                    <div class="metric-value ${loading ? 'loading-shimmer' : ''}">
                        ${loading ? '-' : metrics.active_sessions}
                    </div>
                    <div class="metric-change neutral">
                        リアルタイム
                    </div>
                </div>
                
                <div class="metric-card" style="--accent-color: #10b981">
                    <div class="metric-label">
                        <span class="metric-icon"></span>
                        総スレッド数
                    </div>
                    <div class="metric-value ${loading ? 'loading-shimmer' : ''}">
                        ${loading ? '-' : metrics.total_threads}
                    </div>
                    <div class="metric-change neutral">
                        累計
                    </div>
                </div>
                
                <div class="metric-card" style="--accent-color: #f59e0b">
                    <div class="metric-label">
                        <span class="metric-icon"></span>
                        直近1時間のメッセージ
                    </div>
                    <div class="metric-value ${loading ? 'loading-shimmer' : ''}">
                        ${loading ? '-' : metrics.messages_last_hour}
                    </div>
                    <div class="metric-change neutral">
                        過去60分
                    </div>
                </div>
                
                <div class="metric-card" style="--accent-color: #8b5cf6">
                    <div class="metric-label">
                        <span class="metric-icon"></span>
                        平均セッション時間
                    </div>
                    <div class="metric-value ${loading ? 'loading-shimmer' : ''}">
                        ${loading ? '-' : this.formatDuration(metrics.session_duration_avg)}
                    </div>
                    <div class="metric-change neutral">
                        全期間平均
                    </div>
                </div>
                
                ${metrics.top_tools && metrics.top_tools.length > 0 ? `
                    <div class="metric-card" style="--accent-color: #ef4444; grid-column: 1 / -1;">
                        <div class="metric-label">
                            <span class="metric-icon"></span>
                            人気ツール TOP5
                        </div>
                        <div class="tools-list">
                            ${metrics.top_tools.map(tool => `
                                <div class="tool-item">
                                    <span class="tool-name">${tool.name}</span>
                                    <span class="tool-count">${tool.count}</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}
            </div>
            
            ${lastUpdate ? `
                <div class="update-status">
                    最終更新: ${this.formatTime(lastUpdate)}
                </div>
            ` : ''}
        `;
    }
    
    /**
     * メトリクス更新
     * @param {Object} newMetrics 新しいメトリクス
     */
    updateMetrics(newMetrics) {
        this.setState({
            metrics: newMetrics,
            loading: false,
            lastUpdate: new Date()
        });
    }
    
    /**
     * 時間フォーマット
     * @param {number} seconds 秒数
     * @returns {string} フォーマット済み時間
     */
    formatDuration(seconds) {
        if (!seconds || seconds < 0) return '0s';
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours}h ${minutes}m`;
        } else if (minutes > 0) {
            return `${minutes}m ${secs}s`;
        } else {
            return `${secs}s`;
        }
    }
    
    /**
     * 時刻フォーマット
     * @param {Date} date 日時
     * @returns {string} フォーマット済み時刻
     */
    formatTime(date) {
        return date.toLocaleTimeString('ja-JP', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }
    
    /**
     * ローディング状態設定
     * @param {boolean} loading ローディング状態
     */
    setLoading(loading) {
        this.setState({ loading });
    }
    
    onDisconnected() {
        if (this._metricsTimer) {
            clearInterval(this._metricsTimer);
        }
    }
}

// カスタム要素登録
customElements.define('metrics-panel', MetricsPanel);

export default MetricsPanel;
```

### 1.4 セッション一覧コンポーネント実装
**`src/dashboard/static/js/components/sessions-list.js` 作成:**
```javascript
/**
 * セッション一覧コンポーネント - Web Component  
 * Pure JavaScript ES2024+ + Zero Dependencies
 */

import BaseComponent from './base-component.js';

class SessionsList extends BaseComponent {
    init() {
        this.setState({
            sessions: [],
            loading: true,
            error: null,
            selectedSession: null,
            filterActive: 'all' // 'all', 'active', 'inactive'
        });
    }
    
    render() {
        const sessions = this.getState('sessions');
        const loading = this.getState('loading');
        const error = this.getState('error');
        const selectedSession = this.getState('selectedSession');
        const filterActive = this.getState('filterActive');
        
        // フィルタリング
        const filteredSessions = this.filterSessions(sessions, filterActive);
        
        this.shadowRoot.innerHTML = `
            <style>
                ${this.getStyles()}
                
                .sessions-container {
                    background: white;
                    border-radius: 12px;
                    overflow: hidden;
                    box-shadow: 0 8px 25px rgba(0,0,0,0.1);
                }
                
                .sessions-header {
                    padding: 24px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                
                .sessions-title {
                    font-size: 1.5rem;
                    font-weight: 600;
                    margin: 0;
                }
                
                .sessions-count {
                    background: rgba(255,255,255,0.2);
                    padding: 6px 12px;
                    border-radius: 20px;
                    font-size: 0.875rem;
                    font-weight: 500;
                }
                
                .filter-tabs {
                    display: flex;
                    background: #f8f9fa;
                    margin: 0;
                    border-bottom: 1px solid #e9ecef;
                }
                
                .filter-tab {
                    flex: 1;
                    padding: 16px;
                    border: none;
                    background: transparent;
                    cursor: pointer;
                    font-weight: 500;
                    transition: all 0.2s ease;
                    border-bottom: 3px solid transparent;
                }
                
                .filter-tab.active {
                    background: white;
                    border-bottom-color: #667eea;
                    color: #667eea;
                }
                
                .filter-tab:hover:not(.active) {
                    background: #e9ecef;
                }
                
                .sessions-list {
                    max-height: 600px;
                    overflow-y: auto;
                }
                
                .session-item {
                    padding: 20px 24px;
                    border-bottom: 1px solid #f1f3f4;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    position: relative;
                }
                
                .session-item:hover {
                    background: #f8f9fa;
                    transform: translateX(4px);
                }
                
                .session-item.selected {
                    background: #e8f2ff;
                    border-left: 4px solid #667eea;
                }
                
                .session-item:last-child {
                    border-bottom: none;
                }
                
                .session-info {
                    flex: 1;
                }
                
                .session-id {
                    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
                    font-weight: 600;
                    color: #374151;
                    font-size: 1rem;
                    margin-bottom: 6px;
                }
                
                .session-meta {
                    display: flex;
                    gap: 16px;
                    font-size: 0.875rem;
                    color: #6b7280;
                }
                
                .session-project {
                    font-weight: 500;
                    color: #4b5563;
                }
                
                .session-event {
                    padding: 2px 8px;
                    background: #f3f4f6;
                    border-radius: 4px;
                    font-weight: 500;
                }
                
                .session-time {
                    color: #9ca3af;
                }
                
                .session-status {
                    display: flex;
                    flex-direction: column;
                    align-items: flex-end;
                    gap: 8px;
                }
                
                .status-badge {
                    padding: 6px 12px;
                    border-radius: 20px;
                    font-size: 0.75rem;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                }
                
                .status-badge.active {
                    background: #dcfce7;
                    color: #166534;
                }
                
                .status-badge.inactive {
                    background: #fef2f2;
                    color: #991b1b;
                }
                
                .session-metrics {
                    font-size: 0.75rem;
                    color: #6b7280;
                    text-align: right;
                }
                
                .empty-state {
                    padding: 60px 24px;
                    text-align: center;
                    color: #6b7280;
                }
                
                .empty-icon {
                    width: 64px;
                    height: 64px;
                    margin: 0 auto 16px;
                    background: #f3f4f6;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 24px;
                }
                
                .loading-state {
                    padding: 40px 24px;
                    text-align: center;
                }
                
                .loading-spinner {
                    width: 32px;
                    height: 32px;
                    border: 3px solid #f3f4f6;
                    border-top: 3px solid #667eea;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    margin: 0 auto 16px;
                }
                
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
                
                .error-state {
                    padding: 40px 24px;
                    text-align: center;
                    color: #dc2626;
                }
            </style>
            
            <div class="sessions-container">
                <div class="sessions-header">
                    <h2 class="sessions-title">セッション一覧</h2>
                    <div class="sessions-count">
                        ${filteredSessions.length} セッション
                    </div>
                </div>
                
                <div class="filter-tabs">
                    <button class="filter-tab ${filterActive === 'all' ? 'active' : ''}" 
                            data-filter="all">
                        すべて
                    </button>
                    <button class="filter-tab ${filterActive === 'active' ? 'active' : ''}" 
                            data-filter="active">
                        アクティブ
                    </button>
                    <button class="filter-tab ${filterActive === 'inactive' ? 'active' : ''}" 
                            data-filter="inactive">
                        非アクティブ
                    </button>
                </div>
                
                <div class="sessions-list">
                    ${this.renderSessionsList(filteredSessions, loading, error)}
                </div>
            </div>
        `;
        
        // イベントリスナー追加
        this.addEventListeners('.filter-tab', 'click', this.handleFilterChange);
        this.addEventListeners('.session-item', 'click', this.handleSessionSelect);
    }
    
    renderSessionsList(sessions, loading, error) {
        if (loading) {
            return `
                <div class="loading-state">
                    <div class="loading-spinner"></div>
                    <p>セッションを読み込み中...</p>
                </div>
            `;
        }
        
        if (error) {
            return `
                <div class="error-state">
                    <p>エラーが発生しました: ${error}</p>
                </div>
            `;
        }
        
        if (sessions.length === 0) {
            return `
                <div class="empty-state">
                    <div class="empty-icon">📭</div>
                    <p>セッションがありません</p>
                </div>
            `;
        }
        
        return sessions.map(session => `
            <div class="session-item ${session.session_id === this.getState('selectedSession') ? 'selected' : ''}" 
                 data-session-id="${session.session_id}">
                <div class="session-info">
                    <div class="session-id">${this.truncateSessionId(session.session_id)}</div>
                    <div class="session-meta">
                        <span class="session-project">${session.project_name || 'プロジェクト不明'}</span>
                        <span class="session-event">${session.last_event_type || 'Unknown'}</span>
                        <span class="session-time">${this.formatRelativeTime(session.last_used_at)}</span>
                    </div>
                </div>
                <div class="session-status">
                    <span class="status-badge ${session.is_active ? 'active' : 'inactive'}">
                        ${session.is_active ? 'アクティブ' : '非アクティブ'}
                    </span>
                    <div class="session-metrics">
                        <div>${session.message_count || 0} メッセージ</div>
                        <div>${session.event_count || 0} イベント</div>
                    </div>
                </div>
            </div>
        `).join('');
    }
    
    /**
     * フィルター変更ハンドラー
     */
    handleFilterChange(event) {
        const filter = event.target.dataset.filter;
        this.setState({ filterActive: filter });
        
        // カスタムイベント発火
        this.dispatchEvent(new CustomEvent('filter-change', {
            detail: { filter }
        }));
    }
    
    /**
     * セッション選択ハンドラー  
     */
    handleSessionSelect(event) {
        const sessionId = event.currentTarget.dataset.sessionId;
        this.setState({ selectedSession: sessionId });
        
        // カスタムイベント発火
        this.dispatchEvent(new CustomEvent('session-select', {
            detail: { sessionId }
        }));
    }
    
    /**
     * セッションフィルタリング
     */
    filterSessions(sessions, filter) {
        switch (filter) {
            case 'active':
                return sessions.filter(session => session.is_active);
            case 'inactive':
                return sessions.filter(session => !session.is_active);
            default:
                return sessions;
        }
    }
    
    /**
     * セッションID短縮
     */
    truncateSessionId(sessionId) {
        return sessionId ? `${sessionId.substring(0, 8)}...` : 'Unknown';
    }
    
    /**
     * 相対時間フォーマット
     */
    formatRelativeTime(dateString) {
        if (!dateString) return '時刻不明';
        
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMinutes = Math.floor(diffMs / (1000 * 60));
        
        if (diffMinutes < 1) return 'たった今';
        if (diffMinutes < 60) return `${diffMinutes}分前`;
        
        const diffHours = Math.floor(diffMinutes / 60);
        if (diffHours < 24) return `${diffHours}時間前`;
        
        const diffDays = Math.floor(diffHours / 24);
        return `${diffDays}日前`;
    }
    
    /**
     * セッション更新
     */
    updateSessions(sessions) {
        this.setState({
            sessions,
            loading: false,
            error: null
        });
    }
    
    /**
     * エラー状態設定
     */
    setError(error) {
        this.setState({
            error: error.message || error,
            loading: false
        });
    }
    
    /**
     * ローディング状態設定
     */
    setLoading(loading) {
        this.setState({ loading });
    }
}

// カスタム要素登録
customElements.define('sessions-list', SessionsList);

export default SessionsList;
```

### 1.5 フロントエンド実装手順
```bash
cd /home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix

# 上記のJavaScriptファイルを作成
# (各ファイルの内容をコピーして保存)

# ディレクトリ確認
ls -la src/dashboard/static/js/components/

# 期待結果:
# base-component.js
# metrics-panel.js  
# sessions-list.js
```

## 🔗 Step 2: リアルタイム通信システム実装

### 2.1 SSE（Server-Sent Events）マネージャー実装
**`src/dashboard/static/js/realtime-manager.js` 作成:**