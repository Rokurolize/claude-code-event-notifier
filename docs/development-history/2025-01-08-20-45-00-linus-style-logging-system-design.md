# Linus Torvalds風ログシステム設計案

## 現在の問題点

### 既存システムの課題
- **日付別ログファイル**: ヘビーユーザーの場合、1日で数百MB〜数GBに肥大化
- **セッション混在**: 複数セッションが混在して特定セッションの追跡が困難
- **並行実行問題**: Claude Codeの多重実行時にログが混乱
- **検索性の低さ**: 特定のイベントやエラーを見つけるのが困難

### 現在のログファイル構造
```
~/.claude/hooks/logs/
├── discord_notifier_2025-01-08.log  # 全セッション混在
├── discord_notifier_2025-01-07.log  # 巨大ファイル化
└── ...
```

## Linus Torvalds設計哲学の適用

### 核となる原則
1. **"Good design is when you remove something and it still works"**
   - 過度に複雑な設定は避ける
   - デフォルトで十分に機能する

2. **データ構造を重視**
   - ログエントリの構造を統一
   - ファイル配置の一貫性

3. **Unix哲学の活用**
   - 既存ツール（grep, find, tail）との親和性
   - パイプライン処理の考慮

4. **スケーラビリティ**
   - 大量のログでも性能劣化しない
   - 自動クリーンアップ機能

## 提案する新設計

### 1. 階層的時間窓 + セッション分離

```
~/.claude/hooks/logs/
├── 2025-01-08/
│   ├── 00-04/                    # 4時間窓
│   │   ├── session_abc123.log    # セッション別ログ
│   │   ├── session_def456.log
│   │   └── sessions.index        # セッション索引
│   ├── 04-08/
│   │   ├── session_ghi789.log
│   │   └── sessions.index
│   ├── 08-12/
│   └── ...
├── 2025-01-07/
└── ...
```

### 2. 構造化ログフォーマット

```
# 統一フォーマット: ISO8601時刻 [セッションID] レベル: メッセージ
2025-01-08T14:30:15.123 [abc123] INFO: Processing PreToolUse event
2025-01-08T14:30:15.124 [abc123] DEBUG: Thread lookup: cache miss
2025-01-08T14:30:16.001 [abc123] WARN: Failed to create thread, fallback to main channel
2025-01-08T14:30:16.002 [abc123] ERROR: Discord API error 400: Maximum active threads reached
```

### 3. 実装クラス設計

```python
class LinusStyleLogger:
    """
    Linus Torvalds風のシンプルで効率的なログシステム
    - セッション別ファイル分離
    - 4時間窓での自動分割
    - Unix哲学準拠
    """
    
    def __init__(self, session_id: str, window_hours: int = 4):
        self.session_id = session_id
        self.window_hours = window_hours
        self.current_window = self._get_time_window()
        self.log_file = self._get_log_file()
    
    def _get_time_window(self) -> str:
        """4時間窓でファイルを分割"""
        now = datetime.now()
        window_start = (now.hour // self.window_hours) * self.window_hours
        window_end = window_start + self.window_hours
        return f"{now.date()}/{window_start:02d}-{window_end:02d}"
    
    def _get_log_file(self) -> Path:
        """session_id別 + 時間窓別のログファイル"""
        base_dir = Path("~/.claude/hooks/logs").expanduser()
        window_dir = base_dir / self.current_window
        window_dir.mkdir(parents=True, exist_ok=True)
        
        # セッションファイルへの参照をインデックスに記録
        self._update_session_index(window_dir)
        
        return window_dir / f"session_{self.session_id}.log"
    
    def _update_session_index(self, window_dir: Path):
        """セッション索引を更新（検索最適化）"""
        index_file = window_dir / "sessions.index"
        with open(index_file, "a") as f:
            f.write(f"{self.session_id}\n")
    
    def log(self, level: str, message: str):
        """構造化ログエントリを記録"""
        timestamp = datetime.now().isoformat(timespec='milliseconds')
        entry = f"{timestamp} [{self.session_id}] {level}: {message}\n"
        
        with open(self.log_file, "a") as f:
            f.write(entry)
```

### 4. 自動クリーンアップシステム

```python
def cleanup_old_logs(retention_days: int = 7):
    """
    Linusが好むシンプルな自動クリーンアップ
    - 指定日数より古いログを削除
    - 日別ディレクトリ単位での削除
    """
    cutoff = datetime.now() - timedelta(days=retention_days)
    base_dir = Path("~/.claude/hooks/logs").expanduser()
    
    for log_dir in base_dir.glob("20*"):
        try:
            dir_date = datetime.strptime(log_dir.name, "%Y-%m-%d")
            if dir_date < cutoff:
                shutil.rmtree(log_dir)
                print(f"Cleaned up old logs: {log_dir}")
        except ValueError:
            # 日付形式でないディレクトリは無視
            continue
```

### 5. ログローテーション機能

```python
def rotate_if_needed(log_file: Path, max_size_mb: int = 10):
    """
    ファイルサイズベースの自動ローテーション
    - 10MB超過時に自動ローテート
    - .1, .2, .3 の連番でバックアップ
    """
    if not log_file.exists():
        return
    
    max_size = max_size_mb * 1024 * 1024
    if log_file.stat().st_size > max_size:
        # 既存のローテートファイルをシフト
        for i in range(9, 0, -1):
            old_file = log_file.with_suffix(f".{i}")
            if old_file.exists():
                old_file.rename(log_file.with_suffix(f".{i+1}"))
        
        # 現在のファイルを .1 にリネーム
        log_file.rename(log_file.with_suffix(".1"))
```

## Unix哲学準拠の検索・監視コマンド

### 基本的な検索コマンド

```bash
# 特定セッションのログを見る
find ~/.claude/hooks/logs -name "session_abc123.log" -exec tail -f {} \;

# 最新のエラーを検索
find ~/.claude/hooks/logs -name "*.log" -mtime -1 -exec grep -l "ERROR\|WARN" {} \;

# 今日のスレッドフォールバック事例
grep -r "fallback to.*channel" ~/.claude/hooks/logs/$(date +%Y-%m-%d)/

# 現在のセッションを監視
tail -f ~/.claude/hooks/logs/$(date +%Y-%m-%d)/$(date +%H | awk '{print int($1/4)*4}')-*/session_*.log

# 全エラーを監視
tail -f ~/.claude/hooks/logs/$(date +%Y-%m-%d)/*/session_*.log | grep -E "ERROR|WARN"
```

### 高度な分析コマンド

```bash
# セッション別エラー統計
find ~/.claude/hooks/logs -name "session_*.log" -exec basename {} \; | \
    cut -d_ -f2 | cut -d. -f1 | sort | uniq -c | sort -nr

# 時間帯別ログ分析
find ~/.claude/hooks/logs -name "*.log" -exec grep -l "ERROR" {} \; | \
    grep -o '[0-9]\{2\}-[0-9]\{2\}' | sort | uniq -c

# フォールバック発生頻度分析
grep -r "fallback to.*channel" ~/.claude/hooks/logs/ | \
    cut -d: -f1 | xargs -I {} dirname {} | sort | uniq -c
```

## 実装時の注意点

### 1. 既存システムとの互換性
- 現在の `ConfigLoader` システムに統合
- 既存のデバッグ設定（`DISCORD_DEBUG`）を維持
- 段階的移行でリスクを最小化

### 2. パフォーマンス考慮
- ログファイルの書き込みはバッファリング
- インデックスファイルの効率的な更新
- メモリ使用量の最適化

### 3. エラーハンドリング
- ログシステム自体のエラーがメイン処理を妨げない
- ディスク容量不足時のグレースフルデグラデーション
- 権限問題への対応

### 4. 設定の柔軟性
- 時間窓サイズの調整可能
- ログレベルの細かい制御
- 自動クリーンアップ設定

## 移行計画

### Phase 1: 新ログシステムの実装
1. `LinusStyleLogger` クラスの実装
2. 既存 `discord_notifier.py` への統合
3. 単体テストの作成

### Phase 2: 段階的移行
1. デバッグモードでの並行運用
2. 既存ログとの比較検証
3. 設定オプションでの切り替え

### Phase 3: 完全移行
1. 既存ログシステムの廃止
2. ドキュメントの更新
3. 自動クリーンアップの有効化

## テスト方針

### 1. 単体テスト
- ログファイル作成のテスト
- 時間窓分割のテスト
- セッション索引更新のテスト

### 2. 統合テスト
- 並行セッションでの動作確認
- ログローテーションの検証
- 自動クリーンアップの動作確認

### 3. 性能テスト
- 大量ログでの性能測定
- 検索速度の比較
- メモリ使用量の測定

## 期待される効果

1. **検索性の大幅改善**
   - セッション別ファイルで特定セッションの追跡が容易
   - 時間窓分割で時系列分析が効率的

2. **運用性の向上**
   - 自動クリーンアップでディスク容量管理が不要
   - 構造化ログで自動分析が可能

3. **パフォーマンス向上**
   - 小さなファイルでの高速検索
   - 並行処理での競合回避

4. **Unix哲学準拠**
   - 既存ツールとの親和性
   - パイプライン処理の最適化

この設計により、スケーラビリティ、検索性、リアルタイム監視すべてを両立できます。