from main_thread import main_thread, main_thread_with_config, main_thread_cfg_init
from DBpool import DBpool
from application import genVideo

mth = main_thread_cfg_init(genVideo, path_config='./movie_agent_config.json')
mth.run()

