import asyncio
from pipelines.script2video_pipeline import Script2VideoPipeline


config_path = r"configs/script2video.yaml"
script_path = r"example_inputs\shot_video_scripts/3-无间道.txt"
working_dir = ".working_dir/script2video_pipeline_test/3-无间道"
style = "anime"

pipeline = Script2VideoPipeline.init_from_config(
    config_path=config_path,
    working_dir=working_dir,
)

script = open(script_path, "r", encoding="utf-8").read()
asyncio.run(pipeline(script=script, style=style))
