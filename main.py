import gym
from agent import Agent
import matplotlib.pyplot as plt
import numpy as np
from play import Play
import mujoco_py
import random


ENV_NAME = "FetchPickAndPlace-v1"
INTRO = False
MAX_EPISODES = 1000
MAX_STEPS_PER_EPISODE = 500
memory_size = 100000
batch_size = 64
actor_lr = 1e-4
critic_lr = 1e-3
gamma = 0.99
tau = 0.001
k_future = 4

test_env = gym.make(ENV_NAME)
state_shape = test_env.observation_space.spaces["observation"].shape
n_actions = test_env.action_space.shape[0]
n_goals = test_env.observation_space.spaces["desired_goal"].shape[0]
action_bounds = [test_env.action_space.low[0], test_env.action_space.high[0]]

if INTRO:
    print(f"state_shape:{state_shape}\n"
          f"number of actions:{n_actions}\n"
          f"action boundaries:{action_bounds}")
    for _ in range(3):
        done = False
        test_env.reset()
        while not done:
            action = test_env.action_space.sample()
            test_state, test_reward, test_done, test_info = test_env.step(action)
            # substitute_goal = test_state["achieved_goal"].copy()
            # substitute_reward = test_env.compute_reward(
            #     test_state["achieved_goal"], substitute_goal, test_info)
            # print("r is {}, substitute_reward is {}".format(r, substitute_reward))
            test_env.render()
else:
    env = gym.make(ENV_NAME)
    agent = Agent(n_states=state_shape,
                  n_actions=n_actions,
                  n_goals=n_goals,
                  action_bounds=action_bounds,
                  capacity=memory_size,
                  action_size=n_actions,
                  batch_size=batch_size,
                  actor_lr=actor_lr,
                  critic_lr=critic_lr,
                  gamma=gamma,
                  tau=tau)
    # total_reward = 0
    global_running_r = []
    total_ac_loss = []
    total_cr_loss =[]
    for episode_num in range(MAX_EPISODES):
        agent.reset_randomness()
        env_dict = env.reset()
        state = env_dict["observation"]
        goal = env_dict["desired_goal"]
        episode_reward = 0
        ep_actor_loss = 0
        ep_critic_loss = 0
        done = False
        episode = []
        for step in range(MAX_STEPS_PER_EPISODE):
            action = agent.choose_action(state, goal)
            next_state, reward, done, _ = env.step(action)
            agent.store(state, reward, done, action, next_state["observation"], next_state["desired_goal"])
            episode.append((state, reward, done, action, next_state["observation"], next_state["achieved_goal"]))
            actor_loss, critic_loss = agent.train()
            ep_actor_loss += actor_loss
            ep_critic_loss += critic_loss
            episode_reward += reward
            if done:
                break
            state = next_state["observation"]
            goal = next_state["desired_goal"]

        for i, transition in enumerate(episode):
            state, action, reward, done, next_state, next_achieved_goal = transition
            future_transitions = random.choices(episode[i:], k=k_future)
            for future_transition in future_transitions:
                new_desired_goal = future_transition[-1]
                if (next_achieved_goal == new_desired_goal).all():
                    reward = 0
                else:
                    reward = -1

                agent.store(state, action, reward, done, next_state, new_desired_goal)

        if episode_num == 0:
            global_running_r.append(episode_reward)
        else:
            global_running_r.append(global_running_r[-1] * 0.99 + 0.01 * episode_reward)
        total_ac_loss.append(ep_actor_loss)
        total_cr_loss.append(ep_critic_loss)

        if episode_num % 100 == 0:
            print(f"EP:{episode_num}| "
                  f"EP_running_r:{global_running_r[-1]:.3f}| "
                  f"EP_reward:{episode_reward:.3f}| ")

    agent.save_weights()
    player = Play(env, agent)
    player.evaluate()

    plt.figure()
    plt.subplot(311)
    plt.plot(np.arange(0, MAX_EPISODES), global_running_r)
    plt.title("Reward")

    plt.subplot(312)
    plt.plot(np.arange(0, MAX_EPISODES), total_ac_loss)
    plt.title("Actor loss")

    plt.subplot(313)
    plt.plot(np.arange(0, MAX_EPISODES), total_cr_loss)
    plt.title("Critic loss")

    plt.show()