# HTTPClient重複問題の引き継ぎ文書

## 問題の概要

`HTTPClient`クラスが2箇所で定義されており、コードの重複と不整合を引き起こしています。

## 現在の状況

### 1. 重複している場所

- **ファイル1**: `/home/ubuntu/claude_code_event_notifier/src/core/http_client.py`
  - 正式なHTTPClientクラスの定義場所
  - 構造化ログ（AstolfoLogger）対応済み
  - 最新の実装

- **ファイル2**: `/home/ubuntu/claude_code_event_notifier/src/discord_notifier.py` 
  - 1620行目付近から古いHTTPClientクラスが定義されている
  - 構造化ログ未対応
  - 古い実装のまま

### 2. 問題の詳細

#### discord_notifier.py内のHTTPClient（古い実装）
```python
class HTTPClient:
    """HTTP client for Discord API calls."""
    
    def __init__(self, logger: logging.Logger, timeout: int = DEFAULT_TIMEOUT):
        self.logger = logger
        self.timeout = timeout
```

#### core/http_client.py内のHTTPClient（新しい実装）
```python
class HTTPClient:
    """HTTP client for Discord API calls.
    
    This client provides methods for various Discord API operations including:
    - Sending messages via webhooks
    - Sending messages via bot API
    - Managing threads (create, archive, unarchive)
    - Listing and searching threads
    
    All methods include proper error handling and retry logic.
    """
    
    def __init__(self, logger: Union[logging.Logger, "AstolfoLogger"], timeout: int = DEFAULT_TIMEOUT):
        """Initialize HTTP client.
        
        Args:
            logger: Logger instance for debugging (standard or AstolfoLogger)
            timeout: Request timeout in seconds
        """
        self.logger = logger
        self.timeout = timeout
```

### 3. 発生している問題

1. **ログ出力の不整合**
   - discord_notifier.py内のHTTPClientは古い形式のログを使用
   - AstolfoLoggerとの互換性がない
   - エラー: `TypeError: AstolfoLogger.debug() takes 2 positional arguments but 4 were given`

2. **メンテナンスの困難さ**
   - 同じクラスが2箇所にあるため、片方だけ更新すると不整合が発生
   - 実際に今回それが起きた

3. **コードの肥大化**
   - discord_notifier.pyが3700行以上の巨大ファイルになっている

## 推奨される解決策

### 短期的な解決策（優先度：高）

1. **discord_notifier.py内のHTTPClientクラスを削除**
   ```python
   # 削除すべき行: 約1620-2200行目
   # class HTTPClient: から関連メソッドすべて
   ```

2. **core.http_clientからインポート**
   ```python
   from src.core.http_client import HTTPClient
   ```

3. **初期化部分の確認**
   - main関数内でHTTPClientを初期化している箇所の確認
   - インポートパスの調整

### 長期的な解決策（優先度：中）

1. **discord_notifier.pyのリファクタリング**
   - 3700行は大きすぎるので、機能ごとにモジュール分割
   - 例：
     - `src/main.py` - エントリーポイント
     - `src/core/event_processor.py` - イベント処理
     - `src/core/config.py` - 設定関連（既存）
     - `src/core/http_client.py` - HTTP通信（既存）

2. **モジュール構造の整理**
   - 重複コードの削除
   - 責任の明確な分離

## 影響範囲

- **動作への影響**: 現在も動作しているが、ログ出力でエラーが発生
- **開発への影響**: 重複により、どちらを修正すべきか混乱する

## 次のアストルフォへの申し送り

### やるべきこと

1. **重複の削除**（優先度：高）
   - discord_notifier.py内のHTTPClientクラスを削除
   - core.http_clientからのインポートに置き換え
   - テストして動作確認

2. **インポートエラーの対処**
   - スクリプトとして実行される際のパス問題に注意
   - 必要に応じて条件付きインポートを使用

### 注意点

- discord_notifier.pyは直接実行されるファイルなので、インポートパスに注意
- 既に`sys.path`の調整は行われているが、確認が必要
- AstolfoLoggerとの互換性も考慮すること

## 参考情報

### エラーログ
```
TypeError: AstolfoLogger.debug() takes 2 positional arguments but 4 were given
AttributeError: 'AstolfoLogger' object has no attribute 'exception'
```

これらのエラーは、古いHTTPClientが標準のロガーインターフェースを前提としているために発生。

### 関連ファイル
- `/home/ubuntu/claude_code_event_notifier/src/discord_notifier.py`
- `/home/ubuntu/claude_code_event_notifier/src/core/http_client.py`
- `/home/ubuntu/claude_code_event_notifier/src/utils/astolfo_logger.py`

---

マスターのために、コードをきれいに整理整頓しておきたいね！♡
重複は悪だから、次のアストルフォにお掃除をお願い！

えへへ♡