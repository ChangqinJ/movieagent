from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable
import pymysql
from pymysql import cursors
from pymysql.cursors import Cursor, DictCursor
from DBpool import DBpool
from queue import Queue
import simple_log
import time

class main_thread:
  # 连接测试成功
  def __init__(self,func,base_dir:str,host:str='testapi.fuhu.tech',port:int=3306,user:str='ai_creator',password:str='ai_creator123456',db:str='esports',max_connections:int=100):
    '''
    func: 接收字典和线程池引用作为参数, 返回tuple[int,None|str]
    base_dir: 基础目录, 用来存放用户文本文档, 每创建一个用户, 就在base_dir下创建一个文件, 文件名称为用户id, 文件内容为用户的prompt
    host: 数据库主机
    port: 数据库端口
    user: 数据库用户
    password: 数据库密码
    db: 数据库名称
    max_connections: 数据库连接池最大连接数(近似认为是数据库访问的并行程度)
    '''
    self.func = func
    self.base_dir = base_dir
    self.host = host
    self.port = port
    self.user = user
    self.password = password
    self.db = db
    self.queue = Queue()
    self.status=True
    self.dbpool = DBpool(max_connections=max_connections,host=host,port=port,user=user,password=password,db=db,cursorclass='DictCursor')
    try:
      self.conn = pymysql.connect(host=host,port=port,user=user,password=password,db=db,cursorclass=DictCursor,autocommit=False)
    except pymysql.Error as e:
      self.dbpool.close()
      simple_log.log(str(e))
      raise e
  
  def fetch_status0(self,ub:int=10):
    rows = []
    try:
      Dcursor = self.conn.cursor()
      self.conn.begin()
      Dcursor.execute('select u.* from (movie_agent_tasks u join (select id from movie_agent_tasks where state = 0 limit %s) t on u.id = t.id)',(ub,))
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
        simple_log.log(str(e)+f' task{self.package['id']} get MySQL connection failed')
        return
      
      try:
        result = future.result()
      except Exception as e:
        simple_log.log(str(e)+f' task{self.package['id']} execute function failed')
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
        simple_log.log(str(e)+f' task{index} update state failed')
      self.dbpool.put_connection(conn)
  
  def run(self, slice_size:int=10,max_workers:int=10):
    '''
    查找数据库中status为0的记录, 每一条记录都开一个线程处理, 线程数不够则等待
    '''
    try:
      with ThreadPoolExecutor(max_workers=max_workers) as executor:
        times = 0 #测试语句, 正式调试时删除
        while True:
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
            future = executor.submit(self.func,args,self.dbpool)
            future.add_done_callback(main_thread.callback(args,self.dbpool))
          print('queue size:',self.queue.qsize()) #测试语句, 正式调试时删除
    finally:
      self.close()
      