import asyncio
from pipelines.novel2movie_pipeline import Novel2MoviePipeline
from pipelines.script2video_pipeline import Script2VideoPipeline
import  logging
import base64
import os

def main(package):
    """
    处理小说/剧本生成视频的主函数
    
    Args:
        novel_path: 小说/剧本文件路径
        style: 视频风格 (如 "Realistic")
        working_dir_id: 工作目录ID，用于区分不同任务 (默认为"7")
    
    Returns:
        处理结果
    """
    logging.basicConfig(level=logging.WARNING)
    prompt = package["prompt"]
    task_uuid = package["task_uuid"]
    width = package["width"]
    height = package["height"]
    style = "Realistic"
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
    
if __name__ == "__main__":
    prompt_text = """
@ -0,0 +1,188 @@
The Midnight Gardener
A Short Film Script
CHARACTER DESCRIPTIONS & VOICE NOTES:
​​ARTHUR PENDELTON​​ (68) - A retired botanist with an eccentric obsession with rare moon-blooming flowers
Voice: Soft, scholarly, with a breathless excitement when discussing plants. Speaks in measured, precise sentences, except when overcome by botanical passion.
​​ELEANOR PENDELTON​​ (65) - Arthur's wife, a light sleeper who cheroses her nightly routine and a full eight hours
Voice: Crisp, articulate, with a weary patience that frays quickly. Can convey immense disapproval with a single sigh.
SCENE 1: BEDROOM - 11:45 PM
A dark, quiet bedroom. The only light comes from the moon through the window. The sound of careful, shuffling footsteps. A drawer opens with a faint CREAK. ELEANOR's eyes snap open.
​​ELEANOR:​​ (into the darkness, voice thick with sleep) Arthur? What in heaven's name...?
​​ARTHUR:​​ (stage whisper, brimming with excitement) Shhh, my dear. Go back to sleep. The Selenicereus grandiflorus... it's the night. It will only bloom for a few hours!
​​ELEANOR:​​ (propping herself up on her elbows) It is nearly midnight. You are not going out to talk to the cactus.
​​FADE OUT.​​
​​THE END​​
PRODUCTION NOTES:
Locations needed: Suburban bedroom, hallway, backyard greenhouse, garden
Key props: Botanical journal, special gardening tools, watering can, headlamp, a magnificent (practical or CGI) night-blooming cereus flower.
Tone: Whimsical character study about passion, patience, and the quiet compromises of a long marriage.
Theme: The secret lives we lead after dark, and the beauty found in patience and peculiar obsessions."""
    
    package = {
        "prompt": prompt_text,
        "task_uuid": "1923",
        "width": 1920,
        "height": 1080
    }
    main(package)


