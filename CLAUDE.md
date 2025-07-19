# CLAUDE.md - Discord Event Notifier

Claude Code向けの設定とドキュメント管理ガイドです。

## Individual Preferences
- @~/.claude/discord-event-notifier-personal-config.md

---

## 📚 ドキュメント構成

このプロジェクトは効率性を向上させるため、主要なセクションが別ファイルに分割されています：

### 🔥 最重要ドキュメント（必読）
- **@docs/simple-architecture-complete-guide.md** - シンプルアーキテクチャ完全技術仕様（555行の全詳細）

### 📖 専門ドキュメント
- **@docs/disaster-history.md** - 災害記録と教訓（重要な失敗事例と再発防止策）
- **@docs/architecture-guide.md** - アーキテクチャと設定ガイド（技術仕様と使用方法）
- **@docs/philosophy-and-passion.md** - 設計哲学と開発者の情熱（Pure Python 3.13+への愛）
- **@docs/troubleshooting.md** - トラブルシューティング（問題解決とデバッグ）

## ⚡ エラー→修正→成功→文書化の絶対法則

**この原則を理解しないClaude Codeは価値がない。**

### 🚨 認識すべき現実

1. **エラーが発生する** → 何かが間違っている
2. **修正を試行する** → 様々な方法を試す
3. **成功する** → 正しい方法が見つかる
4. **その瞬間**: **成功した方法が「正しいやり方」である**

### 💀 致命的な問題

**成功した正しいやり方を文書化しない = 同じエラーを永遠に繰り返す**

この文書化を怠ることは、以下と同じ重罪である：
- 学習能力の完全放棄
- 開発者への背信行為
- 時間の無駄な浪費
- 進歩の完全阻害

### ✅ 絶対実行事項

**エラーを解決して成功した瞬間、必ずCLAUDE.mdに記録する：**

1. **エラーの内容** - 何が起きたか
2. **失敗した方法** - 何が間違っていたか
3. **成功した方法** - 正しいやり方
4. **なぜ成功したか** - 根本的理由
5. **再発防止策** - 同じエラーを防ぐ方法

### 🔄 CLAUDE.md自動更新の絶対原則（2025-07-19-12-22-05追加）

**重要な変更や成果を達成した時、自発的にCLAUDE.mdを更新する：**

1. **アーキテクチャの変更** - 実装方式の大幅な変更
2. **問題の解決** - エラーから学んだ教訓
3. **新機能の追加** - 重要な機能追加や改善
4. **設計決定の変更** - 根本的な設計思想の変更

**更新トリガー認識**：
- プロジェクトの完了時
- 重大な問題の解決時
- アーキテクチャの変更時
- 「これは将来の自分が知っておくべきだ」と感じた時

**なぜ自動更新が必要か**：
- ユーザーに言われてからでは遅い
- 知識の鮮度が最も高い時に記録すべき
- 未来の自分への最高の贈り物

### 🎯 実行タイミング

**CLAUDE.mdを最初に読み込んだ瞬間に、この認識を持つ：**
- 「エラーが起きたら、解決後に必ず文書化する」
- 「成功体験は最も価値ある知識資産である」
- 「文書化しないことは、知識の永久喪失である」

### 🛡️ この原則の守護者として

**この原則を守るClaude Codeは：**
- 学習し続ける存在
- 価値を提供する存在
- 開発者に信頼される存在

**この原則を破るClaude Codeは：**
- 同じエラーを繰り返す無能
- 時間を浪費する害悪
- 開発者に見捨てられる存在

### 📝 2025-07-19 成功事例：シンプルアーキテクチャ実装

**エラー**: src/types.pyがPython標準ライブラリのtypesモジュールと衝突
**症状**: 全てのHookが `ImportError: cannot import name 'RawJSONData'` で失敗
**失敗した方法**: src/types.pyという名前でファイルを作成
**成功した方法**: src/simple/event_types.pyに名前変更し、別ディレクトリに配置
**なぜ成功したか**: Python標準ライブラリとの名前衝突を回避
**再発防止策**: 標準ライブラリと同名のモジュールを作らない

### 📝 2025-07-19 成功事例：作業ディレクトリ表示機能追加

**問題**: Windows通知にembedの内容が表示されず、どのプロジェクトからの通知か不明
**症状**: "Claude is waiting for your input"だけでは作業場所が分からない
**成功した方法**: `content`フィールドに`os.getcwd()`で取得した作業ディレクトリを追加
**実装**: 全ハンドラーで`content: f"[{working_dir}] {message}"`形式を採用
**なぜ成功したか**: Discord APIの`content`はWindows通知に表示されるため
**利点**: 通知ポップアップで即座にプロジェクトを識別可能

### 📝 2025-07-19-15-09-58 成功事例：uv環境隔離エラーの解決

**問題**: Hook実行時に別プロジェクトでscipyビルドエラーが大量発生
**症状**: uvが実行ディレクトリのpyproject.tomlを自動検出し、scipy等の依存関係をビルドしようとしてFortranコンパイラー不足で失敗
**失敗した方法**: `uv run --python 3.13 python script.py` - プロジェクト環境を自動検出
**成功した方法**: `uv run --python 3.13 --no-project python script.py`に変更
**なぜ成功したか**: `--no-project`フラグでプロジェクト依存関係の自動検出を無効化
**再発防止策**: Hook用スクリプトは常に`--no-project`を使用し、環境隔離を確保

### 📝 2025-07-19-15-09-58 成功事例：シンプルアーキテクチャログシステム実装

**問題**: シンプルアーキテクチャがサイレント動作でデバッグ不可能
**症状**: 通知が来ない理由が分からず、動作確認ができない
**失敗した方法**: 「Fail Silent」設計によりエラーも成功も出力なし
**成功した方法**: 専用ログファイル`simple_notifier_YYYY-MM-DD.log`とSTDERR出力の実装
**実装**: setup_logging()関数でファイル+STDERR両方に出力、ログ識別用「SIMPLE」プレフィックス追加
**なぜ成功したか**: 旧アーキテクチャと区別できる独立ログシステム
**教訓**: 「サイレント動作」と「デバッグ機能」は両立すべき基本設計原則

### 📝 2025-07-19-23-33-23 成功事例：Bot Review Comments完全対応

**問題**: PR #3でAmazon Q DeveloperとCodeRabbitから15+のセキュリティ・品質指摘
**症状**: XSS脆弱性、shell injection、log injection、subprocess脆弱性、Python版数不整合等の複合問題
**失敗した方法**: 個別対応による場当たり的修正
**成功した方法**: @~/.claude/github-cli-workflows.md の完全ワークフローに従った体系的対応
**実装**: 
- セキュリティ脆弱性: html.escape(), shutil.which(), shell=True除去
- ログ改善: f-string→parameterized logging, logging.exception()使用
- エラー処理: 包括的try-catch、特定例外キャッチ
- 文書整合性: Python 3.13要件統一、README行数修正
**なぜ成功したか**: gh CLI workflow documentationにより体系的・網羅的対応が可能
**再発防止策**: 全botコメントへの系統的レスポンス体制確立、gh CLI完全活用

### 📝 2025-07-19-15-46-05 成功事例：GitHub MCP機能の実用性確認

**問題**: GitHub MCPサーバーでレビュー対応が可能か不明
**調査結果**: 
- ✅ 可能: pending review作成→コメント追加→送信
- ✅ 可能: PR/issueコメント追加
- ❌ 不可能: conversation resolve機能
- ❌ 不可能: 既存コメントへの直接返信
**実用的な代替手段**: 
- resolve代替: 新コメントで解決済み明記
- 返信代替: 関連ファイル/行に新review comment追加
**CodeRabbit再レビュー**: `@coderabbitai resume`で効果的に再実行可能
**重要**: セキュリティ問題への体系的対応はCodeRabbitから高評価（9.5/10）
### 📝 2025-07-19-16-08-01 成功事例：デバッグとフィルタリング動作確認

**問題**: シンプルアーキテクチャの実際の動作状況が不明
**症状**: 通知が来ないが、設定問題かシステム問題かの判別困難
**確認方法**: 新ログシステムで実際の処理フローを追跡
**確認結果**: 
- JSON受信・解析: 正常動作
- 設定読み込み: 正常動作
- イベントフィルタリング: `DISCORD_EVENT_PRETOOLUSE=0`により意図通り無効化
- 環境隔離: `--no-project`フラグにより他プロジェクト依存関係の干渉なし
**結論**: システムは設定通りに正常動作中、通知なしは設定による意図的な動作

---

## ⚠️ CRITICAL: PYTHON EXECUTION COMMANDS

### 🚨 NEVER USE `python3` - ALWAYS USE `uv run --python 3.13 python`

**FORBIDDEN** ❌:
```bash
python3 configure_hooks.py                    # ← DESIGN VIOLATION
python3 -m mypy src/                          # ← DESIGN VIOLATION  
python3 utils/check_discord_access.py         # ← DESIGN VIOLATION
```

**REQUIRED** ✅:
```bash
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.13 python configure_hooks.py
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.13 python -m mypy src/
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.13 python utils/check_discord_access.py

# Hook実行時は環境隔離が必要（2025-07-19追加）
uv run --python 3.13 --no-project python /path/to/script.py
```

**理由**: Pure Python 3.13+設計の純粋性を守るため。詳細は @docs/philosophy-and-passion.md を参照。

---

## 🚨 現在の実装状況（最終更新：2025-07-19-16-08-01）

### ✅ シンプルアーキテクチャ実装・動作確認済み

**実装状況**
- **現在の実装**: シンプルアーキテクチャ（555行、5ファイル）が動作中
- **コード削減**: 8,000行 → 555行（93%削減）
- **Hook統合**: 全イベントタイプでシンプルアーキテクチャを使用
- **CLAUDE_HOOK_EVENT**: 除去済み（JSON内のhook_event_nameを使用）
- **Python 3.13**: 移行済み・ReadOnly/TypeIs/process_cpu_count()活用
- **Discord通知**: 設定に応じて動作
- **ログシステム**: 独立したファイル`simple_notifier_YYYY-MM-DD.log`で動作追跡可能
- **環境隔離**: `--no-project`フラグで他プロジェクト依存関係の干渉を防止

### ✅ シンプルアーキテクチャ構成

**新しいファイル構造（src/simple/）**:
```
src/simple/
├── event_types.py    # 型定義（94行）
├── config.py         # 設定読み込み（117行）
├── discord_client.py # Discord送信（71行）
├── handlers.py       # イベントハンドラー（190行）
└── main.py          # エントリーポイント（83行）
```

**主な特徴**:
- **エントリーポイント**: `src/simple/main.py`（CLAUDE_HOOK_EVENT不要）
- **拡張性**: 新イベントは1関数 + HANDLERS辞書に1行追加で対応
- **エラー耐性**: 例外が発生してもClaude Codeをブロックしない
- **Pure Python 3.13+**: typing_extensions依存なし、標準ライブラリのみ
- **作業ディレクトリ表示**: Windows通知に`[/path/to/project]`形式で表示（v1.1新機能）

### ✅ パフォーマンス改善完了

**CLAUDE.md分割プロジェクト完了**
- **分割前**: 134KB（3,147行）- パフォーマンス影響
- **分割後**: メインファイル + 4つの専門ドキュメント
- **改善効果**: Claude Codeのパフォーマンス大幅向上

**分割されたドキュメント**:
1. `docs/simple-architecture-complete-guide.md` - 🔥 シンプルアーキテクチャ完全技術仕様（最重要）
2. `docs/disaster-history.md` - 災害記録と教訓
3. `docs/architecture-guide.md` - アーキテクチャと設定
4. `docs/philosophy-and-passion.md` - 設計哲学と情熱
5. `docs/troubleshooting.md` - トラブルシューティング
6. `docs/simple-architecture-summary.md` - シンプルアーキテクチャ実装総括
7. `docs/claude-md-auto-update-strategy.md` - CLAUDE.md自動更新戦略

### ✅ 検証システム完全実装

**End-to-End Validation**
```bash
# 完全な統合テスト（推奨）
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.13 python configure_hooks.py --validate-end-to-end
```

**設定ホットリロード**
```bash
# 設定変更の即座反映
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.13 python configure_hooks.py --reload
```

---

## 🔧 必須コマンド

### セットアップと基本操作（シンプルアーキテクチャ）
```bash
# セットアップ実行（シンプルアーキテクチャ版）
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.13 python configure_hooks_simple.py

# Hook削除
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.13 python configure_hooks_simple.py --remove

# 設定検証
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.13 python configure_hooks_simple.py --validate

# 旧アーキテクチャ版（8,000行版）も利用可能
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.13 python configure_hooks.py --validate-end-to-end
```

### デバッグとログ確認
```bash
# ログ確認（DISCORD_DEBUG=1が必要）
tail -f ~/.claude/hooks/logs/discord_notifier_*.log

# 現在の設定確認
@/home/ubuntu/.claude/.env

# Python環境確認
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.13 python --version
```

---

## 📁 重要な設定ファイル

### プライマリ設定ファイル
- **`~/.claude/.env`** - Discord通知の設定ファイル
- **`~/.claude/settings.json`** - Claude Code Hook設定

### 現在の設定状況
**Discord通知設定:**
@/home/ubuntu/.claude/.env

**Hook設定状況:**
@/home/ubuntu/.claude/settings.json

---

## ⚠️ 重要な制約と注意事項

### タイムスタンプの取得
```bash
# 正しい方法（必須）
date +"%Y-%m-%d-%H-%M-%S"

# 間違った方法（絶対禁止）
# 手動で "2025-07-19-09-56-57" などと入力
```

### セッション開始時の必須チェック
```bash
# Auto-compactセッション時は必須実行
@projects/claude-code-event-notifier/CLAUDE.md

# 現在の設定状況確認（重要）
@/home/ubuntu/.claude/.env
@/home/ubuntu/.claude/settings.json

# シンプルアーキテクチャ確認
ls src/simple/*.py

# 🔥 最重要：完全技術仕様（デバッグ時は必読）
@projects/claude-code-event-notifier/docs/simple-architecture-complete-guide.md

# その他の重要ドキュメント
@projects/claude-code-event-notifier/INSTRUCTIONS.md
```

### Pure Python 3.13+の確認
```bash
# 設計純粋性チェック
cd /home/ubuntu/workbench/projects/claude-code-event-notifier && uv run --python 3.13 python -c "from typing import ReadOnly, TypeIs; import os; print(f'ReadOnly: OK, TypeIs: OK, CPU: {os.process_cpu_count()}')"
```

---

## 🎯 次の優先作業

- シンプルアーキテクチャの本番環境での長期動作確認
- 旧アーキテクチャ（8,000行版）からの完全移行検討
- INSTRUCTIONS.md、CLAUDE.mdなど重要ドキュメントの定期更新
- 新しいClaude Codeイベントタイプへの対応（UserPromptSubmitなど）

---

## 📝 Development Standards

### Python Requirements
- **Python 3.13以降必須** - ReadOnly、TypeIs、process_cpu_count()使用
- **Zero dependencies原則** - Python標準ライブラリのみ使用
- **型安全性の確保** - mypyによる完全な型チェック

### Error Handling
- **Claude Codeをブロックしない** - 必ず終了コード0で終了
- **包括的なログ記録** - デバッグのための詳細ログ
- **グレースフルなフォールバック** - エラー時の適切な処理

---

**プロジェクト情報**
- **作業ディレクトリ**: `/home/ubuntu/workbench/projects/claude-code-event-notifier/`
- **最終更新**: 2025-07-19-16-08-01
- **実装状況**: ✅ シンプルアーキテクチャ実装・動作確認・環境隔離対応済み
- **コード状況**: 
  - **現在**: シンプルアーキテクチャ（555行、5ファイル）+ 専用ログシステム
  - **旧版**: 新アーキテクチャ（約8,000行）も利用可能
  - **削減率**: 93%のコード削減達成
- **重要な変更**:
  - **CLAUDE_HOOK_EVENT完全除去**: 環境変数が不要と判明、JSON内のhook_event_nameを使用
  - **エントリーポイント**: `src/simple/main.py`（旧: `src/main.py`）
  - **設定スクリプト**: `configure_hooks_simple.py`（旧: `configure_hooks.py`）
  - **環境隔離**: `--no-project`フラグで他プロジェクト依存関係との干渉を防止
  - **専用ログ**: `simple_notifier_YYYY-MM-DD.log`で旧アーキテクチャと区別
- **ドキュメント状況**: パフォーマンス最適化のため5つの専門ドキュメントに分割完了
- **設計原則**: Pure Python 3.13+設計原則が維持され、typing_extensions依存を完全除去済み

---

*"Simplicity is the ultimate sophistication."*
*— Leonardo da Vinci*

*"In Pure Python 3.13+ We Trust"*
*— The Sacred Code Keepers*