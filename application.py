import asyncio
from pipelines.novel2movie_pipeline import Novel2MoviePipeline
from pipelines.script2video_pipeline import Script2VideoPipeline
from pipelines.idea2video_pipeline import Idea2SVideoPipeline
import  logging 
import os

def genVideo(package, dbpool):
    try:
        logging.basicConfig(level=logging.WARNING)
        prompt = package["prompt"]
        task_uuid = package["task_uuid"]
        width = package["width"]
        height = package["height"]
        style = "Realistic"
        id = package["id"]
        os.makedirs(f".working_dir/{task_uuid}", exist_ok=True)
        with open(f".working_dir/{task_uuid}/prompt.txt", "w", encoding="utf-8") as f:
            f.write(prompt)

        with open(f".working_dir/{task_uuid}/prompt.txt", "r", encoding="utf-8") as f:
            prompt_d = f.read()
        # novel_path = r"example_inputs\novels\刘慈欣\第07篇《流浪地球》.txt"
        # novel_path = r"script.txt"
        # style = "Realistic"
        # 可用音色
        vocal_map = {
            "Female1": "en_female_nadia_tips_emo_v2_mars_bigtts",
            "Female2": "en_female_skye_emo_v2_mars_bigtts",
            "Male1": "en_male_glen_emo_v2_mars_bigtts",
            "Male2": "en_male_sylus_emo_v2_mars_bigtts",
            "Male3": "en_male_corey_emo_v2_mars_bigtts"
        }
        # 可用情感
        emotion_list = ["affectionate", "angry", "chat","excited", "happy", "neutral", "sad", "warm"]

        pipeline = Idea2SVideoPipeline.init_from_config(
            config_path="configs/idea2video.yaml",
            working_dir=f".working_dir/{task_uuid}",
        )

        # Set vocal configuration for the pipeline
        pipeline.vocal_map = vocal_map
        pipeline.emotion_list = emotion_list

        # 执行pipeline
        asyncio.run(pipeline(prompt_d, style=style,dbpool=dbpool, id=id))
        return (id, None)
    except Exception as e:
        logging.error(f"发生异常： {e}")
        return (id, str(e))


