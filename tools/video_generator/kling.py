import logging
import requests
import json
from typing import Literal, List, Optional
from utils.image import image_path_to_b64
import time
from tools.video_generator.base import BaseVideoGenerator

class KlingVideoGenerator(BaseVideoGenerator):
    def __init__(
        self,
        api_key: str,
        base_url: str,
        api_version: str = "v1",
        model: Literal["kling-v1", "kling-v1-5", "kling-v1-6", "kling-v2-master", "kling-v2-1", "kling-v2-1-master"] = "kling-v1",
        aspect_ratio: str = "16:9",
        mode: Literal["std", "pro"] = "std",
        cfg_scale: float = 0.5,
        duration: Literal[5, 10] = 5,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.api_version = api_version
        self.model = model
        self.aspect_ratio = aspect_ratio
        self.mode = mode
        self.cfg_scale = cfg_scale
        self.duration = duration

    def __call__(
        self,
        prompt: str,
        reference_image_paths: List[str] = [],
    ):
        if len(reference_image_paths) > 0 and self.model not in ["kling-v1", "kling-v1-6", "kling-v2-master", "kling-v2-1-master"]:
            raise ValueError(f"Model {self.model} does not support reference images.")

        logging.info(f"Calling {self.model} to generate video")

        if len(reference_image_paths) == 0:
            url = f"{self.base_url}/kling/{self.api_version}/videos/text2video"
        else:
            url = f"{self.base_url}/kling/{self.api_version}/videos/image2video"

        payload = json.dumps({
            "model_name": self.model,
            "image": image_path_to_b64(reference_image_paths[0], mime=False) if len(reference_image_paths) > 0 else None,
            "image_tail": image_path_to_b64(reference_image_paths[1], mime=False) if len(reference_image_paths) > 1 else None,
            "prompt": prompt,
            "aspect_ratio": self.aspect_ratio,
            "cfg_scale": self.cfg_scale,
            "mode": self.mode,
            "duration": self.duration,
        })
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        response = requests.request("POST", url, headers=headers, data=payload).json()

        task_id = response["data"]["task_id"]
        while True:
            if len(reference_image_paths) == 0:
                url = f"{self.base_url}/kling/{self.api_version}/videos/text2video/{task_id}"
            else:
                url = f"{self.base_url}/kling/{self.api_version}/videos/image2video/{task_id}"

            payload = {}
            headers = {
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            }
            response = requests.request("GET", url, headers=headers, data=payload).json()

            if response["data"]["task_status"] != "succeed":
                logging.info(f"Task {task_id} is still processing...")
                time.sleep(1)
                continue

            video_url = response["data"]["task_result"]["videos"]["url"]
            

