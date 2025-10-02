import base64
import os
import asyncio
from abc import abstractmethod
from typing import List, Literal, Optional, Union
from PIL import Image

from utils.video import download_video


class VideoGeneratorOutput:
    fmt: Literal["url"]
    ext: str = "mp4"
    data: Union[str, Image.Image]

    def __init__(
        self,
        fmt: Literal["url"],
        ext: str,
        data: str,
    ):
        self.fmt = fmt
        self.ext = ext
        self.data = data

    def save_url(self, path: str) -> None:
        """Download and save a video from a URL to the specified path.

        Args:
            path (str): Path where the video will be saved.
        """
        download_video(self.data, path)

    def save(self, path: str) -> None:
        save_func = getattr(self, f"save_{self.fmt}")
        save_func(path)



class BaseVideoGenerator:

    async def generate_single_video(
        self,
        prompt: str,
        reference_image_paths: List[str],
    ) -> VideoGeneratorOutput:
        pass

    async def generate_multiple_videos_from_one_prompt(
        self,
        prompt: str,
        reference_image_paths: List[str],
        num_videos: int,
        **kwargs,
    ) -> List[VideoGeneratorOutput]:
        tasks = [
            self.generate_single_video(prompt, reference_image_paths, **kwargs)
            for _ in range(num_videos)
        ]
        output_videos = await asyncio.gather(*tasks)
        return output_videos

    async def generate_multiple_videos_from_multiple_prompts(
        self,
        prompts: List[List[str]],
        reference_image_paths: List[List[str]],
        num_videos_per_prompt: int = 1,
        **kwargs,
    ) -> List[List[VideoGeneratorOutput]]:
        tasks = [
            self.generate_multiple_videos_from_one_prompt(
                prompt,
                ref_image,
                num_videos=num_videos_per_prompt,
                **kwargs
            )
            for prompt, ref_image in zip(prompts, reference_image_paths)
        ]
        output_videos = await asyncio.gather(*tasks)
        return output_videos
