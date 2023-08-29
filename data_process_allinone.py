import os
import argparse
import json
import time
import logging
import shutil
import sys
from tqdm.contrib.concurrent import process_map
from tqdm import tqdm
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
    parser.add_argument('--weather',type=int,nargs='+',default=[0,1,2,3,4,5,6,7,8,9,10,11,12,13])
    parser.add_argument('--remove_haze',action='store_true',default=False)
    parser.add_argument('--merge',action='store_true',default=False)
    parser.add_argument('--delete_origin',action='store_true',default=False)
    parser.add_argument('--convert_to_jpg',action='store_true',default=False)
    parser.add_argument('--vae_feature', action='store_true', default=False)
    parser.add_argument('--clip_feature', action='store_true', default=False)
    parser.add_argument('--index',action='store_true',default=False)
    return parser.parse_args()

def GetCpuNum():
    return os.cpu_count()

def GetDataListFromPath(path:str,weather_list:list):
    data_list = []
    logging.debug('Getting data list from %s' % path)
    logging.debug('Weather list: %s' % weather_list)
    for i in weather_list:
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
    if CheckMergeData(data_path):
        return
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

def CheckMergeData(data_path: str):
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

def MergeData(data_path:str,convert_jpg:bool):
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
        if convert_jpg:
            new.save(os.path.join(data_path, "rgb_full", "%04d.jpg" % i), quality=95)
        else:
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
            shutil.rmtree(rgb_front_path)
            # os.system('rm -rf %s' % rgb_front_path)
        if os.path.exists(rgb_left_path):
            shutil.rmtree(rgb_left_path)
            # os.system('rm -rf %s' % rgb_left_path)
        if os.path.exists(rgb_right_path):
            shutil.rmtree(rgb_right_path)
            # os.system('rm -rf %s' % rgb_right_path)
    if os.path.exists(measurements_full_path):
        if os.path.exists(measurements_path):
            shutil.rmtree(measurements_path)
            # os.system('rm -rf %s' % measurements_path)
        if os.path.exists(actor_data_path):
            shutil.rmtree(actor_data_path)
            # os.system('rm -rf %s' % actor_data_path)

def MergeAndDelete(data_path:str,convert_jpg:bool):
    if not os.path.exists(data_path):
        raise Exception('Data path %s not exists' % data_path)
    if not os.path.isdir(data_path):
        raise Exception('Data path %s is not a directory' % data_path)
    MergeData(data_path,convert_jpg)
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
    rgb_rear_path = os.path.join(data_path,'rgb_rear')
    for i in os.listdir(rgb_rear_path):
        if i.endswith('.png'):
            img = Image.open(os.path.join(rgb_rear_path,i))
            img.save(os.path.join(rgb_rear_path,i.replace('.png','.jpg')), quality=95)
            os.remove(os.path.join(rgb_rear_path,i))

def GenerateDatasetIndexFile(dataset_path:str):
    if not os.path.exists(dataset_path):
        raise Exception('Dataset path %s not exists' % dataset_path)
    routes = []
    length = 0
    for i in range(21):
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
            length += frames
    logging.info('Total %d routes' % len(routes))
    logging.info('Total %d frames' % length)
    dataset_index_filepath = os.path.join(dataset_path,'dataset_index.txt')
    with open(dataset_index_filepath,'w') as f:
        for route,frames in routes:
            f.write('%s %d\n' % (route,frames))
    f.close()

def GenTopdownVAEFeature(datalist: list, batch_size: int = 8):
    #  preprocess, inference, save
    # get task first
    import torch.multiprocessing as mp
    from torch.multiprocessing import Pool,Queue
    tasks = []
    for data_path in datalist:
        topdown_path = os.path.join(data_path, 'topdown')
        if not os.path.exists(topdown_path):
            raise Exception('Topdown path %s not exists' % topdown_path)
        if not os.path.isdir(topdown_path):
            raise Exception('Topdown path %s is not a directory' % topdown_path)
        data_length = len(os.listdir(topdown_path))
        if os.path.exists(os.path.join(data_path, 'vae_feature')):
            if len(os.listdir(os.path.join(data_path, 'vae_feature'))) == data_length:
                logging.debug('Data %s already processed' % data_path)
                continue
        else:
            os.mkdir(os.path.join(data_path, 'vae_feature'))
        for i in range(0, data_length):
            tasks.append((data_path, i))
    logging.debug('Total %d tasks' % len(tasks))
    # start processing
    total = len(tasks)
    task_queue = Queue()
    after_preprocess_queue = Queue(maxsize=128)
    for task in tasks:
        task_queue.put(task)
    preprocess_pool = Pool(1,PreprocessTopdownVAEFeature,(task_queue,after_preprocess_queue))
    preprocess_pool.close()
    import torch
    from model.vae import VAE
    vae_model_path = '/home/frank/code/diff_study/pretrained/vae_one_hot/vae_model_68.pth'
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = VAE(26, 26).to(device)
    model.load_state_dict(torch.load(vae_model_path)['model_state_dict'])
    model.eval()
    with tqdm(total=total,desc='Generating topdown vae feature') as pbar:
        while not (after_preprocess_queue.empty() and task_queue.empty()):
            # tqdm.write('Preprocess queue size: %d' % after_preprocess_queue.qsize())
            batch_data = []
            batch_order = []
            for i in range(batch_size):
                if after_preprocess_queue.empty():
                    break
                batch = after_preprocess_queue.get()
                batch_data.append(batch[2])
                batch_order.append((batch[0],batch[1]))
            if len(batch_data) == 0:
                if (after_preprocess_queue.empty() and task_queue.empty()):
                    break
                elif after_preprocess_queue.empty() and not task_queue.empty():
                    logging.info('Batch data is empty, task queue not,continue')
                    continue
                elif not after_preprocess_queue.empty() and task_queue.empty(): 
                    logging.info('Batch data is empty, task queue is empty,continue')
                    continue
                else:
                    logging.info('Waiting for preprocessing')
                    continue
            batch_data = torch.stack(batch_data)
            batch_data = batch_data.to(device)
            with torch.no_grad():
                mean, logvar = model.encoder(batch_data)
                feature = model.sample(mean, logvar).detach()
                for i in range(len(batch_order)):
                    feature_path = os.path.join(
                        batch_order[i][0], 'vae_feature', '%04d.pt' % batch_order[i][1])
                    cur_feature = feature[i].clone()
                    torch.save(cur_feature, feature_path)
            pbar.update(len(batch_order))
    del model
    torch.cuda.empty_cache()

def PreprocessTopdownVAEFeature(task_queue,after_preprocess_queue):
    import torch
    from torchvision import transforms
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    def get_one_hot(label, N):
        dtype = label.dtype
        shape = label.shape
        ones = torch.eye(N)
        important = [4, 19, 23]
        for i in important:
            ones[i][i] = 100
        ones[6][6] = 10
        onehot = ones.index_select(
            0, label.int().view(-1)).reshape(*shape, N).to(dtype).squeeze(0).permute(2, 0, 1)
        return onehot
    def calc_crop(tar_x, tar_y):
        if tar_x > 512 or tar_y > 512:
            return (0, 0, 512, 512)
        if tar_x < 0 or tar_y < 0:
            raise ValueError("Target size should be positive")
        if tar_x > 256 or tar_y > 256:
            x = (512 - tar_x) // 2
            return (x, 0, x+tar_x, tar_y)
        else:
            x = (512 - tar_x) // 2
            y = 256 - tar_y
            return (x, y, x+tar_x, y+tar_y)
    while not task_queue.empty():
        task = task_queue.get()
        data_path, i = task
        topdown_path = os.path.join(data_path, 'topdown')
        data = Image.open(os.path.join(topdown_path, '%04d.png' % i))
        topdown_img = data.crop(calc_crop(256, 256))
        topdown_img = (transforms.ToTensor()(
            topdown_img) * 255).to(torch.uint8)
        if torch.max(topdown_img) > 25:
            logging.debug("Topdown image has value larger than 25: %s" % (
                os.path.join(topdown_path, '%04d.png' % i)))
            # replace with 7
            topdown_img = torch.where(topdown_img > 25, torch.Tensor(
                [7]).to(torch.uint8), topdown_img)
        topdown_img = get_one_hot(topdown_img, 26).to(torch.float32).to(device)
        while after_preprocess_queue.full():
            time.sleep(0.1)
        after_preprocess_queue.put((data_path, i, topdown_img))
    while not after_preprocess_queue.empty():
        logging.info('Preprocess VAE waiting')
        time.sleep(1)

def GenClipFeature(datalist: list, batch_size: int = 16):
    import torch
    import clip
    import torch.multiprocessing as mp
    from torch.multiprocessing import Pool,Queue
    mp.set_start_method('spawn')
    #  preprocess, inference, save
    # get task first
    tasks = []
    for data_path in datalist:
        frames = len(os.listdir(os.path.join(data_path, "rgb_full")))
        if os.path.exists(os.path.join(data_path, 'clip_feature')):
            if len(os.listdir(os.path.join(data_path, 'clip_feature'))) == frames:
                logging.info('Data %s already processed' % data_path)
                continue
        else:
            os.mkdir(os.path.join(data_path, 'clip_feature'))
        for i in range(0, frames):
            tasks.append((data_path, i))
    logging.debug('Total %d tasks' % len(tasks))
    # start processing
    total = len(tasks)
    task_queue = Queue()
    after_preprocess_queue = Queue(maxsize=4096)
    for task in tasks:
        task_queue.put(task)
    preprocess_pool = Pool(1,PreprocessClipFeature,(task_queue,after_preprocess_queue))
    preprocess_pool.close()
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    clip_encoder, _ = clip.load("ViT-L/14", device=device)
    clip_encoder.eval()
    with tqdm(total=total,desc='Generating clip feature') as pbar:
        while not (after_preprocess_queue.empty() and task_queue.empty()):
            # tqdm.write('Preprocess queue size: %d' % after_preprocess_queue.qsize())
            batch_data = []
            batch_order = []
            for i in range(batch_size):
                if after_preprocess_queue.empty():
                    break
                batch = after_preprocess_queue.get()
                batch_data.append(batch[2])
                batch_order.append((batch[0],batch[1]))
            if len(batch_data) == 0:
                if (after_preprocess_queue.empty() and task_queue.empty()):
                    break
                elif after_preprocess_queue.empty() and not task_queue.empty():
                    logging.info('Batch data is empty, task queue not,continue')
                    continue
                elif not after_preprocess_queue.empty() and task_queue.empty(): 
                    logging.info('Batch data is empty, task queue is empty,continue')
                    continue
                else:
                    logging.info('Waiting for preprocessing')
                    continue
            batch_data = torch.stack(batch_data).reshape(-1, 3, 224, 224)
            with torch.no_grad():
                clip_feature = clip_encoder.encode_image(batch_data)
                for i in range(len(batch_order)):
                    feature_path = os.path.join(
                        batch_order[i][0], 'clip_feature', '%04d.pt' % batch_order[i][1])
                    cur_feature = clip_feature[i:i+4].clone()
                    torch.save(cur_feature, feature_path)
            pbar.update(len(batch_order))
    del clip_encoder
    torch.cuda.empty_cache()

def PreprocessClipFeature(task_queue,after_preprocess_queue):
    import torch
    from torchvision.transforms import Compose, Resize, CenterCrop, ToTensor, Normalize,InterpolationMode
    while not task_queue.empty():
        data_path, i = task_queue.get()
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        image_full = Image.open(os.path.join(data_path, 'rgb_full', '%04d.jpg' % i))
        preprocess = Compose([
            Resize(224, interpolation=InterpolationMode.BILINEAR),
            CenterCrop(224),
            Normalize([0.48145466, 0.4578275, 0.40821073], [0.26862954, 0.26130258, 0.27577711]),
            ])
        image_front = ToTensor()(image_full.crop((0, 0, 800, 600))).unsqueeze(0).to(device)
        image_left = ToTensor()(image_full.crop((0, 600, 800, 1200))).unsqueeze(0).to(device)
        image_right = ToTensor()(image_full.crop((0, 1200, 800, 1800))).unsqueeze(0).to(device)
        image_far = ToTensor()(image_full.crop((200, 150, 600, 450))).unsqueeze(0).to(device)
        image_full_tensor = torch.cat(
            (preprocess(image_front), 
                preprocess(image_left), 
                preprocess(image_right), 
                preprocess(image_far)), dim=0)
        while after_preprocess_queue.full():
            time.sleep(0.1)
        after_preprocess_queue.put((data_path, i, image_full_tensor))
    while not after_preprocess_queue.empty():
        logging.info('Preprocess Clip waiting')
        time.sleep(1)

def GetChunkSize(data_list:list):
    chunk_size = len(data_list) // GetCpuNum()
    if chunk_size == 0:
        chunk_size = 1
    return chunk_size

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    args = SetArgParser()
    data_list = GetDataListFromPath(args.data_path,args.weather)
    data_list.sort()
    chunksize = GetChunkSize(data_list)
    if data_list == []:
        logging.warning(f'No data found in {args.data_path}')
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
    bool_list = [args.convert_to_jpg]*len(data_list)
    if args.merge and args.delete_origin:
        process_map(MergeAndDelete,data_list,bool_list,max_workers=GetCpuNum(),chunksize=chunksize,desc='Merge and delete origin data')
    elif args.merge:
        process_map(MergeData,data_list,bool_list,max_workers=GetCpuNum(),chunksize=chunksize,desc='Merging data')
        logging.info('Not deleting origin data')
    else:
        logging.info('Not merging data')
    if args.convert_to_jpg:
        process_map(ConvertPngToJpg,data_list,max_workers=GetCpuNum(),chunksize=chunksize,desc='Converting png to jpg')
    if args.vae_feature:
        GenTopdownVAEFeature(data_list,batch_size=32)
    if args.clip_feature:
        GenClipFeature(data_list,16)
    if args.index:
        GenerateDatasetIndexFile(args.data_path)
