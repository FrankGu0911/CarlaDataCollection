# CarlaDataCollection
This repo is used to collect training data from carla

## Setup Anaconda
```Shell
wget https://repo.anaconda.com/archive/Anaconda3-2023.03-1-Linux-x86_64.sh
chmod +x Anaconda3-2023.03-1-Linux-x86_64.sh
bash Anaconda3-2023.03-1-Linux-x86_64.sh
```

## Setup Python Environment
```Shell
conda create -n CarlaDataCollect python=3.7
conda activate CarlaDataCollect
pip install -r requirements.txt
```

## Setup CARLA
```Shell
chmod +x setup_carla.sh
bash setup_carla.sh
```
## Setup Bashs
```Shell
cd data_collection
python generate_bashs.py
```

## Run Data Collection
```Shell
python data_collect_single_weather.py --weather 0 --with_carla
```

## Run Data Collection with Multiple GPU
if you have multiple GPU, you can run data collection with multiple GPU
this example is for GPU 0,1,2,3 and each GPU will run 4 data collection process
```Shell
python data_collection_multi_gpu.py --gpu 0 1 2 3 --carla_num 4
```