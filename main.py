from main_thread import main_thread
from DBpool import DBpool
def test_func(args:dict[str,any])->tuple[int,None|str]:
  print('test_func',args)
  if 'prompt' not in list(args.keys()) or args['prompt'] is None:
    return args['id'],'error'
  return args['id'],None

def test_func_with_dbpool(args:dict[str,any],dbpool:DBpool)->tuple[int,None|str]:
  print('test_func_with_dbpool',args)
  print('dbpool',dbpool)
  if 'prompt' not in list(args.keys()) or args['prompt'] is None:
    return args['id'],'error'
  return args['id'],None

if __name__ == '__main__':
  mth = main_thread(func=test_func_with_dbpool,base_dir='./loggings')
  mth.run()