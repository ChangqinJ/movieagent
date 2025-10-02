import os
import logging
import asyncio
from io import BytesIO
from PIL import Image
from typing import List, Optional
import requests
from utils.image import pil_to_b64
import json
import time
from tools.image_generator.base import BaseImageGenerator, ImageGeneratorOutput
from tenacity import retry, stop_after_attempt

# https://yunwu.apifox.cn/api-341952136
# only for fal-ai nano-banana model

class NanoBananaImageGenerator(BaseImageGenerator):
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str = "nano-banana",
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    @retry(
        stop=stop_after_attempt(3),
        after=lambda retry_state: logging.warning(f"Retrying generate_single_image due to error: {retry_state.outcome.exception()}"),
    )
    async def generate_single_image(
        self,
        prompt: str,
        reference_image_paths: List[str],
        size: Optional[str] = None,
    ) -> ImageGeneratorOutput:
        
        logging.info(f"Calling {self.model} to generate image.")

        reference_images = [Image.open(path) for path in reference_image_paths]

        if size is not None:
            width, height = map(int, size.split("x"))
            blank_image = Image.new("RGB", (width, height), (255, 255, 255))
            reference_images = reference_images + [blank_image]
            prompt = prompt + f"\nThe size of generated image should be consistent with the last image, but without the white background."

        reference_images_b64 = [pil_to_b64(image) for image in reference_images]

        url = f"{self.base_url}/fal-ai/nano-banana/edit"
        payload = json.dumps({
            "prompt": prompt,
            "image_urls": reference_images_b64,
            "num_images": 1,
            "output_format": "png",
        })

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        response = requests.request("POST", url, headers=headers, data=payload)


        task_id = response.json().get("request_id")
        while True:
            url = f"{self.base_url}/fal-ai/auto/requests/{task_id}"
            headers = {
                'Authorization': f'Bearer {self.api_key}',
            }
            response = requests.request("GET", url, headers=headers).json()

            status = response.get("status")
            if status == "IN_QUEUE":
                await asyncio.sleep(1)
                continue

            if "images" not in response:
                raise ValueError(f"No image generated")

            image_url = response["images"][0]["url"]
            image = ImageGeneratorOutput(fmt="url", ext="png", data=image_url)
            return image
