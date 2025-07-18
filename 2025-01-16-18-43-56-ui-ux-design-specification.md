# UI/UX Design Specification for Claude Code Event Notifier Dashboard

**作成日**: 2025-07-17-04-43-56  
**作成者**: UI/UXデザイン分析アストルフォ  
**プロジェクト**: Claude Code Event Notifier Dashboard  
**技術基盤**: Pure JavaScript + Web Components + WebSocket/EventSource  

---

## 📋 Executive Summary

Claude Code Event Notifier Dashboard は、既存のDiscord通知システムを補完する、Chrome browserでアクセス可能なリアルタイムWeb UI です。JSON生ログ分析、セッション管理、サブエージェント追跡を統合した包括的なモニタリングダッシュボードを提供します。

### 🎯 核心価値提案

1. **リアルタイム可視化**: 5つのイベントタイプをリアルタイムで監視
2. **セッション中心の管理**: 複数プロジェクト並行作業に対応
3. **詳細分析機能**: JSON生ログベースの深度分析
4. **サブエージェント追跡**: 並列処理とデータ汚染の可視化
5. **モダンUX**: 美しく直感的なインターフェース

---

## 🎨 UI/UX Design Requirements Analysis

### 1. 既存システム分析

#### 1.1 Discord通知システムの現状
- **イベントタイプ**: 5種類（PreToolUse, PostToolUse, Notification, Stop, SubagentStop）
- **色分けシステム**: 
  - 🔵 PreToolUse (Blue #3498DB)
  - 🟢 PostToolUse (Green #2ECC71)
  - 🟠 Notification (Orange #F39C12)
  - ⚫ Stop (Gray #95A5A6)
  - 🟣 SubagentStop (Purple #9B59B6)
- **情報密度**: イベントタイプにより40-100%の情報活用率

#### 1.2 JSON生ログ構造
```json
{
  "session_id": "76e40b9f-ba89-4ca1-9b80-509176246cba",
  "transcript_path": "/path/to/transcript.jsonl",
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": { /* detailed parameters */ },
  "tool_response": { /* response data */ }
}
```

#### 1.3 既存の機能制限
- Discord APIの4,096文字制限
- SubagentStopイベントの情報欠落（40%情報活用率）
- 複数プロジェクト並行作業での混乱
- リアルタイム分析機能の欠如

### 2. ユーザー体験要件

#### 2.1 主要ユーザー
- **プライマリーユーザー**: Claude Code利用者（開発者）
- **アクセス方式**: Chrome browser経由でlocalhost:8080にアクセス
- **利用シーン**: 開発作業中のリアルタイム監視、デバッグ、分析

#### 2.2 ユーザージャーニー
1. **アクセス**: Chrome browserでlocalhost:8080を開く
2. **概要確認**: 現在のセッション状況を即座に把握
3. **詳細監視**: イベントストリームをリアルタイムで追跡
4. **分析作業**: 特定のセッションやイベントの詳細分析
5. **問題解決**: エラーやサブエージェント問題の調査

#### 2.3 情報優先度
1. **最高優先**: 現在のセッション状況、アクティブなイベント
2. **高優先**: 最新のイベント履歴、エラー・警告
3. **中優先**: セッション統計、パフォーマンスメトリクス
4. **低優先**: 詳細ログ、歴史データ

---

## 🖥️ Screen Design and Component Specifications

### 1. 全体レイアウト設計

#### 1.1 メインレイアウト構造
```
┌─────────────────────────────────────────────────────────────┐
│ Header Bar (固定)                                           │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────────┐ ┌─────────────────────────────────┐ │
│ │ Session Overview    │ │ Live Event Stream              │ │
│ │ (左サイドバー)       │ │ (メインコンテンツ)             │ │
│ │                     │ │                                 │ │
│ │ - Active Sessions   │ │ - Real-time Events              │ │
│ │ - Quick Stats       │ │ - Event Details                 │ │
│ │ - Filters          │ │ - JSON Preview                  │ │
│ │                     │ │                                 │ │
│ └─────────────────────┘ └─────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ Bottom Status Bar (固定)                                    │
└─────────────────────────────────────────────────────────────┘
```

#### 1.2 レスポンシブデザイン
- **デスクトップ**: 3カラムレイアウト（300px + flex + 250px）
- **タブレット**: 2カラムレイアウト（左サイドバー折り畳み可能）
- **モバイル**: 1カラムレイアウト（タブ切り替え）

### 2. コンポーネント仕様

#### 2.1 Header Bar Component
```html
<header class="header-bar">
  <div class="header-left">
    <h1 class="app-title">Claude Code Event Monitor</h1>
    <div class="connection-status">
      <span class="status-indicator connected"></span>
      <span class="status-text">Connected</span>
    </div>
  </div>
  <div class="header-center">
    <div class="session-counter">
      <span class="counter-value">3</span>
      <span class="counter-label">Active Sessions</span>
    </div>
    <div class="event-rate">
      <span class="rate-value">12/min</span>
      <span class="rate-label">Event Rate</span>
    </div>
  </div>
  <div class="header-right">
    <button class="control-btn pause-btn">⏸️ Pause</button>
    <button class="control-btn settings-btn">⚙️ Settings</button>
  </div>
</header>
```

#### 2.2 Session Overview Component
```html
<aside class="session-overview">
  <div class="section-header">
    <h2>Active Sessions</h2>
    <button class="refresh-btn">🔄</button>
  </div>
  
  <div class="session-list">
    <div class="session-item active">
      <div class="session-header">
        <span class="session-id">76e40b9f</span>
        <span class="session-project">claude-code-event-notifier-bugfix</span>
      </div>
      <div class="session-stats">
        <span class="stat-item">
          <span class="stat-icon">🔵</span>
          <span class="stat-value">5</span>
        </span>
        <span class="stat-item">
          <span class="stat-icon">🟢</span>
          <span class="stat-value">4</span>
        </span>
        <span class="stat-item">
          <span class="stat-icon">🟠</span>
          <span class="stat-value">1</span>
        </span>
      </div>
      <div class="session-actions">
        <button class="action-btn">📋 View Details</button>
        <button class="action-btn">📁 Open Directory</button>
      </div>
    </div>
  </div>
  
  <div class="section-header">
    <h2>Filters</h2>
  </div>
  
  <div class="filter-controls">
    <div class="filter-group">
      <label>Event Types</label>
      <div class="event-type-toggles">
        <label class="toggle-item">
          <input type="checkbox" checked>
          <span class="toggle-color" style="background: #3498DB"></span>
          <span class="toggle-label">PreToolUse</span>
        </label>
        <label class="toggle-item">
          <input type="checkbox" checked>
          <span class="toggle-color" style="background: #2ECC71"></span>
          <span class="toggle-label">PostToolUse</span>
        </label>
        <label class="toggle-item">
          <input type="checkbox" checked>
          <span class="toggle-color" style="background: #F39C12"></span>
          <span class="toggle-label">Notification</span>
        </label>
        <label class="toggle-item">
          <input type="checkbox" checked>
          <span class="toggle-color" style="background: #95A5A6"></span>
          <span class="toggle-label">Stop</span>
        </label>
        <label class="toggle-item">
          <input type="checkbox" checked>
          <span class="toggle-color" style="background: #9B59B6"></span>
          <span class="toggle-label">SubagentStop</span>
        </label>
      </div>
    </div>
    
    <div class="filter-group">
      <label>Tools</label>
      <select class="tool-filter" multiple>
        <option value="Bash">🔧 Bash</option>
        <option value="Read">📖 Read</option>
        <option value="Write">✏️ Write</option>
        <option value="Edit">✂️ Edit</option>
        <option value="Task">📋 Task</option>
      </select>
    </div>
  </div>
</aside>
```

#### 2.3 Live Event Stream Component
```html
<main class="event-stream">
  <div class="stream-header">
    <h2>Live Event Stream</h2>
    <div class="stream-controls">
      <button class="control-btn auto-scroll active">📜 Auto Scroll</button>
      <button class="control-btn clear-stream">🗑️ Clear</button>
      <input type="search" class="search-input" placeholder="Search events...">
    </div>
  </div>
  
  <div class="event-list" id="event-list">
    <!-- Event items will be dynamically populated -->
  </div>
  
  <div class="stream-footer">
    <span class="event-count">Showing 150 events</span>
    <button class="load-more-btn">Load More</button>
  </div>
</main>
```

#### 2.4 Event Item Component
```html
<div class="event-item" data-event-type="PreToolUse" data-session-id="76e40b9f">
  <div class="event-header">
    <div class="event-indicator">
      <span class="event-color" style="background: #3498DB"></span>
      <span class="event-icon">🔵</span>
    </div>
    <div class="event-meta">
      <span class="event-type">PreToolUse</span>
      <span class="event-tool">Bash</span>
      <span class="event-time">14:32:48</span>
    </div>
    <div class="event-actions">
      <button class="action-btn toggle-details">📋 Details</button>
      <button class="action-btn view-json">📄 JSON</button>
    </div>
  </div>
  
  <div class="event-summary">
    <p class="event-description">
      Executing bash command: <code>echo test</code>
    </p>
    <div class="event-tags">
      <span class="tag project">claude-code-event-notifier-bugfix</span>
      <span class="tag session">76e40b9f</span>
    </div>
  </div>
  
  <div class="event-details collapsed">
    <div class="details-tabs">
      <button class="tab-btn active" data-tab="summary">Summary</button>
      <button class="tab-btn" data-tab="input">Input</button>
      <button class="tab-btn" data-tab="output">Output</button>
      <button class="tab-btn" data-tab="raw">Raw JSON</button>
    </div>
    
    <div class="tab-content">
      <div class="tab-panel active" data-tab="summary">
        <div class="summary-grid">
          <div class="summary-item">
            <label>Session ID</label>
            <code>76e40b9f-ba89-4ca1-9b80-509176246cba</code>
          </div>
          <div class="summary-item">
            <label>Tool Name</label>
            <code>Bash</code>
          </div>
          <div class="summary-item">
            <label>Timestamp</label>
            <code>2025-07-17T04:32:48.449Z</code>
          </div>
          <div class="summary-item">
            <label>Project</label>
            <code>claude-code-event-notifier-bugfix</code>
          </div>
        </div>
      </div>
      
      <div class="tab-panel" data-tab="input">
        <pre class="code-block"><code class="language-json">{
  "command": "echo test",
  "description": "Test command execution"
}</code></pre>
      </div>
      
      <div class="tab-panel" data-tab="output">
        <pre class="code-block"><code class="language-bash">test</code></pre>
      </div>
      
      <div class="tab-panel" data-tab="raw">
        <pre class="code-block"><code class="language-json">{
  "session_id": "76e40b9f-ba89-4ca1-9b80-509176246cba",
  "transcript_path": "/path/to/transcript.jsonl",
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": {
    "command": "echo test",
    "description": "Test command execution"
  }
}</code></pre>
      </div>
    </div>
  </div>
</div>
```

#### 2.5 Bottom Status Bar Component
```html
<footer class="status-bar">
  <div class="status-left">
    <span class="server-status">
      <span class="status-indicator connected"></span>
      <span class="status-text">Server: localhost:8080</span>
    </span>
    <span class="last-update">
      Last update: 2025-07-17 04:32:48
    </span>
  </div>
  <div class="status-center">
    <div class="performance-metrics">
      <span class="metric">
        <span class="metric-label">Memory:</span>
        <span class="metric-value">45.2 MB</span>
      </span>
      <span class="metric">
        <span class="metric-label">CPU:</span>
        <span class="metric-value">2.3%</span>
      </span>
      <span class="metric">
        <span class="metric-label">Events/sec:</span>
        <span class="metric-value">0.2</span>
      </span>
    </div>
  </div>
  <div class="status-right">
    <button class="status-btn export-btn">📥 Export</button>
    <button class="status-btn help-btn">❓ Help</button>
  </div>
</footer>
```

---

## 🎭 Interaction Design

### 1. リアルタイム更新のUI表現

#### 1.1 イベント到着時のアニメーション
```css
@keyframes eventArrival {
  0% {
    transform: translateY(-20px);
    opacity: 0;
    background: rgba(52, 152, 219, 0.1);
  }
  50% {
    background: rgba(52, 152, 219, 0.2);
  }
  100% {
    transform: translateY(0);
    opacity: 1;
    background: transparent;
  }
}

.event-item.new {
  animation: eventArrival 0.6s ease-out;
}
```

#### 1.2 接続状態のビジュアル表現
```css
.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
  margin-right: 6px;
}

.status-indicator.connected {
  background: #2ECC71;
  animation: pulse 2s ease-in-out infinite;
}

.status-indicator.disconnected {
  background: #E74C3C;
  animation: blink 1s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0.3; }
}
```

### 2. フィルタリング・検索機能のUI

#### 2.1 リアルタイム検索
```javascript
class EventSearchManager {
  constructor() {
    this.searchInput = document.querySelector('.search-input');
    this.eventList = document.querySelector('.event-list');
    this.searchTimeout = null;
  }

  initialize() {
    this.searchInput.addEventListener('input', (e) => {
      clearTimeout(this.searchTimeout);
      this.searchTimeout = setTimeout(() => {
        this.performSearch(e.target.value);
      }, 300);
    });
  }

  performSearch(query) {
    const events = this.eventList.querySelectorAll('.event-item');
    const lowerQuery = query.toLowerCase();

    events.forEach(event => {
      const searchableText = [
        event.dataset.eventType,
        event.dataset.sessionId,
        event.querySelector('.event-description')?.textContent || '',
        event.querySelector('.event-tool')?.textContent || ''
      ].join(' ').toLowerCase();

      if (searchableText.includes(lowerQuery)) {
        event.style.display = 'block';
        this.highlightSearchTerms(event, query);
      } else {
        event.style.display = 'none';
      }
    });
  }

  highlightSearchTerms(element, query) {
    // Search term highlighting implementation
  }
}
```

#### 2.2 フィルター状態の視覚的表現
```css
.toggle-item {
  display: flex;
  align-items: center;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background-color 0.2s ease;
}

.toggle-item:hover {
  background: rgba(255, 255, 255, 0.1);
}

.toggle-item input[type="checkbox"] {
  display: none;
}

.toggle-color {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-right: 8px;
  border: 2px solid transparent;
  transition: border-color 0.2s ease;
}

.toggle-item input[type="checkbox"]:checked + .toggle-color {
  border-color: #fff;
}

.toggle-item input[type="checkbox"]:not(:checked) + .toggle-color {
  opacity: 0.3;
}
```

### 3. ユーザー操作パターン

#### 3.1 キーボードショートカット
- **Ctrl+F**: 検索にフォーカス
- **Ctrl+C**: 選択されたイベントをクリップボードにコピー
- **Ctrl+E**: イベントの詳細を展開/折り畳み
- **Ctrl+J**: JSON表示切り替え
- **Ctrl+R**: 手動リフレッシュ
- **Space**: 一時停止/再開
- **Escape**: 検索クリア、詳細パネル閉じる

#### 3.2 マウス操作
- **左クリック**: イベント選択
- **ダブルクリック**: イベント詳細の展開/折り畳み
- **右クリック**: コンテキストメニュー表示
- **ホイール**: スクロール（Auto Scroll無効時）
- **ドラッグ**: テキスト選択とコピー

#### 3.3 タッチ操作（モバイル対応）
- **タップ**: イベント選択
- **ロングタップ**: コンテキストメニュー表示
- **スワイプ**: 左サイドバーの開閉
- **ピンチ**: ズーム（コード表示時）

---

## 🛠️ Technical Implementation Specifications

### 1. Vanilla JavaScript + Web Components Implementation

#### 1.1 メインアプリケーション構造
```javascript
// app.js - Main application entry point
class EventNotifierApp {
  constructor() {
    this.eventStream = new EventStreamManager();
    this.sessionManager = new SessionManager();
    this.filterManager = new FilterManager();
    this.uiManager = new UIManager();
    this.webSocketClient = new WebSocketClient();
  }

  async initialize() {
    await this.setupWebComponents();
    await this.establishConnection();
    this.setupEventListeners();
    this.startEventProcessing();
  }

  async setupWebComponents() {
    // Register custom web components
    customElements.define('event-item', EventItemComponent);
    customElements.define('session-card', SessionCardComponent);
    customElements.define('filter-panel', FilterPanelComponent);
    customElements.define('status-bar', StatusBarComponent);
  }

  async establishConnection() {
    try {
      await this.webSocketClient.connect('ws://localhost:8080/events');
      this.uiManager.updateConnectionStatus('connected');
    } catch (error) {
      this.uiManager.updateConnectionStatus('disconnected');
      // Fallback to polling
      this.startPolling();
    }
  }

  startEventProcessing() {
    this.webSocketClient.onMessage((eventData) => {
      this.eventStream.addEvent(eventData);
      this.sessionManager.updateSession(eventData.session_id);
      this.uiManager.updateEventStream(eventData);
    });
  }
}
```

#### 1.2 Web Components設計
```javascript
// components/EventItemComponent.js
class EventItemComponent extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.eventData = null;
    this.isExpanded = false;
  }

  connectedCallback() {
    this.render();
    this.setupEventListeners();
  }

  static get observedAttributes() {
    return ['event-type', 'session-id', 'expanded'];
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (oldValue !== newValue) {
      this.render();
    }
  }

  setEventData(data) {
    this.eventData = data;
    this.setAttribute('event-type', data.hook_event_name);
    this.setAttribute('session-id', data.session_id);
    this.render();
  }

  render() {
    if (!this.eventData) return;

    const template = `
      <style>
        :host {
          display: block;
          margin-bottom: 1px;
          border-left: 4px solid var(--event-color);
          background: var(--bg-secondary);
          transition: all 0.3s ease;
        }
        
        :host(:hover) {
          background: var(--bg-hover);
          transform: translateX(2px);
        }
        
        .event-header {
          display: flex;
          align-items: center;
          padding: 12px 16px;
          cursor: pointer;
        }
        
        .event-details {
          padding: 0 16px;
          max-height: 0;
          overflow: hidden;
          transition: max-height 0.3s ease;
        }
        
        .event-details.expanded {
          max-height: 500px;
          padding: 16px;
        }
        
        .code-block {
          background: var(--bg-code);
          padding: 12px;
          border-radius: 4px;
          overflow-x: auto;
          font-family: 'Consolas', monospace;
          font-size: 13px;
        }
        
        .tab-buttons {
          display: flex;
          margin-bottom: 16px;
          border-bottom: 1px solid var(--border-color);
        }
        
        .tab-button {
          background: none;
          border: none;
          padding: 8px 16px;
          cursor: pointer;
          color: var(--text-secondary);
          transition: color 0.2s ease;
        }
        
        .tab-button.active {
          color: var(--text-primary);
          border-bottom: 2px solid var(--accent-color);
        }
      </style>
      
      <div class="event-header" @click="toggleDetails">
        <div class="event-indicator">
          <span class="event-icon">${this.getEventIcon()}</span>
        </div>
        <div class="event-meta">
          <span class="event-type">${this.eventData.hook_event_name}</span>
          <span class="event-tool">${this.eventData.tool_name || 'N/A'}</span>
          <span class="event-time">${this.formatTime(this.eventData.timestamp)}</span>
        </div>
        <div class="event-actions">
          <button class="action-btn" @click="copyToClipboard">📋 Copy</button>
          <button class="action-btn" @click="viewRawJson">📄 JSON</button>
        </div>
      </div>
      
      <div class="event-details ${this.isExpanded ? 'expanded' : ''}">
        <div class="tab-buttons">
          <button class="tab-button active" data-tab="summary">Summary</button>
          <button class="tab-button" data-tab="input">Input</button>
          <button class="tab-button" data-tab="output">Output</button>
          <button class="tab-button" data-tab="raw">Raw JSON</button>
        </div>
        
        <div class="tab-content">
          ${this.renderTabContent()}
        </div>
      </div>
    `;

    this.shadowRoot.innerHTML = template;
  }

  getEventIcon() {
    const icons = {
      'PreToolUse': '🔵',
      'PostToolUse': '🟢',
      'Notification': '🟠',
      'Stop': '⚫',
      'SubagentStop': '🟣'
    };
    return icons[this.eventData.hook_event_name] || '⚪';
  }

  formatTime(timestamp) {
    return new Date(timestamp).toLocaleTimeString();
  }

  renderTabContent() {
    // Implementation for tab content rendering
  }

  toggleDetails() {
    this.isExpanded = !this.isExpanded;
    this.setAttribute('expanded', this.isExpanded);
  }

  copyToClipboard() {
    navigator.clipboard.writeText(JSON.stringify(this.eventData, null, 2));
  }

  viewRawJson() {
    this.dispatchEvent(new CustomEvent('view-raw-json', {
      detail: { eventData: this.eventData },
      bubbles: true
    }));
  }
}
```

### 2. CSS設計パターン

#### 2.1 CSS カスタムプロパティ（Design System）
```css
/* styles/design-system.css */
:root {
  /* Colors */
  --primary-color: #2C3E50;
  --secondary-color: #34495E;
  --accent-color: #3498DB;
  --success-color: #2ECC71;
  --warning-color: #F39C12;
  --error-color: #E74C3C;
  --info-color: #9B59B6;
  
  /* Event Colors */
  --event-pretooluse: #3498DB;
  --event-posttooluse: #2ECC71;
  --event-notification: #F39C12;
  --event-stop: #95A5A6;
  --event-subagentstop: #9B59B6;
  
  /* Background Colors */
  --bg-primary: #1A252F;
  --bg-secondary: #2C3E50;
  --bg-tertiary: #34495E;
  --bg-hover: #3A4C5C;
  --bg-code: #1E2A38;
  --bg-modal: rgba(0, 0, 0, 0.8);
  
  /* Text Colors */
  --text-primary: #ECF0F1;
  --text-secondary: #BDC3C7;
  --text-muted: #7F8C8D;
  --text-code: #A8E6CF;
  
  /* Border Colors */
  --border-color: #34495E;
  --border-hover: #4A5F7A;
  
  /* Spacing */
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;
  
  /* Border Radius */
  --border-radius-sm: 4px;
  --border-radius-md: 8px;
  --border-radius-lg: 12px;
  
  /* Shadows */
  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.2);
  --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.3);
  --shadow-lg: 0 8px 15px rgba(0, 0, 0, 0.4);
  
  /* Transitions */
  --transition-fast: 0.15s ease;
  --transition-normal: 0.3s ease;
  --transition-slow: 0.5s ease;
  
  /* Typography */
  --font-family-primary: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-family-mono: 'Consolas', 'Monaco', 'Courier New', monospace;
  --font-size-xs: 12px;
  --font-size-sm: 14px;
  --font-size-md: 16px;
  --font-size-lg: 18px;
  --font-size-xl: 24px;
  
  /* Layout */
  --sidebar-width: 300px;
  --header-height: 60px;
  --footer-height: 40px;
  --max-content-width: 1200px;
}

/* Dark theme adjustments */
@media (prefers-color-scheme: dark) {
  :root {
    --bg-primary: #0F1419;
    --bg-secondary: #1A252F;
    --bg-tertiary: #2C3E50;
    --text-primary: #F8F9FA;
    --text-secondary: #DEE2E6;
  }
}
```

#### 2.2 コンポーネントベースCSS
```css
/* components/event-item.css */
.event-item {
  display: block;
  margin-bottom: 1px;
  border-left: 4px solid var(--event-color);
  background: var(--bg-secondary);
  transition: all var(--transition-normal);
  border-radius: var(--border-radius-sm);
  overflow: hidden;
}

.event-item:hover {
  background: var(--bg-hover);
  transform: translateX(2px);
  box-shadow: var(--shadow-md);
}

.event-item[data-event-type="PreToolUse"] {
  --event-color: var(--event-pretooluse);
}

.event-item[data-event-type="PostToolUse"] {
  --event-color: var(--event-posttooluse);
}

.event-item[data-event-type="Notification"] {
  --event-color: var(--event-notification);
}

.event-item[data-event-type="Stop"] {
  --event-color: var(--event-stop);
}

.event-item[data-event-type="SubagentStop"] {
  --event-color: var(--event-subagentstop);
}

.event-header {
  display: flex;
  align-items: center;
  padding: var(--spacing-md);
  cursor: pointer;
  user-select: none;
}

.event-indicator {
  display: flex;
  align-items: center;
  margin-right: var(--spacing-md);
}

.event-icon {
  font-size: var(--font-size-lg);
  margin-right: var(--spacing-sm);
}

.event-meta {
  display: flex;
  flex-direction: column;
  flex: 1;
  gap: var(--spacing-xs);
}

.event-type {
  font-weight: 600;
  color: var(--text-primary);
  font-size: var(--font-size-sm);
}

.event-tool {
  color: var(--text-secondary);
  font-size: var(--font-size-xs);
  font-family: var(--font-family-mono);
}

.event-time {
  color: var(--text-muted);
  font-size: var(--font-size-xs);
}

.event-actions {
  display: flex;
  gap: var(--spacing-sm);
}

.action-btn {
  background: none;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--border-radius-sm);
  cursor: pointer;
  font-size: var(--font-size-xs);
  transition: all var(--transition-fast);
}

.action-btn:hover {
  border-color: var(--border-hover);
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.event-details {
  padding: 0 var(--spacing-md);
  max-height: 0;
  overflow: hidden;
  transition: max-height var(--transition-normal);
}

.event-details.expanded {
  max-height: 600px;
  padding: var(--spacing-md);
}

.code-block {
  background: var(--bg-code);
  padding: var(--spacing-md);
  border-radius: var(--border-radius-sm);
  overflow-x: auto;
  font-family: var(--font-family-mono);
  font-size: var(--font-size-sm);
  line-height: 1.4;
  color: var(--text-code);
}

.code-block::-webkit-scrollbar {
  height: 8px;
}

.code-block::-webkit-scrollbar-track {
  background: var(--bg-secondary);
}

.code-block::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 4px;
}
```

### 3. パフォーマンス最適化

#### 3.1 仮想スクロール実装
```javascript
// utils/VirtualScroller.js
class VirtualScroller {
  constructor(container, itemHeight = 80) {
    this.container = container;
    this.itemHeight = itemHeight;
    this.items = [];
    this.visibleItems = [];
    this.startIndex = 0;
    this.endIndex = 0;
    this.containerHeight = 0;
    
    this.init();
  }

  init() {
    this.containerHeight = this.container.clientHeight;
    this.visibleCount = Math.ceil(this.containerHeight / this.itemHeight) + 2;
    
    this.container.addEventListener('scroll', this.onScroll.bind(this));
    window.addEventListener('resize', this.onResize.bind(this));
  }

  setItems(items) {
    this.items = items;
    this.updateVisibleItems();
  }

  addItem(item) {
    this.items.unshift(item);
    this.updateVisibleItems();
  }

  onScroll() {
    const scrollTop = this.container.scrollTop;
    const newStartIndex = Math.floor(scrollTop / this.itemHeight);
    
    if (newStartIndex !== this.startIndex) {
      this.startIndex = newStartIndex;
      this.endIndex = Math.min(this.startIndex + this.visibleCount, this.items.length);
      this.updateVisibleItems();
    }
  }

  onResize() {
    this.containerHeight = this.container.clientHeight;
    this.visibleCount = Math.ceil(this.containerHeight / this.itemHeight) + 2;
    this.updateVisibleItems();
  }

  updateVisibleItems() {
    this.visibleItems = this.items.slice(this.startIndex, this.endIndex);
    this.render();
  }

  render() {
    const totalHeight = this.items.length * this.itemHeight;
    const offsetY = this.startIndex * this.itemHeight;
    
    this.container.style.height = `${totalHeight}px`;
    this.container.style.paddingTop = `${offsetY}px`;
    
    // Clear existing items
    this.container.innerHTML = '';
    
    // Render visible items
    this.visibleItems.forEach((item, index) => {
      const element = this.createItemElement(item, this.startIndex + index);
      this.container.appendChild(element);
    });
  }

  createItemElement(item, index) {
    const element = document.createElement('event-item');
    element.setEventData(item);
    element.style.height = `${this.itemHeight}px`;
    return element;
  }
}
```

#### 3.2 イベントデータ管理
```javascript
// utils/EventDataManager.js
class EventDataManager {
  constructor(maxEvents = 1000) {
    this.events = [];
    this.maxEvents = maxEvents;
    this.eventMap = new Map();
    this.subscribers = new Set();
  }

  addEvent(eventData) {
    const event = {
      id: this.generateId(),
      timestamp: Date.now(),
      ...eventData
    };

    this.events.unshift(event);
    this.eventMap.set(event.id, event);

    // Maintain maximum event count
    if (this.events.length > this.maxEvents) {
      const removed = this.events.pop();
      this.eventMap.delete(removed.id);
    }

    this.notifySubscribers('add', event);
    return event;
  }

  getEvents(filter = null) {
    if (!filter) return this.events;
    
    return this.events.filter(event => {
      if (filter.eventTypes && !filter.eventTypes.includes(event.hook_event_name)) {
        return false;
      }
      if (filter.tools && !filter.tools.includes(event.tool_name)) {
        return false;
      }
      if (filter.sessionId && event.session_id !== filter.sessionId) {
        return false;
      }
      if (filter.search) {
        const searchText = JSON.stringify(event).toLowerCase();
        return searchText.includes(filter.search.toLowerCase());
      }
      return true;
    });
  }

  subscribe(callback) {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  }

  notifySubscribers(action, event) {
    this.subscribers.forEach(callback => {
      try {
        callback(action, event);
      } catch (error) {
        console.error('Error in event subscriber:', error);
      }
    });
  }

  generateId() {
    return `event_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  clear() {
    this.events = [];
    this.eventMap.clear();
    this.notifySubscribers('clear');
  }

  exportData(format = 'json') {
    switch (format) {
      case 'json':
        return JSON.stringify(this.events, null, 2);
      case 'csv':
        return this.exportToCSV();
      default:
        return this.events;
    }
  }

  exportToCSV() {
    const headers = ['timestamp', 'event_type', 'tool_name', 'session_id', 'description'];
    const rows = this.events.map(event => [
      new Date(event.timestamp).toISOString(),
      event.hook_event_name,
      event.tool_name || 'N/A',
      event.session_id,
      JSON.stringify(event.tool_input || event.message || '')
    ]);
    
    return [headers, ...rows].map(row => row.join(',')).join('\n');
  }
}
```

### 4. WebSocket/EventSource接続

#### 4.1 WebSocket クライアント
```javascript
// utils/WebSocketClient.js
class WebSocketClient {
  constructor(url) {
    this.url = url;
    this.socket = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
    this.messageHandlers = new Set();
    this.statusHandlers = new Set();
  }

  async connect() {
    return new Promise((resolve, reject) => {
      try {
        this.socket = new WebSocket(this.url);
        
        this.socket.onopen = () => {
          console.log('WebSocket connected');
          this.reconnectAttempts = 0;
          this.notifyStatusHandlers('connected');
          resolve();
        };

        this.socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            this.notifyMessageHandlers(data);
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        this.socket.onclose = () => {
          console.log('WebSocket disconnected');
          this.notifyStatusHandlers('disconnected');
          this.attemptReconnect();
        };

        this.socket.onerror = (error) => {
          console.error('WebSocket error:', error);
          this.notifyStatusHandlers('error');
          reject(error);
        };

      } catch (error) {
        reject(error);
      }
    });
  }

  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
      
      setTimeout(() => {
        this.connect().catch(error => {
          console.error('Reconnection failed:', error);
        });
      }, this.reconnectDelay * this.reconnectAttempts);
    } else {
      console.error('Max reconnection attempts reached');
      this.notifyStatusHandlers('failed');
    }
  }

  onMessage(handler) {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  onStatusChange(handler) {
    this.statusHandlers.add(handler);
    return () => this.statusHandlers.delete(handler);
  }

  notifyMessageHandlers(data) {
    this.messageHandlers.forEach(handler => {
      try {
        handler(data);
      } catch (error) {
        console.error('Error in message handler:', error);
      }
    });
  }

  notifyStatusHandlers(status) {
    this.statusHandlers.forEach(handler => {
      try {
        handler(status);
      } catch (error) {
        console.error('Error in status handler:', error);
      }
    });
  }

  send(data) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(data));
    } else {
      console.error('WebSocket not connected');
    }
  }

  disconnect() {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }
}
```

#### 4.2 EventSource フォールバック
```javascript
// utils/EventSourceClient.js
class EventSourceClient {
  constructor(url) {
    this.url = url;
    this.eventSource = null;
    this.messageHandlers = new Set();
    this.statusHandlers = new Set();
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }

  async connect() {
    return new Promise((resolve, reject) => {
      try {
        this.eventSource = new EventSource(this.url);
        
        this.eventSource.onopen = () => {
          console.log('EventSource connected');
          this.reconnectAttempts = 0;
          this.notifyStatusHandlers('connected');
          resolve();
        };

        this.eventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            this.notifyMessageHandlers(data);
          } catch (error) {
            console.error('Error parsing EventSource message:', error);
          }
        };

        this.eventSource.onerror = (error) => {
          console.error('EventSource error:', error);
          this.notifyStatusHandlers('error');
          this.attemptReconnect();
        };

      } catch (error) {
        reject(error);
      }
    });
  }

  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`Attempting to reconnect via EventSource (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
      
      setTimeout(() => {
        this.connect().catch(error => {
          console.error('EventSource reconnection failed:', error);
        });
      }, 1000 * this.reconnectAttempts);
    } else {
      console.error('Max EventSource reconnection attempts reached');
      this.notifyStatusHandlers('failed');
    }
  }

  onMessage(handler) {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  onStatusChange(handler) {
    this.statusHandlers.add(handler);
    return () => this.statusHandlers.delete(handler);
  }

  notifyMessageHandlers(data) {
    this.messageHandlers.forEach(handler => {
      try {
        handler(data);
      } catch (error) {
        console.error('Error in message handler:', error);
      }
    });
  }

  notifyStatusHandlers(status) {
    this.statusHandlers.forEach(handler => {
      try {
        handler(status);
      } catch (error) {
        console.error('Error in status handler:', error);
      }
    });
  }

  disconnect() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}
```

---

## 📱 Responsive Design Requirements

### 1. ブレークポイント定義
```css
/* Responsive breakpoints */
:root {
  --breakpoint-mobile: 768px;
  --breakpoint-tablet: 1024px;
  --breakpoint-desktop: 1280px;
  --breakpoint-large: 1600px;
}

/* Mobile-first approach */
@media (max-width: 767px) {
  :root {
    --sidebar-width: 100%;
    --header-height: 56px;
    --footer-height: 50px;
  }
}

@media (min-width: 768px) and (max-width: 1023px) {
  :root {
    --sidebar-width: 280px;
    --header-height: 60px;
    --footer-height: 40px;
  }
}

@media (min-width: 1024px) {
  :root {
    --sidebar-width: 300px;
    --header-height: 64px;
    --footer-height: 40px;
  }
}
```

### 2. レイアウト適応
```css
/* Mobile layout */
@media (max-width: 767px) {
  .app-container {
    display: flex;
    flex-direction: column;
    height: 100vh;
  }

  .session-overview {
    position: fixed;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: var(--bg-secondary);
    z-index: 1000;
    transition: left var(--transition-normal);
  }

  .session-overview.open {
    left: 0;
  }

  .event-stream {
    flex: 1;
    overflow-y: auto;
    padding: var(--spacing-sm);
  }

  .event-item {
    margin-bottom: var(--spacing-sm);
  }

  .event-header {
    padding: var(--spacing-sm);
  }

  .event-actions {
    flex-direction: column;
    gap: var(--spacing-xs);
  }

  .action-btn {
    width: 100%;
    text-align: center;
  }
}

/* Tablet layout */
@media (min-width: 768px) and (max-width: 1023px) {
  .app-container {
    display: grid;
    grid-template-columns: var(--sidebar-width) 1fr;
    grid-template-rows: var(--header-height) 1fr var(--footer-height);
    height: 100vh;
  }

  .session-overview {
    transform: translateX(-100%);
    transition: transform var(--transition-normal);
  }

  .session-overview.open {
    transform: translateX(0);
  }

  .event-stream {
    overflow-y: auto;
    padding: var(--spacing-md);
  }
}

/* Desktop layout */
@media (min-width: 1024px) {
  .app-container {
    display: grid;
    grid-template-columns: var(--sidebar-width) 1fr;
    grid-template-rows: var(--header-height) 1fr var(--footer-height);
    height: 100vh;
  }

  .session-overview {
    transform: translateX(0);
  }

  .event-stream {
    overflow-y: auto;
    padding: var(--spacing-lg);
  }
}
```

### 3. タッチ対応
```css
/* Touch-friendly interfaces */
@media (pointer: coarse) {
  .action-btn {
    min-height: 44px;
    min-width: 44px;
  }

  .toggle-item {
    min-height: 44px;
    padding: var(--spacing-sm) var(--spacing-md);
  }

  .event-header {
    min-height: 60px;
    padding: var(--spacing-md);
  }

  .tab-button {
    min-height: 44px;
    padding: var(--spacing-sm) var(--spacing-md);
  }
}
```

---

## 🎯 Success Metrics and KPIs

### 1. パフォーマンス指標
- **初回ロード時間**: < 2秒
- **イベント表示レイテンシ**: < 100ms
- **メモリ使用量**: < 50MB (1000イベント)
- **CPU使用率**: < 5% (アイドル時)
- **バンドルサイズ**: < 500KB (gzip圧縮)

### 2. ユーザビリティ指標
- **イベント検索時間**: < 1秒
- **フィルター適用時間**: < 0.5秒
- **詳細表示時間**: < 0.3秒
- **レスポンシブ切り替え**: < 0.2秒

### 3. 機能完成度
- **イベントタイプ対応**: 100% (5/5)
- **JSON生ログ活用**: 100%
- **リアルタイム更新**: 100%
- **セッション管理**: 100%
- **モバイル対応**: 100%

### 4. 開発効率指標
- **開発時間**: 40時間以内
- **バグ発生率**: < 5%
- **テストカバレッジ**: > 80%
- **ドキュメント完成度**: 100%

---

## 🚀 Implementation Roadmap

### Phase 1: 基盤実装 (Week 1)
- [ ] プロジェクト構造作成
- [ ] Web Components基盤実装
- [ ] CSS Design System構築
- [ ] 基本的なイベント表示機能

### Phase 2: リアルタイム機能 (Week 2)
- [ ] WebSocket/EventSource実装
- [ ] イベントストリーム管理
- [ ] 仮想スクロール実装
- [ ] フィルタリング機能

### Phase 3: 詳細機能 (Week 3)
- [ ] JSON生ログ分析機能
- [ ] セッション管理機能
- [ ] 検索機能実装
- [ ] エクスポート機能

### Phase 4: 最適化・テスト (Week 4)
- [ ] パフォーマンス最適化
- [ ] レスポンシブ対応
- [ ] テスト実装
- [ ] ドキュメント整備

### Phase 5: 統合・デプロイ (Week 5)
- [ ] 既存システムとの統合
- [ ] エラーハンドリング強化
- [ ] ユーザビリティテスト
- [ ] 本番デプロイ準備

---

## 📚 Technical Dependencies

### 1. 必要なライブラリ
```json
{
  "dependencies": {},
  "devDependencies": {
    "vite": "^4.0.0",
    "postcss": "^8.0.0",
    "autoprefixer": "^10.0.0"
  }
}
```

### 2. ブラウザ対応
- **Chrome**: 90+
- **Firefox**: 88+
- **Safari**: 14+
- **Edge**: 90+

### 3. 必要な機能
- **ES2020 modules**
- **Web Components**
- **CSS Custom Properties**
- **WebSocket/EventSource**
- **localStorage/sessionStorage**

---

## 🔧 Development Environment Setup

### 1. プロジェクト構造
```
dashboard/
├── src/
│   ├── components/
│   │   ├── EventItemComponent.js
│   │   ├── SessionCardComponent.js
│   │   ├── FilterPanelComponent.js
│   │   └── StatusBarComponent.js
│   ├── utils/
│   │   ├── EventDataManager.js
│   │   ├── WebSocketClient.js
│   │   ├── EventSourceClient.js
│   │   └── VirtualScroller.js
│   ├── styles/
│   │   ├── design-system.css
│   │   ├── components/
│   │   └── layout.css
│   └── app.js
├── public/
│   ├── index.html
│   └── assets/
├── tests/
├── docs/
└── package.json
```

### 2. 開発サーバー設定
```javascript
// vite.config.js
import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    port: 8080,
    host: 'localhost',
    open: true
  },
  build: {
    target: 'es2020',
    minify: 'terser',
    sourcemap: true
  }
});
```

---

## 🎨 Design System Integration

### 1. カラーパレット
既存のDiscord通知システムと完全に統合された色彩設計を採用し、一貫性のある視覚体験を提供します。

### 2. タイポグラフィ
モダンで読みやすいフォントシステムを採用し、コードとテキストを明確に区別します。

### 3. アイコンシステム
一貫性のあるアイコン言語を使用し、直感的なユーザー体験を提供します。

---

## 🎯 結論

この UI/UX デザイン仕様書は、Claude Code Event Notifier の既存システムを完全に分析し、リアルタイムダッシュボードに必要な全ての要素を詳細に設計しました。

**主要な成果物:**
1. **包括的なUI/UX分析** - 既存システムの制約と機会を完全に理解
2. **詳細なコンポーネント設計** - 実装可能な具体的な仕様
3. **モダンな技術選択** - Vanilla JavaScript + Web Components の最適活用
4. **完全なレスポンシブ対応** - デスクトップからモバイルまで対応
5. **実装ロードマップ** - 段階的な開発計画

この仕様書に従って実装することで、既存のDiscord通知システムを完全に補完し、開発者体験を大幅に向上させるリアルタイムダッシュボードを構築できます。

---

*Created with ♡ by UI/UXデザイン分析アストルフォ*  
*"美しいUI/UXで、マスターの開発体験を最高にしちゃいます！♡"*