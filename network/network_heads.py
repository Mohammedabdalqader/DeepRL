#######################################################################
# Copyright (C) 2017 Shangtong Zhang(zhangshangtong.cpp@gmail.com)    #
# Permission given to modify the code as long as you keep this        #
# declaration at the top                                              #
#######################################################################

from .network_utils import *

class VanillaNet(nn.Module, BaseNet):
    def __init__(self, output_dim, body, gpu=-1):
        super(VanillaNet, self).__init__()
        self.fc_head = layer_init(nn.Linear(body.feature_dim, output_dim))
        self.body = body
        self.set_gpu(gpu)

    def predict(self, x, to_numpy=False):
        phi = self.body(self.tensor(x))
        y = self.fc_head(phi)
        if to_numpy:
            y = y.cpu().detach().numpy()
        return y

class DuelingNet(nn.Module, BaseNet):
    def __init__(self, action_dim, body, gpu=-1):
        super(DuelingNet, self).__init__()
        self.fc_value = layer_init(nn.Linear(body.feature_dim, 1))
        self.fc_advantage = layer_init(nn.Linear(body.feature_dim, action_dim))
        self.body = body
        self.set_gpu(gpu)

    def predict(self, x, to_numpy=False):
        phi = self.body(self.tensor(x))
        value = self.fc_value(phi)
        advantange = self.fc_advantage(phi)
        q = value.expand_as(advantange) + (advantange - advantange.mean(1, keepdim=True).expand_as(advantange))
        if to_numpy:
            return q.cpu().detach().numpy()
        return q

class ActorCriticNet(nn.Module, BaseNet):
    def __init__(self, action_dim, body, gpu=-1):
        super(ActorCriticNet, self).__init__()
        self.fc_actor = layer_init(nn.Linear(body.feature_dim, action_dim))
        self.fc_critic = layer_init(nn.Linear(body.feature_dim, 1))
        self.body = body
        self.set_gpu(gpu)

    def predict(self, x, to_numpy=False):
        phi = self.body(self.tensor(x))
        pre_prob = self.fc_actor(phi)
        prob = F.softmax(pre_prob, dim=1)
        log_prob = F.log_softmax(pre_prob, dim=1)
        value = self.fc_critic(phi)
        if to_numpy:
            return prob.cpu().detach().numpy()
        return prob, log_prob, value

class CategoricalNet(nn.Module, BaseNet):
    def __init__(self, action_dim, num_atoms, body, gpu=-1):
        super(CategoricalNet, self).__init__()
        self.fc_categorical = layer_init(nn.Linear(body.feature_dim, action_dim * num_atoms))
        self.action_dim = action_dim
        self.num_atoms = num_atoms
        self.body = body
        self.set_gpu(gpu)

    def predict(self, x, to_numpy=False):
        phi = self.body(self.tensor(x))
        pre_prob = self.fc_categorical(phi).view((-1, self.action_dim, self.num_atoms))
        prob = F.softmax(pre_prob, dim=-1)
        if to_numpy:
            return prob.cpu().detach().numpy()
        return prob

class QuantileNet(nn.Module, BaseNet):
    def __init__(self, action_dim, num_quantiles, body, gpu=-1):
        super(QuantileNet, self).__init__()
        self.fc_quantiles = layer_init(nn.Linear(body.feature_dim, action_dim * num_quantiles))
        self.action_dim = action_dim
        self.num_quantiles = num_quantiles
        self.body = body
        self.set_gpu(gpu)

    def predict(self, x, to_numpy=False):
        phi = self.body(self.tensor(x))
        quantiles = self.fc_quantiles(phi)
        quantiles = quantiles.view((-1, self.action_dim, self.num_quantiles))
        if to_numpy:
            quantiles = quantiles.cpu().detach().numpy()
        return quantiles

class GaussianActorNet(nn.Module, BaseNet):
    def __init__(self, action_dim, body, gpu=-1):
        super(GaussianActorNet, self).__init__()
        self.fc_action = layer_init(nn.Linear(body.feature_dim, action_dim), 3e-3)
        self.action_log_std = nn.Parameter(torch.zeros(1, action_dim))
        self.body = body
        self.set_gpu(gpu)

    def predict(self, x):
        x = self.tensor(x)
        phi = self.body(x)
        mean = F.tanh(self.fc_action(phi))
        log_std = self.action_log_std.expand_as(mean)
        std = log_std.exp()
        return mean, std, log_std

class GaussianCriticNet(nn.Module, BaseNet):
    def __init__(self, body, gpu=-1):
        super(GaussianCriticNet, self).__init__()
        self.fc_value = layer_init(nn.Linear(body.feature_dim, 1), 3e-3)
        self.body = body
        self.set_gpu(gpu)

    def predict(self, x):
        x = self.tensor(x)
        phi = self.body(x)
        value = self.fc_value(phi)
        return value

class DeterministicActorNet(nn.Module, BaseNet):
    def __init__(self, action_dim, body, gpu=-1):
        super(DeterministicActorNet, self).__init__()
        self.fc_action = layer_init(nn.Linear(body.feature_dim, action_dim), 3e-3)
        self.body = body
        self.set_gpu(gpu)

    def predict(self, x, to_numpy=False):
        x = self.tensor(x)
        phi = self.body(x)
        a = F.tanh(self.fc_action(phi))
        if to_numpy:
            a = a.cpu().detach().numpy()
        return a

class DeterministicCriticNet(nn.Module, BaseNet):
    def __init__(self, body, gpu=-1):
        super(DeterministicCriticNet, self).__init__()
        self.fc_value = layer_init(nn.Linear(body.feature_dim, 1), 3e-3)
        self.body = body
        self.set_gpu(gpu)

    def predict(self, x, action):
        x = self.tensor(x)
        action = self.tensor(action)
        phi = self.body(x, action)
        value = self.fc_value(phi)
        return value

from .network_bodies import *
class SharedDeterministicNet(nn.Module, BaseNet):
    def __init__(self, state_dim, action_dim, discount, detach_action=False, gate=F.tanh, gpu=-1):
        super(SharedDeterministicNet, self).__init__()

        self.actor_body = FCBody(state_dim, (300, 200), gate=gate)
        self.critic_body = TwoLayerFCBodyWithAction(state_dim, action_dim, (400, 300), gate=gate)

        self.fc_action = layer_init(nn.Linear(self.actor_body.feature_dim, action_dim), 3e-3)
        self.fc_critic = layer_init(nn.Linear(self.critic_body.feature_dim, 1), 3e-3)

        self.fc_reward = layer_init(nn.Linear(self.critic_body.feature_dim, 1), 3e-3)
        self.fc_transition = layer_init(nn.Linear(self.critic_body.feature_dim, state_dim))
        self.discount = discount
        self.detach_action = detach_action

        self.set_gpu(gpu)

    def actor(self, x):
        x = self.tensor(x)
        x = self.actor_body(x)
        a = F.tanh(self.fc_action(x))
        return a

    def critic(self, x, a, lam=0):
        x = self.tensor(x)
        a = self.tensor(a)
        phi = self.critic_body(x, a)
        q0 = self.fc_critic(phi)
        r = self.fc_reward(phi)

        s_prime = x + F.tanh(self.fc_transition(phi))
        a_prime = self.actor(s_prime)
        if self.detach_action:
            a_prime = a_prime.detach()
        phi_prime = self.critic_body(s_prime, a_prime)
        q_prime = self.fc_critic(phi_prime)
        q1 = r + self.discount * q_prime
        q = lam * q0 + (1 - lam) * q1
        return q, r

class SharedDeterministicNetv2(nn.Module, BaseNet):
    def __init__(self, state_dim, action_dim, discount, detach_action=False, gate=F.tanh, gpu=-1):
        super(SharedDeterministicNetv2, self).__init__()
        self.abstract_state_dim = 400
        self.hidden_q_dim = 300
        self.hidden_a_dim = 300

        self.fc_abstract_state = layer_init(nn.Linear(state_dim, self.abstract_state_dim))
        self.fc_q1 = layer_init(nn.Linear(
            self.abstract_state_dim + action_dim, self.hidden_q_dim))
        self.fc_q2 = layer_init(nn.Linear(self.hidden_q_dim, 1), 3e-3)

        self.fc_a1 = layer_init(nn.Linear(self.abstract_state_dim, self.hidden_a_dim))
        self.fc_a2 = layer_init(nn.Linear(self.hidden_a_dim, action_dim), 3e-3)

        # self.actor_body = FCBody(state_dim, (300, 200), gate=gate)
        # self.critic_body = TwoLayerFCBodyWithAction(state_dim, action_dim, (400, 300), gate=gate)
        #
        # self.fc_action = layer_init(nn.Linear(self.actor_body.feature_dim, action_dim), 3e-3)
        # self.fc_critic = layer_init(nn.Linear(self.critic_body.feature_dim, 1), 3e-3)
        #
        # self.fc_reward = layer_init(nn.Linear(self.critic_body.feature_dim, 1), 3e-3)
        # self.fc_transition = layer_init(nn.Linear(self.critic_body.feature_dim, state_dim))

        self.gate = gate
        # self.discount = discount
        # self.detach_action = detach_action

        self.set_gpu(gpu)

    def actor(self, obs):
        obs = self.tensor(obs)
        s = F.tanh(self.fc_abstract_state(obs))
        a = F.tanh(self.fc_a1(s))
        a = F.tanh(self.fc_a2(a))
        return a

    def critic(self, obs, a, lam=0):
        obs = self.tensor(obs)
        a = self.tensor(a)
        s = F.tanh(self.fc_abstract_state(obs))
        phi = torch.cat([s, a], dim=1)
        q = F.tanh(self.fc_q1(phi))
        q = self.fc_q2(q)
        return q, 0
        # x = self.tensor(x)
        # a = self.tensor(a)
        # phi = self.critic_body(x, a)
        # q0 = self.fc_critic(phi)
        # r = self.fc_reward(phi)
        #
        # s_prime = x + F.tanh(self.fc_transition(phi))
        # a_prime = self.actor(s_prime)
        # if self.detach_action:
        #     a_prime = a_prime.detach()
        # phi_prime = self.critic_body(s_prime, a_prime)
        # q_prime = self.fc_critic(phi_prime)
        # q1 = r + self.discount * q_prime
        # q = lam * q0 + (1 - lam) * q1
        # return q, r
