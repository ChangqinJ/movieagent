import os
import time

default_log_path = os.path.join(os.path.dirname(__file__),'base_dir','logging_dir','log.txt')

def get_time():
  return time.strftime("%Y_%m_%d_%H_%M_%S", time.localtime())

def log_size(log_path:str=default_log_path):
  if not os.path.exists(log_path):
    open(log_path,'w').close()
    return 0
  else:
    return os.path.getsize(log_path)

#定时执行日志的清理(默认只留下最近10MB的日志)
def clean_log(rest_size:int=1024*1024*10, log_path:str=default_log_path):
  if not os.path.exists(log_path):
    open(log_path,'w').close()
  elif log_size(log_path) < rest_size:
    return
  else:
    with open(log_path,'r') as flog:
      flog.seek(-rest_size,2)
      text = flog.read()
    with open(log_path,'w') as f:
      f.write(text)

def log(message:str,log_path:str=default_log_path):
  if not os.path.exists(log_path):
    open(log_path,'w').close()
  with open(log_path,'a') as f:
    f.write(get_time()+': '+message+'\n')


