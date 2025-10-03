from concurrent.futures import ThreadPoolExecutor, Future
import pymysql
from pymysql import cursors
from pymysql.cursors import Cursor, SSDictCursor
from DBpool import DBpool
from queue import Queue
import simple_log
class args_of_func:
  def __init__(self,id,prompt,uuid,width,height):
    self.prompt = prompt
    self.uuid = uuid
    self.width = width
    self.height = height
    self.id = id

class main_thread:
  # 连接测试成功
  def __init__(self,func,base_dir:str,host:str='testapi.fuhu.tech',port:int=3306,user:str='ai_creator',password:str='ai_creator123456',db:str='esports',max_connections:int=10):
    '''
    func: 接收'file_path'和'workdir_path'
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
    self.dbpool = DBpool(max_connections=10,host=host,port=port,user=user,password=password,db=db)
    
    try:
      self.SSconn = pymysql.connect(host=host,port=port,user=user,password=password,db=db,cursorclass=SSDictCursor)
    except pymysql.Error as e:
      simple_log.log(str(e))
      raise e
    try:
      self.conn = pymysql.connect(host=host,port=port,user=user,password=password,db=db)
    except pymysql.Error as e:
      if self.SSconn.open:
        self.SSconn.close()
      simple_log.log(str(e))
      raise e
    try:
      self.cursor = self.conn.cursor()
    except pymysql.Error as e:
      if self.conn.open:
        self.conn.close()
      if self.SSconn.open:
        self.SSconn.close()
      simple_log.log(str(e))
      raise e
  
  # 测试成功, 抓取单批请求放入queue中
  def fetch_status0(self,ub:int=10):
    '''
    批量查找数据库中status为0的记录, 并加入queue中, 每次加入的条数存在上限1024
    将数据库中取出的行中状态改为1
    '''
    try:
      # 先单独取出所有状态为0的行
      rows = []
      with self.SSconn.cursor() as SS_cursor:
        # 此函数产生死锁?
        SS_cursor.execute('select * from movie_agent_tasks where state = 0 limit %s',(ub,))
        for row in SS_cursor:
          rows.append(row)
      
      print(f"Found {len(rows)} rows to process") #测试语句, 正式调试时删除
      
      # 将取出的行进行修改并全部添加到队列中
      if rows:
        for row in rows:
          self.queue.put(row)
          print(row['id'],' added to queue') #测试语句, 正式调试时删除
          self.cursor.execute('update movie_agent_tasks set state = 1 where id = %s',(row['id'],))
        
        # 确保事务提交
        self.conn.commit()
        print(f"Committed {len(rows)} updates") #测试语句, 正式调试时删除
      else:
        print("No rows to process") #测试语句, 正式调试时删除
        
    except Exception as e:
      print(f"Error in fetch_status0: {e}")
      # 如果出错，回滚事务
      try:
        self.conn.rollback()
        print("Transaction rolled back")
      except:
        pass
      raise e
  
  #测试成功
  def close(self):
    try:
      self.cursor.close()
    except pymysql.Error as e:
      simple_log.log(str(e))
      raise e
    try:
      self.SSconn.close()
    except pymysql.Error as e:
      simple_log.log(str(e))
      raise e
    try:
      self.conn.close()
    except pymysql.Error as e:
      simple_log.log(str(e))
      raise e
    try:
      self.dbpool.close()
    except Exception as e:
      simple_log.log(str(e))
      raise e
  
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
      index = result[0]
      msg = result[1]
      state = None
      if msg is None:
        state = 2
      else:
        state = 3
      try:
        with conn.cursor() as cursor:
          cursor.execute('update movie_agent_tasks set state = %s where id = %s',(state,index))
      except Exception as e:
        conn.rollback()
        simple_log.log(str(e)+f' task{index} update state failed')
      self.dbpool.put_connection(conn)
      
  def run(self, slice_size:int=1024,max_workers:int=10):
    '''
    查找数据库中status为0的记录, 每一条记录都开一个线程处理, 线程数不够则等待
    '''
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
      times = 0 #测试语句, 正式调试时删除
      while True:
        print('times:',times) #测试语句, 正式调试时删除
        times += 1 #测试语句, 正式调试时删除
        if self.status == False:
          break
        print('before fetch_status0, times:',times) #测试语句, 正式调试时删除
        self.fetch_status0(slice_size) #每次获取10条数据, 进行测试, 正式调试传入1024
        # 在第二次执行到此函数时发生卡顿
        
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
          future = executor.submit(self.func,args)
          future.add_done_callback(main_thread.callback(args,self.dbpool))
        print('queue size:',self.queue.qsize()) #测试语句, 正式调试时删除