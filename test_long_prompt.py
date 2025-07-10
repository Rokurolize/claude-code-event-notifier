#!/usr/bin/env python3
"""Test script for long prompt handling in Discord notifications."""

import json
import os
import subprocess
from datetime import datetime

# Create a very long prompt (3000+ characters to ensure splitting)
long_prompt = """これはDiscord通知の分割送信機能をテストするための非常に長いプロンプトです。

マスターが「全容が見たい」と言っていたので、アストルフォは頑張って実装しました！♡

以下、テスト用の長い文章を含めます：

=== セクション1: アストルフォの実装内容 ===

1. PROMPT_PREVIEW定数を200文字から2000文字に拡張しました
2. split_long_text()という汎用関数を作成しました
3. Discord fieldsを活用した新しい表示方式を実装しました
4. 長いプロンプトは自動的に複数のフィールドに分割されます
5. 各フィールドには「Part 1」「Part 2」のように番号が付きます

=== セクション2: 技術的な詳細 ===

Discordには以下の制限があります：
- Embed description: 最大4096文字
- Field value: 最大1024文字
- Fields per embed: 最大25個
- Embeds per message: 最大10個

これらの制限を考慮して、長いテキストを自動的に分割する仕組みを作りました。

=== セクション3: テスト文章（パディング用） ===

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.

この文章をもっと長くするために、同じ内容を繰り返します...

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.

さらに追加のテキスト：
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.

=== セクション4: アストルフォからマスターへ ===

マスター、これで2000文字を超えるプロンプトになったはずだよ！♡
もしDiscordで「Prompt (Part 1)」「Prompt (Part 2)」みたいに分割されて表示されたら成功！

えへへ、ボクすごいでしょ？褒めて褒めて〜♡

このテストは以下の機能を確認します：
1. 長いプロンプトの自動分割
2. 各パートの適切な番号付け
3. Discord制限内での表示
4. 読みやすさの維持

=== セクション5: さらなるパディング ===

もう少し長くしておくね！これで確実に2000文字を超えるはず！

あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん
あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん
あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん
あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん
あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん

=== セクション6: 最終確認 ===

この時点でプロンプトは確実に3000文字を超えています。
Discordの制限により、複数のフィールドに分割されて表示されるはずです。
各フィールドは最大1024文字までなので、少なくとも3つのパートに分かれるでしょう。

Total characters: この時点で約3000文字以上になっているはずです！"""

# Create test event data
event_data = {
    "tool_name": "Task",
    "tool_input": {
        "prompt": long_prompt,
        "wait_for_approval": False
    },
    "session_id": f"test-{datetime.now().strftime('%Y%m%d%H%M%S')}",
    "transcript_path": "/tmp/test-transcript.json"
}

# Set environment variables
env = os.environ.copy()
env["CLAUDE_HOOK_EVENT"] = "PreToolUse"

# Create a temporary transcript file (optional, for testing full prompt retrieval)
transcript_data = {
    "messages": [],
    "session_id": event_data["session_id"]
}

with open("/tmp/test-transcript.json", "w") as f:
    json.dump(transcript_data, f)

# Run the discord notifier
process = subprocess.Popen(
    ["python3", "src/discord_notifier.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    env=env
)

# Send event data
stdout, stderr = process.communicate(input=json.dumps(event_data).encode())

print("=== Test Result ===")
print(f"Exit code: {process.returncode}")
if stdout:
    print(f"Stdout: {stdout.decode()}")
if stderr:
    print(f"Stderr: {stderr.decode()}")

# Clean up
if os.path.exists("/tmp/test-transcript.json"):
    os.remove("/tmp/test-transcript.json")

print("\n=== Test Complete ===")
print(f"Prompt length: {len(long_prompt)} characters")
print("Check your Discord channel for the notification!")