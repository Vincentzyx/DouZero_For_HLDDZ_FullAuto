# -*- coding: utf-8 -*-
# Created by: Vincentzyx
import os
import torch
from torch import nn
from torch.utils.data import DataLoader
from torch.utils.data.dataset import Dataset
from douzero.dmc.models import model_dict_resnet
import time
from douzero.env.game import GameEnv
from douzero.evaluation.deep_agent import DeepAgent


def EnvToOnehot(cards):
    Env2IdxMap = {3: 0, 4: 1, 5: 2, 6: 3, 7: 4, 8: 5, 9: 6, 10: 7, 11: 8, 12: 9, 13: 10, 14: 11, 17: 12, 20: 13, 30: 14}
    cards = [Env2IdxMap[i] for i in cards]
    Onehot = torch.zeros((4, 15))
    for i in range(0, 15):
        Onehot[:cards.count(i), i] = 1
    return Onehot


def RealToOnehot(cards):
    RealCard2EnvCard = {'3': 0, '4': 1, '5': 2, '6': 3, '7': 4,
                        '8': 5, '9': 6, 'T': 7, 'J': 8, 'Q': 9,
                        'K': 10, 'A': 11, '2': 12, 'X': 13, 'D': 14}
    cards = [RealCard2EnvCard[c] for c in cards]
    Onehot = torch.zeros((4, 15))
    for i in range(0, 15):
        Onehot[:cards.count(i), i] = 1
    return Onehot


class Net(nn.Module):
    def __init__(self):
        super().__init__()

        self.fc1 = nn.Linear(60, 512)
        self.fc2 = nn.Linear(512, 512)
        self.fc3 = nn.Linear(512, 512)
        self.fc4 = nn.Linear(512, 512)
        self.fc5 = nn.Linear(512, 512)
        self.fc6 = nn.Linear(512, 1)
        self.dropout5 = nn.Dropout(0.5)
        self.dropout3 = nn.Dropout(0.3)
        self.dropout1 = nn.Dropout(0.1)

    def forward(self, input):
        x = self.fc1(input)
        x = torch.relu(self.dropout3(self.fc2(x)))
        x = torch.relu(self.dropout5(self.fc3(x)))
        x = torch.relu(self.dropout5(self.fc4(x)))
        x = torch.relu(self.dropout5(self.fc5(x)))
        x = self.fc6(x)
        return x


net = Net()
net.eval()
if os.path.exists("./weights/landlord_weights.pkl"):
    if torch.cuda.is_available():
        net.load_state_dict(torch.load('./weights/landlord_weights.pkl'))
    else:
        net.load_state_dict(torch.load('./weights/landlord_weights.pkl', map_location=torch.device("cpu")))
else:
    print("landlord_weights.pkl not found")


def predict(cards):
    cards_onehot = torch.flatten(RealToOnehot(cards))
    y_predict = net(cards_onehot)
    return y_predict[0].item() * 100


ai_players = []
env = GameEnv(ai_players)


def init_model(model_path):
    global ai_players, env
    ai_players = ["landlord", DeepAgent("landlord", model_path)]
    env = GameEnv(ai_players)


def init_model2(model_path, wp_model_path):
    global ai_players, env
    ai_players = ["landlord", DeepAgent("landlord", model_path)]
    ai_players2 = ["landlord", DeepAgent("landlord", wp_model_path)]
    env = GameEnv(ai_players, ai_players2)


def predict_by_model(cards, llc):
    AllEnvCard = [3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 6, 6, 6, 6, 7, 7, 7, 7,
                  8, 8, 8, 8, 9, 9, 9, 9, 10, 10, 10, 10, 11, 11, 11, 11, 12,
                  12, 12, 12, 13, 13, 13, 13, 14, 14, 14, 14, 17, 17, 17, 17, 20, 30]
    RealCard2EnvCard = {'3': 3, '4': 4, '5': 5, '6': 6, '7': 7,
                        '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12,
                        'K': 13, 'A': 14, '2': 17, 'X': 20, 'D': 30}
    env.reset()
    other_hand_cards = []
    card_play_data_list = {}
    three_landlord_cards_env = [RealCard2EnvCard[card] for card in llc]
    user_hand_cards_env = [RealCard2EnvCard[card] for card in cards]
    three_landlord_cards_env.sort()
    user_hand_cards_env.sort()
    for i in set(AllEnvCard):
        other_hand_cards.extend([i] * (AllEnvCard.count(i) - user_hand_cards_env.count(i)))
    card_play_data_list.update({
        'three_landlord_cards': three_landlord_cards_env,
        "landlord": user_hand_cards_env,
        'landlord_up': other_hand_cards[0:17],
        'landlord_down': other_hand_cards[17:]
    })
    env.card_play_init(card_play_data_list)
    action_message, show_action_list = env.step("landlord")
    return action_message["win_rate"]
