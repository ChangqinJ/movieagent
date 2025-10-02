import os
import logging
import asyncio
from io import BytesIO
from PIL import Image
from typing import List, Optional
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt

from tools.image_generator.base import BaseImageGenerator, ImageGeneratorOutput

# https://ai.google.dev/gemini-api/docs/image-generation?hl=zh-cn

class GeminiImageGenerator(BaseImageGenerator):
    def __init__(
        self,
        api_key: str,
        base_url: str,
        api_version: str = "v1beta",
        model: str = "gemini-2.5-flash-image-preview",
    ):
        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                base_url=base_url,
                api_version=api_version,
            ),
        )
        self.model = model


    @retry(
        stop=stop_after_attempt(3),
        after=lambda retry_state: logging.warning(f"Retrying generate_single_image due to error: {retry_state.outcome.exception()}"),
    )
    async def generate_single_image(
        self,
        prompt: str,
        reference_image_paths: List[str] = [],
        size: Optional[str] = None,
    ) -> ImageGeneratorOutput:

        reference_images = [Image.open(path) for path in reference_image_paths]

        if size is not None:
            width, height = map(int, size.split("x"))
            blank_image = Image.new("RGB", (width, height), (255, 255, 255))
            reference_images = reference_images + [blank_image]
            prompt = prompt + f"\nThe size of generated image should be consistent with the last image, but without the white background."

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=reference_images + [prompt],
        )

        image = None
        for part in response.candidates[0].content.parts:
            if part.text is not None:
                logging.debug(f"Text: {part.text}")
            elif part.inline_data is not None:
                image = Image.open(BytesIO(part.inline_data.data))

        if image is None:
            raise ValueError("No image generated")

        return ImageGeneratorOutput(fmt="pil", ext="png", data=image)

