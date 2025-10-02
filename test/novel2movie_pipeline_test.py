import asyncio
from pipelines.novel2movie_pipeline import Novel2MoviePipeline
import  logging


logging.basicConfig(level=logging.WARNING)

# novel_path = r"example_inputs\novels\刘慈欣\第07篇《流浪地球》.txt"
novel_path = r"example_inputs\novels\刘慈欣\第48篇《三体》.txt"
style = "电影写实风格"

novel_text = open(novel_path, "r", encoding="utf-8").read()
pipeline = Novel2MoviePipeline.init_from_config(
    config_path="configs/novel2movie.yaml",
    working_dir=".working_dir/pipeline_test",
)

asyncio.run(pipeline(novel_text, style=style))


