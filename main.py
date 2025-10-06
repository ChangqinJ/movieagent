from main_thread import main_thread, main_thread_with_config
from DBpool import DBpool

def test_func_with_dbpool(args:dict[str,any],dbpool:DBpool)->tuple[int,None|str]:
  print('test_func_with_dbpool',args)
  print('dbpool',dbpool)
  if 'prompt' not in list(args.keys()) or args['prompt'] is None:
    return args['id'],'error'
  return args['id'],None

if __name__ == '__main__':
  # 使用配置文件初始化main_thread
  mth = main_thread_with_config(test_func_with_dbpool,path_config='./movie_agent_config.json')
  mth.run()