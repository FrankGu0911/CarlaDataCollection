import argparse,os,time,sys,logging,tqdm,datetime
import subprocess

exception = ["routes_town01_long.sh"]
if not os.path.exists('log'):
    os.mkdir('log')
def SetArgParser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--weather', type=int, default=0)
    parser.add_argument('--with_carla',action='store_true',default=False)
    parser.add_argument('--carla-root', type=str, default='./carla')
    parser.add_argument('--bash-root', type=str, default='./data_collection/bashs')
    # parser.add_argument('--port', type=int, default=-1)
    args = parser.parse_args()
    return args

def GetLocalTime():
    return datetime.datetime.now().strftime('%m_%d_%H_%M_%S')

class CarlaManager():
    def __init__(self,carla_root:str):
        self.carla_root = carla_root
        self.carla_pid = None
        self.carla_port = None
        self.carla_pgid = None
        self.carla_process = None
    
    def RunCarla(self,port:int):
        carla_cmd = os.path.join(self.carla_root,'CarlaUE4/Binaries/Linux/CarlaUE4-Linux-Shipping CarlaUE4 -resx=800 -resy=600 -quality-level=Epic -fps=20 -world-port=%d' % port)
        logfile = open('log/carla_%s.log' % GetLocalTime(),'w')
        self.carla_process = subprocess.Popen(carla_cmd,shell=True,stdout=logfile,preexec_fn=os.setsid)
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

# {carla-root}/CarlaUE4/Binaries/Linux/CarlaUE4-Linux-Shipping CarlaUE4 -resx=800 -resy=600 -quality-level=Epic -fps=20 -world-port=20002

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    args = SetArgParser()
    # print(args)
    port = 20000 + args.weather * 2
    data_path = os.path.join('dataset','weather-%d' % args.weather)
    if not os.path.exists(data_path):
        os.mkdir(data_path)
    if not os.path.exists(os.path.join(data_path,'results')):
        os.mkdir(os.path.join(data_path,'results'))
    
    if args.with_carla:
        logging.info('Running Carla on port %d' % port)
        carla = CarlaManager(args.carla_root)
        carla.RunCarla(port)
        logging.info('Carla pid is %d' % carla.carla_pid)
    # carla_pid = RunCarla(port,args.carla_root)

    # time.sleep(10)
    # carla.StopCarla()
    # # sys.exit(0)
    bash_list = []
    bash_base_path = os.path.join(args.bash_root,'weather-%d' % args.weather)
    for bash in os.listdir(bash_base_path):
        if bash in exception:
            continue
        bash_list.append(os.path.join(bash_base_path,bash))
    bash_list.sort()
    # print(bash_list)
    for bash in tqdm.tqdm(bash_list):
        x_access = os.access(bash,os.X_OK)
        if not x_access:
            logging.info('%s is not executable' % bash)
            # +x
            logging.info('chmod +x %s' % bash)
            os.chmod(bash,os.stat(bash).st_mode | 0o111)
        logfile_path = os.path.join("log","w%d"%args.weather+os.path.basename(bash).split('.')[0]+GetLocalTime()+'.log')
        logfile = open(logfile_path,'w')
        logging.info('Running bash %s' % bash)
        subprocess.call(bash,shell=True,stdout=logfile)
        time.sleep(5)
    carla.StopCarla()
    