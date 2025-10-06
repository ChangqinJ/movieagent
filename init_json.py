import json
import os
import sys
if __name__ == '__main__':
  path = sys.argv[1] # 运行脚本, 在脚本中输入日志所在的文件夹路径, 不需要文件名称, 只需要文件夹路径
  if os.path.exists(path) == False:
    os.makedirs(path)
  config = {
    'host':'localhost',
    'port':3306,
    'user':'user',
    'password':'password',
    'db':'esports',
    'max_connections':100,
    'output_path':'output',
    'log_path':'./logging_dir',
  }
  
  with open(os.path.join(path,'movie_agent_config.json'),'w') as f:
    json.dump(config,f)
  
  print('Success!\nconfig path:\n',os.path.join(os.path.abspath(path),'movie_agent_config.json'))
  
'''
使用方式: 在服务器初次创建时, 确定配置文件的路径, python运行脚本指令: python init_json.py <配置文件路径>
(配置文件路径为日志所在的文件夹路径, 不需要文件名称, 只需要文件夹路径)

movie_agent_config.json文件内容:
{
  "host":"host",
  "port":3306,
  "user":"user",
  "password":"password",
  "db":"esports",
  "max_connections":100,
  "output_path":"output",
  "log_path":"./logging_dir",
}
用户在使用服务器时, 将movie_agent_config.json中的字段进行改变, 就可以连接到目的数据库, 自定义数据库的最大连接数, 自定义文件输出路径, 自定义日志输出路径, 自定义数据库主机, 自定义数据库端口, 自定义数据库用户, 自定义数据库密码, 自定义数据库名称
'''
  
  
    