from pipelines.base import BasePipeline
import os
import logging


class Idea2ScriptPipeline(BasePipeline):

    async def __call__(
        self,
        idea: str,
    ):
        print("🧠 BRAINSTORMING MODE: Expanding basic idea into a full script")

        planned_script = await self.script_planner.plan_script(basic_idea=idea)
        planned_path = os.path.join(self.working_dir, "planned_script.txt")
        with open(planned_path, "w", encoding="utf-8") as f:
            f.write(planned_script)
            
        print(f"🧠 Planned script saved to {planned_path}")

        print("✨ Enhancing planned script...") 
        enhanced_script = await self.script_enhancer.enhance_script(planned_script=planned_script)
        enhanced_path = os.path.join(self.working_dir, "enhanced_script.txt")
        with open(enhanced_path, "w", encoding="utf-8") as f:
            f.write(enhanced_script)

        print(f"✨ Enhanced script saved to {enhanced_path}")

        return enhanced_script
