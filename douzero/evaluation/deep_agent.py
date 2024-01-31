import torch
import numpy as np

from douzero.env.env import get_obs


def _load_model(position, model_path, model_type):
    from douzero.dmc.models import model_dict, model_dict_resnet, model_dict_general
    # print(position, "loads", model_type, "model: ", model_path)
    if model_type == "general":
        model = model_dict_general[position]()
    elif model_type == "resnet":
        model = model_dict_resnet[position]()
    else:
        model = model_dict[position]()
    model_state_dict = model.state_dict()
    if torch.cuda.is_available():
        pretrained = torch.load(model_path, map_location='cuda:0')
    else:
        pretrained = torch.load(model_path, map_location='cpu')
    pretrained = {k: v for k, v in pretrained.items() if k in model_state_dict}
    model_state_dict.update(pretrained)
    model.load_state_dict(model_state_dict)
    if torch.cuda.is_available():
        model.cuda()
    model.eval()
    return model


class DeepAgent:

    def __init__(self, position, model_path):
        self.model_type = "old"
        if "general" in model_path:
            self.model_type = "general"
        elif "resnet" in model_path:
            self.model_type = "resnet"
        self.model = _load_model(position, model_path, self.model_type)

    def act(self, infoset):
        # 只有一个合法动作时直接返回，这样会得不到胜率信息
        # if len(infoset.legal_actions) == 1:
        #     return infoset.legal_actions[0], 0

        obs = get_obs(infoset, model_type=self.model_type)
        z_batch = torch.from_numpy(obs['z_batch']).float()
        x_batch = torch.from_numpy(obs['x_batch']).float()
        if torch.cuda.is_available():
            z_batch, x_batch = z_batch.cuda(), x_batch.cuda()
        y_pred = self.model.forward(z_batch, x_batch, return_value=True)['values']
        y_pred = y_pred.detach().cpu().numpy()

        best_action_index = np.argmax(y_pred, axis=0)[0]
        best_action = infoset.legal_actions[best_action_index]
        best_action_confidence = y_pred[best_action_index]
        action_list = [(infoset.legal_actions[i], y_pred[i]) for i in range(len(infoset.legal_actions))]
        return best_action, best_action_confidence, action_list
