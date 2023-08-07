#!/bin/bash
CUDA_VISIBLE_DEVICES=2 ./carla/CarlaUE4.sh -quality-level=Epic -fps=20 -world-port=20000 &
CUDA_VISIBLE_DEVICES=2 ./carla/CarlaUE4.sh -quality-level=Epic -fps=20 -world-port=20002 &
CUDA_VISIBLE_DEVICES=2 ./carla/CarlaUE4.sh -quality-level=Epic -fps=20 -world-port=20004 &
CUDA_VISIBLE_DEVICES=2 ./carla/CarlaUE4.sh -quality-level=Epic -fps=20 -world-port=20006 &
CUDA_VISIBLE_DEVICES=3 ./carla/CarlaUE4.sh -quality-level=Epic -fps=20 -world-port=20008 &
CUDA_VISIBLE_DEVICES=3 ./carla/CarlaUE4.sh -quality-level=Epic -fps=20 -world-port=20010 &
CUDA_VISIBLE_DEVICES=3 ./carla/CarlaUE4.sh -quality-level=Epic -fps=20 -world-port=20012 &
CUDA_VISIBLE_DEVICES=3 ./carla/CarlaUE4.sh -quality-level=Epic -fps=20 -world-port=20014 &
CUDA_VISIBLE_DEVICES=4 ./carla/CarlaUE4.sh -quality-level=Epic -fps=20 -world-port=20016 &
CUDA_VISIBLE_DEVICES=4 ./carla/CarlaUE4.sh -quality-level=Epic -fps=20 -world-port=20018 &
CUDA_VISIBLE_DEVICES=4 ./carla/CarlaUE4.sh -quality-level=Epic -fps=20 -world-port=20020 &
CUDA_VISIBLE_DEVICES=4 ./carla/CarlaUE4.sh -quality-level=Epic -fps=20 -world-port=20022 &
CUDA_VISIBLE_DEVICES=5 ./carla/CarlaUE4.sh -quality-level=Epic -fps=20 -world-port=20024 &
CUDA_VISIBLE_DEVICES=5 ./carla/CarlaUE4.sh -quality-level=Epic -fps=20 -world-port=20026 &
CUDA_VISIBLE_DEVICES=5 ./carla/CarlaUE4.sh -quality-level=Epic -fps=20 -world-port=20028 &
CUDA_VISIBLE_DEVICES=5 ./carla/CarlaUE4.sh -quality-level=Epic -fps=20 -world-port=20030 &
