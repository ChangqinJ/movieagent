import os
import shutil
import json
import logging
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, List
from PIL import Image
from moviepy.editor import VideoFileClip
from tenacity import retry

from pipelines.base import BasePipeline
from tools.image_generator.base import ImageGeneratorOutput
from tools.video_generator.base import VideoGeneratorOutput, BaseVideoGenerator
from tools.audio_generator.doubao import TTSGenerator
from tools.video_audio_processor import VideoAudioProcessor
from components.character import CharacterInScene
from components.shot import Shot

def update_progress(dbpool, id, percent):
    conn = dbpool.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('UPDATE movie_agent_tasks SET progress = %s WHERE id = %s', (percent, id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        import logging
        logging.error(f"更新进度失败: {e}")
    finally:
        dbpool.put_connection(conn)
        
class Script2VideoPipeline(BasePipeline):
    """
    ----{working_dir}
        |---- characters
        |       |---- character_registry.json
        |       |---- {character_identifier_in_scene}.json
        |       |---- {character_identifier_in_scene}.png
        |---- shots
        |       |----reference_image_paths
        |       |       |----{shot_idx}_first_frame_reference.json
        |       |       |----{shot_idx}_last_frame_reference.json
        |       |----frame_candidates
        |       |       |----shot_{shot_idx}_first_frame
        |       |               |----0.png
        |       |       |----shot_{shot_idx}_last_frame
        |       |               |----0.png
        |       |----{shot_idx}.json
        |       |----{shot_idx}_first_frame.png
        |       |----{shot_idx}_last_frame.png
        |       |----{shot_idx}_video.mp4
        |       |----shot_{shot_idx}_vocal.wav
    """

    async def __call__(
        self,
        script: str,
        style: str,
        character_registry: Optional[Dict[str, List[Dict[str, str]]]] = None,
        dbpool = None,
        id = None,
        op_path: str = None,
        task_uuid: str = None
    ):
        import sys
        print(f"🔍 DEBUG: Current Python version: {sys.version}")
        print("🔍 DEBUG: Checking event loop status...")
        """
        Args:
            script (str): The input script for video generation.

            character_registry: Optional dictionary mapping character names to their descriptions.
            For example,
            {
                "Alice": [
                    {"path": "path/to/alice1.png", "description": "A front-view portrait of Alice."},
                    {"path": "path/to/alice2.png", "description": "A side-view portrait of Alice."},
                ],
                "Bob": [
                    {"path": "path/to/bob1.png", "description": "A front-view portrait of Bob."},
                ],
            }
        """
        self.output_path = op_path
        self.task_uuid = task_uuid
        print("="*60)
        print("🎬 STARTING VIDEO GENERATION PIPELINE")
        print("="*60)

        if character_registry is None:
            print("⭕ Phase 0: Extract characters and generate portraits...")
            start_time_0 = time.time()
            character_registry = await self._extract_characters_and_generate_portraits(
                script=script,
                style=style,
            )
            end_time_0 = time.time()
            # if dbpool and id:
            #     update_progress(dbpool, id, 20)
            print(f"✅ Phase 0 completed in {end_time_0 - start_time_0:.2f} seconds.")



        print("⭕ Phase 1: Design storyboard, generate frames and generate shots...")
        start_time_1 = time.time()
        try:
            print("🔄 Starting storyboard and shot generation...")
            await self._design_storyboard_and_generate_shots(
                script=script,
                character_registry=character_registry,
            )
            print("🔍 DEBUG: Returned from _design_storyboard_and_generate_shots")
            end_time_1 = time.time()
            # if dbpool and id:
            #     update_progress(dbpool, id, 40)
            print(f"✅ Phase 1 completed in {end_time_1 - start_time_1:.2f} seconds.")
        except Exception as e:
            print(f"❌ Error in Phase 1: {str(e)}")
            logging.exception("Phase 1 error details:")

        print("⭕ Phase 2: Generate vocal...")
        print("🔍 DEBUG: Starting Phase 2")
        try:
            start_time_2 = time.time()
            # 确保事件循环仍在运行
            loop = asyncio.get_event_loop()
            if not loop.is_running():
                print("⚠️ Warning: Event loop is not running at start of Phase 2")
                # 尝试重新启动事件循环
                asyncio.set_event_loop(asyncio.new_event_loop())
            await asyncio.sleep(0)  # 插入一个检查点
            await self._generate_shot_vocal()
            print("🔍 DEBUG: Completed Phase 2 main task")
            end_time_2 = time.time()
            # if dbpool and id:
            #     update_progress(dbpool, id, 60)
        except Exception as e:
            print(f"❌ Error in Phase 2: {str(e)}")
            logging.exception("Phase 2 error details:")
        print(f"✅ Phase 2 completed in {end_time_2 - start_time_2:.2f} seconds.")

        print("⭕ Phase 3: Synchronize audio with video...")
        start_time_3 = time.time()
        await self._synchronize_audio_video()
        end_time_3 = time.time()
        # if dbpool and id:
        #     update_progress(dbpool, id, 80)
        print(f"✅ Phase 3 completed in {end_time_3 - start_time_3:.2f} seconds.")

        print("⭕ Phase 4: Combine all processed shots into final video...")
        start_time_4 = time.time()
        await self._combine_final_video()
        end_time_4 = time.time()
        # if dbpool and id:
        #     update_progress(dbpool, id, 100)
        print(f"✅ Phase 4 completed in {end_time_4 - start_time_4:.2f} seconds.")

        print("="*60)
        print("🎉 VIDEO GENERATION PIPELINE COMPLETED SUCCESSFULLY!")
        print("="*60)



    async def _extract_characters_and_generate_portraits(
        self,
        script: str,
        style: str,
    ):
        working_dir_characters = os.path.join(self.working_dir, "characters")
        os.makedirs(working_dir_characters, exist_ok=True)
        print(f"🗂️ Working directory: {working_dir_characters} ")

        character_registry_path = os.path.join(working_dir_characters, "character_registry.json")
        if os.path.exists(character_registry_path):
            with open(character_registry_path, 'r', encoding='utf-8') as f:
                character_registry = json.load(f)
        else:
            character_registry = {}


        # Load or generate vocal mapping for characters
        vocal_mapping_path = os.path.join(working_dir_characters, "character_vocal_mapping.json")
        
        # Extract characters from script if not provided
        if len(character_registry) > 0:
            characters = []
            for identifier_in_scene in list(character_registry.keys()):
                with open(os.path.join(working_dir_characters, f"{identifier_in_scene}.json"), 'r', encoding='utf-8') as f:
                    character_data = json.load(f)
                    character = CharacterInScene.model_validate(character_data)
                    characters.append(character)
            print(f"⏭️ Skipped character extraction, loaded {len(characters)} characters from existing registry.")
        else:
            print(f"⬜ Extracting characters from script...")
            characters: list[CharacterInScene] = await self.character_extractor(script)
            for character in characters:
                with open(os.path.join(working_dir_characters, f"{character.identifier_in_scene}.json"), 'w', encoding='utf-8') as f:
                    json.dump(character.model_dump(), f, ensure_ascii=False, indent=4)
                character_registry[character.identifier_in_scene] = []
            print(f"☑️ Extracted {len(characters)} characters from script.")

        # Generate vocal mapping for characters
        if os.path.exists(vocal_mapping_path):
            with open(vocal_mapping_path, 'r', encoding='utf-8') as f:
                character_vocal_mapping = json.load(f)
            print(f"⏭️ Skipped vocal mapping generation, loaded existing mapping for {len(character_vocal_mapping)} characters.")
            # Print mapping for user information
            print("📢 Character vocal mapping:")
            for char_name, voice_type in character_vocal_mapping.items():
                print(f"   {char_name} -> {voice_type}")
        else:
            print(f"⬜ Generating vocal mapping for characters...")
            character_vocal_mapping = await self.vocal_mapper.assign_vocal_mapping(characters)
            with open(vocal_mapping_path, 'w', encoding='utf-8') as f:
                json.dump(character_vocal_mapping, f, ensure_ascii=False, indent=4)
            print(f"☑️ Generated vocal mapping for {len(character_vocal_mapping)} characters and saved to {vocal_mapping_path}.")
            
            # Print mapping for user information
            print("📢 Character vocal mapping:")
            for char_name, voice_type in character_vocal_mapping.items():
                print(f"   {char_name} -> {voice_type}")

        # Store the character vocal mapping in pipeline for later use
        self.character_vocal_mapping = character_vocal_mapping


        # Generate portraits for each character if not provided
        prompt_template = "Generate a full-body, front-view portrait of a character based on the following description, with an empty background. The character should be centered in the image, occupying most of the frame. Gazing straight ahead. Standing with arms relaxed at sides. Natural expression.\nfeatures: {features} \nstyle: {style}"

        async def generate_portrait_for_single_character(sem, character: CharacterInScene):
            if len(character_registry[character.identifier_in_scene]) == 0:
                async with sem:
                    features = "(static)" + character.static_features + ", (dynamic)" + character.dynamic_features
                    prompt = prompt_template.format(features=features, style=style)
                    image: ImageGeneratorOutput = await self.image_generator.generate_single_image(
                        prompt=prompt,
                        size="512x512",
                    )
                    portrait_path = os.path.join(working_dir_characters, f"{character.identifier_in_scene}.png")
                    image.save(portrait_path)
                    return character, portrait_path, "A front-view portrait of " + character.identifier_in_scene + "."
            else:
                print(f"⏭️ Skipped portrait generation for {character.identifier_in_scene}, already exists in registry.")
                return character, None, None

        sem = asyncio.Semaphore(3)
        tasks = []
        for character in characters:
            tasks.append(generate_portrait_for_single_character(sem, character))

        if len(tasks) > 0:
            print(f"⬜ Generating portraits for characters...")
        else:
            print(f"⏭️ Skipped portrait generation, all characters already exist in registry.")

        for task in asyncio.as_completed(tasks):
            character, portrait_path, description = await task
            if portrait_path is not None:
                character_registry[character.identifier_in_scene].append({
                    "path": portrait_path,
                    "description": description,
                })
                with open(character_registry_path, 'w', encoding='utf-8') as f:
                    json.dump(character_registry, f, ensure_ascii=False, indent=4)
                print(f"✔️ Generated portrait for {character.identifier_in_scene}, saved to {portrait_path}, and updated registry.")

        print(f"☑️ Finished generating portraits for characters.")

        return character_registry


    async def _design_storyboard_and_generate_shots(
        self,
        script: str,
        character_registry: Dict[str, List[Dict[str, str]]],
    ):
        working_dir = os.path.join(self.working_dir, "shots")
        os.makedirs(working_dir, exist_ok=True)
        print(f"🗂️ Working directory: {working_dir} ")

        reference_image_paths_dir = os.path.join(working_dir, "reference_image_paths")
        os.makedirs(reference_image_paths_dir, exist_ok=True)
        frame_candidates_dir = os.path.join(working_dir, "frame_candidates")
        os.makedirs(frame_candidates_dir, exist_ok=True)

        characters_identifiers = list(character_registry.keys())


        video_futures = []
        executor = ThreadPoolExecutor(max_workers=1)


        available_image_path_and_text_pairs = []
        for character_identifier, portraits in character_registry.items():
            for portrait in portraits:
                available_image_path_and_text_pairs.append((portrait["path"], portrait["description"]))


        # Design storyboard and generate frames
        print(f"⬜ Designing storyboard and generating frames...")
        existing_shots = []
        while True:
            current_shot_idx = len(existing_shots)
            print(f"   🎬 Processing shot {current_shot_idx}...")

            # 1. Design next storyboard shot
            shot_description_path = os.path.join(working_dir, f"{current_shot_idx}.json")
            if os.path.exists(shot_description_path):
                with open(shot_description_path, 'r', encoding='utf-8') as f:
                    shot_data = json.load(f)
                shot_description = Shot.model_validate(shot_data)
                print(f"⏭️ Skipped designing shot {current_shot_idx}, loaded from existing file.")
            else:
                start_time_design_shot = time.time()
                shot_description: Shot = await self.storyboard_generator.get_next_shot_description(
                    script=script,
                    character_identifiers=characters_identifiers,
                    existing_shots=existing_shots,
                )
                with open(shot_description_path, 'w', encoding='utf-8') as f:
                    json.dump(shot_description.model_dump(), f, ensure_ascii=False, indent=4)
                end_time_design_shot = time.time()
                duration_design_shot = end_time_design_shot - start_time_design_shot
                print(f"☑️ Designed new shot {current_shot_idx} and saved to {shot_description_path} (took {duration_design_shot:.2f} seconds).")

            existing_shots.append(shot_description)

            # 2. generate first (and last) frame candidates for the shot
            for frame_type in ["first_frame", "last_frame"]:
                if not hasattr(shot_description, frame_type) or getattr(shot_description, frame_type) is None:
                    logging.info(f"Shot {current_shot_idx} does not require {frame_type}, skipping generation.")
                    continue

                best_save_path = os.path.join(working_dir, f"{current_shot_idx}_{frame_type}.png")
                if os.path.exists(best_save_path):
                    print(f"⏭️ Skipped generating {frame_type} for shot {current_shot_idx}, already exists.")
                    continue

                start_time_generate_frame = time.time()

                # 2.1 select reference image and generate guidance prompt
                ref_path = os.path.join(reference_image_paths_dir, f"{current_shot_idx}_{frame_type}_reference.json")
                if os.path.exists(ref_path):
                    with open(ref_path, 'r', encoding='utf-8') as f:
                        reference = json.load(f)
                    print(f"⏭️ Skipped selecting reference image for {frame_type} of shot {current_shot_idx}, loaded from existing file.")
                else:
                    start_time_select_reference = time.time()
                    reference = self.reference_image_selector(
                        frame_description=getattr(shot_description, frame_type),
                        available_image_path_and_text_pairs=available_image_path_and_text_pairs,
                    )
                    with open(ref_path, 'w', encoding='utf-8') as f:
                        json.dump(reference, f, ensure_ascii=False, indent=4)
                    end_time_select_reference = time.time()
                    print(f"☑️ Selected reference image for {frame_type} of shot {current_shot_idx} and saved to {ref_path} (took {end_time_select_reference - start_time_select_reference:.2f} seconds).")


                # 2.2 generate frame candidates
                num_candidates = 3
                cur_frame_candidates_dir = os.path.join(frame_candidates_dir, f"shot_{current_shot_idx}_{frame_type}")
                print(f"   🎨 Generating {frame_type} candidates for shot {current_shot_idx}...")
                os.makedirs(cur_frame_candidates_dir, exist_ok=True)
                existing_frames = os.listdir(cur_frame_candidates_dir)
                missing_indices = [i for i in range(num_candidates) if f"{i}.png" not in existing_frames]
                if len(existing_frames) >= num_candidates:
                    print(f"⏭️ Skipped generating {frame_type} for shot {current_shot_idx}, already have {len(existing_frames)} candidates.")
                else:
                    print(f"⬜ Generating {num_candidates - len(existing_frames)} candidates for {frame_type} of shot {current_shot_idx}...")
                    start_time_generate_candidates = time.time()
                    prompt = reference["text_prompt"]
                    reference_image_paths = [path for path, _ in reference["reference_image_path_and_text_pairs"]]
                    num_images = num_candidates - len(existing_frames)

                    tasks = []
                    for _ in range(num_images):
                        task = self.image_generator.generate_single_image(
                            prompt=prompt,
                            reference_image_paths=reference_image_paths,
                            size="1600x900",
                        )
                        tasks.append(task)
                    images: List[ImageGeneratorOutput] = await asyncio.gather(*tasks)
                    for idx, image in enumerate(images):
                        image_path = os.path.join(cur_frame_candidates_dir, f"{missing_indices[idx]}.png")
                        image.save(image_path)
                        print(f"✔️ Generated candidate {missing_indices[idx]} for {frame_type} of shot {current_shot_idx}, saved to {image_path}.")

                    # for idx, task in enumerate(asyncio.as_completed(tasks)):
                    #     image: ImageGeneratorOutput = await task
                    #     image_path = os.path.join(cur_frame_candidates_dir, f"{missing_indices[idx]}.png")
                    #     image.save(image_path)
                    #     print(f"✔️ Generated candidate {missing_indices[idx]} for {frame_type} of shot {current_shot_idx}, saved to {image_path}.")

                    end_time_generate_candidates = time.time()
                    print(f"☑️ Generated {num_images} candidates for {frame_type} of shot {current_shot_idx} (took {end_time_generate_candidates - start_time_generate_candidates:.2f} seconds).")

                # 2.3 select the best frame candidate
                print(f"🏆 Selecting best image from candidates...")
                start_time_select_best = time.time()
                ref_image_path_and_text_pairs = reference["reference_image_path_and_text_pairs"]
                target_description = getattr(shot_description, frame_type)
                candidate_image_paths = [os.path.join(cur_frame_candidates_dir, f) for f in os.listdir(cur_frame_candidates_dir)]
                best_image_path = await self.best_image_selector(
                    ref_image_path_and_text_pairs=ref_image_path_and_text_pairs,
                    target_description=target_description,
                    candidate_image_paths=candidate_image_paths,
                )
                shutil.copy(best_image_path, best_save_path)
                end_time_select_best = time.time()
                print(f"☑️ Selected best image for {frame_type} of shot {current_shot_idx} and saved to {best_save_path} (took {end_time_select_best - start_time_select_best:.2f} seconds).")

                end_time_generate_frame = time.time()
                duration_generate_frame = end_time_generate_frame - start_time_generate_frame
                print(f"☑️ Generated {frame_type} for shot {current_shot_idx} (took {duration_generate_frame:.2f} seconds).")


                available_image_path_and_text_pairs.append((best_save_path, target_description))


            #  Submit background video generation immediately after frames are ready

            video_path = os.path.join(working_dir, f"{shot_description.idx}_video.mp4")
            if os.path.exists(video_path):
                print(f"⏭️ Skipped generating video for shot {shot_description.idx}, already exists.")
            else:
                print(f" 🚀 Submitting background video generation for shot {shot_description.idx}...")
                frame_paths = []
                if hasattr(shot_description, "first_frame") and shot_description.first_frame:
                    first_frame_path = os.path.join(working_dir, f"{shot_description.idx}_first_frame.png")
                    frame_paths.append(first_frame_path)

                if hasattr(shot_description, "last_frame") and shot_description.last_frame:
                    last_frame_path = os.path.join(working_dir, f"{shot_description.idx}_last_frame.png")
                    frame_paths.append(last_frame_path)
                future = executor.submit(
                    self._run_video_with_retries,
                    shot_description.visual_content,
                    frame_paths,
                    video_path,
                    3, # max_attempts=3,
                    5, # delay seconds
                )
                ensure_start_deadline = time.time() + 1.0
                while not future.running() and time.time() < ensure_start_deadline:
                    time.sleep(0.05)
                if future.running():
                    print(f"   ▶️ Video task is running for shot {shot_description.idx}")
                video_futures.append((shot_description.idx, future))

            if shot_description.is_last:
                break


        if video_futures:
            print(f"⏳ Waiting for {len(video_futures)} background video task(s) to complete...")
            wait_start = time.time()
            for shot_idx, future in video_futures:
                try:
                    future.result()  
                    print(f"   ✅ Video task completed for shot {shot_idx} ")
                except Exception as e:
                    logging.error(f"Video generation task failed for shot {shot_idx}: {e}")
                    print(f"   ❌ Video task failed for shot {shot_idx}: {str(e)}")
            wait_duration = time.time() - wait_start
            print(f"✅ All background video tasks completed in {wait_duration:.2f}s")
        else:
            print("📁 All videos already exist, skipping generation")
        executor.shutdown(wait=True)
        

    def _run_video_with_retries(
        self,
        prompt: str,
        frame_paths: list,
        save_path: str,
        max_attempts: int = 3,
        delay_seconds: float = 5.0,
    ) -> str:
        """Run video generation with retries in synchronous context."""
        last_error = None
        for attempt in range(1, max_attempts + 1):
            try:
                logging.info(f"[VideoRetry] Attempt {attempt}/{max_attempts} for {save_path}")
                
                # 在同步上下文中运行异步视频生成
                try:
                    # 尝试使用 asyncio.run()
                    video = asyncio.run(self.video_generator.generate_single_video(prompt, frame_paths))
                except RuntimeError as e:
                    # 如果已经有运行的事件循环，使用不同的方法
                    if "asyncio.run() cannot be called from a running event loop" in str(e):
                        # 在当前线程中创建新的事件循环
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            video = loop.run_until_complete(self.video_generator.generate_single_video(prompt, frame_paths))
                        finally:
                            loop.close()
                    else:
                        raise
                
                video.save(save_path)
                if os.path.exists(save_path):
                    logging.info(f"[VideoRetry] Success on attempt {attempt} for {save_path}")
                    return save_path
                else:
                    logging.warning(f"[VideoRetry] No output file after attempt {attempt} for {save_path}")
            except Exception as e:
                last_error = e
                logging.error(f"[VideoRetry] Exception on attempt {attempt} for {save_path}: {e}")
            if attempt < max_attempts:
                time.sleep(delay_seconds)
        # If we get here, all attempts failed
        error_message = f"Video generation failed after {max_attempts} attempts for {save_path}"
        if last_error:
            raise RuntimeError(error_message) from last_error
        raise RuntimeError(error_message)
    


        # print(f"✅ Designed storyboard and generated all frames.")
        # self.video_generator: BaseVideoGenerator

        # shots = existing_shots
        # # Generate video for the shot
        # async def generate_video_for_single_shot(sem, shot: Shot):
        #     async with sem:
        #         video_path = os.path.join(working_dir, f"{shot.idx}_video.mp4")
        #         if os.path.exists(video_path):
        #             print(f"⏭️ Skipped generating video for shot {shot.idx}, already exists.")
        #             return

        #         reference_image_paths = []

        #         if hasattr(shot, "first_frame") and shot.first_frame:
        #             first_frame_path = os.path.join(working_dir, f"{shot.idx}_first_frame.png")
        #             reference_image_paths.append(first_frame_path)
        #         if hasattr(shot, "last_frame") and shot.last_frame:
        #             last_frame_path = os.path.join(working_dir, f"{shot.idx}_last_frame.png")
        #             reference_image_paths.append(last_frame_path)

        #         prompt = shot.visual_content
        #         video: VideoGeneratorOutput = await self.video_generator.generate_single_video(
        #             prompt=prompt,
        #             reference_image_paths=reference_image_paths,
        #         )
        #         video.save(video_path)
        #         print(f"☑️ Generated video for shot {shot.index} and saved to {video_path}.")


        # # Generate video for the shot
        # sem = asyncio.Semaphore(3)
        # tasks = []
        # for shot in shots:
        #     tasks.append(generate_video_for_single_shot(sem, shot))

        # await asyncio.gather(*tasks)
        # print(f"✅ Finished generating videos for all shots.")


    async def _generate_shot_vocal(self):
        shots_dir = os.path.join(self.working_dir, "shots")
        
        # Load character vocal mapping created during character extraction
        character_vocal_mapping = getattr(self, 'character_vocal_mapping', {})
        if not character_vocal_mapping:
            print(f"⚠️ No character vocal mapping found, skipping vocal generation")
            return
        
        # Define vocal_map with actual voice type strings  
        vocal_map = getattr(self, 'vocal_map', {
            "Female1": "en_female_nadia_tips_emo_v2_mars_bigtts",
            "Female2": "en_female_skye_emo_v2_mars_bigtts",
            "Male1": "en_male_glen_emo_v2_mars_bigtts",
            "Male2": "en_male_sylus_emo_v2_mars_bigtts",
            "Male3": "en_male_corey_emo_v2_mars_bigtts"
        })
        
        # Get available emotions from pipeline configuration (set in main.py)
        emotion_list = getattr(self, 'emotion_list', ["affectionate", "angry", "chat", "excited", "happy", "neutral", "sad", "warm"])
        
        print("⬜ Generating vocal for shots...")
        print(f"📋 Character vocal mapping: {character_vocal_mapping}")
        print(f"🎭 Available emotions: {emotion_list}")
        
        idx = 0
        while True:
            shot_file = os.path.join(shots_dir, f"{idx}.json")
            
            # Check if shot file exists
            if not os.path.exists(shot_file):
                break
                
            print(f"🎬 Processing shot {idx}...")
            
            # Load shot data
            with open(shot_file, "r", encoding="utf-8") as f:
                shot_json = json.load(f)
            
            video_file = os.path.join(shots_dir, f"{idx}_video.mp4")
            
            # Check if this shot has a speaker and dialogue
            if shot_json.get("speaker") is None or shot_json.get("line") is None:
                print(f"   ⏭️ Shot {idx} has no speaker/dialogue, keeping original video audio")
                idx += 1
                continue
                
            # This shot has speaker and dialogue, need to process audio
            speaker = shot_json["speaker"]
            line = shot_json["line"]
            emotion = shot_json.get("emotion", "neutral")  # Default to neutral if no emotion specified
            
            # Validate emotion
            if emotion not in emotion_list:
                print(f"   ⚠️ Unknown emotion '{emotion}' for shot {idx}, using 'neutral' instead")
                emotion = "neutral"
            
            # Check if speaker exists in character_vocal_mapping
            if speaker not in character_vocal_mapping:
                print(f"   ⚠️ Speaker '{speaker}' not found in character vocal mapping, skipping shot {idx}")
                print(f"       Available speakers: {list(character_vocal_mapping.keys())}")
                idx += 1
                continue
            
            # Get voice type from character mapping and then actual voice string
            voice_key = character_vocal_mapping[speaker]  # e.g., "Female1"
            if voice_key not in vocal_map:
                print(f"   ⚠️ Voice key '{voice_key}' not found in vocal_map, skipping shot {idx}")
                idx += 1
                continue
                
            voice_type = vocal_map[voice_key]  # e.g., "en_female_nadia_tips_emo_v2_mars_bigtts"
            shots_dir = os.path.join(self.working_dir, "shots")
            audio_filename = os.path.join(shots_dir, f"shot_{idx}_vocal.wav")
            
            # First, mute the video file if it exists and we need to add new audio
            if os.path.exists(video_file):
                try:
                    print(f"   🔇 Muting original video audio for shot {idx}...")
                    
                    # Suppress MoviePy warnings for corrupted frames
                    import warnings
                    with warnings.catch_warnings():
                        warnings.filterwarnings("ignore", message=".*bytes wanted but.*bytes read.*")
                        warnings.filterwarnings("ignore", message=".*Using the last valid frame instead.*")
                        
                        video = VideoFileClip(video_file)
                        
                        # Check if video is valid and has frames
                        if video.duration > 0:
                            video_silent = video.without_audio()
                            # Use temp file to avoid corruption during write
                            # Create temp file with proper extension in a temp directory first
                            import tempfile
                            import shutil
                            
                            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
                                temp_video_file = temp_file.name
                            
                            video_silent.write_videofile(
                                temp_video_file, 
                                codec='libx264', 
                                audio_codec=None, 
                                logger=None,
                                verbose=False
                            )
                            video.close()
                            video_silent.close()
                            
                            # Replace original with temp file
                            shutil.move(temp_video_file, video_file)
                            print(f"   ✅ Muted original video audio for shot {idx}")
                        else:
                            video.close()
                            print(f"   ⚠️ Video file for shot {idx} appears to be empty or corrupted")
                            
                except Exception as e:
                    print(f"   ⚠️ Failed to mute video for shot {idx}: {str(e)}")
                    logging.warning(f"Failed to mute video for shot {idx}: {e}")
                    # Clean up temp file if it exists (temp files are auto-generated, so we try to clean up any that might exist)
                    try:
                        # tempfile creates files in system temp dir, if something went wrong they should be cleaned up automatically
                        # but let's make sure the video clips are closed
                        pass
                    except:
                        pass
            
            # Skip if audio file already exists
            if os.path.exists(audio_filename):
                print(f"   ⏭️ Audio file already exists for shot {idx}, skipping generation")
            else:
                try:
                    print(f"   🎤 Generating vocal for shot {idx}:")
                    print(f"       Speaker: {speaker} -> {voice_key} (voice: {voice_type})")
                    print(f"       Emotion: {emotion}")
                    print(f"       Text: {line[:50]}{'...' if len(line) > 50 else ''}")
                    
                    # Create TTS generator with the voice type for this speaker
                    tts_generator = TTSGenerator(voice_type=voice_type)
                    
                    # Generate vocal audio - save to working directory
                    generated_path = await tts_generator.generate_shot_vocal(
                        text=line,
                        emotion=emotion,
                        output_filename=audio_filename
                    )
                    
                    print(f"   ✅ Generated vocal for shot {idx}, saved to {generated_path}")
                    
                except Exception as e:
                    print(f"   ❌ Failed to generate vocal for shot {idx}: {str(e)}")
                    logging.error(f"Vocal generation failed for shot {idx}: {e}")
            
            idx += 1
        
        print(f"☑️ Finished processing vocal for {idx} shots.")

    async def _synchronize_audio_video(self):
        """Synchronize generated audio with video using multimodal analysis"""
        try:
            # Get API configuration from pipeline config
            api_key = getattr(self, 'multimodal_api_key', '{YOUR_API_KEY}')
            auth_token = getattr(self, 'multimodal_auth_token', '<token>')
            
            if api_key == '{YOUR_API_KEY}':
                print("Multimodal API key not configured, skipping audio-video synchronization")
                print("⚠️ Multimodal API key not configured, skipping audio-video synchronization")
                print("   Please set 'multimodal_api_key' and 'multimodal_auth_token' in your pipeline configuration")
                return
            
            # Initialize video-audio processor
            processor = VideoAudioProcessor(api_key=api_key, auth_token=auth_token)
            
            shots_dir = os.path.join(self.working_dir, "shots")
            temp_dir = os.path.join(self.working_dir, "temp_audio_sync")
            
            print("⬜ Analyzing videos and synchronizing audio...")
            
            # Process all shots for audio synchronization
            synchronized_videos = processor.process_multiple_shots(
                shots_dir=shots_dir,
                working_dir=self.working_dir,
                temp_dir=temp_dir
            )
            
            if synchronized_videos:
                print(f"☑️ Successfully synchronized audio for {len(synchronized_videos)} shots")
                
                # Optional: Replace original videos with synchronized ones
                replace_originals = getattr(self, 'replace_original_videos', True)
                if replace_originals:
                    print("⬜ Replacing original videos with synchronized versions...")
                    for i, synced_video in enumerate(synchronized_videos):
                        original_video = os.path.join(shots_dir, f"{i}_video.mp4")
                        if os.path.exists(synced_video) and os.path.exists(original_video):
                            # Backup original
                            backup_path = os.path.join(shots_dir, f"{i}_video_original.mp4")
                            if not os.path.exists(backup_path):
                                import shutil
                                shutil.copy2(original_video, backup_path)
                            
                            # Replace with synchronized version
                            import shutil
                            shutil.move(synced_video, original_video)
                            print(f"   ✅ Replaced shot {i} video with synchronized version")
                    
                    print("☑️ Finished replacing videos with synchronized versions")
            else:
                print("⚠️ No videos were synchronized")
            
            # Clean up temporary files
            processor.cleanup_temp_files(temp_dir)
            
        except Exception as e:
            print(f"Audio-video synchronization failed: {e}")
            print(f"❌ Audio-video synchronization failed: {str(e)}")
            print("   Continuing with original videos...")

    async def _combine_final_video(self):
        """Combine all processed shot videos into final movie"""
        try:
            shots_dir = os.path.join(self.working_dir, "shots")
            
            print("⬜ Collecting all processed shot videos...")
            
            # Find all video files in shots directory
            video_files = []
            shot_idx = 0
            
            while True:
                # Look for either synchronized or original video files
                synced_video = os.path.join(shots_dir, f"{shot_idx}_video.mp4")
                
                if not os.path.exists(synced_video):
                    break
                    
                video_files.append(synced_video)
                shot_idx += 1
            
            if not video_files:
                print("❌ No video files found to combine!")
                return
            
            print(f"✅ Found {len(video_files)} shot videos to combine")
            
            # Sort files naturally (0, 1, 2, ... instead of 0, 10, 11, 1, 2...)
            import re
            def natural_sort_key(text):
                """Natural sorting key function"""
                return [int(c) if c.isdigit() else c.lower() for c in re.split('([0-9]+)', text)]
            
            video_files.sort(key=natural_sort_key)
            
            print("⬜ Video files order:")
            for i, video_file in enumerate(video_files):
                print(f"   {i+1}. {os.path.basename(video_file)}")
            
            # Output path for final video
            final_video_path = os.path.join(self.working_dir, "final_movie.mp4")
            
            print("⬜ Combining all videos into final movie...")
            
            # Get just the filenames relative to shots_dir for the merge function
            video_filenames = [os.path.basename(f) for f in video_files]
            
            # Use the custom merge function to combine videos
            self._merge_videos_with_custom_dir(video_filenames, final_video_path, shots_dir)
            
            print(f"☑️ Final movie created successfully: {final_video_path}")
            
            # Optionally create a copy in the root directory for easy access
            import shutil
            #root_final_path = "final_movie.mp4"
            user_output_path = os.path.join(self.output_path,"final_movie.mp4")
            top_picture_path = self.working_dir+f"/shots/0_first_frame.png"
            shutil.copy2(final_video_path, user_output_path)
            shutil.copy2(top_picture_path, self.output_path)
            print(f"☑️ Copy created in project root: {user_output_path}")
            
        except Exception as e:
            print(f"❌ Failed to combine final video: {str(e)}")
            print("   Videos are still available individually in the shots directory")
            
    def _merge_videos_with_custom_dir(self, input_files, output_file, video_dir):
        """
        Custom video merging function that works with any directory
        
        Args:
            input_files: List of video filenames
            output_file: Output file path
            video_dir: Directory containing the video files
        """
        try:
            from moviepy.editor import VideoFileClip, concatenate_videoclips
            from utils import normalize_path_for_ffmpeg
            
            print(f"   Loading {len(input_files)} video clips...")
            
            # Load all video clips
            clips = []
            for filename in input_files:
                video_path = os.path.join(video_dir, filename)
                if os.path.exists(video_path):
                    # Load with warning suppression
                    import warnings
                    with warnings.catch_warnings():
                        warnings.filterwarnings("ignore", message=".*bytes wanted but.*bytes read.*")
                        warnings.filterwarnings("ignore", message=".*Using the last valid frame instead.*")
                        clip = VideoFileClip(video_path)
                        clips.append(clip)
                        print(f"     ✅ Loaded {filename} (duration: {clip.duration:.2f}s)")
                else:
                    print(f"     ❌ Warning: {filename} not found, skipping")
            
            if not clips:
                raise ValueError("No valid video clips found to merge")
            
            print("   Concatenating video clips...")
            final_clip = concatenate_videoclips(clips)
            
            total_duration = sum(clip.duration for clip in clips)
            print(f"   Total duration: {total_duration:.2f} seconds")
            
            print("   Writing final video file...")
            # Normalize path for FFMPEG compatibility on Windows
            output_file_ffmpeg = normalize_path_for_ffmpeg(output_file)
            
            final_clip.write_videofile(
                output_file_ffmpeg, 
                codec="libx264", 
                audio_codec="aac",
                logger=None,
                verbose=False,
                threads=4
            )
            
            # Clean up clips
            for clip in clips:
                clip.close()
            final_clip.close()
            
            print(f"   ✅ Successfully merged {len(clips)} videos")
            
        except Exception as e:
            print(f"   ❌ Error during video merging: {str(e)}")
            raise
