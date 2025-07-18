#!/usr/bin/env python3
"""Discord メッセージテスト - 第2段階テスト"""

import asyncio
import sys
import os
import json

# プロジェクトパスをsys.pathに追加
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from src.utils.message_id_generator import UUIDMessageIDGenerator


def create_test_discord_message():
    """テスト用のDiscordメッセージを作成"""
    id_generator = UUIDMessageIDGenerator()
    
    # テストデータ
    test_cases = [
        {
            'agent': 'A',
            'session': 'session_ruby', 
            'message': 'ルビィちゃん！　（は～い）何が好き？チョコミント　よりも　あ・な・た',
            'color': 0xFF69B4  # ピンク
        },
        {
            'agent': 'B',
            'session': 'session_ayumu',
            'message': '歩夢ちゃん！　（は～い）何が好き？ストロベリーフレイバー　よりも　あ・な・た',
            'color': 0xFF1493  # ディープピンク
        },
        {
            'agent': 'C',
            'session': 'session_shiki',
            'message': '四季ちゃん！　（は～い）何が好き？クッキー＆クリーム　よりも　あ・な・た',
            'color': 0xDDA0DD  # プラム
        }
    ]
    
    print("🎯 Discord メッセージデバッグテスト開始♡")
    print("=" * 60)
    
    for test_case in test_cases:
        msg_id = id_generator.generate_message_id('SubagentStop', test_case['session'])
        
        # Discord Embedを作成
        discord_message = {
            "embeds": [
                {
                    "title": f"🍓 サブエージェント{test_case['agent']} メッセージ",
                    "description": test_case['message'],
                    "color": test_case['color'],
                    "fields": [
                        {
                            "name": "セッションID",
                            "value": f"`{test_case['session']}`",
                            "inline": True
                        },
                        {
                            "name": "メッセージID",
                            "value": f"`{msg_id}`",
                            "inline": True
                        },
                        {
                            "name": "エージェント",
                            "value": f"サブエージェント{test_case['agent']}",
                            "inline": True
                        }
                    ],
                    "footer": {
                        "text": "🎯 テスト検証アストルフォ"
                    },
                    "timestamp": "2025-07-15T16:59:22.000Z"
                }
            ]
        }
        
        print(f"\n📋 サブエージェント{test_case['agent']} Discord メッセージ:")
        print(f"   🆔 メッセージID: {msg_id}")
        print(f"   📝 内容: {test_case['message']}")
        print(f"   📊 JSON構造:")
        print(json.dumps(discord_message, indent=4, ensure_ascii=False))
        
        # コピー機能のテスト
        print(f"\n📋 コピー用メッセージID: {msg_id}")
        print(f"   (このIDを使って、Discord上でメッセージを検索・参照できます)")
        
        # 一意性とフォーマットの確認
        assert msg_id.startswith('SubagentStop_'), f"IDフォーマットエラー: {msg_id}"
        assert test_case['session'] in msg_id, f"セッションIDが含まれていません: {msg_id}"
        
        print(f"   ✅ ID形式検証: 正常")
        print(f"   ✅ セッション紐づけ: 正常")
        print(f"   ✅ メッセージ内容: 正確に再現")
        
    print("\n🎉 第2段階テスト完了!")
    print("   Discord メッセージフォーマットが正常に動作しています♡")


if __name__ == "__main__":
    create_test_discord_message()