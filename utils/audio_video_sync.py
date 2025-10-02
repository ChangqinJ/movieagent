import os
import logging
from typing import List, Optional
from moviepy.editor import VideoClip, VideoFileClip, AudioFileClip, CompositeAudioClip
# Custom speedx implementation for MoviePy 1.0.3 compatibility
def speedx(clip, factor=1.0):
    """Change the speed of a clip by a given factor."""
    if factor == 1.0:
        return clip
    
    # Use fl_time to change playback speed
    def time_transform(t):
        return t * factor
    
    return clip.fl_time(time_transform, apply_to=['mask']).set_duration(clip.duration / factor)
import librosa
import soundfile as sf
import numpy as np

logger = logging.getLogger(__name__)

class AudioVideoSynchronizer:
    """
    Synchronizes audio with video based on speech timing analysis by adjusting video speed.
    
    Instead of stretching audio to match video timing, this synchronizer adjusts the video
    playback speed within the target segment to match the audio duration.
    """
    
    def __init__(self):
        pass
    
    def stretch_audio(self, audio_path: str, target_duration: float, output_path: str) -> str:
        """
        Stretch or compress audio to match target duration while preserving quality
        
        NOTE: This method is kept for backward compatibility and fallback scenarios.
        The new approach adjusts video speed instead of stretching audio.
        
        Args:
            audio_path: Path to input audio file
            target_duration: Target duration in seconds
            output_path: Path for output audio file
            
        Returns:
            Path to the processed audio file
        """
        try:
            # Load audio using librosa for better quality processing
            y, sr = librosa.load(audio_path, sr=None)
            current_duration = len(y) / sr
            
            if current_duration == 0:
                raise ValueError("Audio file has zero duration")
            
            # Calculate stretch factor
            stretch_factor = target_duration / current_duration
            
            logger.info(f"Stretching audio from {current_duration:.2f}s to {target_duration:.2f}s (factor: {stretch_factor:.3f})")
            
            # Use librosa's time stretching (preserves pitch)
            if abs(stretch_factor - 1.0) > 0.05:  # Only stretch if significant difference
                y_stretched = librosa.effects.time_stretch(y, rate=1/stretch_factor)
            else:
                y_stretched = y
                logger.info("Audio duration is close enough, no stretching needed")
            
            # Save the stretched audio
            sf.write(output_path, y_stretched, sr)
            
            # Verify the output duration
            verify_duration = len(y_stretched) / sr
            logger.info(f"Audio stretching completed. Final duration: {verify_duration:.2f}s")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to stretch audio {audio_path}: {e}")
            # Fallback: use moviepy for stretching
            try:
                logger.info("Falling back to moviepy for audio stretching")
                audio_clip = AudioFileClip(audio_path)
                current_duration = audio_clip.duration
                
                if current_duration == 0:
                    raise ValueError("Audio clip has zero duration")
                
                stretch_factor = target_duration / current_duration
                stretched_audio = audio_clip.fx(speedx, factor=1/stretch_factor)
                stretched_audio.write_audiofile(output_path, logger=None)
                
                audio_clip.close()
                stretched_audio.close()
                
                return output_path
                
            except Exception as fallback_error:
                logger.error(f"Fallback audio stretching also failed: {fallback_error}")
                raise
    
    def sync_audio_with_video(
        self, 
        video_path: str, 
        audio_path: str, 
        start_time: float, 
        end_time: float, 
        output_path: str,
        temp_dir: Optional[str] = None
    ) -> str:
        """
        Synchronize audio with video at specified time segment by adjusting video speed
        
        Args:
            video_path: Path to input video file
            audio_path: Path to audio file to sync (will not be stretched)
            start_time: Start time in seconds for audio placement from multimodal analysis
            end_time: End time in seconds for audio placement from multimodal analysis
            output_path: Path for output video file
            temp_dir: Directory for temporary files
            
        Returns:
            Path to the synchronized video file
        """
        try:
            if temp_dir is None:
                temp_dir = os.path.dirname(output_path)
            
            os.makedirs(temp_dir, exist_ok=True)
            
            # Load video with warning suppression
            import warnings
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=".*bytes wanted but.*bytes read.*")
                warnings.filterwarnings("ignore", message=".*Using the last valid frame instead.*")
                video = VideoFileClip(video_path)
            video_duration = video.duration
            
            # Load audio to get its duration
            audio_clip = AudioFileClip(audio_path)
            audio_duration = audio_clip.duration
            
            logger.info(f"Video duration: {video_duration:.2f}s")
            logger.info(f"Audio duration: {audio_duration:.2f}s")
            logger.info(f"Multimodal analysis suggests audio placement: {start_time:.2f}s to {end_time:.2f}s")
            
            # Validate and adjust timing
            if start_time < 0:
                logger.warning(f"Start time {start_time} is negative, setting to 0")
                start_time = 0
            
            if end_time > video_duration:
                logger.warning(f"End time {end_time:.2f}s exceeds video duration {video_duration:.2f}s, adjusting to video end")
                end_time = video_duration
            
            if start_time >= end_time:
                logger.warning(f"Invalid timing: start {start_time} >= end {end_time}, using minimal segment")
                end_time = min(start_time + 1.0, video_duration)
            
            target_video_segment_duration = end_time - start_time
            logger.info(f"Target video segment duration: {target_video_segment_duration:.2f}s")
            
            # Calculate speed adjustment factor based on audio duration vs target segment duration
            # If audio is longer than target segment, speed up the video
            # If audio is shorter than target segment, slow down the video
            speed_factor = target_video_segment_duration / audio_duration
            logger.info(f"Video speed adjustment factor: {speed_factor:.3f}")
            
            if speed_factor > 1.0:
                logger.info(f"Audio ({audio_duration:.2f}s) is shorter than target segment ({target_video_segment_duration:.2f}s), slowing down video")
            elif speed_factor < 1.0:
                logger.info(f"Audio ({audio_duration:.2f}s) is longer than target segment ({target_video_segment_duration:.2f}s), speeding up video")
            else:
                logger.info(f"Audio duration matches target segment, no speed adjustment needed")
            
            # Extract the segment that needs to be speed-adjusted
            before_segment = video.subclip(0, start_time) if start_time > 0 else None
            target_segment = video.subclip(start_time, end_time)
            after_segment = video.subclip(end_time, video_duration) if end_time < video_duration else None
            
            # Apply speed adjustment to the target segment
            if abs(speed_factor - 1.0) > 0.05:  # Only adjust if significant difference
                adjusted_segment = speedx(target_segment, factor=speed_factor)
                logger.info(f"Adjusted segment duration: {adjusted_segment.duration:.2f}s")
            else:
                adjusted_segment = target_segment
                logger.info("Speed adjustment not significant, keeping original segment")
            
            # Combine video segments
            video_segments = []
            if before_segment is not None:
                video_segments.append(before_segment)
            video_segments.append(adjusted_segment)
            if after_segment is not None:
                video_segments.append(after_segment)
            
            # Concatenate all segments
            if len(video_segments) > 1:
                from moviepy.editor import concatenate_videoclips
                final_video_clip = concatenate_videoclips(video_segments)
            else:
                final_video_clip = video_segments[0]
            
            # Calculate the final video duration after speed adjustment
            final_video_duration = final_video_clip.duration
            logger.info(f"Final video duration after speed adjustment: {final_video_duration:.2f}s")
            
            # Create extended audio that matches the entire video duration
            # Structure: [silence before] + [original audio] + [silence after]
            
            # Calculate timing for audio placement within the final video
            # We need to map the original start_time to the adjusted video timeline
            if before_segment is not None:
                # Audio should start at the original start_time position in the final video
                audio_start_in_final = before_segment.duration
            else:
                # No before_segment, use original start_time but ensure it's within bounds
                audio_start_in_final = min(start_time, final_video_duration - audio_duration)
            
            audio_end_in_final = min(audio_start_in_final + audio_duration, final_video_duration)
            
            logger.info(f"Audio will be placed from {audio_start_in_final:.2f}s to {audio_end_in_final:.2f}s in final video")
            
            # Create silence segments
            from moviepy.editor import AudioClip
            
            def make_silence(duration):
                """Create a silent audio clip of specified duration"""
                if duration <= 0:
                    return None
                return AudioClip(lambda t: 0, duration=duration)
            
            # Build the extended audio track
            audio_segments = []
            
            # 1. Silence before audio (if needed)
            silence_before_duration = audio_start_in_final
            if silence_before_duration > 0:
                silence_before = make_silence(silence_before_duration)
                audio_segments.append(silence_before)
                logger.info(f"Added {silence_before_duration:.2f}s of silence before audio")
            
            # 2. Original audio (may need to be trimmed if video is shorter)
            actual_audio_duration = audio_end_in_final - audio_start_in_final
            if actual_audio_duration < audio_duration:
                # Trim audio if video is too short
                trimmed_audio = audio_clip.subclip(0, actual_audio_duration)
                audio_segments.append(trimmed_audio)
                logger.info(f"Trimmed audio to {actual_audio_duration:.2f}s to fit video duration")
            else:
                audio_segments.append(audio_clip)
                logger.info(f"Using full audio duration: {audio_duration:.2f}s")
            
            # 3. Silence after audio (if needed)
            silence_after_duration = final_video_duration - audio_end_in_final
            if silence_after_duration > 0:
                silence_after = make_silence(silence_after_duration)
                audio_segments.append(silence_after)
                logger.info(f"Added {silence_after_duration:.2f}s of silence after audio")
            
            # Concatenate all audio segments
            if len(audio_segments) > 1:
                from moviepy.editor import concatenate_audioclips
                extended_audio = concatenate_audioclips(audio_segments)
            else:
                extended_audio = audio_segments[0]
            
            logger.info(f"Created extended audio track with duration: {extended_audio.duration:.2f}s (matches video: {final_video_duration:.2f}s)")
            
            # Create composite audio (mix with existing video audio if any)
            if final_video_clip.audio is not None:
                # Keep original video audio and add the new extended audio
                final_audio = CompositeAudioClip([final_video_clip.audio, extended_audio])
                logger.info("Mixed new audio with existing video audio")
            else:
                # No original audio, just use the extended audio
                final_audio = extended_audio
                logger.info("Using extended audio as the only audio track")
            
            # Set the audio to the video
            final_video = final_video_clip.set_audio(final_audio)
            
            # Write output video with better settings to avoid static frames
            logger.info(f"Writing synchronized video to {output_path}")
            # Normalize paths for FFMPEG compatibility on Windows
            from utils import normalize_path_for_ffmpeg
            output_path_ffmpeg = normalize_path_for_ffmpeg(output_path)
            temp_audiofile_ffmpeg = normalize_path_for_ffmpeg(os.path.join(temp_dir, 'temp_audio.m4a'))
            final_video.write_videofile(
                output_path_ffmpeg, 
                codec='libx264', 
                audio_codec='aac',
                logger=None,
                temp_audiofile=temp_audiofile_ffmpeg,
                ffmpeg_params=["-avoid_negative_ts", "make_zero"],  # Fix timing issues
                verbose=False,
                threads=4
            )
            
            # Clean up
            video.close()
            audio_clip.close()
            extended_audio.close()
            final_audio.close()
            final_video.close()
            if before_segment:
                before_segment.close()
            target_segment.close()
            adjusted_segment.close()
            if after_segment:
                after_segment.close()
            final_video_clip.close()
            
            # Clean up audio segments
            for segment in audio_segments:
                if segment:
                    segment.close()
            
            logger.info(f"Successfully created synchronized video: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to sync audio with video: {e}")
            raise
    
    def sync_multiple_audio_segments(
        self,
        video_path: str,
        audio_segments: List[dict],
        output_path: str,
        temp_dir: Optional[str] = None
    ) -> str:
        """
        Synchronize multiple audio segments with a video
        
        Args:
            video_path: Path to input video file
            audio_segments: List of dicts with keys: 'audio_path', 'start_time', 'end_time'
            output_path: Path for output video file
            temp_dir: Directory for temporary files
            
        Returns:
            Path to the synchronized video file
        """
        try:
            if not audio_segments:
                logger.warning("No audio segments provided, copying original video")
                import shutil
                shutil.copy2(video_path, output_path)
                return output_path
            
            if temp_dir is None:
                temp_dir = os.path.dirname(output_path)
            
            os.makedirs(temp_dir, exist_ok=True)
            
            # Start with the original video
            current_video_path = video_path
            
            # Apply each audio segment sequentially
            for i, segment in enumerate(audio_segments):
                temp_output = os.path.join(temp_dir, f"temp_video_{i}.mp4")
                
                self.sync_audio_with_video(
                    video_path=current_video_path,
                    audio_path=segment['audio_path'],
                    start_time=segment['start_time'],
                    end_time=segment['end_time'],
                    output_path=temp_output,
                    temp_dir=temp_dir
                )
                
                # Update current video path for next iteration
                if current_video_path != video_path:
                    # Remove previous temporary file
                    try:
                        os.remove(current_video_path)
                    except:
                        pass
                
                current_video_path = temp_output
            
            # Move final result to output path
            if current_video_path != output_path:
                import shutil
                shutil.move(current_video_path, output_path)
            
            logger.info(f"Successfully synchronized {len(audio_segments)} audio segments")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to sync multiple audio segments: {e}")
            raise
