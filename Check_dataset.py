import os,argparse,json,time,logging
dt = {
    "topdown": "%04d.png",
    "seg_right": "%04d.png",
    "seg_left": "%04d.png",
    "seg_front": "%04d.png",
    "rgb_rear": "%04d.png",
    "depth_right": "%04d.png",
    "depth_left": "%04d.png",
    "depth_front": "%04d.png",
    "lidar": "%04d.npy",
    "birdview": "%04d.png",
    "affordances": "%04d.npy",
    "actors_data": "%04d.json",
    "3d_bbs": "%04d.npy",
    "2d_bbs_left": "%04d.npy",
    "2d_bbs_right": "%04d.npy",
    "2d_bbs_front": "%04d.npy",
}
not_merged = {
    "seg_front": "%04d.png",
    "rgb_right": "%04d.png",
    "rgb_left": "%04d.png",
    "measurements": "%04d.json",
}
merged = {
    "rgb_full": "%04d.png",
    "measurements_full": "%04d.json",
}

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
        raise Exception('Cannot find measurements')
    if not (rgb_front or rgb_full):
        raise Exception('Cannot find rgb')
    if not lidar:
        raise Exception('Cannot find lidar')
    if not measurements_full:
        return False
    if not rgb_full:
        return False
    if measurements_full and rgb_full:
        return True
    raise Exception('Unknown Error')

def CheckDatasetinPath(data_path:str):
    if not os.path.exists(data_path):
        logging.error("Path not exist: {}".format(data_path))
        return False
    if not os.path.isdir(data_path):
        logging.error("Path is not a directory: {}".format(data_path))
        return False
    folders = os.listdir(data_path)
    for key in dt:
        if key not in folders:
            logging.error("Folder not exist: {} Path:{}".format(key,data_path))
            return False
    length = len(os.listdir(os.path.join(data_path,'topdown')))
    if not CheckMergeData(data_path):
        logging.info("Data not merged")
        flag = False
        for key in not_merged:
            if len(os.listdir(os.path.join(data_path,key))) != length:
                logging.error("Data length not match: {} Path:{}".format(key,data_path))
                flag = True
        if flag:
            return False
    else:
        flag = False
        for key in merged:
            if len(os.listdir(os.path.join(data_path,key))) != length:
                logging.error("Data length not match: {} Path:{}".format(key,data_path))
                flag = True
        if flag:
            return False
    return True
    

if __name__ == "__main__":
    data_list = GetDataListFromPath("dataset")
    f = open('dataset_error.txt','w')
    for data_path in data_list:
        if not CheckDatasetinPath(data_path):
            f.write(data_path+'\n')
    f.close()