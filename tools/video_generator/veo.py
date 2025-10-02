import http.client
import json
import base64
import time
import requests
import os
from utils.image import pil_to_b64, image_path_to_b64
import logging
from typing import List, Optional
from tools.video_generator.base import VideoGeneratorOutput, BaseVideoGenerator
from PIL import Image
import asyncio

class VeoVideoGenerator(BaseVideoGenerator):
    def __init__(
        self,
        base_url: str,
        api_key: str,
        ff2v_model: str = "veo3-fast-frames",   # first frame to video
        flf2v_model: str = "veo2-fast-frames",  # first and last frame to video
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.ff2v_model = ff2v_model
        self.flf2v_model = flf2v_model

    async def generate_single_video(
        self,
        prompt: str = "",
        reference_image_paths: List[Image.Image] = [],
    ):
        if len(reference_image_paths) == 1:
            model = self.ff2v_model
        else:
            model = self.flf2v_model

        logging.info(f"Calling {model} to generate video...")

        conn = http.client.HTTPSConnection("yunwu.ai")
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "prompt": prompt,
            "model": model,
            "images": [image_path_to_b64(image_path) for image_path in reference_image_paths],
            "enhance_prompt": True,
        }
        if model == "veo3-fast-frames":
            payload["aspect_ratio"] = "16:9"

        payload = json.dumps(payload)

        conn.request("POST", "/v1/video/create", payload, headers)
        res = conn.getresponse()

        response_data = json.loads(res.read().decode("utf-8"))
        task_id = response_data["id"]
        boundary = ''
        payload = ''
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
            'Content-type': 'multipart/form-data; boundary={}'.format(boundary)
        }

        while True:
            conn.request("GET", f"/v1/video/query?id={task_id}", payload, headers)
            res = conn.getresponse()
            data = json.loads(res.read().decode("utf-8"))
            if data["status"] == "completed":
                logging.info(f"Video generation completed successfully")
                video_url = data["video_url"]
                video = VideoGeneratorOutput(fmt="url", ext="mp4", data=video_url)
                return video
            elif data["status"] == "failed":
                logging.error(f"Video generation failed: \n{data}")
                break
            else:
                logging.info(f"Video generation status: {data['status']}, waiting 1 second...")
                await asyncio.sleep(1)
                continue
