import math
import random
import numpy as np
import matplotlib.pyplot as plt
from collections import namedtuple
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
torch.backends.cudnn.benchmark = True
Transition = namedtuple('Transition',
                        ('state', 'action', 'next_state', 'reward'))
class ReplayMemory(object):
    def __init__(self, capacity):
        self.capacity = capacity
        self.memory = []
        self.position = 0
    def push(self, *args):
        """Saves a transition."""
        if len(self.memory) < self.capacity:
            self.memory.append(None)
        self.memory[self.position] = Transition(*args)
        self.position = (self.position + 1) % self.capacity
    def sample(self, batch_size):
        return random.sample(self.memory, batch_size)
    def __len__(self):
        return len(self.memory)
class DQN(nn.Module):
    def __init__(self, inputs, outputs):
        super(DQN, self).__init__()
        val = int((inputs+outputs)/2)
        self.fc1 = nn.Linear(inputs, val)
        self.fc2 = nn.Linear(val, val)
        self.fc3 = nn.Linear(val, val)
        self.fc4 = nn.Linear(val,  outputs)
    def forward(self, x):
        x = x.float()
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = F.relu(self.fc3(x))
        x = self.fc4(x)
        return F.log_softmax(x, dim=1)
BATCH_SIZE = 64*3
Alpha = 0.999
GAMMA = 0.999
Belta = 0.999
EPS_START = 1
EPS_END = 0
EPS_DECAY = 1000
TARGET_UPDATE = 1
STEP_MULTIPLIER = 400
class Agent():
    def __init__(self, inputs, outputs):
        self.n_actions = outputs
        self.policy_net = DQN(inputs, outputs).to(device)
        self.target_net = DQN(inputs, outputs).to(device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()
        self.optimizer = optim.RMSprop(self.policy_net.parameters())
        self.memory = ReplayMemory(4000)
        self.steps_done = 0
        self.episode_durations = []
        self.lossDat = []
        self.steps = 0
        self.eps = .9
    def select_action(self,        state):
        sample = random.random()
        eps_threshold = EPS_END + (EPS_START - EPS_END) * \
            math.exp(-1. * self.steps_done / EPS_DECAY)
        self.steps_done += STEP_MULTIPLIER
        if sample > eps_threshold:
            with torch.no_grad():
                return self.policy_net(state).max(1)[1].view(1, 1)
        else:
            return torch.as_tensor([[random.randrange(self.n_actions)]], device=device, dtype=torch.long)
    def predict(self, state):
        sample = random.random()
        eps_threshold = EPS_END + (EPS_START - EPS_END) * \
            math.exp(-1. * self.steps_done / EPS_DECAY)
        if sample > eps_threshold:
            with torch.no_grad():
                return self.policy_net(state).max(1)[1].view(1, 1)
        else:
            return torch.as_tensor([[random.randrange(self.n_actions)]], device=device, dtype=torch.long)
    def optimize_model(self):
        if len(self.memory) < BATCH_SIZE:
            return
        transitions = self.memory.sample(BATCH_SIZE)
        batch = Transition(*zip(*transitions))
        non_final_mask = torch.as_tensor(tuple(map(lambda s: s is not None,
                                                   batch.next_state)), device=device, dtype=torch.bool)
        non_final_next_states = torch.cat([s for s in batch.next_state
                                           if s is not None])
        state_batch = torch.cat(batch.state)
        action_batch = torch.cat(batch.action)
        reward_batch = torch.cat(batch.reward)
        state_action_values = self.policy_net(
            state_batch).gather(1, action_batch)
        next_state_values = torch.zeros(BATCH_SIZE, device=device)
        next_state_values[non_final_mask] = self.target_net(
            non_final_next_states).max(1)[0].detach()
        expected_state_action_values = (
            next_state_values * GAMMA) + reward_batch
        loss = F.smooth_l1_loss(state_action_values,
                                expected_state_action_values.unsqueeze(1))
        self.optimizer.zero_grad()
        loss.backward()
        for param in self.policy_net.parameters():
            param.grad.data.clamp_(-1, 1)
        self.optimizer.step()
class Agent():
    def __init__(self, env):
        self.env = env
        self.num_agents = int(self.env.observation_space.nvec[0])
        self.agents = []
        self.nodes = list(self.env.graph.nodes)
        self.initialize()
        global EPS_DECAY
        EPS_DECAY = EPS_DECAY * self.num_agents
    def initialize(self):
        for i in range(len(self.nodes)):
            self.agents.append(Agent(
                self.num_agents, len(list(self.env.graph.neighbors(self.nodes[i])))))
    def _format_input(self, input):
        '''Given destination:int return one hot destination'''
        try:
            arr = np.zeros(shape=(1, self.num_agents))
            arr[0][self.nodes.index(input)] = 1
            arr = torch.from_numpy(arr)
        except Exception as e:
            print("error:", input, arr, e)
        return arr
    def run(self, episodes=100):
        for i in range(episodes):
            obs, done = self.env.reset(), False
            curr_agent = self.nodes.index(obs[0])
            state = self._format_input(obs[1])
            rews = 0
            while not done:
                action = self.agents[curr_agent].select_action(state)
                obs, reward, done, infos = self.env.step(action.item())
                rews += reward
                reward = torch.as_tensor([reward], device=device)
                if not done:
                    next_state = self._format_input(obs[1])
                else:
                    next_state = None
                self.agents[curr_agent].memory.push(
                    state, action, next_state, reward)
                state = next_state
                self.agents[curr_agent].optimize_model()
                curr_agent = self.nodes.index(obs[0])
            if i % TARGET_UPDATE == 0:
                for j in range(len(self.agents)):
                    self.agents[j].target_net.load_state_dict(
                        self.agents[j].policy_net.state_dict())
            if i % 100 == 0:
                print(i, rews)
    def test(self, num_episodes=350):
        good = 0
        bad = 0
        for _ in range(num_episodes):
            obs, done = self.env.reset(), False
            curr_node = obs[0]
            curr_agent = self.nodes.index(obs[0])
            obs = self._format_input(obs[1])
            rews = 0
            while not done:
                with torch.no_grad():
                    action = self.agents[curr_agent].predict(obs)
                    while action >= len(list(self.env.graph.neighbors(curr_node))):
                        action = torch.as_tensor(
                            [[random.randint(0, len(list(self.env.graph.neighbors(curr_node)))-1)]])
                    obs, reward, done, infos = self.env.step(action.item())
                    rews += reward
                    curr_node = obs[0]
                    curr_agent = self.nodes.index(obs[0])
                    obs = self._format_input(obs[1])
            if reward == 1.01 or reward == -1.51:
                good += 1
            else:
                bad += 1
        print(f"%dqn Routed: {good / float(good + bad)} {good} {bad}")
