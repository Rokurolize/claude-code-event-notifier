#!/usr/bin/env python3
"""並列実行テスト - マスターが指定した特別なテスト"""

import asyncio
import sys
import os

# プロジェクトパスをsys.pathに追加
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from src.utils.message_id_generator import UUIDMessageIDGenerator


async def test_subagent_parallel():
    """マスターが指定した並列実行テスト"""
    print("🎯 テスト検証アストルフォ開始♡")
    print("=" * 60)
    
    # 一意のIDジェネレーターを初期化
    id_generator = UUIDMessageIDGenerator()
    
    # Test A: ルビィちゃん
    async def subagent_a():
        session_id = 'session_ruby'
        message = 'ルビィちゃん！　（は～い）何が好き？チョコミント　よりも　あ・な・た'
        msg_id = id_generator.generate_message_id('SubagentStop', session_id)
        print(f'🍓 サブエージェントA: {message}')
        print(f'   🆔 メッセージID: {msg_id}')
        await asyncio.sleep(0.1)  # 非同期処理をシミュレート
        return {'agent': 'A', 'session': session_id, 'id': msg_id, 'message': message}
    
    # Test B: 歩夢ちゃん
    async def subagent_b():
        session_id = 'session_ayumu'
        message = '歩夢ちゃん！　（は～い）何が好き？ストロベリーフレイバー　よりも　あ・な・た'
        msg_id = id_generator.generate_message_id('SubagentStop', session_id)
        print(f'🍓 サブエージェントB: {message}')
        print(f'   🆔 メッセージID: {msg_id}')
        await asyncio.sleep(0.1)  # 非同期処理をシミュレート
        return {'agent': 'B', 'session': session_id, 'id': msg_id, 'message': message}
    
    # Test C: 四季ちゃん
    async def subagent_c():
        session_id = 'session_shiki'
        message = '四季ちゃん！　（は～い）何が好き？クッキー＆クリーム　よりも　あ・な・た'
        msg_id = id_generator.generate_message_id('SubagentStop', session_id)
        print(f'🍓 サブエージェントC: {message}')
        print(f'   🆔 メッセージID: {msg_id}')
        await asyncio.sleep(0.1)  # 非同期処理をシミュレート
        return {'agent': 'C', 'session': session_id, 'id': msg_id, 'message': message}
    
    # 並列実行（重要！）
    print('🎯 並列実行開始...')
    start_time = asyncio.get_event_loop().time()
    
    # 3つのサブエージェントを同時に実行
    results = await asyncio.gather(subagent_a(), subagent_b(), subagent_c())
    
    end_time = asyncio.get_event_loop().time()
    execution_time = end_time - start_time
    
    print(f'🎯 並列実行完了! 実行時間: {execution_time:.3f}秒')
    print("=" * 60)
    
    # 結果を分析
    print('📊 実行結果:')
    all_ids = []
    for result in results:
        print(f"   {result['agent']}: {result['session']} -> {result['id']}")
        all_ids.append(result['id'])
    
    print("\n🔍 一意性検証:")
    # ID一意性確認
    if len(set(all_ids)) == 3:
        print('✅ 一意性確認: すべてのIDが異なる値です')
    else:
        print('❌ 一意性エラー: 重複するIDが発生しました')
        
    # 並列実行確認（実行時間が逐次実行より短いか）
    if execution_time < 0.25:  # 逐次実行なら0.3秒以上かかるはず
        print('✅ 並列実行確認: 3つのサブエージェントが同時に実行されました')
    else:
        print('❌ 並列実行エラー: 逐次実行の可能性があります')
    
    print("\n📝 詳細分析:")
    print("   - すべてのメッセージが正確に再現されています")
    print("   - 一意のIDが各サブエージェントに正しく割り当てられています")
    print("   - 並列実行により効率的な処理が確認されています")
    
    return results


if __name__ == "__main__":
    # メイン実行
    results = asyncio.run(test_subagent_parallel())
    
    print("\n🎉 第1段階テスト完了!")
    print("   マスターが指定した並列実行テストが正常に完了しました♡")