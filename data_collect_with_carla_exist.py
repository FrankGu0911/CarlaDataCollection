import argparse,os,time,logging,datetime,subprocess,re
from multiprocessing import Pool,Manager

exceptions = ["routes_town01_long.sh","tiny"]
weather_without_exceptions = [0,1,2,3,5,7,11,14,17,19,20]

def SetArgParser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, nargs='+', required=True)
    parser.add_argument('--carla_root', type=str, default='./carla')
    parser.add_argument('--bash_root', type=str, default='./data_collection/bashs')
    # weather
    parser.add_argument('--weather', type=int, nargs='+', default=[0,1,2,3,4,5,6,7,8,9,10,11,12,13])
    args = parser.parse_args()
    return args

PORT_LIST = Manager().list()

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
        
def CollectOneBash(bash_cmd:str,PORT_LIST):
    port = PORT_LIST.pop()
    tm_port = port + 1000
    logging.info('Running on port %d, tm_port %d' % (port,tm_port))
    logging.info('Running bash %s' % bash_cmd)
    CheckXAccess(bash_cmd)
    #Get Data Path dataset/weather-0
    pattern = re.compile(r'weather-\d+')
    weather = pattern.findall(bash_cmd)[0]
    data_path = os.path.join('dataset',weather)
    CheckDataPath(data_path)
    bash_base = os.path.basename(bash_cmd).split('.')[0]
    logfile = open('log/%s_%s_%s.log' % (datetime.datetime.now().strftime('%m_%d_%H_%M_%S'),weather,bash_base),'w')
    bash_cmd = "PORT=%d TM_PORT=%d " % (port,tm_port) + bash_cmd
    p = subprocess.Popen(bash_cmd,shell=True,stdout=logfile,stderr=logfile)
    try:
        p.wait()
    except KeyboardInterrupt:
        lb_pg = os.getpgid(p.pid)
        logging.warning('KeyboardInterrupt, kill process group %d' % lb_pg)
        os.killpg(lb_pg,9)
    finally:
        PORT_LIST.append(port)

def GetBashs(base_path:str,weather:int):
    bash_list = []
    path = os.path.join(base_path,'weather-%d' % weather)
    for root,dirs,files in os.walk(path):
        for file in files:
            flag = False
            if weather not in weather_without_exceptions:
                for exception in exceptions:
                    if exception in file:
                        flag = True
            else:
                logging.info('Weather-%d is not in weather_without_exceptions' % weather)
            if not flag:
                bash_list.append(os.path.join(root,file))
    bash_list.sort()
    return bash_list

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    args = SetArgParser()
    CheckDataPath('log')
    # Init PORT_LIST
    for i in args.port:
        PORT_LIST.append(i)
    # Find all bashs
    weather_list = args.weather
    bash_list = []
    for weather in weather_list:
        bash_list += GetBashs(args.bash_root,weather)
    bash_list.sort()
    logging.info('Found %d bashs' % len(bash_list))
    pool = Pool(processes=len(args.port))
    for bash in bash_list:
        pool.apply_async(CollectOneBash,args=(bash,PORT_LIST))
        time.sleep(1)
    pool.close()
    pool.join()

    