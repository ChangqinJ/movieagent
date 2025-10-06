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
    successful_connections = 0
    for i in range(max_connections):
      try:
        if cursorclass == 'Default' or cursorclass is None or cursorclass == 'Cursor':
          conn = pymysql.connect(host=self.host,port=self.port,user=self.user,password=self.password,db=self.db)
        elif cursorclass == 'DictCursor':
          conn = pymysql.connect(host=self.host,port=self.port,user=self.user,password=self.password,db=self.db,cursorclass=DictCursor)
        elif cursorclass == 'SSDictCursor':
          conn = pymysql.connect(host=self.host,port=self.port,user=self.user,password=self.password,db=self.db,cursorclass=SSDictCursor)
        elif cursorclass == 'SSCursor':
          conn = pymysql.connect(host=self.host,port=self.port,user=self.user,password=self.password,db=self.db,cursorclass=SSCursor)
        else:
          raise Exception(f"Invalid cursorclass: {cursorclass}")
        
        self.pool.put(conn)
        successful_connections += 1
        #改为日志记录
        print(f"Successfully created connection {successful_connections}/{max_connections}")
        
      except Exception as e:
        #改为日志记录
        print(f"Failed to create connection {i+1}: {str(e)}")
        break
    actual_connections = self.pool.qsize()
    if actual_connections != max_connections:
      #改为日志记录
      print(f"Warning: Only created {actual_connections} out of {max_connections} requested connections")
      while self.pool.empty() == False:
        self.pool.get().close()
      raise Exception(f"Failed to create {max_connections} connections. Only {actual_connections} connections were created successfully. This might be due to MySQL max_connections limit or system resource constraints.")

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
  
  # 获取当前连接池大小
  def get_pool_size(self):
    return self.pool.qsize()
  
  # 检查MySQL连接限制
  def check_mysql_limits(self):
    try:
      conn = self.pool.get()
      with conn.cursor() as cursor:
        cursor.execute("SHOW VARIABLES LIKE 'max_connections'")
        result = cursor.fetchone()
        max_conn = result[1] if result else "Unknown"
        
        cursor.execute("SHOW STATUS LIKE 'Threads_connected'")
        result = cursor.fetchone()
        current_conn = result[1] if result else "Unknown"
        
        cursor.execute("SHOW STATUS LIKE 'Max_used_connections'")
        result = cursor.fetchone()
        max_used = result[1] if result else "Unknown"
        
        print(f"MySQL Status:")
        print(f"  Max connections allowed: {max_conn}")
        print(f"  Current connections: {current_conn}")
        print(f"  Max connections used: {max_used}")
        
      self.pool.put(conn)
      return max_conn, current_conn, max_used
    except Exception as e:
      print(f"Error checking MySQL limits: {e}")
      return None, None, None