import base64
import os
import asyncio
from abc import abstractmethod
from typing import List, Literal, Optional, Union
from PIL import Image

from utils.image import download_image


class ImageGeneratorOutput:
    fmt: Literal["b64", "url", "pil"]
    ext: str = "png"
    data: Union[str, Image.Image]

    def __init__(
        self,
        fmt: Literal["b64", "url", "pil"],
        ext: str,
        data: Union[str, Image.Image],
    ):
        self.fmt = fmt
        self.ext = ext
        self.data = data


    def save_b64(self, path: str) -> None:
        """Save a base64 encoded image to the specified path.

        Args:
            path (str): Path where the image will be saved.
        """
        with open(path, 'wb') as f:
            f.write(base64.b64decode(self.data))

    def save_url(self, path: str) -> None:
        """Download and save an image from a URL to the specified path.

        Args:
            path (str): Path where the image will be saved.
        """
        download_image(self.data, path)

    def save_pil(self, path: str) -> None:
        """Save a PIL Image to the specified path.

        Args:
            path (str): Path where the image will be saved.
        """
        self.data.save(path)

    def save(self, path: str) -> None:
        save_func = getattr(self, f"save_{self.fmt}")
        save_func(path)


class BaseImageGenerator:

    async def generate_single_image(
        self,
        prompt: str,
        reference_image_paths: List[str],
    ) -> ImageGeneratorOutput:
        pass

    async def generate_multiple_images_from_one_prompt(
        self,
        prompt: str,
        reference_image_paths: List[str],
        num_images: int,
        **kwargs,
    ) -> List[ImageGeneratorOutput]:
        tasks = [
            self.generate_single_image(prompt, reference_image_paths, **kwargs)
            for _ in range(num_images)
        ]
        output_images = await asyncio.gather(*tasks)
        return output_images

    async def generate_multiple_images_from_multiple_prompts(
        self,
        prompts: List[List[str]],
        reference_image_paths: List[List[str]],
        num_images_per_prompt: int = 1,
        **kwargs,
    ) -> List[List[ImageGeneratorOutput]]:
        tasks = [
            self.generate_multiple_images_from_one_prompt(
                prompt,
                ref_image,
                num_images=num_images_per_prompt,
                **kwargs
            )
            for prompt, ref_image in zip(prompts, reference_image_paths)
        ]
        output_images = await asyncio.gather(*tasks)
        return output_images
