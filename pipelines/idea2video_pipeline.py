from pipelines.base import BasePipeline
import os
import logging
from pipelines.idea2script_pipeline import Idea2ScriptPipeline
from pipelines.script2video_pipeline import Script2VideoPipeline

class Idea2SVideoPipeline(BasePipeline):

    async def __call__(
        self,
        idea: str,
        style: str,
        dbpool=None,
        id=None,
        op_path=None,
        task_uuid=None
    ): 
        script = await self.idea2script_pipeline(idea=idea)
        await self.script2video_pipeline(script=script, style=style, dbpool=dbpool, id=id, op_path=op_path,task_uuid=task_uuid)

        pass

