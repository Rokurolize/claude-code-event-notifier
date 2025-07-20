# Discord Event Notifier - トラブルシューティングガイド

このドキュメントでは、Discord Event Notifierで発生する可能性のある問題の診断と解決方法について説明します。

---

## 🚨 実装前必須チェックリスト

**⚠️ 全ての作業開始前に絶対実行 - 1つでも失敗したら作業停止**

### 🔥 STEP 0: PYTHON ENVIRONMENT VERIFICATION (ABSOLUTE PRIORITY)
```bash
# ⚠️ CRITICAL: 最初に実行 - 失敗時は即座作業停止
uv run --python 3.14 python --version

# 期待結果: Python 3.13.x or higher ONLY
# 3.12以下が出力された場合 → STOP IMMEDIATELY

# Pure Python 3.13+ 機能確認（設計純粋性チェック）
uv run --python 3.14 python -c "from typing import ReadOnly, TypeIs; import os; print(f'ReadOnly: OK, TypeIs: OK, CPU: {os.process_cpu_count()}')"

# 期待結果: "ReadOnly: OK, TypeIs: OK, CPU: X"
# ImportError発生時 → DESIGN VIOLATION - 作業停止
```

### 🛡️ STEP 1: セッション状況把握
```bash
# Auto-compactされたセッションでは必須実行
# 1. CLAUDE.mdで現在状況確認（最新の実装状況理解）
@projects/claude-code-event-notifier/CLAUDE.md

# 2. 重要な調査報告書確認
ls 2025-*-investigation-*.md  # 調査報告書一覧
ls 2025-*-*-report.md         # その他の報告書

# 3. 進行中の作業があれば確認
ls 2025-*-*.md | tail -5      # 最新のドキュメント
```

### 🔧 STEP 2: コマンド実行パターン検証
```bash
# Python 3.13確認（これが失敗したら作業停止）
uv run --python 3.14 python --version

# ReadOnly機能確認（エラーが出たらtyping_extensionsフォールバック確認）
uv run --python 3.14 python -c "from typing import ReadOnly; print('ReadOnly: OK')"

# 新アーキテクチャモジュール構文チェック
uv run --python 3.14 python -m py_compile src/core/config.py
uv run --python 3.14 python -m py_compile src/settings_types.py
```

### タイムスタンプ取得（CLAUDE.md更新時は必須）
```bash
# タイムスタンプ取得（手動入力は絶対禁止）
date +"%Y-%m-%d-%H-%M-%S"
```

### 設定ファイル確認
```bash
# 設定ファイル存在確認
ls -la ~/.claude/.env

# Hook設定確認（新アーキテクチャ用main.pyが指定されているか）
grep -A 5 "discord_notifier\|main.py" ~/.claude/settings.json
```

---

## 🛠️ 既知のエラーと即座対処法

### パターン1: 「動作確認せずに実装開始」
**症状**: ReadOnlyインポートエラーで即座に作業停止
**回避**: [実装前必須チェックリスト](#-実装前必須チェックリスト) を必ず実行

### パターン2: 「Python環境の混乱」
**症状**: 古いPythonバージョンによる設計純粋性の汚染
**回避**: 全ての実行で `uv run --python 3.14 python` を使用

### パターン3: 「設定ファイル場所の混乱」
**症状**: .envファイルとHookの設定不一致
**正解**: Hook用設定は `~/.claude/.env` のみ

### パターン4: 「ConfigLoader重複の無視」
**症状**: 新旧両方のConfigLoaderが存在することを忘れる
**対処**: 新アーキテクチャでは `src/core/config.py` のConfigLoaderを使用

### パターン5: 「タイムスタンプの手動入力」 ⚠️ 重大
**症状**: CLAUDE.md更新時に手動でタイムスタンプを入力してしまう
**対処**: **絶対にタイムスタンプを手動入力しない**
```bash
# 正しい方法（必須）
date +"%Y-%m-%d-%H-%M-%S"

# 間違った方法（絶対禁止）
# 手動で "2025-07-16-16-45-32" などと入力
```

### パターン6: 「Auto-compactセッションでの状況把握不足」 ⚠️ 致命的
**症状**: Auto-compactされたセッションで状況確認せずに作業開始
**対処**: **必ず最初にCLAUDE.mdと関連ファイルを読み込む**
```bash
# セッション開始直後に必須実行
@projects/claude-code-event-notifier/CLAUDE.md
ls 2025-*-investigation-*.md | head -3
```

---

## 🔧 具体的なエラー対処法

### `ImportError: cannot import name 'ReadOnly' from 'typing'`
**原因**: Python 3.12環境でReadOnlyインポート失敗
**対処**: typing_extensionsフォールバック確認
```bash
# 確認コマンド
uv run --python 3.14 python -c "
try:
    from typing import ReadOnly
    print('ReadOnly from typing: OK')
except ImportError:
    try:
        from typing_extensions import ReadOnly
        print('ReadOnly from typing_extensions: OK')
    except ImportError:
        print('ReadOnly completely unavailable')
"
```

### `configure_hooks.py`実行時のモジュールインポートエラー
**原因**: settings_types.pyでのReadOnly依存問題
**対処**: Python 3.13強制実行
```bash
# 正しい実行方法
uv run --python 3.14 python configure_hooks.py
```

### Hook実行時の「ファイルが見つからない」エラー
**原因**: パス設定の混乱
**対処**: 絶対パス確認
```bash
# 現在のパス確認
pwd
ls -la src/discord_notifier.py
ls -la src/main.py  # 新アーキテクチャの場合
```

---

## 🆘 緊急復旧手順

### 新アーキテクチャで問題が発生した場合
```bash
# 1. 設定ファイル確認
ls -la ~/.claude/.env

# 2. 設定の再読み込み
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python configure_hooks.py --reload

# 3. エンドツーエンドテスト実行
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python configure_hooks.py --validate-end-to-end

# 4. 問題が解決しない場合：Claude Code再起動
```

### 完全にHookが動作しなくなった場合
```bash
# 1. Hook設定を完全削除
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python configure_hooks.py --remove

# 2. 設定ファイル確認
ls -la ~/.claude/.env

# 3. 新アーキテクチャで再設定
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python configure_hooks.py

# 4. Claude Code再起動後、動作確認
```

---

## 🔍 デバッグ情報収集

### 問題発生時に必ず実行すべきコマンド
```bash
# Python環境情報
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python --version

# 重要ファイル存在確認
ls -la src/main.py src/core/config.py src/handlers/discord_sender.py

# Hook設定確認
grep -C 3 "main.py" ~/.claude/settings.json

# 設定ファイル確認
ls -la ~/.claude/.env
cat ~/.claude/.env | grep -v "TOKEN\|WEBHOOK"  # 機密情報除外

# エラーログ確認
tail -20 ~/.claude/hooks/logs/discord_notifier_*.log
```

---

## ⚠️ CRITICAL: PYTHON EXECUTION COMMANDS
### 🚨 NEVER USE `python3` - ALWAYS USE `uv run --python 3.14 python`

#### 🔥 ABSOLUTE COMMAND ENFORCEMENT

**FORBIDDEN** ❌:
```bash
python3 configure_hooks.py                    # ← DESIGN VIOLATION
python3 -m mypy src/                          # ← DESIGN VIOLATION  
python3 utils/check_discord_access.py         # ← DESIGN VIOLATION
uv run --no-sync --python 3.14 python ...    # ← ENVIRONMENT CONTAMINATION RISK
```

**REQUIRED** ✅:
```bash
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python configure_hooks.py
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python -m mypy src/
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python utils/check_discord_access.py
```

#### 🛡️ WHY THIS MATTERS: Pure Python 3.13+ Design Philosophy

**`python3` は設計汚染の源泉である:**
- System python3 may be Python 3.8, 3.9, 3.10, 3.11, or 3.12
- Those versions **DO NOT SUPPORT** `typing.ReadOnly`, `TypeIs`, `process_cpu_count()`
- Using them **VIOLATES** the Pure Python 3.13+ design principles
- It creates **TECHNICAL DEBT** and **ARCHITECTURE CONTAMINATION**

**`--no-sync` は環境汚染の危険因子である:**
- **2025-07-17環境汚染危機**: `--no-sync`がPython 3.12環境を強制使用
- **ReadOnly Import Error**: 汚染された環境でのタイプ機能欠如
- **コンテキスト依存性**: 実行ディレクトリによる動作不整合

**`cd project_root && uv run --python 3.14 python` は純粋性の保証である:**
- **GUARANTEES** Python 3.13+ execution environment
- **PRESERVES** access to cutting-edge type features
- **MAINTAINS** design integrity and architectural beauty
- **PREVENTS** fallback to contaminated older versions
- **ENSURES** context-independent execution

---

## ✅ 実装成功の最終確認

### 新アーキテクチャ実装完了の判定基準

#### 必須チェック項目（すべて✅になったら完了）
- [x] `src/main.py` が作成され、構文チェックが通る
- [x] `cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python configure_hooks.py` がエラーなく実行される
- [x] Hook設定がmain.pyを指している（~/.claude/settings.json確認）
- [x] 実際のHook実行でDiscordにメッセージが送信される
- [x] Claude Code再起動後も正常動作する

#### 動作テスト手順
```bash
# 1. 構文チェック
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python -m py_compile src/main.py

# 2. Hook設定
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python configure_hooks.py

# 3. Claude Code再起動（マニュアル操作）

# 4. 動作確認（何らかのツールを実行してHookが発火することを確認）

# 5. Discordでメッセージ受信確認
```

#### 失敗した場合の判断基準
以下のいずれかが発生したら即座に古い実装に戻す：
- ReadOnlyインポートエラーが解決できない
- main.pyの構文エラーが発生
- Hook実行時にDiscordメッセージが送信されない
- Claude Codeの動作が不安定になる

---

## 📊 Discord送信検証システム

### 個別検証ツール

#### 🔍 基本Discord API検証
```bash
# 基本的なAPIアクセステスト
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python utils/check_discord_access.py
```

#### 📊 高度Discord API検証
```bash
# 詳細なメッセージ分析と複数回検証
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python src/utils/discord_api_validator.py
```

#### 🚀 End-to-End Validation System（推奨）
```bash
# 完全統合テストコマンド（自律実行可能）
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python configure_hooks.py --validate-end-to-end
```

### 🛡️ トラブルシューティング実行手順

#### 問題発生時の系統的診断
```bash
# 1. 基本動作確認
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python configure_hooks.py --validate-end-to-end

# 2. 失敗時: 個別コンポーネント確認
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python configure_hooks.py --reload
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python utils/check_discord_access.py

# 3. Hook単体実行テスト
echo '{"session_id":"test","tool_name":"Test"}' | CLAUDE_HOOK_EVENT=PreToolUse cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.14 python src/main.py
```

### 💡 検証機能の特徴

#### 🔧 認証方式の自動検出
- **Webhook Mode**: Bot Token不要、送信成功のみ検証
- **API Mode**: Bot Token使用、送受信完全検証

#### 📊 メッセージ検出の精密性
- Discord Notifierメッセージをfooterの"Discord Notifier"テキストで自動識別
- ベースライン比較による新メッセージ検出
- 複数回検証による誤検出防止

#### ⚡ リアルタイム反映
- 3秒待機による Discord API 伝播待ち
- Hot Reload機能との完全統合
- 設定変更の即座反映確認

---

## 🐛 デバッグデータ保存機能

### 概要
`DISCORD_DEBUG=1` が設定されている場合、すべてのHookイベントの入力データと出力データが自動的に保存されます。

### 保存場所
```
~/.claude/hooks/debug/
├── {timestamp}_{event_type}_raw_input.json         # フックから受信した生データ
└── {timestamp}_{event_type}_formatted_output.json  # Discord送信用フォーマット済みデータ
```

### 主な機能

1. **自動クリーンアップ**
   - 7日以上古いファイルは自動削除
   - ディスク容量の無駄遣いを防止

2. **機密情報の自動マスキング**
   - Discord Bot Token: `NzYz***MASKED***514` 
   - Webhook URL: `***WEBHOOK_URL_MASKED***`
   - その他の認証情報も安全にマスク

3. **デバッグ分析コマンド**
   ```bash
   # 最新のデバッグファイルを確認
   ls -lt ~/.claude/hooks/debug/ | head -10
   
   # 特定イベントタイプのみ表示
   ls ~/.claude/hooks/debug/*Task* | tail -5
   
   # formatted_outputが存在しないケースを調査
   for f in ~/.claude/hooks/debug/*_raw_input.json; do
     output="${f/_raw_input.json/_formatted_output.json}"
     [ ! -f "$output" ] && echo "No output for: $(basename $f)"
   done
   ```

### トラブルシューティング例

**Q: なぜ一部のイベントで `formatted_output.json` が作成されない？**
A: 以下の理由が考えられます：
- ツールがフィルタリングで無効化されている（例: `DISCORD_TOOL_BASH=0`）
- イベントタイプが無効化されている（例: `DISCORD_EVENT_STOP=0`）
- ハンドラーがメッセージ生成をスキップした

## 🔍 Raw JSON ログ分析機能

### 生JSONログの完全活用
すべてのHook実行時に、受信した生のJSONデータが自動的に保存されます。これにより、通知内容の詳細分析が可能です。

### 保存場所と構造
```bash
# 保存場所
~/.claude/hooks/logs/raw_json/

# ファイル命名形式
{timestamp}_{event_type}_{session_id}.json          # 生データ
{timestamp}_{event_type}_{session_id}_pretty.json   # 整形済みデータ

# 例
2025-07-16_17-59-33-063_PreToolUse_76e40b9f-ba89-4ca1-9b80-509176246cba.json
2025-07-16_17-59-33-063_PreToolUse_76e40b9f-ba89-4ca1-9b80-509176246cba_pretty.json
```

### Write操作の詳細分析
```bash
# Write操作のJSONを検索
grep -l '"tool_name": "Write"' ~/.claude/hooks/logs/raw_json/*.json

# 特定のWrite操作を確認
cat ~/.claude/hooks/logs/raw_json/2025-07-16_17-59-33-063_PreToolUse_*_pretty.json
```

### JSONログから取得できる情報
```json
{
  "session_id": "76e40b9f-ba89-4ca1-9b80-509176246cba",
  "hook_event_name": "PreToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/path/to/file.py",
    "content": "#!/usr/bin/env python3\n実際に書き込まれる内容..."
  }
}
```

### 分析用コマンド集
```bash
# 今日のWrite操作を全て確認
find ~/.claude/hooks/logs/raw_json/ -name "$(date +%Y-%m-%d)*Write*pretty.json" -exec basename {} \; | sort

# 特定ファイルへの書き込みを追跡
grep -l "specific_file.py" ~/.claude/hooks/logs/raw_json/*Write*pretty.json

# 書き込み内容の長さを確認
jq '.tool_input.content | length' ~/.claude/hooks/logs/raw_json/*Write*pretty.json

# 書き込み内容の最初の10行を確認
jq -r '.tool_input.content' ~/.claude/hooks/logs/raw_json/*Write*pretty.json | head -10
```

### なぜDiscord通知で内容が見えないのか
1. **現在の制限**: Write操作のDiscord通知は、ファイルパスと成功ステータスのみ表示
2. **content情報の欠落**: 実際の書き込み内容（`tool_input.content`）は通知に含まれない
3. **解決策**: 生JSONログから`tool_input.content`を直接確認する

### 実際の分析例
```bash
# 最新のWrite操作を確認
latest_write=$(find ~/.claude/hooks/logs/raw_json/ -name "*Write*pretty.json" | sort | tail -1)
echo "最新のWrite操作: $latest_write"

# 書き込み先ファイルを確認
jq -r '.tool_input.file_path' "$latest_write"

# 書き込み内容のサイズを確認
jq -r '.tool_input.content | length' "$latest_write"
echo "文字数"

# 書き込み内容の最初の部分を確認
jq -r '.tool_input.content' "$latest_write" | head -20
```

---

## 📋 設定確認とデバッグ

### Discord通知が表示されない場合の診断手順

1. **設定ファイルの確認**
```bash
# イベントタイプ別の有効/無効設定を確認
grep -E "DISCORD_EVENT_|DISCORD_TOOL_" ~/.claude/.env | grep -v "^#"

# 特定のツールが無効化されていないか確認
grep "DISCORD_DISABLED_TOOLS" ~/.claude/.env
```

2. **Hook設定の確認**
```bash
# Hook設定でmain.pyが使用されているか確認
grep -A 3 "main.py" ~/.claude/settings.json | head -20
```

3. **ログファイルの確認**
```bash
# Discord Notifierのログを確認
tail -f ~/.claude/hooks/logs/discord_notifier_*.log

# エラーの有無を確認
grep -i "error\|failed\|exception" ~/.claude/hooks/logs/discord_notifier_*.log | tail -10
```

### よくある設定ミス

1. **PreToolUse/PostToolUseが無効**
```bash
# 無効化されている場合の例
DISCORD_EVENT_PRETOOLUSE=0
DISCORD_EVENT_POSTTOOLUSE=0
```
→ この場合、Taskツールの実行前後通知は送信されない

2. **特定ツールが無効化**
```bash
# Taskツールが無効化されている場合
DISCORD_DISABLED_TOOLS=Read,Edit,TodoWrite,Grep,Task
```
→ Taskツールに関する全ての通知が無効

3. **認証情報の不備**
```bash
# Webhook URLまたはBot Token + Channel IDが必要
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
# または
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_CHANNEL_ID=your_channel_id
```

---

*"The best debugger is the human brain. The second best is good logging."*
*— Anonymous Developer*