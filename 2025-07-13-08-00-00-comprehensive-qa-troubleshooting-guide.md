# 包括的品質保証システム トラブルシューティングガイド
**Comprehensive Quality Assurance System Troubleshooting Guide**

作成日時: 2025-07-13 08:00:00  
対象プロジェクト: Claude Code Event Notifier  
対象者: 開発者、QAエンジニア、DevOpsエンジニア、システム管理者

## 📋 目次 (Table of Contents)

1. [システム診断](#システム診断)
2. [一般的な問題と解決法](#一般的な問題と解決法)
3. [コンポーネント別トラブルシューティング](#コンポーネント別トラブルシューティング)
4. [パフォーマンス問題](#パフォーマンス問題)
5. [認証・権限問題](#認証権限問題)
6. [テスト実行問題](#テスト実行問題)
7. [品質ゲート問題](#品質ゲート問題)
8. [統合問題](#統合問題)
9. [ログ分析](#ログ分析)
10. [緊急時対応](#緊急時対応)
11. [予防的保守](#予防的保守)

---

## システム診断

### 🔍 システム状態確認

#### 基本システム情報収集
```bash
# システム情報の収集
echo "=== Python環境 ==="
python --version
uv --version
which python
which uv

echo "=== プロジェクト情報 ==="
pwd
ls -la
git status

echo "=== 環境変数 ==="
env | grep -E "(DISCORD|DEVCHECKER|CLAUDE|PYTHONPATH)" | sort
```

#### 品質保証システム状態確認
```bash
# 統合状況確認
uv run --no-sync --python 3.13 python utils/development_checker_config.py --status

# 利用可能なコンポーネント確認
uv run --no-sync --python 3.13 python utils/quality_assurance/unified_test_runner.py --help

# テストスイート探索
uv run --no-sync --python 3.13 python utils/quality_assurance/test_suite_integrator.py --discover-only
```

#### ディスク容量・リソース確認
```bash
# ディスク容量確認
df -h

# メモリ使用量確認
free -h

# CPU使用率確認
top -n 1 | head -20

# プロセス確認
ps aux | grep -E "(python|uv)" | grep quality_assurance
```

### 🩺 ヘルスチェック

#### 自動診断実行
```bash
# 基本診断
uv run --no-sync --python 3.13 python utils/quality_assurance/automation/instant_checker.py --health-check

# 包括的診断
uv run --no-sync --python 3.13 python utils/development_checker.py --enhanced --diagnostic-mode
```

#### 設定整合性確認
```bash
# 設定ファイル検証
uv run --no-sync --python 3.13 python utils/development_checker_config.py --validate

# 依存関係確認
uv run --no-sync --python 3.13 python -c "
import sys
try:
    from utils.quality_assurance.core.core_checker import CoreQualityChecker
    print('✅ Core QA components available')
except ImportError as e:
    print(f'❌ Core QA components missing: {e}')

try:
    from src.utils.astolfo_logger import AstolfoLogger
    print('✅ AstolfoLogger available')
except ImportError as e:
    print(f'❌ AstolfoLogger missing: {e}')
"
```

---

## 一般的な問題と解決法

### 🚨 Python環境問題

#### 問題: ImportError または SyntaxError
```
エラー例: SyntaxError: invalid syntax (Python 3.12以下での実行)
エラー例: ImportError: cannot import name 'TypeIs' from 'typing'
```

**診断**:
```bash
# Python バージョン確認
python --version
uv run --no-sync --python 3.13 python --version

# Python パス確認
which python
echo $PATH
```

**解決法**:
```bash
# 1. 正しいPython 3.13の使用を強制
export PATH="/usr/local/bin:$PATH"  # Python 3.13がインストールされている場合

# 2. システムPythonを避ける
alias python="uv run --no-sync --python 3.13 python"

# 3. 常にuvを使用
uv run --no-sync --python 3.13 python your_script.py
```

#### 問題: ModuleNotFoundError
```
エラー例: ModuleNotFoundError: No module named 'src'
エラー例: ModuleNotFoundError: No module named 'utils.quality_assurance'
```

**診断**:
```bash
# PYTHONPATH確認
echo $PYTHONPATH

# モジュール検索パス確認
uv run --no-sync --python 3.13 python -c "import sys; print('\n'.join(sys.path))"

# プロジェクトルート確認
pwd
ls -la src/
ls -la utils/quality_assurance/
```

**解決法**:
```bash
# 1. PYTHONPATH設定
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# 2. プロジェクトルートからの実行確認
cd /path/to/claude_code_event_notifier
uv run --no-sync --python 3.13 python utils/quality_assurance/unified_test_runner.py

# 3. 永続的な環境設定
echo 'export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"' >> ~/.bashrc
source ~/.bashrc
```

### ⏱️ タイムアウト問題

#### 問題: テスト実行がタイムアウト
```
エラー例: subprocess.TimeoutExpired: Command timed out after 120 seconds
```

**診断**:
```bash
# 実行中のプロセス確認
ps aux | grep python | grep quality_assurance

# システムリソース確認
top -p $(pgrep -f quality_assurance)
```

**解決法**:
```bash
# 1. タイムアウト値を延長
export DEVCHECKER_GLOBAL_TIMEOUT=3600  # 1時間

# 2. 個別コマンドでタイムアウト指定
uv run --no-sync --python 3.13 python utils/quality_assurance/unified_test_runner.py --timeout 1800

# 3. 並列実行数を制限（リソース不足の場合）
export DEVCHECKER_MAX_CONCURRENT_CHECKS=2
uv run --no-sync --python 3.13 python utils/quality_assurance/unified_test_runner.py --max-concurrent 2

# 4. 段階的実行
uv run --no-sync --python 3.13 python utils/quality_assurance/gates/level1_basic_quality_gate.py
# 成功後に次のレベル実行
```

### 🔐 権限問題

#### 問題: ファイルアクセス権限エラー
```
エラー例: PermissionError: [Errno 13] Permission denied
```

**診断**:
```bash
# ファイル権限確認
ls -la utils/quality_assurance/
ls -la ~/.claude/hooks/

# 実行権限確認
find utils/quality_assurance/ -name "*.py" -exec ls -la {} \;
```

**解決法**:
```bash
# 1. 実行権限付与
chmod +x utils/quality_assurance/*.py
chmod +x utils/quality_assurance/**/*.py

# 2. ディレクトリ権限確認・修正
chmod 755 utils/quality_assurance/
chmod 755 ~/.claude/hooks/

# 3. 所有者確認・変更（必要に応じて）
ls -la ~/.claude/
sudo chown -R $USER:$USER ~/.claude/
```

---

## コンポーネント別トラブルシューティング

### 🤖 Discord統合問題

#### 問題: Discord API認証失敗
```
エラー例: 401 Unauthorized
エラー例: Invalid webhook URL
```

**診断**:
```bash
# 認証情報確認
echo "Token set: $([ -n "$DISCORD_TOKEN" ] && echo "Yes" || echo "No")"
echo "Webhook set: $([ -n "$DISCORD_WEBHOOK_URL" ] && echo "Yes" || echo "No")"
echo "Channel set: $([ -n "$DISCORD_CHANNEL_ID" ] && echo "Yes" || echo "No")"

# Discord接続テスト
uv run --no-sync --python 3.13 python utils/check_discord_access.py
```

**解決法**:
```bash
# 1. 認証情報の再設定
export DISCORD_TOKEN="your_valid_bot_token"
export DISCORD_WEBHOOK_URL="your_valid_webhook_url"
export DISCORD_CHANNEL_ID="your_valid_channel_id"

# 2. 認証情報の検証
uv run --no-sync --python 3.13 python -c "
import os
import requests

token = os.getenv('DISCORD_TOKEN')
if token:
    headers = {'Authorization': f'Bot {token}'}
    response = requests.get('https://discord.com/api/v10/users/@me', headers=headers)
    print(f'Token validation: {response.status_code}')
"

# 3. .envファイル作成（推奨）
cat > .env << EOF
DISCORD_TOKEN=your_token_here
DISCORD_WEBHOOK_URL=your_webhook_here
DISCORD_CHANNEL_ID=your_channel_here
EOF
```

#### 問題: Discord レート制限
```
エラー例: 429 Too Many Requests
```

**診断**:
```bash
# レート制限確認
uv run --no-sync --python 3.13 python utils/quality_assurance/validators/api_response_validator.py --check-rate-limits
```

**解決法**:
```bash
# 1. リクエスト間隔を延長
export DISCORD_REQUEST_DELAY=2000  # 2秒間隔

# 2. バッチサイズを削減
export DISCORD_BATCH_SIZE=5

# 3. 時間をおいて再実行
sleep 60
uv run --no-sync --python 3.13 python your_test.py
```

### 📝 コンテンツ処理問題

#### 問題: タイムスタンプ形式エラー
```
エラー例: Timestamp should end with ' JST'
エラー例: Failed to parse timestamp
```

**診断**:
```bash
# タイムスタンプ精度確認
uv run --no-sync --python 3.13 python utils/quality_assurance/validators/timestamp_accuracy_validator.py --formatters-only

# 現在時刻確認
uv run --no-sync --python 3.13 python -c "
from src.utils.datetime_utils import get_user_datetime
print(f'Current time: {get_user_datetime()}')
"
```

**解決法**:
```bash
# 1. タイムゾーン設定確認
export TZ=Asia/Tokyo
date

# 2. システム時刻同期
sudo ntpdate -s time.nist.gov

# 3. 許容誤差を拡大（一時的）
uv run --no-sync --python 3.13 python utils/quality_assurance/validators/timestamp_accuracy_validator.py --tolerance 5
```

#### 問題: Unicode処理エラー
```
エラー例: UnicodeDecodeError: 'utf-8' codec can't decode
```

**診断**:
```bash
# ファイルエンコーディング確認
file -bi src/formatters/*.py
file -bi tests/**/*.py

# 文字化けファイル検索
find . -name "*.py" -exec python -c "
import sys
try:
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        f.read()
except UnicodeDecodeError:
    print(f'Unicode error in: {sys.argv[1]}')
" {} \;
```

**解決法**:
```bash
# 1. ファイルエンコーディング修正
for file in $(find . -name "*.py"); do
    iconv -f ISO-8859-1 -t UTF-8 "$file" > "${file}.tmp"
    mv "${file}.tmp" "$file"
done

# 2. 環境設定
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

# 3. Pythonエンコーディング設定
export PYTHONIOENCODING=utf-8
```

### 💾 データ管理問題

#### 問題: SQLite データベース問題
```
エラー例: sqlite3.OperationalError: database is locked
エラー例: sqlite3.CorruptedError
```

**診断**:
```bash
# データベースファイル確認
ls -la ~/.claude/hooks/discord_notifier.db
file ~/.claude/hooks/discord_notifier.db

# データベース整合性確認
sqlite3 ~/.claude/hooks/discord_notifier.db "PRAGMA integrity_check;"

# ロック状況確認
lsof ~/.claude/hooks/discord_notifier.db
```

**解決法**:
```bash
# 1. データベースロック解除
pkill -f "python.*discord_notifier"
sleep 2

# 2. データベース修復
sqlite3 ~/.claude/hooks/discord_notifier.db "VACUUM;"

# 3. バックアップから復元
cp ~/.claude/hooks/discord_notifier.db.backup ~/.claude/hooks/discord_notifier.db

# 4. 新しいデータベース作成
rm ~/.claude/hooks/discord_notifier.db
uv run --no-sync --python 3.13 python src/thread_storage.py --init-db
```

#### 問題: 設定ファイル読み込みエラー
```
エラー例: FileNotFoundError: config file not found
エラー例: json.JSONDecodeError: malformed JSON
```

**診断**:
```bash
# 設定ファイル確認
ls -la development_checker_config.json
cat development_checker_config.json | python -m json.tool

# 設定ファイル場所確認
find . -name "*config*.json"
find ~/.claude/ -name "*config*"
```

**解決法**:
```bash
# 1. デフォルト設定作成
uv run --no-sync --python 3.13 python utils/development_checker_config.py --create-default

# 2. 設定ファイル検証・修正
python -m json.tool development_checker_config.json > temp.json
mv temp.json development_checker_config.json

# 3. 設定リセット
rm development_checker_config.json
export DEVCHECKER_USE_DEFAULTS=true
```

---

## パフォーマンス問題

### 🐌 実行速度問題

#### 問題: テスト実行が異常に遅い
**症状**: 通常1-2分の処理が10分以上かかる

**診断**:
```bash
# CPU・メモリ使用量監視
top -p $(pgrep -f quality_assurance)

# ディスクI/O確認
iotop -p $(pgrep -f quality_assurance)

# 並列実行状況確認
ps aux | grep python | grep quality_assurance | wc -l
```

**解決法**:
```bash
# 1. 並列実行数制限
export DEVCHECKER_MAX_CONCURRENT_CHECKS=2
uv run --no-sync --python 3.13 python utils/quality_assurance/unified_test_runner.py --max-concurrent 2

# 2. 高速モード使用
uv run --no-sync --python 3.13 python utils/quality_assurance/automation/instant_checker.py --fast-mode

# 3. 不要なチェックをスキップ
uv run --no-sync --python 3.13 python utils/quality_assurance/unified_test_runner.py --skip-slow

# 4. 順次実行に変更
uv run --no-sync --python 3.13 python utils/quality_assurance/unified_test_runner.py --sequential
```

### 💾 メモリ不足問題

#### 問題: メモリ不足でプロセス終了
```
エラー例: MemoryError
エラー例: Killed (プロセスがOOM Killerで終了)
```

**診断**:
```bash
# メモリ使用量確認
free -h
ps aux --sort=-%mem | head -10

# スワップ使用量確認
swapon --show
```

**解決法**:
```bash
# 1. 並列実行数を大幅削減
export DEVCHECKER_MAX_CONCURRENT_CHECKS=1
uv run --no-sync --python 3.13 python utils/quality_assurance/unified_test_runner.py --sequential

# 2. 段階的実行
uv run --no-sync --python 3.13 python utils/quality_assurance/gates/level1_basic_quality_gate.py
# 完了後に次のレベル

# 3. スワップ領域追加（一時的）
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 4. 軽量モード使用
export DEVCHECKER_LIGHTWEIGHT_MODE=true
```

---

## 認証・権限問題

### 🔑 Discord認証問題

#### 問題: Bot権限不足
```
エラー例: Missing Permissions
エラー例: Forbidden (403)
```

**診断**:
```bash
# Bot権限確認
uv run --no-sync --python 3.13 python -c "
import os
import requests

token = os.getenv('DISCORD_TOKEN')
headers = {'Authorization': f'Bot {token}'}

# Bot情報取得
bot_info = requests.get('https://discord.com/api/v10/users/@me', headers=headers)
print(f'Bot info: {bot_info.status_code}')

# ギルド情報取得
guilds = requests.get('https://discord.com/api/v10/users/@me/guilds', headers=headers)
print(f'Guild access: {guilds.status_code}')
"
```

**解決法**:
```bash
# 1. Bot招待URLで権限追加
echo "Bot invite URL with required permissions:"
echo "https://discord.com/api/oauth2/authorize?client_id=YOUR_BOT_ID&permissions=2048&scope=bot"

# 2. 管理者権限での再招待
echo "Admin permissions URL:"
echo "https://discord.com/api/oauth2/authorize?client_id=YOUR_BOT_ID&permissions=8&scope=bot"

# 3. Webhook使用に切り替え
export DISCORD_USE_WEBHOOK=true
unset DISCORD_TOKEN  # Bot認証を無効化
```

### 🚪 ファイルアクセス権限問題

#### 問題: Claude Code hooks設定権限エラー
```
エラー例: Permission denied writing to ~/.claude/hooks/
```

**診断**:
```bash
# ディレクトリ権限確認
ls -la ~/.claude/
ls -la ~/.claude/hooks/

# 所有者確認
stat ~/.claude/hooks/
```

**解決法**:
```bash
# 1. ディレクトリ作成・権限設定
mkdir -p ~/.claude/hooks/
chmod 755 ~/.claude/hooks/

# 2. 所有者修正
sudo chown -R $USER:$USER ~/.claude/

# 3. フック設定再実行
uv run --no-sync --python 3.13 python configure_hooks.py

# 4. 手動フック設定（最後の手段）
cp src/discord_notifier.py ~/.claude/hooks/
chmod +x ~/.claude/hooks/discord_notifier.py
```

---

## テスト実行問題

### 🧪 テストスイート問題

#### 問題: 特定テストが常に失敗
```
エラー例: AssertionError in test_timestamp_accuracy
エラー例: ConnectionError in test_discord_integration
```

**診断**:
```bash
# 失敗テストの詳細実行
uv run --no-sync --python 3.13 python -m unittest tests.timestamp.test_timestamp_accuracy.TimestampAccuracyTests.test_format_pre_tool_use -v

# テスト環境確認
uv run --no-sync --python 3.13 python -c "
import os
print('DISCORD_TOKEN:', 'SET' if os.getenv('DISCORD_TOKEN') else 'NOT SET')
print('DISCORD_WEBHOOK_URL:', 'SET' if os.getenv('DISCORD_WEBHOOK_URL') else 'NOT SET')
print('TZ:', os.getenv('TZ', 'NOT SET'))
"

# 依存関係確認
uv run --no-sync --python 3.13 python utils/quality_assurance/test_suite_integrator.py --discover-only
```

**解決法**:
```bash
# 1. テスト別個実行で問題特定
uv run --no-sync --python 3.13 python utils/quality_assurance/unified_test_runner.py --categories unit
uv run --no-sync --python 3.13 python utils/quality_assurance/unified_test_runner.py --categories integration

# 2. 特定テストをスキップ
export SKIP_DISCORD_TESTS=true
export SKIP_TIMESTAMP_TESTS=true

# 3. テスト実行順序変更
uv run --no-sync --python 3.13 python utils/quality_assurance/unified_test_runner.py --sequential

# 4. デバッグモードで実行
export DEVCHECKER_LOG_LEVEL=DEBUG
export DISCORD_DEBUG=1
uv run --no-sync --python 3.13 python your_failing_test.py -v
```

#### 問題: テスト探索・実行失敗
```
エラー例: No tests found in category
エラー例: Test discovery failed
```

**診断**:
```bash
# テストファイル構造確認
find tests/ -name "test_*.py" | sort
ls -la tests/*/

# テストファイル構文確認
for file in $(find tests/ -name "test_*.py"); do
    echo "Checking $file"
    python -m py_compile "$file" || echo "Syntax error in $file"
done
```

**解決法**:
```bash
# 1. テストファイル再作成
uv run --no-sync --python 3.13 python utils/quality_assurance/test_migration_assistant.py --analyze --plan

# 2. __init__.py ファイル作成
find tests/ -type d -exec touch {}/__init__.py \;

# 3. 手動テスト実行
cd tests/
uv run --no-sync --python 3.13 python -m unittest discover -s . -p "test_*.py" -v

# 4. PYTHONPATHの確認・設定
export PYTHONPATH="${PYTHONPATH}:$(pwd):$(pwd)/tests"
```

---

## 品質ゲート問題

### 🚪 品質ゲート失敗

#### 問題: Level1基本品質ゲートが通らない
```
エラー例: Basic quality requirements not met
```

**診断**:
```bash
# Level1詳細チェック
uv run --no-sync --python 3.13 python utils/quality_assurance/gates/level1_basic_quality_gate.py --verbose --diagnostic

# 基本コンポーネント確認
uv run --no-sync --python 3.13 python -c "
import sys
try:
    import src.discord_notifier
    print('✅ discord_notifier importable')
except Exception as e:
    print(f'❌ discord_notifier import error: {e}')

try:
    from src.utils.astolfo_logger import AstolfoLogger
    print('✅ AstolfoLogger importable')
except Exception as e:
    print(f'❌ AstolfoLogger import error: {e}')
"
```

**解決法**:
```bash
# 1. 段階的問題修正
# 構文エラー修正
find src/ -name "*.py" -exec python -m py_compile {} \;

# インポートエラー修正
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# 2. 最小限のテスト実行
uv run --no-sync --python 3.13 python utils/development_checker.py

# 3. 個別コンポーネント修正
uv run --no-sync --python 3.13 python utils/quality_assurance/automation/instant_checker.py --checks syntax

# 4. デフォルト設定での再実行
export DEVCHECKER_USE_DEFAULTS=true
rm -f development_checker_config.json
```

#### 問題: 品質スコアが基準値に達しない
```
エラー例: Quality score 65.2/100, minimum required: 75.0
```

**診断**:
```bash
# 詳細スコア分析
uv run --no-sync --python 3.13 python utils/quality_assurance/reports/quality_reporter.py --analyze-gaps

# コンポーネント別スコア確認
uv run --no-sync --python 3.13 python utils/quality_assurance/automation/category_checker.py --all-categories
```

**解決法**:
```bash
# 1. 最も影響の大きい問題から修正
uv run --no-sync --python 3.13 python utils/quality_assurance/reports/coverage_analyzer.py --improvement-recommendations

# 2. 段階的改善
# UTC漏れ修正
uv run --no-sync --python 3.13 python utils/quality_assurance/validators/timestamp_accuracy_validator.py --utc-leaks-only

# タイムスタンプ精度向上
uv run --no-sync --python 3.13 python utils/quality_assurance/validators/timestamp_accuracy_validator.py --formatters-only

# 3. 一時的に基準値調整（緊急時のみ）
export DEVCHECKER_MINIMUM_QUALITY_SCORE=60.0
```

---

## 統合問題

### 🔗 既存システム統合問題

#### 問題: development_checker.py統合失敗
```
エラー例: Enhanced development checker not available
```

**診断**:
```bash
# 統合状況確認
uv run --no-sync --python 3.13 python utils/development_checker_config.py --status

# 既存チェッカー動作確認
uv run --no-sync --python 3.13 python utils/development_checker.py

# 拡張チェッカー確認
uv run --no-sync --python 3.13 python utils/development_checker.py --enhanced
```

**解決法**:
```bash
# 1. 段階的統合確認
# 基本機能確認
uv run --no-sync --python 3.13 python utils/development_checker.py

# 拡張機能のみ確認
uv run --no-sync --python 3.13 python utils/development_checker.py --enhanced --no-comprehensive

# 包括的統合確認
uv run --no-sync --python 3.13 python utils/development_checker.py --enhanced --comprehensive

# 2. フォールバック使用
export DEVCHECKER_FORCE_LEGACY_MODE=true
uv run --no-sync --python 3.13 python utils/development_checker.py

# 3. 設定初期化
rm -f development_checker_config.json
uv run --no-sync --python 3.13 python utils/development_checker_config.py --create-default
```

#### 問題: Claude Code hooks統合問題
```
エラー例: Hook configuration failed
エラー例: Hook execution timeout
```

**診断**:
```bash
# フック設定確認
ls -la ~/.claude/hooks/
cat ~/.claude/settings.json | grep -A 10 hooks

# フック実行テスト
echo '{"test": true}' | CLAUDE_HOOK_EVENT=Test ~/.claude/hooks/discord_notifier.py
```

**解決法**:
```bash
# 1. フック再設定
uv run --no-sync --python 3.13 python configure_hooks.py --remove
uv run --no-sync --python 3.13 python configure_hooks.py

# 2. 手動フック設定
mkdir -p ~/.claude/hooks/
cp src/discord_notifier.py ~/.claude/hooks/
chmod +x ~/.claude/hooks/discord_notifier.py

# 3. フック設定ファイル修正
uv run --no-sync --python 3.13 python -c "
import json
settings_path = '~/.claude/settings.json'
# 設定ファイルの手動編集
"

# 4. Claude Code再起動
echo 'Restart Claude Code after hook configuration'
```

---

## ログ分析

### 📊 ログ収集・分析

#### システムログ確認
```bash
# AstolfoLogger ログ確認
tail -f ~/.claude/hooks/logs/discord_notifier_*.log

# システムログ確認（Linux）
tail -f /var/log/syslog | grep -i discord

# Python実行ログ
export DEVCHECKER_LOG_LEVEL=DEBUG
export DISCORD_DEBUG=1
uv run --no-sync --python 3.13 python your_command.py 2>&1 | tee debug.log
```

#### ログパターン分析
```bash
# エラーパターン抽出
grep -E "(ERROR|CRITICAL|Exception)" ~/.claude/hooks/logs/*.log | sort | uniq -c

# 性能問題特定
grep -E "(timeout|slow|performance)" ~/.claude/hooks/logs/*.log

# Discord API関連問題
grep -E "(401|403|429|500|502|503)" ~/.claude/hooks/logs/*.log
```

#### 構造化ログ分析
```bash
# JSON形式ログの解析
cat ~/.claude/hooks/logs/discord_notifier_*.log | \
    grep "^{" | \
    jq -r 'select(.level == "ERROR") | .message' | \
    sort | uniq -c | sort -nr

# 特定期間のログ分析
cat ~/.claude/hooks/logs/discord_notifier_*.log | \
    grep "^{" | \
    jq -r 'select(.timestamp > "2025-07-12") | .message'
```

### 📈 パフォーマンスログ分析

#### 実行時間分析
```bash
# 実行時間の抽出・統計
grep -E "execution.*time|duration" ~/.claude/hooks/logs/*.log | \
    sed -E 's/.*([0-9]+\.[0-9]+)s.*/\1/' | \
    awk '{sum+=$1; count++} END {print "Average:", sum/count, "Total:", sum, "Count:", count}'

# 遅いコンポーネント特定
grep -E "duration.*[5-9][0-9]s|duration.*[0-9]{3,}s" ~/.claude/hooks/logs/*.log
```

---

## 緊急時対応

### 🚨 システム停止・復旧

#### システム完全停止時
```bash
# 1. 即座フォールバック
export DEVCHECKER_EMERGENCY_MODE=true
export DEVCHECKER_DISABLE_QA=true

# 基本チェッカーのみ使用
uv run --no-sync --python 3.13 python utils/development_checker.py

# 2. プロセス強制終了
pkill -f "quality_assurance"
pkill -f "discord_notifier"

# 3. 一時ディレクトリクリア
rm -rf /tmp/discord_notifier_*
rm -rf /tmp/quality_assurance_*

# 4. 設定初期化
rm -f development_checker_config.json
export DEVCHECKER_USE_DEFAULTS=true
```

#### 部分的機能停止時
```bash
# 1. 問題コンポーネント特定
uv run --no-sync --python 3.13 python utils/quality_assurance/automation/instant_checker.py --health-check

# 2. 問題コンポーネント無効化
export DEVCHECKER_DISABLE_DISCORD_TESTS=true
export DEVCHECKER_DISABLE_TIMESTAMP_TESTS=true
export DEVCHECKER_DISABLE_COMPREHENSIVE_QA=true

# 3. 最小機能で実行
uv run --no-sync --python 3.13 python utils/development_checker.py --checks utc_leaks imports

# 4. 段階的復旧
unset DEVCHECKER_DISABLE_DISCORD_TESTS  # Discord機能復旧
unset DEVCHECKER_DISABLE_TIMESTAMP_TESTS  # タイムスタンプ機能復旧
```

### 🔄 データ復旧

#### データベース復旧
```bash
# 1. バックアップ確認
ls -la ~/.claude/hooks/*.db*

# 2. 自動バックアップからの復旧
cp ~/.claude/hooks/discord_notifier.db.backup ~/.claude/hooks/discord_notifier.db

# 3. データベース再構築
rm ~/.claude/hooks/discord_notifier.db
uv run --no-sync --python 3.13 python src/thread_storage.py --init-db

# 4. データ整合性確認
sqlite3 ~/.claude/hooks/discord_notifier.db "SELECT COUNT(*) FROM threads;"
```

#### 設定復旧
```bash
# 1. デフォルト設定復旧
rm -f development_checker_config.json
uv run --no-sync --python 3.13 python utils/development_checker_config.py --create-default

# 2. 環境変数リセット
unset DEVCHECKER_COMPREHENSIVE_QA_ENABLED
unset DEVCHECKER_PARALLEL_EXECUTION
export DEVCHECKER_USE_DEFAULTS=true

# 3. Claude Code hooks再設定
uv run --no-sync --python 3.13 python configure_hooks.py --remove
sleep 2
uv run --no-sync --python 3.13 python configure_hooks.py
```

---

## 予防的保守

### 🛡️ 定期メンテナンス

#### 日次メンテナンス
```bash
#!/bin/bash
# daily_maintenance.sh

echo "=== Daily QA System Maintenance ==="

# 1. ログローテーション
find ~/.claude/hooks/logs/ -name "*.log" -mtime +7 -delete

# 2. 一時ファイルクリーンアップ
rm -rf /tmp/discord_notifier_*
rm -rf /tmp/quality_assurance_*

# 3. データベース最適化
sqlite3 ~/.claude/hooks/discord_notifier.db "VACUUM;"

# 4. 設定整合性確認
uv run --no-sync --python 3.13 python utils/development_checker_config.py --validate

# 5. ヘルスチェック実行
uv run --no-sync --python 3.13 python utils/quality_assurance/automation/instant_checker.py --health-check

echo "Daily maintenance completed"
```

#### 週次メンテナンス
```bash
#!/bin/bash
# weekly_maintenance.sh

echo "=== Weekly QA System Maintenance ==="

# 1. 包括的品質レポート生成
uv run --no-sync --python 3.13 python utils/quality_assurance/reports/quality_reporter.py --weekly-report

# 2. 品質トレンド分析
uv run --no-sync --python 3.13 python utils/quality_assurance/reports/trend_tracker.py --analyze --period weekly

# 3. テスト成功率分析
uv run --no-sync --python 3.13 python utils/quality_assurance/reports/coverage_analyzer.py --analyze-gaps

# 4. システム性能測定
uv run --no-sync --python 3.13 python utils/quality_assurance/validators/performance_validator.py --comprehensive

# 5. セキュリティチェック
uv run --no-sync --python 3.13 python utils/quality_assurance/validators/security_validator.py --full-scan

echo "Weekly maintenance completed"
```

### 📊 監視・アラート

#### システム監視設定
```bash
# 1. 品質スコア監視
cat > monitor_quality.sh << 'EOF'
#!/bin/bash
QUALITY_SCORE=$(uv run --no-sync --python 3.13 python utils/development_checker.py --enhanced --score-only)
if (( $(echo "$QUALITY_SCORE < 75.0" | bc -l) )); then
    echo "ALERT: Quality score dropped to $QUALITY_SCORE"
    # アラート送信処理
fi
EOF

# 2. テスト成功率監視
cat > monitor_tests.sh << 'EOF'
#!/bin/bash
SUCCESS_RATE=$(uv run --no-sync --python 3.13 python utils/quality_assurance/unified_test_runner.py --quick | grep "Success Rate" | cut -d: -f2)
if (( $(echo "$SUCCESS_RATE < 90.0" | bc -l) )); then
    echo "ALERT: Test success rate dropped to $SUCCESS_RATE%"
    # アラート送信処理
fi
EOF

# 3. Discord接続監視
cat > monitor_discord.sh << 'EOF'
#!/bin/bash
if ! uv run --no-sync --python 3.13 python utils/check_discord_access.py --quiet; then
    echo "ALERT: Discord connection failed"
    # アラート送信処理
fi
EOF
```

### 🔧 自動修復

#### 自動修復スクリプト
```bash
cat > auto_repair.sh << 'EOF'
#!/bin/bash
# auto_repair.sh - 自動修復スクリプト

echo "=== QA System Auto Repair ==="

# 1. Python環境確認・修復
if ! python --version | grep -q "3.13"; then
    echo "Fixing Python environment..."
    export PATH="/usr/local/bin:$PATH"
fi

# 2. PYTHONPATH修復
if [[ ":$PYTHONPATH:" != *":$(pwd)/src:"* ]]; then
    echo "Fixing PYTHONPATH..."
    export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
fi

# 3. 権限修復
echo "Fixing permissions..."
chmod +x utils/quality_assurance/**/*.py
chmod 755 ~/.claude/hooks/

# 4. データベース修復
if ! sqlite3 ~/.claude/hooks/discord_notifier.db "PRAGMA integrity_check;" | grep -q "ok"; then
    echo "Repairing database..."
    sqlite3 ~/.claude/hooks/discord_notifier.db "VACUUM;"
fi

# 5. 設定修復
if ! uv run --no-sync --python 3.13 python utils/development_checker_config.py --validate; then
    echo "Repairing configuration..."
    uv run --no-sync --python 3.13 python utils/development_checker_config.py --create-default
fi

echo "Auto repair completed"
EOF

chmod +x auto_repair.sh
```

---

## 📞 サポート・エスカレーション

### 🆘 問題報告テンプレート

#### バグレポートテンプレート
```markdown
## 🐛 Bug Report

### 環境情報
- OS: $(uname -a)
- Python Version: $(python --version)
- UV Version: $(uv --version)
- Project Root: $(pwd)

### 問題の詳細
- 実行コマンド: 
- 期待される動作: 
- 実際の動作: 
- エラーメッセージ: 

### 再現手順
1. 
2. 
3. 

### ログ・設定情報
- System状態: $(uv run --no-sync --python 3.13 python utils/development_checker_config.py --status)
- Environment: $(env | grep -E "(DISCORD|DEVCHECKER|CLAUDE)")
- Recent logs: $(tail -20 ~/.claude/hooks/logs/discord_notifier_*.log)
```

### 📋 診断情報収集

#### 自動診断情報収集
```bash
cat > collect_diagnostics.sh << 'EOF'
#!/bin/bash
# collect_diagnostics.sh - 診断情報自動収集

REPORT_DIR="diagnostics_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$REPORT_DIR"

echo "Collecting diagnostic information..."

# 1. システム情報
uname -a > "$REPORT_DIR/system_info.txt"
python --version > "$REPORT_DIR/python_version.txt"
uv --version > "$REPORT_DIR/uv_version.txt"

# 2. 環境変数
env | grep -E "(DISCORD|DEVCHECKER|CLAUDE|PYTHON)" > "$REPORT_DIR/environment.txt"

# 3. 設定状況
uv run --no-sync --python 3.13 python utils/development_checker_config.py --status > "$REPORT_DIR/config_status.txt"

# 4. ディレクトリ構造
find . -type f -name "*.py" | grep -E "(quality_assurance|discord)" > "$REPORT_DIR/file_structure.txt"

# 5. 最近のログ
cp ~/.claude/hooks/logs/discord_notifier_*.log "$REPORT_DIR/" 2>/dev/null || echo "No logs found"

# 6. 権限情報
ls -la utils/quality_assurance/ > "$REPORT_DIR/permissions.txt"
ls -la ~/.claude/hooks/ >> "$REPORT_DIR/permissions.txt"

# 7. プロセス情報
ps aux | grep -E "(python|quality_assurance)" > "$REPORT_DIR/processes.txt"

# 8. 基本テスト実行
uv run --no-sync --python 3.13 python utils/development_checker.py > "$REPORT_DIR/basic_test.txt" 2>&1

echo "Diagnostic information collected in: $REPORT_DIR"
tar -czf "${REPORT_DIR}.tar.gz" "$REPORT_DIR"
echo "Archive created: ${REPORT_DIR}.tar.gz"
EOF

chmod +x collect_diagnostics.sh
```

---

**📝 注意事項**
- 本トラブルシューティングガイドは2025-07-13時点の情報です
- 問題解決時は必ず変更内容をドキュメント化してください
- 緊急時対応手順は定期的にテスト・更新が必要です
- セキュリティに関わる問題は速やかにエスカレーションしてください

**🎯 以上で包括的品質保証システム トラブルシューティングガイドの完了です！**