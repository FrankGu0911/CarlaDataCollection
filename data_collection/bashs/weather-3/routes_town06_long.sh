#!/bin/bash
export DATA_ROOT=dataset
export YAML_ROOT=data_collection/yamls
export CARLA_ROOT=carla
export CARLA_SERVER=${CARLA_ROOT}/CarlaUE4.sh
export PYTHONPATH=$PYTHONPATH:${CARLA_ROOT}/PythonAPI
export PYTHONPATH=$PYTHONPATH:${CARLA_ROOT}/PythonAPI/carla
export PYTHONPATH=$PYTHONPATH:$CARLA_ROOT/PythonAPI/carla/dist/carla-0.9.10-py3.7-linux-x86_64.egg
export PYTHONPATH=$PYTHONPATH:leaderboard
export PYTHONPATH=$PYTHONPATH:leaderboard/team_code
export PYTHONPATH=$PYTHONPATH:scenario_runner

export LEADERBOARD_ROOT=leaderboard

export CHECKPOINT_ENDPOINT=${DATA_ROOT}/weather-3/results/routes_town06_long.json
export SAVE_PATH=${DATA_ROOT}/weather-3/data
export TEAM_CONFIG=${YAML_ROOT}/weather-3.yaml
export TRAFFIC_SEED=20006
export CARLA_SEED=20006
export SCENARIOS=${LEADERBOARD_ROOT}/data/scenarios/town06_all_scenarios.json
export ROUTES=${LEADERBOARD_ROOT}/data/additional_routes/routes_town06_long.xml
export TM_PORT=20506
export PORT=20006
export HOST=localhost
export CHALLENGE_TRACK_CODENAME=SENSORS
export DEBUG_CHALLENGE=0
export REPETITIONS=1 # multiple evaluation runs
export TEAM_AGENT=${LEADERBOARD_ROOT}/team_code/auto_pilot.py # agent
export RESUME=True

python3 ${LEADERBOARD_ROOT}/leaderboard/leaderboard_evaluator.py \
--scenarios=${SCENARIOS}  \
--routes=${ROUTES} \
--repetitions=${REPETITIONS} \
--track=${CHALLENGE_TRACK_CODENAME} \
--checkpoint=${CHECKPOINT_ENDPOINT} \
--agent=${TEAM_AGENT} \
--agent-config=${TEAM_CONFIG} \
--debug=${DEBUG_CHALLENGE} \
--record=${RECORD_PATH} \
--resume=${RESUME} \
--port=${PORT} \
--host=${HOST} \
--trafficManagerPort=${TM_PORT} \
--carlaProviderSeed=${CARLA_SEED} \
--trafficManagerSeed=${TRAFFIC_SEED}
