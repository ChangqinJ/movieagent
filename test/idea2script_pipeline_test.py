from pipelines.idea2script_pipeline import Idea2ScriptPipeline
import asyncio

idea = "The science fiction novel Dune, only two characters."
pipeline = Idea2ScriptPipeline.init_from_config(
    config_path="configs/idea2script.yaml",
    working_dir=".working_dir/idea2script_pipeline_test",
)

asyncio.run(pipeline(idea=idea))
