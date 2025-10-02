import asyncio
from pipelines.novel2movie_pipeline import Novel2MoviePipeline
from pipelines.script2video_pipeline import Script2VideoPipeline
import  logging


logging.basicConfig(level=logging.WARNING)

# novel_path = r"example_inputs\novels\刘慈欣\第07篇《流浪地球》.txt"
novel_path = r"script.txt"
style = "Realistic"
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

novel_text = open(novel_path, "r", encoding="utf-8").read()
pipeline = Script2VideoPipeline.init_from_config(
    config_path="configs/script2video.yaml",
    working_dir=".working_dir/7",
)

# Set vocal configuration for the pipeline
pipeline.vocal_map = vocal_map
pipeline.emotion_list = emotion_list

asyncio.run(pipeline(novel_text, style=style))


