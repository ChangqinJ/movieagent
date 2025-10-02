import os
import cv2
import numpy as np
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)

class VideoQualityChecker:
    """Check video quality and detect static frames"""
    
    def __init__(self):
        pass
    
    def detect_static_frames(self, video_path: str, threshold: float = 0.01) -> List[Tuple[int, float]]:
        """
        Detect static frames in a video by comparing consecutive frames
        
        Args:
            video_path: Path to the video file
            threshold: Threshold for frame difference (lower = more sensitive)
            
        Returns:
            List of (frame_index, difference_score) for static frames
        """
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"Could not open video: {video_path}")
                return []
            
            static_frames = []
            prev_frame = None
            frame_index = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Convert to grayscale for comparison
                gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                if prev_frame is not None:
                    # Calculate frame difference
                    diff = cv2.absdiff(prev_frame, gray_frame)
                    diff_score = np.mean(diff) / 255.0  # Normalize to 0-1
                    
                    if diff_score < threshold:
                        static_frames.append((frame_index, diff_score))
                        logger.debug(f"Static frame detected at index {frame_index}, diff: {diff_score:.4f}")
                
                prev_frame = gray_frame.copy()
                frame_index += 1
            
            cap.release()
            
            logger.info(f"Found {len(static_frames)} static frames in {video_path}")
            return static_frames
            
        except Exception as e:
            logger.error(f"Error analyzing video {video_path}: {e}")
            return []
    
    def get_video_info(self, video_path: str) -> dict:
        """Get basic video information"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return {}
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = frame_count / fps if fps > 0 else 0
            
            cap.release()
            
            return {
                'fps': fps,
                'frame_count': frame_count,
                'width': width,
                'height': height,
                'duration': duration,
                'file_size': os.path.getsize(video_path)
            }
            
        except Exception as e:
            logger.error(f"Error getting video info for {video_path}: {e}")
            return {}
    
    def analyze_video_quality(self, video_path: str) -> dict:
        """Comprehensive video quality analysis"""
        try:
            info = self.get_video_info(video_path)
            static_frames = self.detect_static_frames(video_path)
            
            # Calculate percentage of static frames
            static_percentage = 0
            if info.get('frame_count', 0) > 0:
                static_percentage = (len(static_frames) / info['frame_count']) * 100
            
            # Detect if ending frames are static
            ending_static = False
            if static_frames and info.get('frame_count', 0) > 0:
                # Check if last 10% of frames contain static frames
                last_10_percent_start = info['frame_count'] * 0.9
                ending_static_frames = [f for f, _ in static_frames if f >= last_10_percent_start]
                ending_static = len(ending_static_frames) > 0
            
            result = {
                'video_info': info,
                'static_frames_count': len(static_frames),
                'static_frames_percentage': static_percentage,
                'ending_has_static_frames': ending_static,
                'static_frames': static_frames[:10],  # First 10 static frames
                'file_path': video_path
            }
            
            logger.info(f"Video analysis for {os.path.basename(video_path)}:")
            logger.info(f"  - Duration: {info.get('duration', 0):.2f}s")
            logger.info(f"  - Static frames: {len(static_frames)} ({static_percentage:.1f}%)")
            logger.info(f"  - Ending has static frames: {ending_static}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing video quality: {e}")
            return {}

def analyze_shots_directory(shots_dir: str) -> List[dict]:
    """Analyze all videos in a shots directory"""
    checker = VideoQualityChecker()
    results = []
    
    if not os.path.exists(shots_dir):
        logger.error(f"Shots directory not found: {shots_dir}")
        return results
    
    # Find all video files
    video_files = [f for f in os.listdir(shots_dir) if f.endswith('.mp4')]
    video_files.sort()
    
    for video_file in video_files:
        video_path = os.path.join(shots_dir, video_file)
        analysis = checker.analyze_video_quality(video_path)
        if analysis:
            results.append(analysis)
    
    return results

if __name__ == "__main__":
    # Example usage
    import sys
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        checker = VideoQualityChecker()
        analysis = checker.analyze_video_quality(video_path)
        print("Video Analysis Results:")
        print(f"Static frames: {analysis.get('static_frames_count', 0)}")
        print(f"Ending has static frames: {analysis.get('ending_has_static_frames', False)}")
    else:
        print("Usage: python video_quality_checker.py <video_path>")
