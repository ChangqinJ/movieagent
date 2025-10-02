import logging
import requests
import json
from typing import Literal, List
from utils.image import image_path_to_b64



class JimengVideoGenerator:
    def __init__(
        self,
        api_key: str,
        base_url: str,
    ):
        self.api_key = api_key
        self.base_url = base_url

    def __call__(
        self,
        model_name: Literal["kling-v1", "kling-v1-5", "kling-v1-6"],
        prompt: str = "",
        image_paths: List[str] = [],
        duration: int = 5,
    ):
        logging.info(f"Calling {model_name} to generate video")
        url = self.base_url
        payload = json.dumps({
            "model_name": model_name,
            "image": image_path_to_b64(image_paths[0]),
            "image_tail": image_path_to_b64(image_paths[1]) if len(image_paths) > 1 else None,
            "prompt": prompt,
            "negative_prompt": "",
            "aspect_ratio": "16:9",
            "cfg_scale": 0.5,
            "mode": "std",
            "duration": duration,
        })
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        response = requests.request("POST", url, headers=headers, data=payload)
        print(response.text)
        response_data = json.loads(response.text)
        print(response_data)