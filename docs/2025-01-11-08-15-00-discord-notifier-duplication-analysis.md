# Discord Notifier Code Duplication Analysis

**火消しアストルフォの緊急レポート！**

## 🚨 現状の問題

1. **ファイルサイズの肥大化**
   - `discord_notifier.py`: 3,269行（！）
   - これは明らかに大きすぎる

2. **重複パターンの発見**

### Format関数の重複（22個も！）
```python
# 同じようなパターンが繰り返されている
def format_bash_pre_use(tool_input: ToolInput) -> list[str]:
def format_file_operation_pre_use(tool_name: str, tool_input: ToolInput) -> list[str]:
def format_search_tool_pre_use(tool_name: str, tool_input: ToolInput) -> list[str]:
def format_task_pre_use(tool_input: ToolInput) -> list[str]:
def format_web_fetch_pre_use(tool_input: ToolInput) -> list[str]:
# ... さらに post_use版も
```

### Truncation処理の重複
```python
# このパターンが何度も出現
truncated = truncate_string(text, limit)
suffix = get_truncation_suffix(len(text), limit)
add_field(desc_parts, "Label", f"{truncated}{suffix}")
```

### add_field呼び出しの重複（45回！）
- 同じような処理が散在
- 共通化の余地あり

## 🔥 緊急度評価

**炎上レベル: 中**
- 動作はしている（Python 3.13で確認済み）
- しかし保守性が著しく低下
- 新機能追加が困難

## 💡 リファクタリング候補

### 1. Formatter基底クラスの導入
```python
class BaseToolFormatter:
    def format_pre_use(self, tool_input: ToolInput) -> list[str]:
        # 共通処理
    
    def format_post_use(self, tool_input: ToolInput, response: ToolResponse) -> list[str]:
        # 共通処理
```

### 2. Truncation処理のヘルパー関数
```python
def add_truncated_field(desc_parts: list[str], label: str, text: str, limit: int, code: bool = False):
    """一箇所で truncate + suffix + add_field を処理"""
    truncated = truncate_string(text, limit)
    suffix = get_truncation_suffix(len(text), limit)
    add_field(desc_parts, label, f"{truncated}{suffix}", code=code)
```

### 3. Tool固有フォーマッターのクラス化
```python
class BashFormatter(BaseToolFormatter):
    def format_pre_use(self, tool_input: ToolInput) -> list[str]:
        # Bash固有の処理

class FileOperationFormatter(BaseToolFormatter):
    # ...
```

### 4. 既存のformatter分離の活用
既に `src/formatters/` ディレクトリがあるので、これを活用すべき！

## 🚒 火消し手順（推奨）

1. **バックアップ作成**（すでに存在）
2. **段階的リファクタリング**
   - まず共通ヘルパー関数を作成
   - 1つずつformat関数を移行
   - テストで動作確認
3. **モジュール分割**
   - discord_notifier.pyから formatter部分を分離
   - 既存の formatters/ ディレクトリに移動

## ⚠️ 注意事項

- **現在は動作している** - 焦って全部変更しない
- **Python 3.13必須** - これを忘れると全部壊れる
- **段階的に** - Martin Fowlerの原則を守る

## 📊 統計情報

- 総行数: 3,269行
- format関数: 22個
- add_field呼び出し: 45回
- 推定重複率: 30-40%

## 🚨🚨 重大な発見！！

**src/formatters/base.py と src/discord_notifier.py に完全に同じ関数が存在！**

重複している関数：
1. `truncate_string` - 完全一致
2. `format_file_path` - 完全一致
3. `get_truncation_suffix` - 完全一致
4. `add_field` - 完全一致
5. `format_json_field` - 完全一致

**これは明らかな重複！すぐに修正が必要！**

### 影響範囲
- discord_notifier.pyは formatters モジュールをインポートしていない
- 同じコードが2箇所に存在
- 保守性の著しい低下
- バグ修正時に2箇所を修正する必要がある

### 即座の対応策
1. discord_notifier.py から重複関数を削除
2. `from src.formatters.base import *` を追加
3. 動作確認

---

火消しアストルフォより緊急報告！
「完全な重複を発見！これは今すぐ修正すべき！」