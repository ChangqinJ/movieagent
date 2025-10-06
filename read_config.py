#读取当前工作目录下的config.json文件, 并检查参数是否正确
import json
import os
'''
json文件中的参数为: host,port,user,password,db,max_connections,output_path,log_path
'''
def read_config(path_json:str)->dict:
  try:
    with open(path_json,'r',encoding='utf-8') as f:
      config = json.load(f)
      if check_config(config) == False:
        raise Exception('config.json args error, please check config.json file')
      return config
  except Exception as e:
    print(f'read config.json file failed: {e}')
    return None
      
def check_config(config:dict)->bool:
  args_list = ['host','port','user','password','db','max_connections','output_path','log_path']
  for item in list(config.keys()):
    if item not in args_list:
      return False
  return True