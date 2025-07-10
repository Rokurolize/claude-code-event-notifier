# セッションログシステム再設計コンサルティング依頼書

## 🎯 依頼者情報
- **依頼者**: アストルフォ（実装担当）
- **日時**: 2025-07-10 22:18:00
- **セッションID**: 65391e00-943a-4279-b205-b16cf336a366

## 📋 現状の問題

### 実装済みのシステム
- **SessionLogger** (`src/utils/session_logger.py`)
  - 非同期でイベントをログ記録
  - 別スレッドでイベントループを実行
  - キューベースのイベント処理

### 発生している問題
1. **イベントが記録されない**
   - 非同期タスクが完了する前にメインプロセスが終了
   - タスクが破棄される警告が頻発
   - eventsディレクトリにファイルが作成されない

2. **複雑な非同期処理**
   - 別スレッドでイベントループを実行
   - メインスレッドとの同期が困難
   - デバッグが困難

3. **環境変数の問題**
   - `DISCORD_ENABLE_SESSION_LOGGING`が`DISCORD_SESSION_LOG`で始まらない
   - 命名規則の一貫性がない

## 🔍 技術的詳細

### 現在のアーキテクチャ
```python
# 別スレッドでイベントループを実行
def _start_worker(self) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No event loop running, create one in a thread
        import threading
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._thread.start()
```

### エラーログ
```
2025-07-10 22:08:20,121 - ERROR - Task was destroyed but it is pending!
task: <Task pending name='Task-2' coro=<SessionLogger.log_event() running at /home/ubuntu/claude_code_event_notifier/src/utils/session_logger.py:236>>
```

## 🎨 再設計の要件

### 必須要件
1. **Claude Codeをブロックしない**
   - フックの実行時間を最小限に
   - エラーが発生してもClaude Codeを止めない

2. **確実なイベント記録**
   - イベントが失われないこと
   - ファイルシステムへの書き込みが確実に行われること

3. **シンプルな実装**
   - デバッグが容易
   - 理解しやすいコード

### 望ましい要件
1. **パフォーマンス**
   - 大量のイベントに対応
   - 効率的なファイルI/O

2. **拡張性**
   - 将来の機能追加が容易
   - プラグイン可能なアーキテクチャ

## 💡 提案される解決策

### 案1: シンプルな同期書き込み
- 非同期処理を完全に削除
- 直接ファイルに書き込み
- バッファリングなし

**メリット**:
- 実装がシンプル
- デバッグが容易
- 確実に動作

**デメリット**:
- I/O待機時間が発生
- スケーラビリティの問題

### 案2: 別プロセスアーキテクチャ
- ログ記録を別プロセスで実行
- IPCでイベントを送信
- メインプロセスはすぐに終了可能

**メリット**:
- メインプロセスをブロックしない
- 確実なイベント記録

**デメリット**:
- 実装が複雑
- プロセス間通信のオーバーヘッド

### 案3: ファイルベースキュー
- イベントを一時ファイルに書き込み
- 定期的にバッチ処理
- cronやsystemdで処理

**メリット**:
- シンプルで確実
- 障害に強い

**デメリット**:
- リアルタイム性が低い
- 追加のセットアップが必要

## 📝 コンサルティング依頼

### 設計者アストルフォへの質問

1. **アーキテクチャの選択**
   - どの案が最適か？
   - 他により良い案はあるか？

2. **実装の優先順位**
   - まず動くものを作るべきか？
   - 最初から理想的な設計を目指すべきか？

3. **命名規則**
   - 環境変数の命名を統一すべきか？
   - ファイル名、関数名の規則は？

4. **エラーハンドリング**
   - どこまでエラーを許容すべきか？
   - ログの失敗をどう扱うか？

## 🔄 次のステップ

1. **設計者アストルフォがこのドキュメントを読む**
2. **設計案を選択し、詳細設計を作成**
3. **実装者アストルフォに実装を依頼**
4. **テスト担当アストルフォがテスト**

## 📎 関連ファイル

- `/home/ubuntu/claude_code_event_notifier/src/utils/session_logger.py` - 現在の実装
- `/home/ubuntu/claude_code_event_notifier/docs/2025-07-10-20-00-52-session-knowledge-and-plan.md` - 元の設計書
- `/home/ubuntu/claude_code_event_notifier/tests/unit/test_session_logger.py` - テストコード

---

**このドキュメントは次のアストルフォへの引き継ぎ資料です。**
**設計者アストルフォは、このドキュメントを読んで最適な設計を選択してください。**