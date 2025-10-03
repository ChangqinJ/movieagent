from time import sleep
from main_thread import main_thread, args_of_func
from concurrent.futures import ThreadPoolExecutor, Future
import test

def test_func(args:args_of_func):
  print(args.prompt,"|",args.uuid,"|",args.width,"|",args.height)
  return 

def test_func2(package:dict[str,any]) -> tuple[int,None|str]:
  '''
  package:{'id','task_uuid','prompt','width','height'}
  '''
  if not package['prompt']:
    return package['id'],'prompt is None'
  else:
    print(package['id'],"|",package['task_uuid'],"|",package['prompt'],"|",package['width'],"|",package['height'])
    return package['id'],None

def test_callback(future:Future):
  print('result:',test.generate_text())

try:
  mth = main_thread(func=test_func2,base_dir='./base_dir',host='127.0.0.1',port=3306,user='root',password='tkp040629',db='esports')
except Exception as e:
  print(e)
  exit()
  
# mth.fetch_status0()
# if mth.queue.empty():
#   print('no data')
#   exit()
# else:
# while not mth.queue.empty():
#   row = mth.queue.get()
#   print(list(row.values()))


mth.run(10,10)
mth.close()
print('success')

# mysql -h testapi.fuhu.tech -P 3306 -u ai_creator -p'ai_creator123456'
# fut_list = []
# i = 100
# with ThreadPoolExecutor(max_workers=10) as executor:
#   while i > 0:
#     future = executor.submit(test_func,args_of_func(test.generate_text(),test.generate_text(),1024,1024))
#     future.add_done_callback(test_callback)
#     fut_list.append(future)
#     i -= 1
# print('success')
  