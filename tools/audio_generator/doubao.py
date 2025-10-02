#!/usr/bin/env python3
import argparse
import json
import logging
import uuid
from typing import Optional

import websockets

from tools.audio_generator.protocols import MsgType, full_client_request, receive_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TTSGenerator:
    def __init__(
            self,
            appid: str = "4329438072",
            access_token: str = "WwluX6oAxE5XM6NRGCfUdsy5oqTEPBKu",
            voice_type: str = "en_female_lauren_moon_bigtts",
            cluster: str = "",
            encoding: str = "wav",
            endpoint: str = "wss://openspeech.bytedance.com/api/v1/tts/ws_binary"
    ):
        self.appid = appid
        self.access_token = access_token
        self.voice_type = voice_type
        self.cluster = cluster if cluster else self._get_cluster(voice_type)
        self.encoding = encoding
        self.endpoint = endpoint

    def _get_cluster(self, voice: str) -> str:
        """Determine cluster based on voice type"""
        if voice.startswith("S_"):
            return "volcano_icl"
        return "volcano_tts"

    async def generate_shot_vocal(self, text: str, emotion: str, output_filename: Optional[str] = None) -> str:
        """
        Generate vocal audio from text

        Args:
            text: Text to convert to speech
            output_filename: Optional custom filename. If not provided, uses voice_type.encoding

        Returns:
            str: Path to the generated audio file
        """
        # Prepare headers
        headers = {
            "Authorization": f"Bearer;{self.access_token}",
        }

        logger.info(f"Connecting to {self.endpoint} with headers: {headers}")
        websocket = await websockets.connect(
            self.endpoint, additional_headers=headers, max_size=10 * 1024 * 1024
        )
        logger.info(
            f"Connected to WebSocket server, Logid: {websocket.response.headers['x-tt-logid']}",
        )

        try:
            # Prepare request payload
            request = {
                "app": {
                    "appid": self.appid,
                    "token": self.access_token,
                    "cluster": self.cluster,
                },
                "user": {
                    "uid": str(uuid.uuid4()),
                },
                "audio": {
                    "voice_type": self.voice_type,
                    "emotion": emotion,
                    "encoding": self.encoding,
                    "enable_emotion": True,
                },
                "request": {
                    "reqid": str(uuid.uuid4()),
                    "text": text,
                    "operation": "submit",
                    "with_timestamp": "1",
                    "extra_param": json.dumps(
                        {
                            "disable_markdown_filter": False,
                        }
                    ),
                },
            }

            # Send request
            await full_client_request(websocket, json.dumps(request).encode())

            # Receive audio data
            audio_data = bytearray()
            while True:
                msg = await receive_message(websocket)

                if msg.type == MsgType.FrontEndResultServer:
                    continue
                elif msg.type == MsgType.AudioOnlyServer:
                    audio_data.extend(msg.payload)
                    if msg.sequence < 0:  # Last message
                        break
                else:
                    raise RuntimeError(f"TTS conversion failed: {msg}")

            # Check if we received any audio data
            if not audio_data:
                raise RuntimeError("No audio data received")

            # Save audio file
            filename = output_filename or f"{self.voice_type}.{self.encoding}"
            with open(filename, "wb") as f:
                f.write(audio_data)
            logger.info(f"Audio received: {len(audio_data)}, saved to {filename}")

            return filename

        finally:
            await websocket.close()
            logger.info("Connection closed")


async def main():
    """Command line interface for the TTS generator"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--appid", default="4329438072", help="APP ID")
    parser.add_argument("--access_token", default="WwluX6oAxE5XM6NRGCfUdsy5oqTEPBKu", help="Access Token")
    parser.add_argument("--voice_type", default="en_female_lauren_moon_bigtts", help="Voice type")
    parser.add_argument("--cluster", default="", help="Cluster name")
    parser.add_argument("--text", required=True, help="Text to convert")
    parser.add_argument("--encoding", default="wav", help="Output file encoding")
    parser.add_argument(
        "--endpoint",
        default="wss://openspeech.bytedance.com/api/v1/tts/ws_binary",
        help="WebSocket endpoint URL",
    )
    parser.add_argument("--output", help="Output filename")

    args = parser.parse_args()

    # Create TTS generator instance
    tts_generator = TTSGenerator(
        appid=args.appid,
        access_token=args.access_token,
        voice_type=args.voice_type,
        cluster=args.cluster,
        encoding=args.encoding,
        endpoint=args.endpoint
    )

    # Generate vocal
    filename = await tts_generator.generate_shot_vocal(args.text, "neutral", args.output)
    print(f"Generated audio file: {filename}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())