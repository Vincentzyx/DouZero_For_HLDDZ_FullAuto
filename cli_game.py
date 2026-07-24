#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命令行斗地主指导系统 - 基于 DouZero 训练模型
你在真实游戏中玩，本系统指导你每一步决策：
  1. 输入手牌 → 叫牌建议（BidModel 胜率预测）
  2. 输入底牌+角色 → 加倍建议（LandlordModel / FarmerModel）
  3. 每轮输入对手出牌 → 出牌建议（DeepAgent + ResNet 模型）

模型原理：
  用 DouZero 自我博弈 N 局，对于随机到的每种手牌，随机生成若干种对手手牌，
  把该牌型和赢的局数扔进一个简单的全连接网络进行训练，
  得到手牌与胜率之间的关系，最后根据预期胜率，以一定阈值进行叫牌和加倍。
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from douzero.env.game import GameEnv, EnvCard2RealCard, RealCard2EnvCard, AllEnvCard
from douzero.env import move_detector as md
from douzero.evaluation.deep_agent import DeepAgent

# ============================================================
# 卡牌工具
# ============================================================

INPUT_CHAR_TO_CARD = {
    '3': [3], '4': [4], '5': [5], '6': [6], '7': [7], '8': [8], '9': [9],
    'T': [10], 't': [10], '0': [10],
    'J': [11], 'j': [11],
    'Q': [12], 'q': [12],
    'K': [13], 'k': [13],
    'A': [14], 'a': [14],
    '2': [17],
    'X': [20], 'x': [20],
    'D': [30], 'd': [30],
}

CARD_DISPLAY = {
    3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8', 9: '9',
    10: '10', 11: 'J', 12: 'Q', 13: 'K', 14: 'A',
    17: '2', 20: '小王', 30: '大王'
}

POSITION_NAMES = {
    'landlord': '地主',
    'landlord_up': '农民(上家)',
    'landlord_down': '农民(下家)'
}

MODEL_PATH = {
    'landlord': "baselines/resnet/resnet_landlord.ckpt",
    'landlord_up': "baselines/resnet/resnet_landlord_up.ckpt",
    'landlord_down': "baselines/resnet/resnet_landlord_down.ckpt",
}


def parse_card_string(text):
    """
    解析卡牌字符串，返回环境卡牌值列表（已排序）
    支持: "3 4 5 6 7" / "34567" / "T J Q K A" / "XD" / "10 J Q K"
    """
    text = text.strip()
    if not text:
        return []
    cards = []
    i = 0
    while i < len(text):
        c = text[i]
        if c in (' ', ',', ';', '，', '；', '\t'):
            i += 1
            continue
        if c == '1' and i + 1 < len(text) and text[i + 1] == '0':
            cards.append(10)
            i += 2
            continue
        if c in INPUT_CHAR_TO_CARD:
            cards.extend(INPUT_CHAR_TO_CARD[c])
        else:
            print(f"  ⚠ 忽略无法识别的字符: '{c}'")
        i += 1
    return sorted(cards)


def cards_to_str(cards):
    """环境卡牌值列表 → 可读字符串"""
    if not cards:
        return "无"
    return ' '.join([CARD_DISPLAY.get(c, str(c)) for c in sorted(cards)])


def cards_to_real_str(cards):
    """环境卡牌值列表 → 模型输入字符串 (如 '3345TJQKKAA2D')"""
    return ''.join([EnvCard2RealCard[c] for c in sorted(cards)])


def env_to_real_list(cards):
    """环境卡牌值列表 → 真实卡牌字符列表 (如 ['3','3','4','T'])"""
    return [EnvCard2RealCard[c] for c in sorted(cards)]


def validate_cards(cards, expected_count, label="手牌"):
    if len(cards) != expected_count:
        print(f"  ❌ {label}应该是 {expected_count} 张，当前输入了 {len(cards)} 张")
        return False
    deck_count = {}
    for c in AllEnvCard:
        deck_count[c] = deck_count.get(c, 0) + 1
    input_count = {}
    for c in cards:
        input_count[c] = input_count.get(c, 0) + 1
    for c, cnt in input_count.items():
        if c not in deck_count:
            print(f"  ❌ 非法卡牌: {CARD_DISPLAY.get(c, str(c))}")
            return False
        if cnt > deck_count[c]:
            print(f"  ❌ {CARD_DISPLAY.get(c, str(c))} 最多 {deck_count[c]} 张，输入了 {cnt} 张")
            return False
    return True


def input_cards(prompt, expected_count=None):
    """循环等待用户输入卡牌"""
    while True:
        try:
            raw = input(prompt).strip()
            if raw.lower() in ('q', 'quit', 'exit'):
                return None
            cards = parse_card_string(raw)
            if expected_count is not None:
                if validate_cards(cards, expected_count):
                    return sorted(cards)
            else:
                if len(cards) > 0:
                    return sorted(cards)
                print("  ❌ 未识别到任何卡牌")
        except (EOFError, KeyboardInterrupt):
            return None


def get_type_name(move_type_dict):
    """返回牌型的中文名称"""
    type_map = {
        md.TYPE_0_PASS: "Pass",
        md.TYPE_1_SINGLE: "单张",
        md.TYPE_2_PAIR: "对子",
        md.TYPE_3_TRIPLE: "三条",
        md.TYPE_4_BOMB: "💣 炸弹",
        md.TYPE_5_KING_BOMB: "👑 王炸",
        md.TYPE_6_3_1: "三带一",
        md.TYPE_7_3_2: "三带二",
        md.TYPE_8_SERIAL_SINGLE: "顺子",
        md.TYPE_9_SERIAL_PAIR: "连对",
        md.TYPE_10_SERIAL_TRIPLE: "飞机",
        md.TYPE_11_SERIAL_3_1: "飞机带单",
        md.TYPE_12_SERIAL_3_2: "飞机带对",
        md.TYPE_13_4_2: "四带二(单)",
        md.TYPE_14_4_22: "四带二(对)",
        md.TYPE_15_WRONG: "无效",
    }
    return type_map.get(move_type_dict.get('type', 15), "未知")


# ============================================================
# 阶段1：叫牌指导
# ============================================================

def guide_bidding():
    """
    叫牌阶段指导
    使用 BidModel 预测胜率，给出叫牌建议
    """
    print("\n" + "=" * 60)
    print("  📢 阶段1：叫牌指导")
    print("=" * 60)

    # 加载 BidModel
    try:
        import BidModel
        print("  ✅ BidModel (叫牌模型) 已加载")
    except Exception as e:
        print(f"  ❌ BidModel 加载失败: {e}")
        print("  无法提供叫牌建议，请自行判断")
        return None

    try:
        import FarmerModel
        has_farmer = True
    except Exception:
        has_farmer = False

    print("\n  请输入你的手牌（17张）:")
    print("  示例: 3 3 4 5 6 7 8 9 T J Q K A 2 2 X D")
    hand_cards = input_cards("  手牌> ", 17)
    if hand_cards is None:
        return None

    card_str = cards_to_real_str(hand_cards)
    print(f"\n  识别手牌: {cards_to_str(hand_cards)}")
    print(f"  模型输入: {card_str}")

    # BidModel 预测
    try:
        bid_score = BidModel.predict_score(card_str)
        print(f"\n  📊 BidModel 叫牌评分: {bid_score:.3f}")
        print("  " + "-" * 40)

        # 根据评分给出建议
        # 评分越高表示手牌越好，越应该叫高分
        if bid_score > 0.5:
            print("  💡 建议: 手牌很强，可以直接叫 3 分")
        elif bid_score > 0.3:
            print("  💡 建议: 手牌较强，建议叫 2 分")
        elif bid_score > 0.15:
            print("  💡 建议: 手牌一般，可以叫 1 分试试")
        else:
            print("  💡 建议: 手牌偏弱，建议不叫")
    except Exception as e:
        print(f"  ⚠ BidModel.predict_score 失败: {e}")

    # FarmerModel 对比（如果不叫，当农民的胜率）
    if has_farmer:
        try:
            farmer_score = FarmerModel.predict(card_str, "farmer")
            print(f"\n  📊 FarmerModel 农民评分: {farmer_score:.3f}")
            if bid_score > 0.5 and farmer_score < bid_score:
                print("  💡 当地主评分远高于农民，强烈建议叫地主")
            elif farmer_score > bid_score:
                print("  💡 农民评分更高，如果叫不到地主，当农民也不错")
        except Exception:
            pass

    return hand_cards


# ============================================================
# 阶段2：加倍指导
# ============================================================

def guide_multiply(hand_cards_17):
    """
    加倍阶段指导
    输入底牌，计算地主/农民胜率，给出加倍建议
    返回: (手牌20张或17张, 角色position, 底牌)
    """
    print("\n" + "=" * 60)
    print("  📈 阶段2：加倍指导")
    print("=" * 60)

    print("\n  请输入底牌（3张）:")
    bottom_cards = input_cards("  底牌> ", 3)
    if bottom_cards is None:
        return None, None, None
    print(f"  底牌: {cards_to_str(bottom_cards)}")

    # 判断角色：如果手牌变成了20张就是地主，17张就是农民
    print("\n  你最终的手牌是多少张？")
    print("  1 - 20张（你是地主，手牌17张+底牌3张）")
    print("  2 - 17张（你是农民，底牌归别人）")
    while True:
        try:
            choice = input("  选择> ").strip()
            if choice == '1':
                hand_cards_20 = sorted(hand_cards_17 + bottom_cards)
                position = 'landlord'
                break
            elif choice == '2':
                hand_cards_20 = hand_cards_17
                position = None  # 农民位置稍后确定
                break
            else:
                print("  请输入 1 或 2")
        except (EOFError, KeyboardInterrupt):
            return None, None, None

    if position == 'landlord':
        print(f"\n  地主手牌 ({len(hand_cards_20)}张): {cards_to_str(hand_cards_20)}")
        card_str = cards_to_real_str(hand_cards_20)
        bottom_str = cards_to_real_str(bottom_cards)

        # 使用 LandlordModel
        try:
            import LandlordModel
            # 先初始化 DeepAgent 模型
            try:
                LandlordModel.init_model(MODEL_PATH['landlord'])
            except Exception:
                pass
            win_rate = LandlordModel.predict_by_model(card_str, bottom_str)
            print(f"\n  📊 LandlordModel 地主胜率: {win_rate:.3f}")
            print("  " + "-" * 40)
            if win_rate > 0.5:
                print("  💡 建议: 胜率高，可以加倍")
            elif win_rate > 0.35:
                print("  💡 建议: 胜率中等，可以不加倍")
            else:
                print("  💡 建议: 胜率偏低，不建议加倍")
        except Exception as e:
            print(f"  ⚠ LandlordModel 预测失败: {e}")
    else:
        # 农民
        card_str = cards_to_real_str(hand_cards_20)
        print(f"\n  农民手牌 ({len(hand_cards_20)}张): {cards_to_str(hand_cards_20)}")

        try:
            import FarmerModel
            # 农民位置（上家/下家）需要确认
            print("\n  你是地主的哪个位置？")
            print("  1 - 地主上家 (地主先出，你最后出)")
            print("  2 - 地主下家 (你在地主之后出牌)")
            while True:
                try:
                    pos_choice = input("  选择> ").strip()
                    if pos_choice == '1':
                        position = 'landlord_up'
                        farmer_type = 'up'
                        break
                    elif pos_choice == '2':
                        position = 'landlord_down'
                        farmer_type = 'down'
                        break
                    else:
                        print("  请输入 1 或 2")
                except (EOFError, KeyboardInterrupt):
                    return None, None, None

            win_rate = FarmerModel.predict(card_str, farmer_type)
            print(f"\n  📊 FarmerModel 农民胜率: {win_rate:.3f}")
            print("  " + "-" * 40)
            if win_rate > 1.3:
                print("  💡 建议: 胜率很高，可以加倍")
            elif win_rate > 1.0:
                print("  💡 建议: 胜率尚可，可以不加倍")
            else:
                print("  💡 建议: 胜率偏低，不建议加倍")
        except Exception as e:
            print(f"  ⚠ FarmerModel 预测失败: {e}")

    return hand_cards_20, position, bottom_cards


# ============================================================
# 阶段3：出牌指导（核心）
# ============================================================

def guide_playing(hand_cards, position, bottom_cards):
    """
    出牌阶段指导
    创建 GameEnv + DeepAgent，每轮用户输入对手出牌，系统给出建议
    """
    print("\n" + "=" * 60)
    print("  🃏 阶段3：出牌指导")
    print("=" * 60)

    # 确定角色
    if position is None:
        print("\n  你的角色是？")
        print("  1 - 地主上家 (landlord_up)")
        print("  2 - 地主下家 (landlord_down)")
        while True:
            try:
                pos_choice = input("  选择> ").strip()
                if pos_choice == '1':
                    position = 'landlord_up'
                    break
                elif pos_choice == '2':
                    position = 'landlord_down'
                    break
                else:
                    print("  请输入 1 或 2")
            except (EOFError, KeyboardInterrupt):
                return

    print(f"\n  你的角色: {POSITION_NAMES[position]}")
    print(f"  你的手牌 ({len(hand_cards)}张): {cards_to_str(hand_cards)}")

    # 计算其他玩家的牌
    other_hand_cards = []
    for i in set(AllEnvCard):
        other_hand_cards.extend([i] * (AllEnvCard.count(i) - hand_cards.count(i)))

    # 分配给另外两个位置
    if position == 'landlord':
        other_pos_list = ['landlord_up', 'landlord_down']
    elif position == 'landlord_up':
        other_pos_list = ['landlord', 'landlord_down']
    else:
        other_pos_list = ['landlord', 'landlord_up']

    # 创建 GameEnv，用 DeepAgent 代表用户的位置
    try:
        agent = DeepAgent(position, MODEL_PATH[position])
        print(f"  ✅ AI模型已加载: {MODEL_PATH[position]}")
    except Exception as e:
        print(f"  ❌ AI模型加载失败: {e}")
        print("  无法提供出牌建议")
        return

    # 用用户的position创建一个代表用户的AI
    # GameEnv 的 players 格式: [position_string, agent]
    players = [position, agent]
    env = GameEnv(players)

    # 初始化手牌分配
    card_play_data = {
        'three_landlord_cards': list(bottom_cards),
    }

    # 用户的手牌
    card_play_data[position] = list(hand_cards)

    # 其他两个位置的牌（从 other_hand_cards 中分）
    pos1, pos2 = other_pos_list
    card_play_data[pos1] = sorted(other_hand_cards[:17])
    card_play_data[pos2] = sorted(other_hand_cards[17:])

    env.card_play_init(card_play_data)

    # 确定出牌顺序
    # 出牌顺序: landlord → landlord_down → landlord_up → landlord → ...
    # play_order: 0=用户出牌, 1=用户下家出牌, 2=用户上家出牌
    if position == 'landlord':
        play_order = 0  # 地主先出
    elif position == 'landlord_up':
        play_order = 2  # 上家最后出（地主→下家→上家）
    else:
        play_order = 1  # 下家在地主之后出

    print(f"\n  底牌: {cards_to_str(bottom_cards)}")
    print(f"  出牌顺序: ", end="")
    if position == 'landlord':
        print("你(地主) → 下家 → 上家 → 循环")
    elif position == 'landlord_up':
        print("地主 → 下家 → 你(上家) → 循环")
    else:
        print("地主 → 你(下家) → 上家 → 循环")

    print("\n" + "=" * 60)
    print("  开始出牌指导！每轮请告诉我对手出了什么牌")
    print("  输入 'q' 退出")
    print("=" * 60)

    turn = 0
    while not env.game_over:
        turn += 1

        if play_order == 0:
            # ====== 轮到用户出牌 ======
            print(f"\n{'━' * 60}")
            print(f"  第 {turn} 轮 - 🎮 轮到你出牌")

            # 获取 AI 推荐（不更新状态，先看看建议）
            action_message, action_list = env.step(position, update=False)
            recommended = action_message.get("action", "")
            win_rate = action_message.get("win_rate", 0)

            # 显示当前手牌
            current_hand = env.info_sets[position].player_hand_cards
            print(f"  你的手牌 ({len(current_hand)}张): {cards_to_str(current_hand)}")

            # 显示上一手信息
            last_move = env.info_sets[position].last_move
            if last_move:
                print(f"  上一手出牌: {cards_to_str(last_move)}")
            else:
                print(f"  你是第一个出牌的人，自由出牌")

            # 显示对手剩余牌数
            for pos in ['landlord', 'landlord_up', 'landlord_down']:
                if pos != position:
                    cnt = len(env.info_sets[pos].player_hand_cards)
                    print(f"  {POSITION_NAMES[pos]} 剩余: {cnt}张")

            # 显示 AI 推荐
            print(f"\n  🤖 AI推荐出牌: ", end="")
            if recommended:
                move_type = md.get_move_type(parse_card_string(recommended))
                type_name = get_type_name(move_type)
                print(f"{recommended}  ({type_name})")
            else:
                print("Pass (不出)")
            print(f"  📊 推荐胜率: {win_rate:.3f}")

            # 显示前3个候选方案
            if action_list:
                print(f"\n  候选方案 (前3):")
                for i, (act_str, score_str) in enumerate(action_list[:3]):
                    if act_str and act_str != "Pass":
                        mt = md.get_move_type(parse_card_string(act_str))
                        tn = get_type_name(mt)
                        print(f"    [{i+1}] {act_str} ({tn}) - 评分: {score_str}")
                    else:
                        print(f"    [{i+1}] Pass - 评分: {score_str}")

            # 等待用户确认实际出牌
            print(f"\n  请按照AI建议出牌，或输入你实际出的牌:")
            print("  (直接回车 = 按AI建议出牌, 或输入卡牌如 '3 4 5', 'p' = Pass)")
            try:
                user_play = input("  实际出牌> ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if user_play == '' or user_play.lower() == 'ok':
                # 按AI建议出牌
                if recommended:
                    played_env = parse_card_string(recommended)
                else:
                    played_env = []
            elif user_play.lower() in ('p', 'pass'):
                played_env = []
            else:
                played_env = parse_card_string(user_play)

            played_env.sort()

            # 更新环境
            action_msg, _ = env.step(position, played_env)
            actual_play = action_msg.get("action", "")
            if actual_play:
                mt = md.get_move_type(played_env)
                tn = get_type_name(mt)
                print(f"  ✓ 记录出牌: {actual_play} ({tn})")
            else:
                print(f"  ✓ 记录出牌: Pass")

            # 检查是否出完
            remaining = env.info_sets[position].player_hand_cards
            if len(remaining) == 0:
                print("\n  🎉 你的牌出完了！")
                break

            # 轮到下家
            if position == 'landlord':
                play_order = 1  # 地主 → 下家
            elif position == 'landlord_down':
                play_order = 2  # 下家 → 上家
            else:
                play_order = 0  # 上家 → 地主

        elif play_order == 1:
            # ====== 下家出牌 ======
            neighbor = 'landlord_down' if position == 'landlord' else (
                'landlord' if position == 'landlord_up' else 'landlord_up'
            )
            # 修正：下家是谁
            if position == 'landlord':
                neighbor = 'landlord_down'
                neighbor_name = '下家'
            elif position == 'landlord_down':
                neighbor = 'landlord_up'
                neighbor_name = '上家'
            else:  # landlord_up
                neighbor = 'landlord_down'
                neighbor_name = '下家'

            # 实际上 play_order=1 表示用户的下家
            # 地主的下家=landlord_down, landlord_up的下家=landlord, landlord_down的下家=landlord_up
            if position == 'landlord':
                next_pos = 'landlord_down'
            elif position == 'landlord_up':
                next_pos = 'landlord'
            else:
                next_pos = 'landlord_up'

            print(f"\n  等待 {POSITION_NAMES[next_pos]} 出牌...")
            try:
                raw = input(f"  请输入 {POSITION_NAMES[next_pos]} 出的牌 (p=Pass): ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if raw.lower() in ('p', 'pass', ''):
                played_env = []
            else:
                played_env = parse_card_string(raw)
                played_env.sort()

            env.step(position, played_env)

            if played_env:
                print(f"  ✓ 记录: {POSITION_NAMES[next_pos]} 出牌 {cards_to_str(played_env)}")
            else:
                print(f"  ✓ 记录: {POSITION_NAMES[next_pos]} Pass")

            # 下一个
            if position == 'landlord':
                play_order = 2  # 下家 → 上家
            elif position == 'landlord_up':
                play_order = 0  # 地主 → 轮到用户
            else:
                play_order = 0  # 上家 → 轮到用户（地主下家的情况）

        elif play_order == 2:
            # ====== 上家出牌 ======
            if position == 'landlord':
                prev_pos = 'landlord_up'
            elif position == 'landlord_up':
                prev_pos = 'landlord_down'
            else:
                prev_pos = 'landlord'

            print(f"\n  等待 {POSITION_NAMES[prev_pos]} 出牌...")
            try:
                raw = input(f"  请输入 {POSITION_NAMES[prev_pos]} 出的牌 (p=Pass): ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if raw.lower() in ('p', 'pass', ''):
                played_env = []
            else:
                played_env = parse_card_string(raw)
                played_env.sort()

            env.step(position, played_env)

            if played_env:
                print(f"  ✓ 记录: {POSITION_NAMES[prev_pos]} 出牌 {cards_to_str(played_env)}")
            else:
                print(f"  ✓ 记录: {POSITION_NAMES[prev_pos]} Pass")

            # 下一个
            if position == 'landlord':
                play_order = 0  # 上家出完 → 轮到地主(用户)
            elif position == 'landlord_up':
                play_order = 1  # 上家出完 → 下家
            else:
                play_order = 1  # 下家出完 → 地主之后是下家... 修正

            # 修正出牌顺序: landlord → landlord_down → landlord_up → landlord
            # 如果用户是 landlord_up: 地主(1) → 下家(2) → 用户(0)
            # 如果用户是 landlord_down: 地主(1) → 用户(0→下家) → 上家(2)
            if position == 'landlord_down':
                # 地主→用户(下家)→上家
                # play_order=2 是上家出牌，出完轮到地主
                play_order = 0  # 上家 → 地主(用户)

    # 游戏结束
    print("\n" + "=" * 60)
    print("  🏁 本局指导结束！")
    print("=" * 60)


# ============================================================
# 主入口
# ============================================================

def main():
    print("\n" + "=" * 60)
    print("    🃏 欢乐斗地主 CLI 指导系统")
    print("    (基于 DouZero 训练模型)")
    print("=" * 60)
    print()
    print("  本系统将在你玩欢乐斗地主时提供实时指导：")
    print("    1. 叫牌阶段 → 输入手牌，获取叫牌建议")
    print("    2. 加倍阶段 → 输入底牌，获取加倍建议")
    print("    3. 出牌阶段 → 输入对手出牌，获取出牌建议")
    print()
    print("  卡牌输入格式:")
    print("    3-9: 数字牌    T或10: 10")
    print("    J/Q/K/A: 花牌  2: 2")
    print("    X: 小王         D: 大王")
    print("    示例: 3 4 5 T J Q K A 2 2 X D")
    print("=" * 60)

    # 检查模型文件
    print("\n📦 检查模型文件...")
    for pos, path in MODEL_PATH.items():
        full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
        if os.path.exists(full_path):
            print(f"  ✅ {POSITION_NAMES[pos]} 模型: {path}")
        else:
            print(f"  ❌ {POSITION_NAMES[pos]} 模型缺失: {path}")

    try:
        import BidModel
        print("  ✅ BidModel 可用")
    except Exception as e:
        print(f"  ⚠ BidModel 不可用: {e}")

    try:
        import LandlordModel
        print("  ✅ LandlordModel 可用")
    except Exception as e:
        print(f"  ⚠ LandlordModel 不可用: {e}")

    try:
        import FarmerModel
        print("  ✅ FarmerModel 可用")
    except Exception as e:
        print(f"  ⚠ FarmerModel 不可用: {e}")

    # 主循环
    while True:
        print("\n" + "=" * 60)
        print("  选择操作:")
        print("  1 - 完整流程（叫牌→加倍→出牌指导）")
        print("  2 - 仅叫牌指导")
        print("  3 - 仅出牌指导（跳过叫牌/加倍）")
        print("  q - 退出")
        print("=" * 60)

        try:
            choice = input("  请选择> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  再见！👋")
            break

        if choice in ('q', 'quit', 'exit'):
            print("  再见！👋")
            break

        elif choice == '1':
            # 完整流程
            hand_cards = guide_bidding()
            if hand_cards is None:
                continue

            hand_cards_final, position, bottom_cards = guide_multiply(hand_cards)
            if hand_cards_final is None:
                continue

            guide_playing(hand_cards_final, position, bottom_cards)

        elif choice == '2':
            guide_bidding()

        elif choice == '3':
            # 仅出牌指导
            print("\n  请输入你的手牌:")
            print("  如果你是地主(20张): 3 3 4 5 6 7 8 9 T J Q K A 2 2 X D 3 K A")
            print("  如果你是农民(17张): 3 3 4 5 6 7 8 9 T J Q K A 2 2 X D")
            hand_cards = input_cards("  手牌> ")
            if hand_cards is None:
                continue

            print("\n  请输入底牌（3张）:")
            bottom_cards = input_cards("  底牌> ", 3)
            if bottom_cards is None:
                continue

            print("\n  你的角色是？")
            print("  1 - 地主 (landlord)")
            print("  2 - 地主上家 (landlord_up)")
            print("  3 - 地主下家 (landlord_down)")
            while True:
                try:
                    pos_c = input("  选择> ").strip()
                    if pos_c == '1':
                        position = 'landlord'
                        break
                    elif pos_c == '2':
                        position = 'landlord_up'
                        break
                    elif pos_c == '3':
                        position = 'landlord_down'
                        break
                    else:
                        print("  请输入 1/2/3")
                except (EOFError, KeyboardInterrupt):
                    break

            guide_playing(hand_cards, position, bottom_cards)

        else:
            print("  ❌ 无效选择")


if __name__ == '__main__':
    main()
