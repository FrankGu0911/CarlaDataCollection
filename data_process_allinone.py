import os,argparse,json,time,logging
from tqdm.contrib.concurrent import process_map
from PIL import Image
import numpy as np

'''
    This script is used to process data collected,
    including:
        1. Remove haze data and recollect data
        2. Merge data
        3. Delete origin data after merge
'''

dt = {
    "topdown": "%04d.png",
    "seg_right": "%04d.png",
    "seg_left": "%04d.png",
    "seg_front": "%04d.png",
    "rgb_right": "%04d.png",
    "rgb_left": "%04d.png",
    "rgb_front": "%04d.png",
    "rgb_rear": "%04d.png",
    "depth_right": "%04d.png",
    "depth_left": "%04d.png",
    "depth_front": "%04d.png",
    "measurements": "%04d.json",
    "lidar": "%04d.npy",
    "birdview": "%04d.png",
    "affordances": "%04d.npy",
    "actors_data": "%04d.json",
    "3d_bbs": "%04d.npy",
    "2d_bbs_left": "%04d.npy",
    "2d_bbs_right": "%04d.npy",
    "2d_bbs_front": "%04d.npy",
}

def SetArgParser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data_path',type=str,required=True)
    parser.add_argument('--remove_haze',action='store_true',default=False)
    parser.add_argument('--merge',action='store_true',default=False)
    parser.add_argument('--delete_origin',action='store_true',default=False)
    parser.add_argument('--convert_to_jpg',action='store_true',default=False)
    parser.add_argument('--index',action='store_true',default=False)
    return parser.parse_args()

def GetCpuNum():
    return os.cpu_count()

def GetDataListFromPath(path:str):
    data_list = []
    for i in range(14):
        data_path = os.path.join(path,'weather-%d' % i,'data')
        if not os.path.exists(data_path):
            # print('Path %s not exists' % data_path)
            continue
        subs = os.listdir(data_path)
        for sub in subs:
            route_path = os.path.join(data_path,sub)
            if not os.path.exists(route_path):
                continue
            data_list.append(route_path)
    return data_list

def GetBlockedDataList(data_path:str):
    blocked_data_list = []
    measurements_path = os.path.join(data_path,'measurements')
    full_flag = False
    if not os.path.exists(measurements_path):
        measurements_full_path = os.path.join(data_path,'measurements_full')
        if not os.path.exists(measurements_full_path):
            raise Exception('No measurements found, Data Error')
        else:
            full_flag = True
            measurements_path = measurements_full_path
    frames = len(os.listdir(measurements_path))
    stop = 0
    max_stop = 0
    last_actor_num = 0
    for i in range(frames):
        if full_flag:
            m_f = json.load(open(os.path.join(data_path,'measurements_full','%04d.json' % i),'r'))
            json_data = m_f
            actors_data = m_f['actors_data']
        else:
            json_data = json.load(open(os.path.join(data_path,'measurements','%04d.json' % i),'r'))
            actors_data = json.load(open(os.path.join(data_path,'actors_data','%04d.json' % i),'r'))
        actors_num = len(actors_data)
        light = json_data["is_red_light_present"]
        speed = json_data["speed"]
        junction = json_data["is_junction"]
        brake = json_data["should_brake"]
        if speed < 0.1 and len(light) == 0 and brake == 1:
            stop += 1
            max_stop = max(max_stop, stop)
        else:
            if stop >= 10 and actors_num < last_actor_num:
                blocked_data_list.append((data_path, i, stop))
            stop = 0
        last_actor_num = actors_num
    if stop >= 10:
        blocked_data_list.append((data_path, frames - 1, stop))
    return blocked_data_list

def RemoveHazeData(task:tuple):
    route_dir, end_id, length = task
    for i in range(end_id - length + 6, end_id - 3):
        for key in dt:
            # f.write(os.path.join(route_dir, key, dt[key] % i)+"\n")
            os.remove(os.path.join(route_dir, key, dt[key] % i))

def RecollectBlockedData(data_path:str):
    for folder in dt:
        temp = dt[folder]
        files = os.listdir(os.path.join(data_path, folder))
        fs = []
        for file in files:
            fs.append(int(file[:4]))
        fs.sort()
        for i in range(len(fs)):
            if i == fs[i]:
                continue
            try:
                os.rename(
                    os.path.join(data_path, folder, temp % fs[i]),
                    os.path.join(data_path, folder, temp % i),
                )
            except Exception as e:
                print(e)

def CheckMergeData(data_path:str):
    if not os.path.exists(data_path):
        raise Exception('Data path %s not exists' % data_path)
    measurements_path = os.path.join(data_path,'measurements')
    rgb_front_path = os.path.join(data_path,'rgb_front')
    measurements_full_path = os.path.join(data_path,'measurements_full')
    rgb_full_path = os.path.join(data_path,'rgb_full')
    lidar_path = os.path.join(data_path,'lidar')
    measurements = os.path.exists(measurements_path)
    rgb_front = os.path.exists(rgb_front_path)
    measurements_full = os.path.exists(measurements_full_path)
    rgb_full = os.path.exists(rgb_full_path)
    lidar = os.path.exists(lidar_path)
    if not (measurements or measurements_full):
        logging.error('Cannot find measurements: %s' % data_path)
        raise Exception('Cannot find measurements')
    if not (rgb_front or rgb_full):
        logging.error('Cannot find rgb: %s' % data_path)
        raise Exception('Cannot find rgb')
    if not lidar:
        logging.error('Cannot find lidar: %s' % data_path)
        raise Exception('Cannot find lidar')
    if not measurements_full:
        return False
    if not rgb_full:
        return False
    if len(os.listdir(measurements_full_path)) != len(os.listdir(lidar_path)):
        return False
    if len(os.listdir(rgb_full_path)) != len(os.listdir(lidar_path)):
        return False
    if measurements_full and rgb_full:
        return True
    raise Exception('Unknown Error')

def MergeData(data_path:str):
    if CheckMergeData(data_path):
        logging.info('Data %s already merged' % data_path)
        return
    frames = len(os.listdir(os.path.join(data_path, "measurements")))
    if not os.path.exists(os.path.join(data_path, "rgb_full")):
        os.mkdir(os.path.join(data_path, "rgb_full"))
    if not os.path.exists(os.path.join(data_path, "measurements_full")):
        os.mkdir(os.path.join(data_path, "measurements_full"))
    for i in range(frames):
        img_front = Image.open(os.path.join(data_path, "rgb_front/%04d.png" % i))
        img_left = Image.open(os.path.join(data_path, "rgb_left/%04d.png" % i))
        img_right = Image.open(os.path.join(data_path, "rgb_right/%04d.png" % i))
        new = Image.new(img_front.mode, (800, 1800))
        new.paste(img_front, (0, 0))
        new.paste(img_left, (0, 600))
        new.paste(img_right, (0, 1200))
        new.save(os.path.join(data_path, "rgb_full", "%04d.png" % i))

        measurements = json.load(
            open(os.path.join(data_path, "measurements/%04d.json" % i))
        )
        actors_data = json.load(
            open(os.path.join(data_path, "actors_data/%04d.json" % i))
        )
        affordances = np.load(
            os.path.join(data_path, "affordances/%04d.npy" % i), allow_pickle=True
        )

        measurements["actors_data"] = actors_data
        measurements["stop_sign"] = affordances.item()["stop_sign"]
        json.dump(
            measurements,
            open(os.path.join(data_path, "measurements_full/%04d.json" % i), "w"),
        )

def DeleteAfterMerge(data_path:str):
    if not os.path.exists(data_path):
        return
    rgb_full_path = os.path.join(data_path,'rgb_full')
    rgb_front_path = os.path.join(data_path,'rgb_front')
    rgb_left_path = os.path.join(data_path,'rgb_left')
    rgb_right_path = os.path.join(data_path,'rgb_right')
    measurements_path = os.path.join(data_path,'measurements')
    actor_data_path = os.path.join(data_path,'actor_data')
    measurements_full_path = os.path.join(data_path,'measurements_full')
    if os.path.exists(rgb_full_path):
        if os.path.exists(rgb_front_path):
            os.system('rm -rf %s' % rgb_front_path)
        if os.path.exists(rgb_left_path):
            os.system('rm -rf %s' % rgb_left_path)
        if os.path.exists(rgb_right_path):
            os.system('rm -rf %s' % rgb_right_path)
    if os.path.exists(measurements_full_path):
        if os.path.exists(measurements_path):
            os.system('rm -rf %s' % measurements_path)
        if os.path.exists(actor_data_path):
            os.system('rm -rf %s' % actor_data_path)

def MergeAndDelete(data_path:str):
    if not os.path.exists(data_path):
        raise Exception('Data path %s not exists' % data_path)
    if not os.path.isdir(data_path):
        raise Exception('Data path %s is not a directory' % data_path)
    MergeData(data_path)
    DeleteAfterMerge(data_path)

def ConvertPngToJpg(data_path:str):
    if CheckMergeData(data_path):
        rgb_full_path = os.path.join(data_path,'rgb_full')
        for i in os.listdir(rgb_full_path):
            if i.endswith('.png'):
                img = Image.open(os.path.join(rgb_full_path,i))
                try:
                    img.save(os.path.join(rgb_full_path,i.replace('.png','.jpg')), quality=95)
                except Exception as e:
                    print(e)
                    print('Error in %s' % os.path.join(rgb_full_path,i))
                    raise e
                os.remove(os.path.join(rgb_full_path,i))
    else:
        rgb_front_path = os.path.join(data_path,'rgb_front')
        rgb_left_path = os.path.join(data_path,'rgb_left')
        rgb_right_path = os.path.join(data_path,'rgb_right')
        for i in os.listdir(rgb_front_path):
            if i.endswith('.png'):
                img = Image.open(os.path.join(rgb_front_path,i))
                img.save(os.path.join(rgb_front_path,i.replace('.png','.jpg')), quality=95)
                os.remove(os.path.join(rgb_front_path,i))
        for i in os.listdir(rgb_left_path):
            if i.endswith('.png'):
                img = Image.open(os.path.join(rgb_left_path,i))
                img.save(os.path.join(rgb_left_path,i.replace('.png','.jpg')), quality=95)
                os.remove(os.path.join(rgb_left_path,i))
        for i in os.listdir(rgb_right_path):
            if i.endswith('.png'):
                img = Image.open(os.path.join(rgb_right_path,i))
                img.save(os.path.join(rgb_right_path,i.replace('.png','.jpg')), quality=95)
                os.remove(os.path.join(rgb_right_path,i))
        
def GenerateDatasetIndexFile(dataset_path:str):
    if not os.path.exists(dataset_path):
        raise Exception('Dataset path %s not exists' % dataset_path)
    routes = []
    for i in range(14):
        weather_data_path = os.path.join(dataset_path,'weather-%d' % i,'data')
        if not os.path.exists(weather_data_path):
            logging.warning('Weather %d not exists' % i)
            logging.warning('%s' % weather_data_path)
            continue
        for route in os.listdir(weather_data_path):
            route_path = os.path.join(weather_data_path,route)
            if not os.path.isdir(route_path):
                logging.warning('Route %s not exists' % route)
                continue
            if CheckMergeData(route_path):
                frames = len(os.listdir(os.path.join(route_path, "measurements_full")))
            else:
                frames = len(os.listdir(os.path.join(route_path, "measurements")))
            relative_route_path = os.path.join('weather-%d' % i,'data',route)
            routes.append((relative_route_path,frames))
    dataset_index_filepath = os.path.join(dataset_path,'dataset_index.txt')
    with open(dataset_index_filepath,'w') as f:
        for route,frames in routes:
            f.write('%s %d\n' % (route,frames))
    f.close()

def GetChunkSize(data_list:list):
    chunk_size = len(data_list) // GetCpuNum()
    if chunk_size == 0:
        chunk_size = 1
    return chunk_size

if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    args = SetArgParser()
    data_list = GetDataListFromPath(args.data_path)
    data_list.sort()
    chunksize = GetChunkSize(data_list)
    if data_list == []:
        logging.warning('No data found')
        exit(0)
    if args.remove_haze:
        blocked_data_list = []
        blocked_data_list = process_map(GetBlockedDataList,data_list,max_workers=GetCpuNum(),chunksize=chunksize,desc='Getting blocked data')
        blocked_data_list = [item for sublist in blocked_data_list for item in sublist]
        if len(blocked_data_list) == 0:
            logging.info('No blocked data found')
        else:
            logging.info('Found %d blocked data' % len(blocked_data_list))
            process_map(RemoveHazeData,blocked_data_list,max_workers=GetCpuNum(),chunksize=chunksize,desc='Removing blocked data')
            process_map(RecollectBlockedData,data_list,max_workers=GetCpuNum(),chunksize=chunksize,desc='Recollecting blocked data')
    if args.merge and args.delete_origin:
        process_map(MergeAndDelete,data_list,max_workers=GetCpuNum(),chunksize=chunksize,desc='Merge and delete origin data')
    elif args.merge:
        process_map(MergeData,data_list,max_workers=GetCpuNum(),chunksize=chunksize,desc='Merging data')
        logging.info('Not deleting origin data')
    else:
        logging.info('Not merging data')
    if args.convert_to_jpg:
        process_map(ConvertPngToJpg,data_list,max_workers=GetCpuNum(),chunksize=chunksize,desc='Converting png to jpg')
    if args.index:
        GenerateDatasetIndexFile(args.data_path)

    
