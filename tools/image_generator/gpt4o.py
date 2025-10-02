import os
import logging
from typing import List
from openai import OpenAI
from tools.image_generator.base import BaseImageGenerator, ImageGeneratorOutput

# https://platform.openai.com/docs/guides/image-generation?image-generation-model=gpt-image-1&api=image

class GPT4oImageGenerator(BaseImageGenerator):
    def __init__(
        self,
        api_key: str,
        base_url: str,
        api_version: str = "v1",
        model: str = "gpt-image-1",
        background: str = "auto",
    ):
        base_url = base_url.rstrip("/") + f"/{api_version}"
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.background = background


    async def generate_single_image(
        self,
        prompt: str = None,
        reference_image_paths: List[str] = [],
        size: str = "auto",
    ) -> ImageGeneratorOutput:
        """
        Args:
            model: The model to use for image generation

            prompt: The text prompt to guide the image generation. The maximum length is 32000 characters for gpt-image-1.

            image_paths: A list of image file paths to use as input for the image generation

            num_generated_images: The number of images to generate. Must be between 1 and 10.

            background: Must be one of `transparent`, `opaque` or `auto` (default value). When `auto` is used, the model will automatically determine the best background for the image.

            size: Must be one of `1024x1024`, `1536x1024` (landscape), `1024x1536` (portrait), or `auto` (default value) for `gpt-image-1`
        """

        logging.info(f"Calling {self.model} to generate images")

        if len(reference_image_paths) == 0:
            response = self.client.images.generate(
                model=self.model,
                prompt=prompt,
                n=1,
                response_format="b64_json",
                size=size,
                background=self.background,
            )
        else:
            # For `gpt-image-1`, each image should be a `png`, `webp`, or `jpg` file less than 50MB. You can provide up to 16 images.

            # check image file types and sizes
            if len(reference_image_paths) > 16:
                raise ValueError("Too many images provided. Please provide up to 16 images.")

            for image_path in reference_image_paths:
                if not image_path.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    raise ValueError(f"Invalid image file type: {image_path}")
                if os.path.getsize(image_path) > 50 * 1024 * 1024:
                    raise ValueError(f"Image file too large: {image_path}")

            response = self.client.images.edit(
                model=self.model,
                prompt=prompt,
                image=[open(image_path, "rb") for image_path in reference_image_paths],
                n=1,
                response_format="b64_json",
                size=size,
                background=self.background,
            )

        output = ImageGeneratorOutput(
            fmt="b64",
            ext="png",
            data=response.data[0].b64_json,
        )
        return output
