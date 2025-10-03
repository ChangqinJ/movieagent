import asyncio
from pipelines.novel2movie_pipeline import Novel2MoviePipeline
from pipelines.script2video_pipeline import Script2VideoPipeline
import  logging 
import os

def genVideo(package):
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

        pipeline = Script2VideoPipeline.init_from_config(
            config_path="configs/script2video.yaml",
            working_dir=f".working_dir/{task_uuid}",
        )

        # Set vocal configuration for the pipeline
        pipeline.vocal_map = vocal_map
        pipeline.emotion_list = emotion_list

        # 执行pipeline
        asyncio.run(pipeline(prompt_d, style=style))
        return (id, "成功生成")
    except Exception as e:
        logging.error(f"发生异常： {e}")
        return (id, str(e))

# 运行示例
if __name__ == "__main__":
    prompt_text = """
@ -0,0 +1,188 @@
# The Midnight Baker
## A Short Film Script

### CHARACTER DESCRIPTIONS & VOICE NOTES:

**MARK RIVERA** (38) - A graphic designer with a compulsive need to bake perfect sourdough bread
- Voice: Usually calm and measured, but becomes animated and slightly frantic when discussing fermentation or crust development

**SARAH RIVERA** (36) - Mark's wife, a light sleeper with a low tolerance for 3 AM kitchen noise
- Voice: Sleepy but sharp, capable of conveying deep disapproval through muffled pillow-talk

### SCENE 1: KITCHEN - 3:15 AM

*Dark apartment kitchen illuminated only by the glow of the oven light. MARK is carefully scoring a proofed loaf. The faint sound of jazz piano plays from his phone. SARAH appears in the doorway, squinting against the light.*

**SARAH:** (muffled by sleep) Mark... are you baking? Again?

**MARK:** (jumping slightly) Shh, the bulk fermentation was perfect today. This is the window.

**SARAH:** (rubbing eyes) It's three AM. The window for normal people is for sleeping.

**FADE OUT.**

---

**THE END**

### PRODUCTION NOTES:
- Locations needed: Apartment kitchen, bedroom doorway, bakery (flashback)
- Key props: Stand mixer, banneton basket, lame, digital scale, perfectly crusty loaf
- Tone: Quirky domestic comedy about obsession and compromise
- Theme: The pursuit of perfection in imperfect circumstances"""
    
    package = {
        "prompt": prompt_text,
        "task_uuid": "c124d1a2",
        "width": 1920,
        "height": 1080,
        "id": 2
    }
    print(genVideo(package)[1])


