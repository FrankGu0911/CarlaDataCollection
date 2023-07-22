import argparse,os

exception = ["routes_town01_long.sh"]

def SetArgParser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--weather', type=int, default=0)
    parser.add_argument('--with_carla', type=bool, default=True)
    parser.add_argument('--carla-root', type=str, default='./carla')
    parser.add_argument('--bash-root', type=str, default='./data_collection/bashs')
    parser.add_argument('--port', type=int, default=-1)
    
    args = parser.parse_args()
    return args

if __name__ == '__main__':
    args = SetArgParser()
    if args.port == -1:
        args.port = 20000 + args.weather * 2
    else:
        raise ValueError('Port number is not correct')
    data_path = os.path.join('dataset','weather-%d' % args.weather)
    if not os.path.exists(data_path):
        os.mkdir(data_path)
    if not os.path.exists(os.path.join(data_path,'results')):
        os.mkdir(os.path.join(data_path,'results'))
    
    print(args)
    
    