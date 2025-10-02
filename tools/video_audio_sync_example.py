#!/usr/bin/env python3
"""
Example usage of the video-audio synchronization system

This example demonstrates how to use the new audio-video synchronization functionality
that analyzes video content with multimodal models and synchronizes generated audio.
"""

import asyncio
import os
import logging
from tools.video_audio_processor import VideoAudioProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def example_sync_single_shot():
    """Example: Synchronize audio for a single shot"""
    
    # Configuration - replace with your actual API credentials
    API_KEY = "your_api_key_here"  # Replace with your yunwu.ai API key
    AUTH_TOKEN = "your_auth_token_here"  # Replace with your authorization token
    
    # Initialize processor
    processor = VideoAudioProcessor(api_key=API_KEY, auth_token=AUTH_TOKEN)
    
    # File paths (adjust to your actual files)
    video_path = ".working_dir/5/shots/0_video.mp4"
    audio_path = ".working_dir/5/shots/shot_0_vocal.wav"
    characters_dir = ".working_dir/5/characters"
    output_path = ".working_dir/5/shots/0_video_synced.mp4"
    
    # Load shot information
    import json
    with open(".working_dir/5/shots/0.json", "r", encoding="utf-8") as f:
        shot_info = json.load(f)
    
    try:
        # Process audio synchronization
        result = processor.process_shot_audio_sync(
            video_path=video_path,
            audio_path=audio_path,
            shot_info=shot_info,
            characters_dir=characters_dir,
            output_path=output_path
        )
        
        print(f"✅ Successfully synchronized audio for shot")
        print(f"   Output: {result}")
        
    except Exception as e:
        print(f"❌ Failed to synchronize audio: {e}")

async def example_sync_multiple_shots():
    """Example: Synchronize audio for multiple shots"""
    
    # Configuration
    API_KEY = "your_api_key_here"
    AUTH_TOKEN = "your_auth_token_here"
    
    # Initialize processor
    processor = VideoAudioProcessor(api_key=API_KEY, auth_token=AUTH_TOKEN)
    
    # Directory paths
    shots_dir = ".working_dir/5/shots"
    working_dir = ".working_dir/5"
    
    try:
        # Process all shots
        synchronized_videos = processor.process_multiple_shots(
            shots_dir=shots_dir,
            working_dir=working_dir
        )
        
        print(f"✅ Successfully synchronized {len(synchronized_videos)} shots")
        for i, video in enumerate(synchronized_videos):
            print(f"   Shot {i}: {video}")
            
    except Exception as e:
        print(f"❌ Failed to synchronize multiple shots: {e}")

def example_configuration():
    """Example: How to configure the system in your pipeline"""
    
    print("=== Configuration Example ===")
    print()
    print("1. Update your configs/script2video.yaml file:")
    print("""
# Audio-Video Synchronization Configuration
multimodal_api_key: "your_actual_api_key"     # Your yunwu.ai API key
multimodal_auth_token: "your_actual_token"    # Your authorization token
replace_original_videos: true                 # Whether to replace original videos
""")
    print()
    print("2. The system will automatically:")
    print("   - Analyze each video to identify when speakers are talking")
    print("   - Use character information to identify the correct speaker")
    print("   - Stretch/compress audio to match the detected speech timing")
    print("   - Replace original videos with synchronized versions")
    print()
    print("3. Required dependencies:")
    print("   - moviepy (for video/audio processing)")
    print("   - librosa (for high-quality audio stretching)")
    print("   - soundfile (for audio I/O)")
    print()
    print("   Install with: pip install moviepy librosa soundfile")

if __name__ == "__main__":
    print("🎬 Audio-Video Synchronization Example")
    print("="*50)
    
    # Show configuration example
    example_configuration()
    
    print("\n" + "="*50)
    print("Note: Update API_KEY and AUTH_TOKEN before running examples")
    print("="*50)
    
    # Uncomment to run examples (after setting API credentials)
    # asyncio.run(example_sync_single_shot())
    # asyncio.run(example_sync_multiple_shots())
