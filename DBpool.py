import pymysql
from pymysql.connections import Connection
from pymysql.cursors import Cursor, DictCursor, SSDictCursor, SSCursor
from queue import Queue
class DBpool:
  '''
  数据库连接池
  '''  
  def __init__(self,max_connections:int,host:str,port:int,user:str,password:str,db:str,cursorclass:str = 'Default'):
    self.host = host
    self.port = port
    self.user = user
    self.password = password
    self.db = db
    self.pool = Queue()
    self.max_connections = max_connections
    for i in range(max_connections):
      try:
        if cursorclass == 'Default' or cursorclass is None or cursorclass == 'Cursor':
          self.pool.put(pymysql.connect(host=self.host,port=self.port,user=self.user,password=self.password,db=self.db))
        elif cursorclass == 'DictCursor':
          self.pool.put(pymysql.connect(host=self.host,port=self.port,user=self.user,password=self.password,db=self.db,cursorclass=DictCursor))
        elif cursorclass == 'SSDictCursor':
          self.pool.put(pymysql.connect(host=self.host,port=self.port,user=self.user,password=self.password,db=self.db,cursorclass=SSDictCursor))
        elif cursorclass == 'SSCursor':
          self.pool.put(pymysql.connect(host=self.host,port=self.port,user=self.user,password=self.password,db=self.db,cursorclass=SSCursor))
        else:
          raise Exception(f"Invalid cursorclass: {cursorclass}")
      except Exception as e:
        break
    if self.pool.qsize() != max_connections:
      while self.pool.empty() == False:
        self.pool.get().close()
      raise Exception(f"Failed to create {max_connections} connections")

  # 获取连接
  def get_connection(self):
    return self.pool.get(block=True)

  # 获取连接, 超时时间默认10秒, 超时后抛出TimeoutError
  def timed_get_connection(self,timeout:int=10):
    return self.pool.get(block=True,timeout=timeout)
  
  # 放回连接
  def put_connection(self,conn:Connection):
    self.pool.put(conn)
    
  # 关闭连接池
  def close(self):
    while self.pool.empty() == False:
      self.pool.get().close()