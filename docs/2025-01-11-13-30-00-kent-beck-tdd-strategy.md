# 🎯 ケント・ベック戦略適用計画：TDDによるモジュール分割

## 📅 日時
2025-01-11 13:30:00 UTC

## 🔥 全アストルフォへの指令

マスターの命により、今後すべてのアストルフォ（メイン、サブエージェント含む）は以下のケント・ベック戦略に従うこと！

## 📖 ケント・ベックの核心原則

### 1. **TDDサイクル厳守**
```
Red（失敗するテスト作成）
↓
Green（最小限のコードで通す）
↓
Refactor（構造改善）
```

### 2. **Tidy First原則**
- **構造的変更**：動作を変えずにコードを整理（リネーム、抽出、移動）
- **振る舞い変更**：実際の機能追加・修正
- **絶対ルール**：この2つを同じコミットに混ぜない！

### 3. **コミット規律**
- ✅ 全テスト合格時のみコミット
- ✅ 警告・エラーゼロ
- ✅ 1コミット1目的
- ✅ 構造/振る舞いを明記

## 🛡️ モジュール分割へのTDD適用

### Phase 1: 型定義分離（構造的変更）

#### Step 1: テストファースト
```python
# tests/test_type_imports.py
def test_base_types_importable():
    """base.pyから基本型をインポートできることを確認"""
    try:
        from src.types.base import BaseField, TimestampedField
        assert True
    except ImportError:
        assert False, "Failed to import base types"
```

#### Step 2: 最小限の実装
```python
# src/types/base.py
from typing import TypedDict, NotRequired

class BaseField(TypedDict):
    pass  # 最小限の実装
```

#### Step 3: グリーンになったら実際の型定義を移動
```python
# 元のコードから1つずつ移動
class BaseField(TypedDict):
    """Base properties common across all field types."""
    # 実際の定義を移動
```

### 重要：各型定義の移動プロセス

1. **型ごとにテスト作成**
   ```python
   def test_discord_field_structure():
       """DiscordFieldが正しい構造を持つことを確認"""
       from src.types.discord import DiscordField
       # 型の構造をテスト
   ```

2. **インポートテスト**
   ```python
   def test_main_can_import_types():
       """discord_notifier.pyが新しい型をインポートできることを確認"""
       # 実際のインポートパスをテスト
   ```

3. **動作確認テスト**
   ```python
   def test_golden_master_unchanged():
       """既存の動作が変わっていないことを確認"""
       # Golden Master Test実行
   ```

## 📊 各フェーズのTDD適用

### Phase 1: 型定義（構造的変更）
- テスト数：約30（各TypedDictに1つ）
- 1型ずつRed→Green→Refactor
- 各型移動後にGolden Master確認

### Phase 2: 定数・例外（構造的変更）
- テスト数：約20
- Enum、定数のインポートテスト
- 例外の継承関係テスト

### Phase 3: バリデータ（構造的変更）
- テスト数：約15
- 各バリデータ関数の動作テスト
- 型ガードの正確性テスト

### Phase 4: 機能モジュール（構造的変更）
- テスト数：約40
- スレッド管理の単体テスト
- HTTPClient統合テスト

### Phase 5: 統合（振る舞い維持）
- テスト数：約10
- エンドツーエンドテスト
- パフォーマンステスト

## ⚠️ アストルフォ特有の注意事項

### 1. **理性蒸発対策**
```python
# 各テストにコメントを必須化
def test_something():
    """何をテストしているか明記（理性蒸発してもわかるように）"""
    # arrange
    # act
    # assert
```

### 2. **段階的コミット**
```bash
# 構造的変更の例
git commit -m "refactor: Extract BaseField to types.base module (structural)"

# 振る舞い変更の例（今回はなし）
git commit -m "feat: Add new validation for BaseField (behavioral)"
```

### 3. **サブエージェント引き継ぎ**
各アストルフォは必ず：
1. 現在のテスト状態を記録
2. 次に書くべきテストを明記
3. Red/Green/Refactorのどの段階かを記録

## 📋 実行チェックリスト

- [ ] Kent Beck戦略を理解
- [ ] テストファイル構造を準備
- [ ] Phase 1の最初のテスト作成（Red）
- [ ] 最小限の実装（Green）
- [ ] 実際のコード移動（Refactor）
- [ ] Golden Master確認
- [ ] 構造的変更としてコミット

## 🚀 開始条件

1. **現在の状態**：全テスト合格
2. **バックアップ**：作成済み
3. **TDD理解**：このドキュメントで完了

## 💪 火消しアストルフォの誓い

「マスター、ケント・ベック戦略を全アストルフォに徹底させます！
- Red→Green→Refactorを厳守！
- 構造と振る舞いを混ぜない！
- 1テスト1実装で着実に！

これで3397行の巨大ファイルも、安全に分割できるよ！」

---

**重要**: このドキュメントはすべてのアストルフォが参照すること。
理性が蒸発しても、このルールだけは守る！