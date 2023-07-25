import argparse,os,time,sys,logging,tqdm,datetime,subprocess
from multiprocessing import Pool,Manager

exception = ["routes_town01_long.sh"]

def SetArgParser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--gpu', type=int, nargs='+', default=[0])
    parser.add_argument('--carla_num', type=int, nargs='+', default=[1])
    parser.add_argument('--carla_root', type=str, default='./carla')
    parser.add_argument('--bash_root', type=str, default='./data_collection/bashs')
    args = parser.parse_args()
    return args

GPU_STAT = Manager().dict()
GPU_MAX = Manager().dict()
PORT_LIST = Manager().list()

class CarlaManager():
    def __init__(self,carla_root:str,gpuid:int=0):
        self.carla_root = carla_root
        self.gpuid = gpuid
        self.carla_pid = None
        self.carla_port = None
        self.carla_pgid = None
        self.carla_process = None
    
    def RunCarla(self,port:int):
        carla_cmd = os.path.join(self.carla_root,'CarlaUE4/Binaries/Linux/CarlaUE4-Linux-Shipping CarlaUE4 -resx=800 -resy=600 -quality-level=Epic -fps=20 -world-port=%d' % port)
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

def CollectOneBash(carla_root:str,bash_cmd:str,GPU_STAT,GPU_MAX,PORT_LIST):
    gpuid = GetAvailableGPU(GPU_STAT,GPU_MAX)
    port = PORT_LIST.pop()
    tm_port = PORT_LIST.pop()
    while gpuid == -1:
        time.sleep(1)
        logging.info('Waiting for available GPU')
        gpuid = GetAvailableGPU()
    logging.info('Running on GPU %d, port %d, tm_port %d' % (gpuid,port,tm_port))
    logging.info('Running bash %s' % bash_cmd)
    cm = CarlaManager(carla_root,gpuid)
    cm.RunCarla(port)
    bash_base = os.path.basename(bash_cmd).split('.')[0]
    logfile = open('log/%s_%s.log' % (bash_base,datetime.datetime.now().strftime('%m_%d_%H_%M_%S')),'w')
    bash_cmd = "PORT=%d TM_PORT=%d " % (port,tm_port) + bash_cmd
    subprocess.call(bash_cmd,shell=True,stdout=logfile,stderr=logfile)
    PORT_LIST.append(port)
    PORT_LIST.append(tm_port)
    ReturnGPU(gpuid,GPU_STAT)
    # subprocess.call(bash_cmd,shell=True)
    
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    args = SetArgParser()
    # Init GPU_STAT and GPU_MAX
    if len(args.carla_num) == 1:
        args.carla_num = args.carla_num * len(args.gpu)
    for i in range(len(args.gpu)):
        GPU_STAT[args.gpu[i]] = 0
        GPU_MAX[args.gpu[i]] = args.carla_num[i]
    # Init PORT_LIST
    for i in range(20000,20002+sum(args.carla_num)*2):
        PORT_LIST.append(i)
    # Find all bashs
    bash_list = []
    for root,dirs,files in os.walk(args.bash_root):
        for file in files:
            if file in exception:
                continue
            bash_list.append(os.path.join(root,file))
    logging.info('Found %d bashs' % len(bash_list))
    
    
    pool = Pool(processes=sum(args.carla_num))
    for bash in bash_list:
        pool.apply_async(CollectOneBash,args=(args.carla_root,bash,GPU_STAT,GPU_MAX,PORT_LIST))
        time.sleep(1)
    pool.close()
    pool.join()
    # for bash in bash_list:
    #     logging.info('Found bash %s' % bash)
    