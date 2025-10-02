import asyncio
import logging
from PIL import Image
from tools.video_generator.base import VideoGeneratorOutput, BaseVideoGenerator
import http.client
import json
import http.client
import mimetypes
from codecs import encode

def upload2runninghub(api_key: str, image: str):
    conn = http.client.HTTPSConnection("www.runninghub.cn")
    dataList = []
    boundary = 'wL36Yn8afVp8Ag7AmP8qZ0SA4n1v9T'
    dataList.append(encode('--' + boundary))
    dataList.append(encode('Content-Disposition: form-data; name=apiKey;'))

    dataList.append(encode('Content-Type: {}'.format('text/plain')))
    dataList.append(encode(''))

    dataList.append(encode(api_key))
    dataList.append(encode('--' + boundary))
    dataList.append(encode('Content-Disposition: form-data; name=file; filename={0}'.format(
        image)))

    fileType = mimetypes.guess_type(image)[0] or 'application/octet-stream'
    dataList.append(encode('Content-Type: {}'.format(fileType)))
    dataList.append(encode(''))

    with open(image, 'rb') as f:
        dataList.append(f.read())
    dataList.append(encode('--' + boundary))
    dataList.append(encode('Content-Disposition: form-data; name=fileType;'))

    dataList.append(encode('Content-Type: {}'.format('text/plain')))
    dataList.append(encode(''))

    dataList.append(encode("image"))
    dataList.append(encode('--' + boundary + '--'))
    dataList.append(encode(''))
    body = b'\r\n'.join(dataList)
    payload = body
    headers = {
        'Host': 'www.runninghub.cn',
        'Content-type': 'multipart/form-data; boundary={}'.format(boundary)
    }
    conn.request("POST", "/task/openapi/upload", payload, headers)
    res = conn.getresponse()
    data = res.read()
    print(data.decode("utf-8"))
    fieldValue = json.loads(data.decode("utf-8"))["data"]["fileName"]
    return fieldValue

class WanVideoGenerator(BaseVideoGenerator):
    def __init__(
        self,
        api_key: str,
        ff2v_model: str = "wan 2.2 ff2v",  # first frame to video
        flf2v_model: str = "wan 2.2 flf2v",  # first and last frame to video
    ):
        self.api_key = api_key
        self.ff2v_model = ff2v_model
        self.flf2v_model = flf2v_model

    async def generate_single_video(
        self,
        prompt: str = "",
        reference_image_paths: list[str] = [],
    ):
        fieldValues = []
        for i, img_path in enumerate(reference_image_paths):
            fieldValue = upload2runninghub(self.api_key, img_path)
            fieldValues.append(fieldValue)
        conn = http.client.HTTPSConnection("www.runninghub.cn")
        if len(reference_image_paths) == 1:
            model = self.ff2v_model
            logging.info(f"Calling {model} to generate video...")
            payload = json.dumps({
                "apiKey": self.api_key,
                "workflowId": "1967890630330449922",
                "nodeInfoList": [
                    {
                        "nodeId": "67",
                        "fieldName": "image",
                        "fieldValue": fieldValues[0]
                    },
                    {
                        "nodeId": "102",
                        "fieldName": "text",
                        "fieldValue": prompt
                    }
                ]
            })
        else:
            payload = json.dumps({
                "apiKey": self.api_key,
                "workflowId": "1967861144633376769",
                "nodeInfoList": [
                    {
                        "nodeId": "204",
                        "fieldName": "image",
                        "fieldValue": fieldValues[0]
                    },
                    {
                        "nodeId": "205",
                        "fieldName": "image",
                        "fieldValue": fieldValues[1]
                    },
                    {
                        "nodeId": "119",
                        "fieldName": "text",
                        "fieldValue": prompt
                    }
                ],
            })
        headers = {
            'Host': 'www.runninghub.cn',
            'Content-Type': 'application/json'
        }

        while True:
            conn.request("POST", "/task/openapi/create", payload, headers)
            res = conn.getresponse()
            data = res.read()
            data = json.loads(data.decode("utf-8"))
            if data["data"] is not None:
                break
            else:
                msg = data["msg"]
                logging.error(f"Video generation request failed: {msg}, waiting 1 second to retry...")
                await asyncio.sleep(1)
                continue

        # print(data.decode("utf-8"))
        while True:
            # query status
            taskId = data["data"]["taskId"]
            conn = http.client.HTTPSConnection("www.runninghub.cn")
            payload = json.dumps({
                "apiKey": self.api_key,
                "taskId": taskId
            })
            headers = {
                'Host': 'www.runninghub.cn',
                'Content-Type': 'application/json'
            }

            conn.request("POST", "/task/openapi/status", payload, headers)
            query_res = conn.getresponse()
            query_data = json.loads(query_res.read().decode("utf-8"))
            if query_data["data"] == "SUCCESS":
                logging.info(f"Video generation completed successfully")
                conn.request("POST", "/task/openapi/outputs", payload, headers)
                output_res = conn.getresponse()
                output_data = json.loads(output_res.read().decode("utf-8"))
                video_url = output_data["data"][0]["fileUrl"]
                video = VideoGeneratorOutput(fmt="url", ext="mp4", data=video_url)
                return video
            elif query_data["data"] == "FAILED":
                logging.error(f"Video generation failed: \n{query_data}")
                break
            else:
                logging.info(f"Video generation status: {query_data['data']}, waiting 1 second...")
                await asyncio.sleep(5)
                continue