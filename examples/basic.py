import time
import random
import argparse

from rich.progress import track
from rich.console import Console

console = Console()

from inspirai_fps import Game, ActionVariable
from inspirai_fps.utils import get_position


parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default=50051)
parser.add_argument("--timeout", type=int, default=10)
parser.add_argument("--game-mode", type=int, default=0)
parser.add_argument("--random-seed", type=int, default=0)
parser.add_argument("--num-episodes", type=int, default=1)
parser.add_argument("--map-id", type=int, default=1)
parser.add_argument("--map-dir", type=str, default="../map_data")
parser.add_argument("--engine-dir", type=str, default="../unity3d")
parser.add_argument("--use-depth-map", action="store_true")
parser.add_argument("--random-start-location", action="store_true")
parser.add_argument("--num-agents", type=int, default=1)
parser.add_argument("--record", action="store_true")
parser.add_argument("--replay-suffix", type=str, default="")
parser.add_argument("--start-location", type=float, nargs=3, default=[0, 0, 0])
parser.add_argument("--target-location", type=float, nargs=3, default=[5, 0, 5])
args = parser.parse_args()
console.print(args)


def my_policy(state):
    """Define a random policy"""
    return [
        random.randint(0, 360),  # walk_dir
        random.randint(1, 10),  # walk_speed
        random.choice([-1, 0, 1]),  # turn_lr_delta
        random.choice([-1, 0, 1]),  # turn_ud_delta
        random.random() > 0.5,  # jump
    ]


used_actions = [
    ActionVariable.WALK_DIR,
    ActionVariable.WALK_SPEED,
    ActionVariable.TURN_LR_DELTA,
    ActionVariable.LOOK_UD_DELTA,
    ActionVariable.JUMP,
]

game = Game(map_dir=args.map_dir, engine_dir=args.engine_dir, server_port=args.port)
game.set_game_mode(args.game_mode)
game.set_random_seed(args.random_seed)
game.set_supply_heatmap_center([args.start_location[0], args.start_location[2]])
game.set_supply_heatmap_radius(30)
game.set_supply_indoor_richness(80)
game.set_supply_outdoor_richness(20)
game.set_supply_indoor_quantity_range(10, 50)
game.set_supply_outdoor_quantity_range(1, 5)
game.set_supply_spacing(5)
game.set_episode_timeout(args.timeout)
game.set_start_location(args.start_location)
game.set_target_location(args.target_location)
game.set_available_actions(used_actions)
game.set_map_id(args.map_id)

for agent_id in range(1, args.num_agents):
    game.add_agent()

if args.use_depth_map:
    game.turn_on_depth_map()

if args.record:
    game.turn_on_record()


game.init()
for ep in track(range(args.num_episodes), description="Running Episodes ..."):
    if args.random_start_location:
        for agent_id in range(args.num_agents):
            game.random_start_location(agent_id)
   
    game.set_game_replay_suffix(f"{args.replay_suffix}_episode_{ep}")
    console.print(game.get_game_config())

    game.new_episode()
    while not game.is_episode_finished():
        t = time.perf_counter()
        state_all = game.get_state_all()
        action_all = {agent_id: my_policy(state_all[agent_id]) for agent_id in state_all}
        game.make_action(action_all)
        dt = time.perf_counter() - t

        agent_id = 0
        state = state_all[agent_id]
        step_info = {
            "Episode": ep,
            "GameState": state.game_state,
            "TimeStep": state.time_step,
            "AgentID": agent_id,
            "Location": get_position(state),
            "Action": {name: val for name, val in zip(used_actions, action_all[agent_id])},
            "#SupplyInfo": len(state.supply_states),
            "#EnemyInfo": len(state.enemy_states),
            "StepRate": round(1 / dt),
        }
        if args.use_depth_map:
            step_info["DepthMap"] = state.depth_map.shape
        console.print(step_info, style="bold magenta")

    print("episode ended ...")

game.close()
