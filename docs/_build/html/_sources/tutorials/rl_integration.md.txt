# Reinforcement Learning Integration

This tutorial shows how to integrate SimCraft simulations with reinforcement learning frameworks.

## What You'll Learn

- Implementing the `RLInterface` for your simulation
- Defining state and action spaces
- Creating a Gym-compatible environment
- Training an RL agent

## Overview

SimCraft provides native RL integration through:

- **RLInterface**: Abstract base class for RL-compatible simulations
- **RLEnvironment**: Gym-compatible wrapper
- **ActionSpace/StateSpace**: Space definitions
- **ReplayBuffer**: Experience storage for off-policy learning

## Step 1: Define the Problem

We'll create an RL environment for a simple inventory control problem:

- **State**: Current inventory level
- **Action**: How much to order (0, 10, 20, or 30 units)
- **Reward**: Revenue minus holding and ordering costs

## Step 2: Implement RLInterface

```python
import simcraft
from simcraft.optimization import RLInterface, ActionSpace, StateSpace
import numpy as np


class InventoryRL(simcraft.Simulation, RLInterface):
    """Inventory control simulation with RL interface."""

    def __init__(self):
        simcraft.Simulation.__init__(self)
        RLInterface.__init__(self)

        # Parameters
        self.max_inventory = 100
        self.holding_cost = 0.5
        self.ordering_cost = 2.0
        self.stockout_cost = 10.0
        self.unit_revenue = 5.0

        # State
        self.inventory = 50
        self.total_reward = 0.0

        # Statistics
        self.daily_demand = simcraft.Tally()

    def on_init(self):
        """Start the simulation."""
        self.schedule(self.daily_cycle, delay=0.0)

    def daily_cycle(self):
        """Process one day: demand arrives, costs accrue."""
        # Generate demand
        demand = int(self.rng.poisson(lam=15))
        self.daily_demand.observe(demand)

        # Fulfill demand
        sold = min(demand, self.inventory)
        self.inventory -= sold
        stockout = demand - sold

        # Calculate daily reward
        revenue = sold * self.unit_revenue
        holding = self.inventory * self.holding_cost
        stockout_penalty = stockout * self.stockout_cost

        self.total_reward += revenue - holding - stockout_penalty

        # Schedule next day (this triggers decision point)
        if self.now < self.end_time:
            self.schedule(self.daily_cycle, delay=1.0)

    # ========== RLInterface Implementation ==========

    def get_state_space(self) -> StateSpace:
        """Define the state space."""
        return StateSpace(
            low=np.array([0]),
            high=np.array([self.max_inventory]),
            dtype=np.float32
        )

    def get_action_space(self) -> ActionSpace:
        """Define the action space (discrete: order 0, 10, 20, or 30)."""
        return ActionSpace(
            space_type="discrete",
            n=4  # Actions: 0, 1, 2, 3 -> order 0, 10, 20, 30
        )

    def get_state(self) -> np.ndarray:
        """Return current state observation."""
        return np.array([self.inventory], dtype=np.float32)

    def apply_action(self, action: int) -> None:
        """Apply the ordering decision."""
        order_quantity = action * 10  # Convert action to order amount
        order_cost = order_quantity * self.ordering_cost
        self.total_reward -= order_cost

        # Receive order (instant delivery for simplicity)
        self.inventory = min(self.inventory + order_quantity, self.max_inventory)

    def get_reward(self) -> float:
        """Return reward since last action."""
        reward = self.total_reward
        self.total_reward = 0.0  # Reset for next period
        return reward

    def is_done(self) -> bool:
        """Check if episode is complete."""
        return self.now >= self.end_time

    def reset_for_episode(self) -> np.ndarray:
        """Reset simulation for new episode."""
        self.reset()
        self.inventory = 50
        self.total_reward = 0.0
        self.end_time = 30  # 30-day episodes
        return self.get_state()
```

## Step 3: Create the Gym Environment

Wrap the simulation in a Gym-compatible environment:

```python
from simcraft.optimization import RLEnvironment


def create_inventory_env():
    """Create a Gym-compatible environment."""
    sim = InventoryRL()
    sim.end_time = 30

    env = RLEnvironment(
        simulation=sim,
        max_steps=30
    )
    return env
```

## Step 4: Training Loop

Here's a simple training loop (using a basic Q-learning approach):

```python
import numpy as np


def train_agent(env, num_episodes=1000, learning_rate=0.1, discount=0.99):
    """Train a simple Q-learning agent."""
    # Discretize state space into bins
    num_state_bins = 11  # 0, 10, 20, ..., 100
    num_actions = 4

    # Initialize Q-table
    q_table = np.zeros((num_state_bins, num_actions))

    # Training parameters
    epsilon = 1.0
    epsilon_decay = 0.995
    epsilon_min = 0.01

    rewards_history = []

    for episode in range(num_episodes):
        state = env.reset()
        state_bin = int(state[0] / 10)  # Discretize
        total_reward = 0
        done = False

        while not done:
            # Epsilon-greedy action selection
            if np.random.random() < epsilon:
                action = np.random.randint(num_actions)
            else:
                action = np.argmax(q_table[state_bin])

            # Take action
            next_state, reward, done, info = env.step(action)
            next_state_bin = int(min(next_state[0], 100) / 10)

            # Q-learning update
            best_next = np.max(q_table[next_state_bin])
            q_table[state_bin, action] += learning_rate * (
                reward + discount * best_next - q_table[state_bin, action]
            )

            state_bin = next_state_bin
            total_reward += reward

        rewards_history.append(total_reward)
        epsilon = max(epsilon_min, epsilon * epsilon_decay)

        if (episode + 1) % 100 == 0:
            avg_reward = np.mean(rewards_history[-100:])
            print(f"Episode {episode + 1}, Avg Reward: {avg_reward:.2f}")

    return q_table, rewards_history


if __name__ == "__main__":
    env = create_inventory_env()
    q_table, rewards = train_agent(env)

    # Print learned policy
    print("\nLearned Policy (state -> order quantity):")
    for state in range(11):
        action = np.argmax(q_table[state])
        print(f"  Inventory {state * 10}: Order {action * 10}")
```

## Using with Stable-Baselines3

For more sophisticated RL algorithms, use Stable-Baselines3:

```python
from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env


def train_with_sb3():
    """Train using Stable-Baselines3 PPO."""
    env = create_inventory_env()

    # Verify environment compatibility
    check_env(env)

    # Create and train model
    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        verbose=1
    )

    model.learn(total_timesteps=100_000)

    # Evaluate
    obs = env.reset()
    total_reward = 0
    done = False

    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, done, info = env.step(action)
        total_reward += reward

    print(f"Evaluation reward: {total_reward:.2f}")

    return model
```

## Decision Points

For more complex simulations, use `DecisionPoint` to define where actions are needed:

```python
from simcraft.optimization import DecisionPoint


class ComplexSimulation(simcraft.Simulation, RLInterface):
    def __init__(self):
        super().__init__()
        self.decision_points = []

    def on_machine_idle(self, machine):
        """Called when a machine becomes idle."""
        # Create decision point: which job to process next?
        dp = DecisionPoint(
            state=self.get_state(),
            available_actions=self.get_available_jobs(machine),
            context={"machine": machine}
        )
        self.decision_points.append(dp)
        # Wait for action from RL agent
```

## Multi-Agent RL

For multi-agent scenarios, use `MultiAgentInterface`:

```python
from simcraft.optimization import MultiAgentInterface


class MultiAgentSim(simcraft.Simulation, MultiAgentInterface):
    def get_agent_ids(self):
        return ["agent_1", "agent_2", "agent_3"]

    def get_state(self, agent_id):
        # Return agent-specific observation
        pass

    def apply_action(self, agent_id, action):
        # Apply agent-specific action
        pass
```

## Next Steps

- See [Port Terminal Example](../examples/port_terminal) for a complete RL-ready simulation
- Explore the [Optimization API](../api/optimization) for more details
- Check out [Stable-Baselines3 documentation](https://stable-baselines3.readthedocs.io/)
