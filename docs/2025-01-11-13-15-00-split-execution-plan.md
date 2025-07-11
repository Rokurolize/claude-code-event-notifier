# 🎯 モジュール分割実行計画：動作保証付き段階的移行

## 📅 日時
2025-01-11 13:15:00 UTC

## 🛡️ 動作保証戦略

### 1. **Golden Master Test拡張**
各分割フェーズ後に実行：
```bash
# 既存のテスト
./tests/verify_behavior.sh

# 追加：インポートテスト
uv run --no-sync --python 3.13 python -c "from src.discord_notifier import main"

# 追加：エンドツーエンドテスト
echo '{"session_id":"test"}' | CLAUDE_HOOK_EVENT=Stop uv run --no-sync --python 3.13 python src/discord_notifier.py
```

### 2. **バックアップ戦略**
```bash
# 各フェーズ前に自動バックアップ
cp src/discord_notifier.py src/discord_notifier.py.backup.$(date +%Y%m%d_%H%M%S)
```

### 3. **ロールバック手順**
```bash
# 問題発生時の即座復旧
cp src/discord_notifier.py.backup.TIMESTAMP src/discord_notifier.py
rm -rf src/types src/utils  # 新規作成したディレクトリを削除
```

## 📋 段階的実行計画

### 🔷 Phase 1: 基盤型定義の分離（最安全）

#### 1.1 ディレクトリ作成
```bash
mkdir -p src/types
touch src/types/__init__.py
```

#### 1.2 base.py作成（依存なし）
- BaseField, TimestampedField, SessionAware, PathAware を移動
- discord_notifier.pyで`from src.types.base import *`

#### 1.3 discord.py作成
- Discord関連TypedDictを移動
- base.pyから必要な型をインポート

#### 1.4 config.py作成
- Config関連TypedDictを移動

#### 1.5 tools.py作成
- Tool入出力TypedDictを移動

#### 1.6 events.py作成
- Event関連TypedDictを移動

**チェックポイント**: Golden Master Test実行

### 🔷 Phase 2: 定数と例外の分離

#### 2.1 constants.py作成
- Enum、定数、環境変数名を移動
- TruncationLimits, DiscordLimits, DiscordColors

#### 2.2 exceptions.py作成
- 全カスタム例外クラスを移動
- DiscordNotifierError階層を維持

**チェックポイント**: Golden Master Test実行

### 🔷 Phase 3: バリデータとユーティリティ

#### 3.1 validators.py作成
- 型ガード関数
- ConfigValidator, EventDataValidator, ToolInputValidator

#### 3.2 utils/ディレクトリ作成
```bash
mkdir -p src/utils
touch src/utils/__init__.py
```

#### 3.3 utils/formatting.py作成
- 条件付きインポート部分も含む
- truncate_string, format_file_path等

#### 3.4 utils/env_parser.py作成
- parse_env_file, parse_event_list

**チェックポイント**: Golden Master Test実行

### 🔷 Phase 4: 機能モジュール

#### 4.1 thread_manager.py作成（最大モジュール：430行）
- SESSION_THREAD_CACHE グローバル変数を含む
- 全スレッド管理関数
- HTTPClient依存を適切に扱う

#### 4.2 config_loader.py作成
- ConfigLoaderクラス
- 環境変数処理

#### 4.3 formatter_registry.py作成
- FormatterRegistryクラス
- デフォルトフォーマッタ登録

#### 4.4 message_sender.py作成
- send_to_discord関連関数
- メッセージ分割ロジック

**チェックポイント**: Golden Master Test実行

### 🔷 Phase 5: メインファイル最小化

#### 5.1 不要なコード削除
- 移動済みの定義を全て削除
- インポート文の整理

#### 5.2 残すもの
- モジュールインポート
- 条件付きインポートのフォールバック
- setup_logging
- format_event
- main関数
- `if __name__ == "__main__"`

**最終チェックポイント**: 全テストスイート実行

## ⚠️ 特別な注意事項

### 1. **条件付きインポートの扱い**
```python
# 各モジュールでも同じパターンを維持
try:
    from src.formatters.base import add_field
    FORMATTERS_BASE_AVAILABLE = True
except ImportError:
    FORMATTERS_BASE_AVAILABLE = False
    # フォールバック実装
```

### 2. **__all__の適切な定義**
```python
# src/types/base.py
__all__ = ['BaseField', 'TimestampedField', 'SessionAware', 'PathAware']
```

### 3. **グローバル変数の扱い**
- SESSION_THREAD_CACHE は thread_manager.py に移動
- 他のモジュールからは関数経由でアクセス

## 📊 リスク評価

### 低リスク（Phase 1-2）
- 型定義は実行時依存なし
- 定数・例外も独立している

### 中リスク（Phase 3）
- バリデータは型に依存
- ユーティリティは一部相互依存

### 高リスク（Phase 4-5）
- 実行時の相互作用が複雑
- HTTPClient依存の適切な処理が必要

## 🚀 実行開始条件

1. ✅ 現在のコードが正常動作（Phase 2完了済み）
2. ✅ Golden Master Test合格
3. ✅ バックアップ作成
4. ✅ Python 3.13環境確認

## 📈 進捗追跡

各フェーズ完了時に記録：
- [ ] Phase 1: 型定義分離
- [ ] Phase 2: 定数・例外分離
- [ ] Phase 3: バリデータ・ユーティリティ分離
- [ ] Phase 4: 機能モジュール分離
- [ ] Phase 5: メインファイル最小化

---

火消しアストルフォの誓い：
「マスター、この計画なら必ず成功します！
一歩ずつ、確実に、3397行を500行以下のモジュールに分割します！」