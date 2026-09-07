#!/usr/bin/env python3
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import copy
import csv
import math
import os
import sys
import time
import pickle as pkl
import tqdm

from logger import Logger
from replay_buffer import ReplayBuffer
from reward_model import RewardModel
from collections import deque

import utils
import hydra

class Workspace(object):
    def __init__(self, cfg):
        self.work_dir = os.getcwd()
        print(f'workspace: {self.work_dir}')

        self.cfg = cfg
        self.logger = Logger(
            self.work_dir,
            save_tb=cfg.log_save_tb,
            log_frequency=cfg.log_frequency,
            agent=cfg.agent.name)

        utils.set_seed_everywhere(cfg.seed)
        self.device = torch.device(cfg.device)
        self.log_success = False
        
        # make env
        if 'metaworld' in cfg.env:
            self.env = utils.make_metaworld_env(cfg)
            self.log_success = True
        else:
            self.env = utils.make_env(cfg)
        
        cfg.agent.params.obs_dim = self.env.observation_space.shape[0]
        cfg.agent.params.action_dim = self.env.action_space.shape[0]
        cfg.agent.params.action_range = [
            float(self.env.action_space.low.min()),
            float(self.env.action_space.high.max())
        ]
        self.agent = hydra.utils.instantiate(cfg.agent)

        self.replay_buffer = ReplayBuffer(
            self.env.observation_space.shape,
            self.env.action_space.shape,
            int(cfg.replay_buffer_capacity),
            self.device)
        
        # for logging
        self.total_feedback = 0
        self.labeled_feedback = 0
        self.step = 0

        # Causal / frozen-window bookkeeping
        self.enable_causal_metrics = bool(cfg.enable_causal_metrics)
        self.window_id = -1
        self.window_start_step = 0
        self.reward_update_count = 0
        self._init_causal_csvs()

        # Separate env for on-policy preference accuracy (do not disturb train env).
        self.metric_env = None
        if self.enable_causal_metrics and int(cfg.onpolicy_acc_pairs) > 0:
            if 'metaworld' in cfg.env:
                self.metric_env = utils.make_metaworld_env(cfg)
            else:
                self.metric_env = utils.make_env(cfg)

        # instantiating the reward model
        self.reward_model = RewardModel(
            self.env.observation_space.shape[0],
            self.env.action_space.shape[0],
            ensemble_size=cfg.ensemble_size,
            size_segment=cfg.segment,
            activation=cfg.activation, 
            lr=cfg.reward_lr,
            mb_size=cfg.reward_batch, 
            large_batch=cfg.large_batch, 
            label_margin=cfg.label_margin, 
            teacher_beta=cfg.teacher_beta, 
            teacher_gamma=cfg.teacher_gamma, 
            teacher_eps_mistake=cfg.teacher_eps_mistake, 
            teacher_eps_skip=cfg.teacher_eps_skip, 
            teacher_eps_equal=cfg.teacher_eps_equal,
            val_fraction=cfg.val_fraction,
            fixed_ref_size=cfg.fixed_ref_size)
        
    def _init_causal_csvs(self):
        self.window_csv_path = os.path.join(self.work_dir, 'causal_window.csv')
        self.reward_csv_path = os.path.join(self.work_dir, 'reward_update_metrics.csv')
        if not self.enable_causal_metrics:
            return
        with open(self.window_csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'step', 'episode', 'window_id', 'step_in_window',
                'proxy_return', 'true_return', 'total_feedback',
            ])
            writer.writeheader()
        with open(self.reward_csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'step', 'window_id', 'reward_update_count', 'total_feedback',
                'labeled_feedback', 'train_fit_acc',
                'acc_train', 'acc_heldout', 'acc_onpolicy', 'acc_fixed_ref',
            ])
            writer.writeheader()

    def _append_csv(self, path, row):
        with open(path, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(row.keys()))
            writer.writerow(row)

    def evaluate(self):
        average_episode_reward = 0
        average_true_episode_reward = 0
        success_rate = 0
        
        for episode in range(self.cfg.num_eval_episodes):
            obs = self.env.reset()
            self.agent.reset()
            done = False
            episode_reward = 0
            true_episode_reward = 0
            if self.log_success:
                episode_success = 0

            while not done:
                with utils.eval_mode(self.agent):
                    action = self.agent.act(obs, sample=False)
                next_obs, reward, done, extra = self.env.step(action)
                reward_hat = self.reward_model.r_hat(
                    np.concatenate([obs, action], axis=-1))

                episode_reward += reward_hat
                true_episode_reward += reward
                if self.log_success:
                    episode_success = max(episode_success, extra['success'])
                obs = next_obs
                
            average_episode_reward += episode_reward
            average_true_episode_reward += true_episode_reward
            if self.log_success:
                success_rate += episode_success
            
        average_episode_reward /= self.cfg.num_eval_episodes
        average_true_episode_reward /= self.cfg.num_eval_episodes
        if self.log_success:
            success_rate /= self.cfg.num_eval_episodes
            success_rate *= 100.0
        
        self.logger.log('eval/episode_reward', average_episode_reward,
                        self.step)
        self.logger.log('eval/true_episode_reward', average_true_episode_reward,
                        self.step)
        if self.log_success:
            self.logger.log('eval/success_rate', success_rate,
                    self.step)
            self.logger.log('train/true_episode_success', success_rate,
                        self.step)
        self.logger.dump(self.step)

    def measure_onpolicy_acc(self):
        """Roll out current policy on metric_env; oracle-label; score frozen RM."""
        n_pairs = int(self.cfg.onpolicy_acc_pairs)
        n_episodes = int(self.cfg.onpolicy_acc_episodes)
        if n_pairs <= 0 or n_episodes <= 0 or self.metric_env is None:
            return float('nan')

        segment = int(self.cfg.segment)
        traj_sa = []
        traj_r = []
        for _ in range(n_episodes):
            obs = self.metric_env.reset()
            self.agent.reset()
            done = False
            episode_step = 0
            sa_steps = []
            r_steps = []
            while not done:
                with utils.eval_mode(self.agent):
                    action = self.agent.act(obs, sample=False)
                next_obs, reward, done, _extra = self.metric_env.step(action)
                sa_steps.append(np.concatenate([obs, action], axis=-1))
                r_steps.append([reward])
                obs = next_obs
                episode_step += 1
                if episode_step >= self.metric_env._max_episode_steps:
                    break
            if len(sa_steps) >= segment:
                traj_sa.append(np.asarray(sa_steps, dtype=np.float32))
                traj_r.append(np.asarray(r_steps, dtype=np.float32))

        if len(traj_sa) < 2:
            return float('nan')

        # Match get_queries: require equal-length trajs; truncate to min length.
        min_len = min(len(t) for t in traj_sa)
        if min_len < segment:
            return float('nan')
        traj_sa = [t[:min_len] for t in traj_sa]
        traj_r = [t[:min_len] for t in traj_r]
        train_inputs = np.stack(traj_sa, axis=0)
        train_targets = np.stack(traj_r, axis=0)
        max_len = train_inputs.shape[0]

        batch_index_1 = np.random.choice(max_len, size=n_pairs, replace=True)
        batch_index_2 = np.random.choice(max_len, size=n_pairs, replace=True)
        sa_t_1 = train_inputs[batch_index_1]
        r_t_1 = train_targets[batch_index_1]
        sa_t_2 = train_inputs[batch_index_2]
        r_t_2 = train_targets[batch_index_2]

        time_index = np.array([
            list(range(i * min_len, i * min_len + segment)) for i in range(n_pairs)
        ])
        max_start = min_len - segment
        time_index_1 = time_index + np.random.choice(
            max_start + 1, size=n_pairs, replace=True).reshape(-1, 1)
        time_index_2 = time_index + np.random.choice(
            max_start + 1, size=n_pairs, replace=True).reshape(-1, 1)

        sa_flat_1 = sa_t_1.reshape(-1, sa_t_1.shape[-1])
        r_flat_1 = r_t_1.reshape(-1, r_t_1.shape[-1])
        sa_flat_2 = sa_t_2.reshape(-1, sa_t_2.shape[-1])
        r_flat_2 = r_t_2.reshape(-1, r_t_2.shape[-1])
        sa_t_1 = np.take(sa_flat_1, time_index_1, axis=0)
        r_t_1 = np.take(r_flat_1, time_index_1, axis=0)
        sa_t_2 = np.take(sa_flat_2, time_index_2, axis=0)
        r_t_2 = np.take(r_flat_2, time_index_2, axis=0)

        sa_t_1, sa_t_2, r_t_1, r_t_2, labels = self.reward_model.get_oracle_label(
            sa_t_1, sa_t_2, r_t_1, r_t_2)
        if labels is None or len(labels) == 0:
            return float('nan')
        return self.reward_model.preference_accuracy(sa_t_1, sa_t_2, labels)

    def log_reward_update_metrics(self, train_fit_acc):
        """Accuracy suite + checkpoints immediately after each RM update."""
        self.reward_update_count += 1
        self.window_id += 1
        self.window_start_step = self.step

        if self.enable_causal_metrics:
            self.reward_model.maybe_init_fixed_reference()

            acc_train = self.reward_model.get_train_acc()
            acc_heldout = self.reward_model.get_heldout_acc()
            acc_onpolicy = self.measure_onpolicy_acc()
            acc_fixed_ref = self.reward_model.get_fixed_ref_acc()

            metrics = {
                'step': self.step,
                'window_id': self.window_id,
                'reward_update_count': self.reward_update_count,
                'total_feedback': self.total_feedback,
                'labeled_feedback': self.labeled_feedback,
                'train_fit_acc': float(np.mean(train_fit_acc)) if np.ndim(train_fit_acc) else float(train_fit_acc),
                'acc_train': acc_train,
                'acc_heldout': acc_heldout,
                'acc_onpolicy': acc_onpolicy,
                'acc_fixed_ref': acc_fixed_ref,
            }
            self._append_csv(self.reward_csv_path, metrics)

            # Log into meters for TB/console on the next train dump; do not dump here
            # (avoids mid-episode train.csv rows and CSV schema races).
            for key, value in [
                ('train/window_id', self.window_id),
                ('train/reward_acc_train', acc_train),
                ('train/reward_acc_heldout', acc_heldout),
                ('train/reward_acc_onpolicy', acc_onpolicy),
                ('train/reward_acc_fixed_ref', acc_fixed_ref),
            ]:
                if value == value:  # skip NaN
                    self.logger.log(key, value, self.step, log_frequency=1)

            def _fmt(x):
                return 'nan' if x != x else f'{x:.4f}'

            print(
                f"[causal] RM update #{self.reward_update_count} step={self.step} "
                f"window={self.window_id} "
                f"acc_train={_fmt(acc_train)} acc_heldout={_fmt(acc_heldout)} "
                f"acc_onpolicy={_fmt(acc_onpolicy)} acc_fixed_ref={_fmt(acc_fixed_ref)}"
            )

        if self.cfg.save_rm_every_update:
            ckpt_dir = os.path.join(self.work_dir, 'checkpoints')
            os.makedirs(ckpt_dir, exist_ok=True)
            self.reward_model.save(ckpt_dir, self.step)
            self.agent.save(ckpt_dir, self.step)
    
    def learn_reward(self, first_flag=0):
                
        # get feedbacks
        labeled_queries, noisy_queries = 0, 0
        if first_flag == 1:
            # if it is first time to get feedback, need to use random sampling
            labeled_queries = self.reward_model.uniform_sampling()
        else:
            if self.cfg.feed_type == 0:
                labeled_queries = self.reward_model.uniform_sampling()
            elif self.cfg.feed_type == 1:
                labeled_queries = self.reward_model.disagreement_sampling()
            elif self.cfg.feed_type == 2:
                labeled_queries = self.reward_model.entropy_sampling()
            elif self.cfg.feed_type == 3:
                labeled_queries = self.reward_model.kcenter_sampling()
            elif self.cfg.feed_type == 4:
                labeled_queries = self.reward_model.kcenter_disagree_sampling()
            elif self.cfg.feed_type == 5:
                labeled_queries = self.reward_model.kcenter_entropy_sampling()
            else:
                raise NotImplementedError
        
        self.total_feedback += self.reward_model.mb_size
        self.labeled_feedback += labeled_queries
        
        train_acc = 0
        total_acc = 0
        if self.labeled_feedback > 0:
            # update reward
            for epoch in range(self.cfg.reward_update):
                if self.cfg.label_margin > 0 or self.cfg.teacher_eps_equal > 0:
                    train_acc = self.reward_model.train_soft_reward()
                else:
                    train_acc = self.reward_model.train_reward()
                total_acc = np.mean(train_acc)
                
                if total_acc > 0.97:
                    break
                    
        print("Reward function is updated!! ACC: " + str(total_acc))
        self.log_reward_update_metrics(total_acc)

    def run(self):
        episode, episode_reward, done = 0, 0, True
        if self.log_success:
            episode_success = 0
        true_episode_reward = 0
        
        # store train returns of recent 10 episodes
        avg_train_true_return = deque([], maxlen=10) 
        start_time = time.time()

        interact_count = 0
        while self.step < self.cfg.num_train_steps:
            if done:
                if self.step > 0:
                    self.logger.log('train/duration', time.time() - start_time, self.step)
                    start_time = time.time()
                    self.logger.dump(
                        self.step, save=(self.step > self.cfg.num_seed_steps))

                # evaluate agent periodically
                if self.step > 0 and self.step % self.cfg.eval_frequency == 0:
                    self.logger.log('eval/episode', episode, self.step)
                    self.evaluate()
                
                self.logger.log('train/episode_reward', episode_reward, self.step)
                self.logger.log('train/true_episode_reward', true_episode_reward, self.step)
                self.logger.log('train/total_feedback', self.total_feedback, self.step)
                self.logger.log('train/labeled_feedback', self.labeled_feedback, self.step)
                if self.enable_causal_metrics:
                    step_in_window = self.step - self.window_start_step
                    self.logger.log('train/window_id', self.window_id, self.step)
                    self.logger.log('train/step_in_window', step_in_window, self.step)
                    self._append_csv(self.window_csv_path, {
                        'step': self.step,
                        'episode': episode,
                        'window_id': self.window_id,
                        'step_in_window': step_in_window,
                        'proxy_return': episode_reward,
                        'true_return': true_episode_reward,
                        'total_feedback': self.total_feedback,
                    })
                
                if self.log_success:
                    self.logger.log('train/episode_success', episode_success,
                        self.step)
                    self.logger.log('train/true_episode_success', episode_success,
                        self.step)
                
                obs = self.env.reset()
                self.agent.reset()
                done = False
                episode_reward = 0
                avg_train_true_return.append(true_episode_reward)
                true_episode_reward = 0
                if self.log_success:
                    episode_success = 0
                episode_step = 0
                episode += 1

                self.logger.log('train/episode', episode, self.step)
                        
            # sample action for data collection
            if self.step < self.cfg.num_seed_steps:
                action = self.env.action_space.sample()
            else:
                with utils.eval_mode(self.agent):
                    action = self.agent.act(obs, sample=True)

            # run training update                
            if self.step == (self.cfg.num_seed_steps + self.cfg.num_unsup_steps):
                # update schedule
                if self.cfg.reward_schedule == 1:
                    frac = (self.cfg.num_train_steps-self.step) / self.cfg.num_train_steps
                    if frac == 0:
                        frac = 0.01
                elif self.cfg.reward_schedule == 2:
                    frac = self.cfg.num_train_steps / (self.cfg.num_train_steps-self.step +1)
                else:
                    frac = 1
                self.reward_model.change_batch(frac)
                
                # update margin --> not necessary / will be updated soon
                new_margin = np.mean(avg_train_true_return) * (self.cfg.segment / self.env._max_episode_steps)
                self.reward_model.set_teacher_thres_skip(new_margin)
                self.reward_model.set_teacher_thres_equal(new_margin)
                
                # first learn reward
                self.learn_reward(first_flag=1)
                
                # relabel buffer
                self.replay_buffer.relabel_with_predictor(self.reward_model)
                
                # reset Q due to unsuperivsed exploration
                self.agent.reset_critic()
                
                # update agent
                self.agent.update_after_reset(
                    self.replay_buffer, self.logger, self.step, 
                    gradient_update=self.cfg.reset_update, 
                    policy_update=True)
                
                # reset interact_count
                interact_count = 0
            elif self.step > self.cfg.num_seed_steps + self.cfg.num_unsup_steps:
                # update reward function
                if self.total_feedback < self.cfg.max_feedback:
                    if interact_count == self.cfg.num_interact:
                        # update schedule
                        if self.cfg.reward_schedule == 1:
                            frac = (self.cfg.num_train_steps-self.step) / self.cfg.num_train_steps
                            if frac == 0:
                                frac = 0.01
                        elif self.cfg.reward_schedule == 2:
                            frac = self.cfg.num_train_steps / (self.cfg.num_train_steps-self.step +1)
                        else:
                            frac = 1
                        self.reward_model.change_batch(frac)
                        
                        # update margin --> not necessary / will be updated soon
                        new_margin = np.mean(avg_train_true_return) * (self.cfg.segment / self.env._max_episode_steps)
                        self.reward_model.set_teacher_thres_skip(new_margin * self.cfg.teacher_eps_skip)
                        self.reward_model.set_teacher_thres_equal(new_margin * self.cfg.teacher_eps_equal)
                        
                        # corner case: new total feed > max feed
                        if self.reward_model.mb_size + self.total_feedback > self.cfg.max_feedback:
                            self.reward_model.set_batch(self.cfg.max_feedback - self.total_feedback)
                            
                        self.learn_reward()
                        self.replay_buffer.relabel_with_predictor(self.reward_model)
                        interact_count = 0
                        
                self.agent.update(self.replay_buffer, self.logger, self.step, 1)
                
            # unsupervised exploration
            elif self.step > self.cfg.num_seed_steps:
                self.agent.update_state_ent(self.replay_buffer, self.logger, self.step, 
                                            gradient_update=1, K=self.cfg.topK)
                
            next_obs, reward, done, extra = self.env.step(action)
            reward_hat = self.reward_model.r_hat(np.concatenate([obs, action], axis=-1))

            # allow infinite bootstrap
            done = float(done)
            done_no_max = 0 if episode_step + 1 == self.env._max_episode_steps else done
            episode_reward += reward_hat
            true_episode_reward += reward
            
            if self.log_success:
                episode_success = max(episode_success, extra['success'])
                
            # adding data to the reward training data
            self.reward_model.add_data(obs, action, reward, done)
            self.replay_buffer.add(
                obs, action, reward_hat, 
                next_obs, done, done_no_max)

            obs = next_obs
            episode_step += 1
            self.step += 1
            interact_count += 1
            
        self.agent.save(self.work_dir, self.step)
        self.reward_model.save(self.work_dir, self.step)
        
@hydra.main(config_path='config/train_PEBBLE.yaml', strict=True)
def main(cfg):
    workspace = Workspace(cfg)
    workspace.run()

if __name__ == '__main__':
    main()
