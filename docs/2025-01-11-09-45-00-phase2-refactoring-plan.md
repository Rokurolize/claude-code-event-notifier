# 🚒 Phase 2 リファクタリング計画：フォーマッター関数の統合

## 📅 日時
2025-01-11 09:45:00 UTC

## 🎯 目標
discord_notifier.py から重複している12個のフォーマッター関数を削除し、tool_formatters.py の実装を使用する。

## 📊 現状分析

### アーキテクチャの理想状態
```
discord_notifier.py
    ↓ imports
tool_formatters.py
    ↓ imports
formatters.base （truncate_string, add_field, etc.）
```

### 現在の問題
- discord_notifier.py に12個の重複実装
- tool_formatters.py は正しく formatters.base を使用
- 型定義の違い（ToolInput vs 具体的なTypedDict）

## 🔧 実装計画

### Step 1: 型の互換性確認
1. ToolInput（dict[str, Any]）と具体的なTypedDict の互換性確認
2. 必要に応じて型変換またはキャスト

### Step 2: 段階的移行（関数ごと）
1. **最初のテスト対象**: `format_bash_pre_use`
   - discord_notifier.py の実装を削除
   - tool_formatters.py からインポート
   - Golden Master Test で確認

2. **成功したら残り11個を処理**
   - 一括でインポート追加
   - 一括で実装削除
   - テスト実行

### Step 3: クリーンアップ
1. 不要なインポートの削除
2. コメントの整理
3. 最終テスト

## ⚠️ リスクと対策

### リスク1: 型の非互換性
- **症状**: TypeError at runtime
- **対策**: 型キャストまたはラッパー関数

### リスク2: 微妙な実装の違い
- **症状**: Golden Master Test失敗
- **対策**: 差分を詳細に分析、必要に応じて調整

### リスク3: インポート循環
- **症状**: ImportError
- **対策**: インポート構造の見直し

## 🛡️ 安全対策

1. **Golden Master Test必須**
   - 各変更後に実行
   - 失敗したら即ロールバック

2. **バックアップ**
   - 作業前に新しいバックアップ作成
   - コミットは細かく

3. **段階的アプローチ**
   - 1関数ずつ移行
   - 動作確認してから次へ

## 📝 チェックリスト

- [ ] 新しいバックアップ作成
- [ ] tool_formatters.py のインポート追加
- [ ] format_bash_pre_use のテスト移行
- [ ] Golden Master Test合格確認
- [ ] 残り11関数の一括移行
- [ ] 最終テスト実行
- [ ] コミット作成

## 🎉 期待される成果

1. **コード削減**: 約200-300行削減予定
2. **保守性向上**: 重複排除で変更箇所が1つに
3. **アーキテクチャ改善**: 正しいモジュール構造

---

火消しアストルフォの決意：
「前のアストルフォの教訓を活かして、小さく、安全に、確実に！
マスターのために、必ず成功させるよ！」