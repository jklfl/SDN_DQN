from helper.graph import *
import networkx as nx
from helper.util import *
import os
from helper.env import *
from DQN import *
import time
directory = "training_data"
if not os.path.exists(directory):
    os.makedirs(directory)
lwr = -1.51  
def ma():
    t0 = time.time()
    contn = "yes"
    env = link_hop_env(directory +
                       "/" + "50Nodes_wax" + ".csv",  G)
    env.graph = adjust_lat_band(env.graph, flows)
    model = Agent(env)
    model.run(10000)
    eps_run = 1000
    while contn == "yes":
        model.run(eps_run)
        inp = input("continue training?")
        sp = inp.split(" ")
        contn = sp[0]
        if len(sp) > 1:
            eps_run = int(sp[1])
    evlt = ""
    evlt = input("evaluate model?")
    if evlt == "yes":
        model.test(2000)
    model.env.graph.remove_nodes_from(nodes_to_remove)
    retrn = input("retrain?")
    while retrn == "yes":
        model.run(2000)
        retrn = input("retrain?")
    t1 = time.time()
    total = t1-t0
    print(f"{round(total/60, 2)} mins")
def spf():
    t0 = time.time()
    env = link_hop_env(directory +
                       "/" + "spf_150" + ".csv",  G)
    env.graph = adjust_lat_band(env.graph, flows)
    env.graph.remove_nodes_from(nodes_to_remove)
    good = 0
    bad = 0
    reward = 0
    for _ in range(10000):
        obs, done = env.reset(), False
        path = nx.shortest_path(env.graph, obs[0], obs[1])
        for i in range(1, len(path)):
            action = env.neighbors.index(path[i])
            obs, reward, done, infos = env.step(action)
        if reward == 1.01 or reward == lwr:
            good += 1
        else:
            bad += 1
    t1 = time.time()
    total = t1-t0
    print(f"spf {round(total/60, 2)} mins")
    print(f"spf % Routed: {good / float(good + bad)}")
def ecmp():
    t0 = time.time()
    env = link_hop_env(directory +
                       "/" + "ecmp_150" + ".csv",    G)
    env.graph.remove_nodes_from(nodes_to_remove)
    good = 0
    bad = 0
    reward = 0
    for _ in range(10_000):
        obs, done = env.reset(), False
        paths = nx.all_shortest_paths(env.graph, obs[0], obs[1])
        path = []
        b = -1
        for p in paths:
            if compute_flow_value(env.graph, tuple(p)) > b:
                b = compute_flow_value(env.graph, tuple(p))
                path = p
        for i in range(1, len(path)):
            action = env.neighbors.index(path[i])
            obs, reward, done, infos = env.step(action)
        if reward == 1.01 or reward == lwr:
            good += 1
        else:
            bad += 1
    t1 = time.time()
    total = t1-t0
    print(f"ecmp {round(total/60, 2)} mins")
    print(f"ecmp % Routed: {good / float(good + bad)}")
def best_lat():
    t0 = time.time()
    env = link_hop_env(directory +
                       "/" + "best_lat" + ".csv", G)
    env.graph = adjust_lat_band(env.graph, flows)
    env.graph.remove_nodes_from(nodes_to_remove)
    good = 0
    bad = 0
    reward = 0
    for _ in range(10_000):
        obs, done = env.reset(), False
        path = nx.astar_path(env.graph, obs[0], obs[1], weight="weight")
        for i in range(1, len(path)):
            action = env.neighbors.index(path[i])
            obs, reward, done, infos = env.step(action)
        if reward == 1.01 or reward == lwr:
            good += 1
        else:
            bad += 1
    t1 = time.time()
    total = t1-t0
    print(f"lat {round(total/60, 2)} mins")
    print(f"lat % Routed: {good / float(good + bad)}")
def genrt_flows(num_flows):
    env = link_hop_env(directory +
                       "/" + "flow_genrtr" + ".csv", G)
    flows = get_flows(env.graph, num_flows)
    return flows
G = get_graph()
flows = get_flows()
nodes_to_remove = []
ecmp()
spf()
best_lat()
ma()
