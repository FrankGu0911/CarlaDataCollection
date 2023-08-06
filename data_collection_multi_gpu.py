import argparse,os,time,sys,logging,tqdm,datetime,subprocess,re
from multiprocessing import Pool,Manager

exceptions = ["routes_town01_long.sh","tiny"]

def SetArgParser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--gpu', type=int, nargs='+', default=[0])
    parser.add_argument('--carla_num', type=int, nargs='+', default=[1])
    parser.add_argument('--carla_root', type=str, default='./carla')
    parser.add_argument('--bash_root', type=str, default='./data_collection/bashs')
    # weather
    parser.add_argument('--weather', type=int, nargs='+', default=[0,1,2,3,4,5,6,7,8,9,10,11,12,13])
    args = parser.parse_args()
    return args

GPU_STAT = Manager().dict()
GPU_MAX = Manager().dict()
PORT_LIST = Manager().list()
PGID_LIST = Manager().list()

class CarlaManager():
    def __init__(self,carla_root:str,gpuid:int=0):
        self.carla_root = carla_root
        self.gpuid = gpuid
        self.carla_pid = None
        self.carla_port = None
        self.carla_pgid = None
        self.carla_process = None
    
    def RunCarla(self,port:int):
        carla_cmd = os.path.join(self.carla_root,'CarlaUE4/Binaries/Linux/CarlaUE4-Linux-Shipping CarlaUE4 -quality-level=Epic -fps=20 -world-port=%d' % port)
        carla_cmd = "CUDA_VISIBLE_DEVICES=%d " % self.gpuid + carla_cmd
        logfile = open('log/carla_%s.log' % datetime.datetime.now().strftime('%m_%d_%H_%M_%S'),'w')
        self.carla_process = subprocess.Popen(carla_cmd,shell=True,stdout=logfile,stderr=logfile,preexec_fn=os.setsid)
        self.carla_pid = self.carla_process.pid
        self.carla_pgid = os.getpgid(self.carla_pid)
        self.carla_port = port
        time.sleep(5)

    def StopCarla(self):
        os.killpg(self.carla_pgid,9)
        self.carla_pid = None
        self.carla_pgid = None
        self.carla_port = None
        self.carla_process = None

def GetAvailableGPU(GPU_STAT,GPU_MAX):
    for gpu in GPU_MAX.keys():
        if GPU_STAT[gpu] < GPU_MAX[gpu]:
            GPU_STAT[gpu] += 1
            return gpu
    return -1

def ReturnGPU(gpu:int,GPU_STAT):
    GPU_STAT[gpu] -= 1

def CheckDataPath(data_path:str):
    if not os.path.exists(data_path):
        os.mkdir(data_path)
    if not os.path.exists(os.path.join(data_path,'results')):
        os.mkdir(os.path.join(data_path,'results'))

def CheckXAccess(bash:str):
    x_access = os.access(bash,os.X_OK)
    if not x_access:
        logging.info('%s is not executable' % bash)
        # +x
        logging.info('chmod +x %s' % bash)
        os.chmod(bash,os.stat(bash).st_mode | 0o111)

def CollectOneBash(carla_root:str,bash_cmd:str,GPU_STAT,GPU_MAX,PORT_LIST,PGID_LIST):
    gpuid = GetAvailableGPU(GPU_STAT,GPU_MAX)
    port = PORT_LIST.pop()
    tm_port = port + 1000
    while gpuid == -1:
        time.sleep(1)
        logging.info('Waiting for available GPU')
        gpuid = GetAvailableGPU()
    logging.info('Running on GPU %d, port %d, tm_port %d' % (gpuid,port,tm_port))
    logging.info('Running bash %s' % bash_cmd)
    cm = CarlaManager(carla_root,gpuid)
    cm.RunCarla(port)
    CheckXAccess(bash_cmd)
    #Get Data Path dataset/weather-0
    pattern = re.compile(r'weather-\d+')
    weather = pattern.findall(bash_cmd)[0]
    data_path = os.path.join('dataset',weather)
    CheckDataPath(data_path)
    bash_base = os.path.basename(bash_cmd).split('.')[0]
    logfile = open('log/%s_%s_%s.log' % (datetime.datetime.now().strftime('%m_%d_%H_%M_%S'),weather,bash_base),'w')
    bash_cmd = "PORT=%d TM_PORT=%d " % (port,tm_port) + bash_cmd
    p = subprocess.Popen(bash_cmd,shell=True,stdout=logfile,stderr=logfile,preexec_fn=os.setsid)
    pgid = os.getpgid(p.pid)
    carla_pgid = cm.carla_pgid
    PGID_LIST.append(pgid)
    PGID_LIST.append(carla_pgid)
    try:
        p.wait()
    except KeyboardInterrupt:
        lb_pg = os.getpgid(p.pid)
        logging.warning('KeyboardInterrupt, kill process group %d' % lb_pg)
        os.killpg(lb_pg,9)
    finally:
        cm.StopCarla()
        PORT_LIST.append(port)
        # PORT_LIST.append(tm_port)
        ReturnGPU(gpuid,GPU_STAT)
    if carla_pgid in PGID_LIST:
        PGID_LIST.remove(carla_pgid)
    if pgid in PGID_LIST:
        PGID_LIST.remove(pgid)

def GetBashs(base_path:str,weather:int):
    bash_list = []
    path = os.path.join(base_path,'weather-%d' % weather)
    for root,dirs,files in os.walk(path):
        for file in files:
            flag = False
            for exception in exceptions:
                if exception in file:
                    flag = True
            if not flag:
                bash_list.append(os.path.join(root,file))
    bash_list.sort()
    return bash_list

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    args = SetArgParser()
    CheckDataPath('log')
    # Init GPU_STAT and GPU_MAX
    if len(args.carla_num) == 1:
        args.carla_num = args.carla_num * len(args.gpu)
    for i in range(len(args.gpu)):
        GPU_STAT[args.gpu[i]] = 0
        GPU_MAX[args.gpu[i]] = args.carla_num[i]
    # Init PORT_LIST
    for i in range(20000,20002+sum(args.carla_num)*2,2):
        PORT_LIST.append(i)
    # Find all bashs
    weather_list = args.weather
    bash_list = []
    for weather in weather_list:
        bash_list += GetBashs(args.bash_root,weather)
    bash_list.sort()
    logging.info('Found %d bashs' % len(bash_list))
    pool = Pool(processes=sum(args.carla_num))
    try:
        for bash in bash_list:
            pool.apply_async(CollectOneBash,args=(args.carla_root,bash,GPU_STAT,GPU_MAX,PORT_LIST,PGID_LIST))
            time.sleep(1)
        pool.close()
        pool.join()
    except KeyboardInterrupt:
        pgid_list = list(set(PGID_LIST))
        logging.warning('KeyboardInterrupt, kill all process group')
        logging.warning('Total process num: %d' %len(pgid_list))
        for pgid in pgid_list:
            logging.warning('kill process group %d' % pgid)
        # for pgid in PGID_LIST:
            os.killpg(pgid,9)
    