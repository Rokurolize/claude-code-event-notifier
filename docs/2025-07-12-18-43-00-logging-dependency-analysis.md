# Logging モジュールの依存関係分析レポート

生成日時: 2025-07-12 18:43:00
分析者: 調査アストルフォ

## 概要

src全体のloggingモジュールとAstolfoLoggerの使用状況、インポート依存関係、移行リスクの分析結果をまとめました。

## 1. 現在のロガー使用状況

### 1.1 AstolfoLoggerを使用しているモジュール

| モジュール | 使用方法 | 依存度 |
|-----------|---------|--------|
| `discord_notifier.py` | setup_astolfo_logger()でメインロガー作成 | 高（中心的役割） |
| `thread_storage.py` | setup_astolfo_logger()で独自ロガー作成 | 中 |
| `discord_sender.py` | AstolfoLoggerを型として受け取る | 高（必須依存） |

### 1.2 標準loggingを使用しているモジュール

| モジュール | 使用方法 | 移行難易度 |
|-----------|---------|----------|
| `session_logger.py` | logging.getLogger(__name__) | 低 |
| `transcript_reader.py` | logging.getLogger(__name__) | 低 |
| `config.py` | logging.getLogger(__name__) | 低 |
| `http_client.py` | Union[logging.Logger, AstolfoLogger] | 中（既に対応済み） |
| `thread_manager.py` | logging（importのみ） | 低 |
| `message_sender.py` | logging（importのみ） | 低 |

## 2. インポート依存関係の分析

### 2.1 依存関係グラフ

```
discord_notifier.py
├── utils.astolfo_logger (setup_astolfo_logger, AstolfoLogger)
├── thread_storage.py
│   └── utils.astolfo_logger (独自インスタンス)
├── handlers.discord_sender.py
│   └── utils.astolfo_logger (AstolfoLogger型)
├── core.http_client.py
│   └── utils.astolfo_logger (条件付きインポート)
└── その他のモジュール（標準logging使用）
```

### 2.2 循環インポートのリスク評価

**現在検出された循環インポート: なし**

潜在的リスク箇所:
- `http_client.py` が条件付きで `AstolfoLogger` をインポート
- `discord_sender.py` が `AstolfoLogger` を型として必須依存

## 3. 移行時の推奨順序

### Phase 1: 基盤モジュール（リスク: 低）
1. **session_logger.py**
   - 独立したモジュール
   - 他モジュールからの依存なし
   - `logging.getLogger(__name__)` → `setup_astolfo_logger(__name__)`

2. **transcript_reader.py**
   - 独立したモジュール
   - 他モジュールからの依存なし
   - 同様の変更で対応可能

### Phase 2: コアモジュール（リスク: 中）
3. **config.py**
   - 多くのモジュールから使用される
   - ただしロガーは内部使用のみ
   - 慎重なテストが必要

4. **thread_manager.py**
   - loggingをインポートしているが未使用
   - 実装時に `setup_astolfo_logger` を使用

5. **message_sender.py**
   - loggingをインポートしているが未使用
   - 実装時に `setup_astolfo_logger` を使用

### Phase 3: 既存実装の改善（リスク: 低）
6. **http_client.py**
   - 既に `Union[logging.Logger, AstolfoLogger]` 対応済み
   - 条件付きインポートの整理のみ

## 4. 実装上の注意点

### 4.1 インポート順序の推奨

```python
# 標準ライブラリ
import logging  # 必要な場合のみ
from typing import ...

# プロジェクト内部
from src.utils.astolfo_logger import setup_astolfo_logger, AstolfoLogger

# モジュール初期化
logger = setup_astolfo_logger(__name__)
```

### 4.2 型アノテーションの扱い

```python
# 型チェック時のみのインポート
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.utils.astolfo_logger import AstolfoLogger

# 実行時のセットアップ
def setup_logger(name: str) -> "AstolfoLogger":
    from src.utils.astolfo_logger import setup_astolfo_logger
    return setup_astolfo_logger(name)
```

### 4.3 後方互換性の維持

```python
# 移行期間中の互換性確保
try:
    from src.utils.astolfo_logger import setup_astolfo_logger
    logger = setup_astolfo_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
```

## 5. テスト戦略

### 5.1 単体テスト
- 各モジュール個別の動作確認
- ロガー出力の検証
- エラーハンドリングの確認

### 5.2 統合テスト
- モジュール間の連携確認
- 実際のイベント処理フロー検証
- パフォーマンステスト

### 5.3 段階的リリース
1. 開発環境でPhase 1実施
2. 問題なければPhase 2へ
3. 全体テスト後に本番適用

## 6. 結論

現在の実装は比較的クリーンで、循環インポートのリスクは低い。推奨順序に従って段階的に移行することで、安全にAstolfoLoggerへの統一が可能。

特に注意すべき点:
- `discord_sender.py` は既にAstolfoLoggerに強く依存
- `config.py` は多くのモジュールから使用されるため慎重に
- 移行は独立性の高いモジュールから開始

---

*このレポートは2025-07-12時点の分析結果です。コードベースの変更により内容が古くなる可能性があります。*