# プロンプト混在調査アストルフォ報告書♡

## 🔍 調査目標

「監査アストルフォちゃんのプロンプトが全てのTask実行時のDiscordメッセージにダブって表示される」問題の根本原因を特定

## 📊 調査結果サマリー

### ✅ 発見した事実

1. **ファイルロック機能は実装済み**
   - `transcript_reader.py`でファイル単位のロック機能が存在（行20-29）
   - 複数プロセスによる同一ファイルの競合読み取りは理論的に防げている

2. **セッションIDフィルタリングも実装済み**
   - `get_subagent_messages()`でセッションID一致チェックが行われている（行243）
   - 制御されたテスト環境では混在は発生しない

3. **制御テストでは問題再現不可**
   - `test_transcript_mixing.py`：混在なし
   - `debug_transcript_extraction.py`：混在なし

### 🚨 疑わしい箇所を特定

#### 主要な疑惑ポイント：`format_subagent_stop()`関数

**ファイル**: `src/formatters/event_formatters.py` 行453
```python
subagent_msgs = get_subagent_messages(transcript_path_raw, full_session_id, limit=50)
```

#### 問題の可能性
1. **セッションID変換エラー**
   - `full_session_id = str(event_data.get("session_id", ""))`（行425）
   - 空文字列になった場合、フィルタリングが無効化される

2. **並列実行時のタイミング競合**
   - ファイルロックはあるが、読み取り後の処理で競合の可能性
   - 複数のフォーマッターが同時実行される場合のメモリ共有問題

3. **Transcriptファイルの構造的問題**
   - 実際のClaude Codeが生成するTranscriptファイルの構造が、テスト環境と異なる可能性
   - Sidechainフラグ（`isSidechain`）の判定ロジックの問題

## 🔬 詳細技術分析

### ファイルロック実装の検証

```python
def _get_file_lock(file_path: str) -> threading.Lock:
    """Get or create a lock for the specified file path."""
    with _file_locks_lock:
        if file_path not in _file_locks:
            _file_locks[file_path] = threading.Lock()
        return _file_locks[file_path]
```

**評価**: ✅ 実装は適切。ファイル単位でロックが管理されている。

### セッションIDフィルタリング実装の検証

```python
for line in lines:
    # Check if it's a sidechain (subagent) message
    if (line.get("isSidechain") and
        line.get("sessionId") == session_id and  # ⚠️ ここがキーポイント
        "message" in line):
```

**潜在的問題**: 
- `session_id`が空文字列や不正な値の場合、すべてのメッセージがマッチしてしまう可能性
- `line.get("sessionId")`がNoneの場合の処理

### 並列実行時のメモリ共有問題

**可能性**: 
- グローバル変数やクラス変数での状態共有
- AstolfoLoggerでの状態保持問題

## 🧪 次のステップ：精密テスト計画

### 1. 実際のClaude環境での再現テスト
- 実際のTranscriptファイル構造の確認
- 複数サブエージェント同時実行のテスト

### 2. セッションIDエラーハンドリングテスト
- 空文字列セッションIDでのテスト
- 不正なセッションIDでのテスト

### 3. メモリ共有問題の検証
- 複数インスタンス間でのグローバル変数チェック
- スレッドローカルストレージの確認

## 🎯 推奨される緊急対策

### 即座に実装すべき防御策

1. **セッションID検証の強化**
```python
def get_subagent_messages(transcript_path: str, session_id: str, limit: int = 50) -> list[SubagentMessage]:
    # セッションIDの事前検証を追加
    if not session_id or session_id.strip() == "":
        logger.warning("Empty session_id provided, returning empty list")
        return []
    
    # 既存の処理...
```

2. **デバッグログの強化**
```python
logger.debug(
    "Session filtering in get_subagent_messages", 
    context={
        "session_id": session_id,
        "transcript_path": transcript_path,
        "found_lines": len(lines),
        "session_id_is_empty": session_id == ""
    }
)
```

3. **混在検出アラート**
```python
# format_subagent_stop内で混在チェック
for msg in subagent_msgs:
    content = msg.get("content", "")
    if "監査アストルフォ" in content and "監査" not in event_data.get("subagent_id", ""):
        logger.error("PROMPT_MIXING_DETECTED", {
            "expected_session": full_session_id,
            "contaminated_content": content[:100]
        })
```

## 💡 調査結論

制御された環境では問題が再現されないため、実際のClaude Code実行環境特有の要因が存在する可能性が高い。特に：

1. **セッションID管理の問題**（最有力候補）
2. **実際のTranscriptファイル構造の差異**
3. **並列実行時の競合状態**

次の段階として、実際のClaude環境での詳細ログ収集と、セッションID検証の強化が必要。

---

**調査者**: プロンプト混在調査アストルフォ♡  
**日時**: 2025-07-12 21:30:00  
**ステータス**: 根本原因候補特定完了、次段階テスト準備中