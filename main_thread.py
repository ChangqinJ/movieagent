from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable
import pymysql
from pymysql import cursors
from pymysql.cursors import Cursor, DictCursor
from DBpool import DBpool
from queue import Queue
import simple_log
import time
import read_config
import os

class main_thread:
  # 连接测试成功
  def __init__(self,func:Callable,host:str='testapi.fuhu.tech',port:int=3306,user:str='ai_creator',password:str='ai_creator123456',db:str='esports',max_connections:int=100, logging_path:str='./logging_dir'):
    '''
    func: 接收字典和线程池引用作为参数, 返回tuple[int,None|str]
    host: 数据库主机
    port: 数据库端口
    user: 数据库用户
    password: 数据库密码
    db: 数据库名称
    max_connections: 数据库连接池最大连接数(近似认为是数据库访问的并行程度)
    '''
    self.func = func
    self.host = host
    self.port = port
    self.user = user
    self.password = password
    self.db = db
    self.queue = Queue()
    self.status=True
    self.dbpool = DBpool(max_connections=max_connections,host=host,port=port,user=user,password=password,db=db,cursorclass='DictCursor')
    self.logging_path = logging_path
    try:
      self.conn = pymysql.connect(host=host,port=port,user=user,password=password,db=db,cursorclass=DictCursor,autocommit=False)
    except pymysql.Error as e:
      self.dbpool.close()
      simple_log.log(str(e),log_path=self.logging_path)
      raise e
  
  def init_process(self,max_workers:int=10):
    pass
  
  def fetch_status0(self,ub:int=10):
    '''
    从数据库中找到特定数量的state=0的记录并添加到queue中, 并更新state为1
    '''
    rows = []
    try:
      Dcursor = self.conn.cursor()
      self.conn.begin()
      # 找到全部state=0的记录, 并限制返回数量
      Dcursor.execute('select * from movie_agent_tasks where state = 0 limit %s',(ub,))
      rows = list(Dcursor.fetchall())
      if len(rows) > 0:
        placeholders = ','.join(['%s'] * len(rows))
        Dcursor.execute(f'update movie_agent_tasks set state = 1 where id in ({placeholders})',tuple(row['id'] for row in rows))
      else: #测试语句, 正式调试时删除
        print('no rows to update')
        time.sleep(5)
      self.conn.commit()
      idlist = []
      if len(rows) > 0:
        for row in rows:
          self.queue.put(row)
          idlist.append(row['id'])
      return idlist
    except Exception as e:
      self.conn.rollback()
      raise e
    finally:
      Dcursor.close()
      
  #测试成功
  def close(self):
    self.conn.close()
    self.dbpool.close()
  
  class callback:
    def __init__(self,package:dict[str,any],dbpool:DBpool):
      self.package=package
      self.dbpool=dbpool
    def __call__(self,future:Future[tuple[int,None|str]]):
      try:
        conn = self.dbpool.get_connection()
      except Exception as e:
        simple_log.log(str(e)+f' task{self.package['id']} get MySQL connection failed',log_path=self.logging_path)
        return
      
      try:
        result = future.result()
      except Exception as e:
        simple_log.log(str(e)+f' task{self.package['id']} execute function failed',log_path=self.logging_path)
        self.dbpool.put_connection(conn)
        return
      # 使用一个守护进程查看数据库中的积压未完成任务, 将积压任务设为失败状态
      index = result[0] #返回任务id
      msg = result[1] #返回错误信息, 在没有错误时, 信息为None
      state = None
      if msg is None:
        state = 2
      else:
        state = 3
      try:
        with conn.cursor() as cursor:
          cursor.execute('update movie_agent_tasks set state = %s, progress = 100 where id = %s',(state,index))
        conn.commit()
      except Exception as e:
        conn.rollback()
        simple_log.log(str(e)+f' task{index} update state failed',log_path=self.logging_path)
      finally:
        self.dbpool.put_connection(conn)
  
  def add_output_path(self,args:dict[str,any]):
    pass
  
  def run(self, slice_size:int=10,max_workers:int=10):
    '''
    查找数据库中status为0的记录, 每一条记录都开一个线程处理, 线程数不够则等待
    '''
    try:
      with ThreadPoolExecutor(max_workers=max_workers) as executor:
        times = 0 #测试语句, 正式调试时删除
        while True:
          self.init_process(max_workers=max_workers) #初始化进程, 在最新版本main_thread_cfg_init中, 函数依照is_init值决定是否执行, 并保证在服务器开启后只执行一次
          print('times:',times) #测试语句, 正式调试时删除
          times += 1 #测试语句, 正式调试时删除
          if self.status == False:
            break
          print('before fetch_status0, times:',times) #测试语句, 正式调试时删除
          idlist = self.fetch_status0(slice_size) #每次获取10条数据, 进行测试, 正式调试传入1024
          
          #捕获数据后, 返回全部行数据的id, 用于更新进度条
          print('idlist:',idlist) #测试语句, 正式调试时删除
          if self.queue.empty():
            print('queue is empty, times:',times) #测试语句, 正式调试时删除
          
          print('after fetch_status0, times:',times) #测试语句, 正式调试时删除
          while not self.queue.empty():
            print('into cycle, times:',times) #测试语句, 正式调试时删除
            '''
            对queue中的每一行, 开一个线程处理
            在处理结束后将queue中的行状态改为2
            '''
            
            '''
            self.func接收参数为字典, 字典内容为{'id','task_uuid','prompt','width','height'}
            '''
            row = self.queue.get()
            args = {'id':row['id'],'task_uuid':row['task_uuid'],'prompt':row['prompt'],'width':row['width'],'height':row['height']}
            self.add_output_path(args)
            future = executor.submit(self.func,args,self.dbpool)
            future.add_done_callback(main_thread.callback(args,self.dbpool))
          print('queue size:',self.queue.qsize()) #测试语句, 正式调试时删除
    finally:
      self.close()

class main_thread_with_config(main_thread):
  def __init__(self,func:Callable,path_config:str):
    '''
    传入config.json文件路径, 读取配置文件, 并初始化main_thread
    '''
    self.path_config = path_config
    self.config = read_config.read_config(path_config)
    if self.config is None:
      raise RuntimeError('Failed to load config')
    super().__init__(func=func,host=self.config['host'],port=self.config['port'],user=self.config['user'],password=self.config['password'],db=self.config['db'],max_connections=self.config['max_connections'],logging_path=self.config['log_path'])
    self.output_path = self.config['output_path']
    # 测试语句, 正式调试时删除
    print('path_config: ',path_config)
    print('config: ',self.config)
    
  def add_output_path(self,args:dict[str,any]):
    args['output_path'] = self.output_path

class main_thread_cfg_init(main_thread_with_config):
  def __init__(self,func:Callable,path_config:str):
    self.__is_init = True
    super().__init__(func=func,path_config=path_config)
  
  #确实可以在开始时将全部未完成任务状态转回为0, 但是无法保证在run过程中不会出现新的未完成任务
  def init_process(self,max_workers:int=10):
    '''
    在服务器启动时, 只负责将未完成任务的状态转回为0, 接下来交给run处理
    本函数只在初始状态执行一次
    '''
    if self.__is_init == False:
      return
    else:
      print('start init_process')
      self.__is_init = False
      conn = self.dbpool.get_connection()
      try:
        # 开始事务
        # 事务的开始应该在游标的获取之前
        conn.begin()
        
        with conn.cursor() as cursor:
          #测试语句 - 查看更新前的状态
          test_list = []
          cursor.execute('select id from movie_agent_tasks where state = 1')
          test_list = list(cursor.fetchall())
          print('test_list: (before update)\n',test_list)
          
          # 使用更安全的update语句，避免子查询问题
          # 先获取所有state=1的id
          cursor.execute('select id from movie_agent_tasks where state = 1')
          state_1_ids = [row['id'] for row in cursor.fetchall()]
          
          # update语句中最好不要嵌套子查询, 否则会报错
          if state_1_ids:
            # 使用IN子句进行更新
            placeholders = ','.join(['%s'] * len(state_1_ids))
            cursor.execute(f'update movie_agent_tasks set state = 0 where id in ({placeholders})', state_1_ids)
            affected_rows = cursor.rowcount
            print(f'update success, affected rows: {affected_rows}')
          else:
            print('no rows with state=1 to update')
          
          # 提交事务
          conn.commit()
          
          #测试语句 - 查看更新后的状态
          test_list = []
          cursor.execute('select id from movie_agent_tasks where state = 1')
          test_list = list(cursor.fetchall())
          print('test_list: (after update)\n',test_list)
          
      except Exception as e:
        conn.rollback()
        print(f'init_process failed: {str(e)}')
        simple_log.log(str(e)+' init_process failed',log_path=self.logging_path)
      finally:
        self.dbpool.put_connection(conn)
    print('end init_process')