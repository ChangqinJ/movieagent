import asyncio
from pipelines.idea2video_pipeline import Idea2SVideoPipeline

idea = "The science fiction novel Dune, only two characters."
style = "二次元"
pipeline = Idea2SVideoPipeline.init_from_config(
    config_path="configs/idea2video.yaml",
    working_dir=".working_dir/idea2video_pipeline_test",
)

asyncio.run(pipeline(idea=idea, style=style))
