# -*- coding: utf-8 -*-
# Created by: Vincentzyx
from douzero.env.game import GameEnv
from douzero.evaluation.deep_agent import DeepAgent

RealCard2EnvCard = {'3': 3, '4': 4, '5': 5, '6': 6, '7': 7,
                    '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12,
                    'K': 13, 'A': 14, '2': 17, 'X': 20, 'D': 30}

card_play_model_path_dict = {
    'landlord': "baselines/douzero_WP/landlord.ckpt",
    'landlord_up': "baselines/douzero_WP/landlord_up.ckpt",
    'landlord_down': "baselines/douzero_WP/landlord_down.ckpt"
}

user_position = "landlord"  # 玩家角色代码：0-地主上家, 1-地主, 2-地主下家
ai_players = [0, 0]
ai_players[0] = user_position
ai_players[1] = DeepAgent(user_position, card_play_model_path_dict[user_position])

env = GameEnv(ai_players)
card_play_data_list = {}

def GetWinRate(cards):
    env.reset()
    card_play_data_list.update({
        'three_landlord_cards': [RealCard2EnvCard[i] for i in "333"],
        'landlord': [RealCard2EnvCard[i] for i in cards],
        'landlord_up': [RealCard2EnvCard[i] for i in "33333333333333333"],
        'landlord_down': [RealCard2EnvCard[i] for i in "33333333333333333"]
    })

    env.card_play_init(card_play_data_list)
    action_message = env.step(user_position)
    win_rate = float(action_message["win_rate"].replace("%",""))
    return win_rate