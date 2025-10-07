import random
import string
import pymysql
from datetime import datetime

def generate_random_string(length:int=20):
  return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_random_date() -> str:
  return datetime.now().strftime('%Y-%m-%d')

def random_num_0_to_3() -> int:
  return random.randint(0,3)

# if __name__ == '__main__':
#   print(generate_random_string(20))

if __name__ == '__main__':
  #向数据库中插入1000条数据
  conn = pymysql.connect(host='127.0.0.1',port=3306,user='root',password='tkp040629',database='esports')
  with conn.cursor() as cursor:
    placeholders = ','.join(['%s']*11)
    for i in range(1000):
      cursor.execute(f'insert into movie_agent_tasks values ({placeholders})',(
      None,
      generate_random_date(),
      generate_random_date(),
      generate_random_date(),
      generate_random_string(100),
      generate_random_string(20),
      1024,
      1024,
      random_num_0_to_3(),
      0,
      generate_random_string(20),
      ))
    conn.commit()
  conn.close()
  print('insert 1000 rows success')

# if __name__ == '__main__':
#   conn = pymysql.connect(host='testapi.fuhu.tech',port=3306,user='ai_creator',password='ai_creator123456',database='esports')
#   with conn.cursor() as cursor:
#     cursor.execute('select * from movie_agent_tasks where state in (0,1,2)')
#     conn.commit()
#     rows = cursor.fetchall()
#     for row in rows:
#       print(row)
#   conn.close()