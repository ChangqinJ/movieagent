import os
import json
import logging
from typing import Dict, List, Optional
from tools.video_analyzer import VideoSpeechAnalyzer, SpeechSegment
from utils.audio_video_sync import AudioVideoSynchronizer

logger = logging.getLogger(__name__)

class VideoAudioProcessor:
    """
    Integrated processor for synchronizing audio with video based on speech analysis
    """
    
    def __init__(self, api_key: str, auth_token: str = "<token>"):
        """
        Initialize the processor
        
        Args:
            api_key: API key for the multimodal model
            auth_token: Authorization token for the API
        """
        self.video_analyzer = VideoSpeechAnalyzer(api_key, auth_token)
        self.audio_synchronizer = AudioVideoSynchronizer()
    
    def load_character_info(self, characters_dir: str, speaker_name: str) -> Dict:
        """
        Load character information from JSON file
        
        Args:
            characters_dir: Directory containing character JSON files
            speaker_name: Name of the speaker
            
        Returns:
            Character information dictionary
        """
        character_file = os.path.join(characters_dir, f"{speaker_name}.json")
        
        if not os.path.exists(character_file):
            logger.warning(f"Character file not found: {character_file}")
            return {
                'identifier_in_scene': speaker_name,
                'static_features': f'Character named {speaker_name}',
                'dynamic_features': 'No specific appearance details available'
            }
        
        try:
            with open(character_file, 'r', encoding='utf-8') as f:
                character_info = json.load(f)
            logger.info(f"Loaded character info for {speaker_name}")
            return character_info
        except Exception as e:
            logger.error(f"Failed to load character info for {speaker_name}: {e}")
            raise
    
    def _select_best_speech_segment(self, speech_segments: List, shot_info: Dict) -> object:
        """
        Select the best speech segment from multiple segments based on various criteria
        
        Args:
            speech_segments: List of SpeechSegment objects
            shot_info: Shot information dictionary
            
        Returns:
            Best SpeechSegment object
        """
        if not speech_segments:
            raise ValueError("No speech segments provided")
        
        if len(speech_segments) == 1:
            return speech_segments[0]
        
        # Selection criteria (in order of priority):
        # 1. Highest confidence score
        # 2. Longest duration (more speech content)
        # 3. Earlier start time (prefer earlier speech)
        
        best_segment = speech_segments[0]
        best_score = 0
        
        for segment in speech_segments:
            duration = segment.end_time - segment.start_time
            
            # Calculate composite score
            # Confidence weight: 0.6, Duration weight: 0.3, Early timing weight: 0.1
            confidence_score = segment.confidence * 0.6
            duration_score = min(duration / 5.0, 1.0) * 0.3  # Normalize to max 5 seconds
            timing_score = max(0, (10.0 - segment.start_time) / 10.0) * 0.1  # Prefer earlier timing
            
            composite_score = confidence_score + duration_score + timing_score
            
            logger.debug(f"Segment {segment.start_time:.1f}-{segment.end_time:.1f}s: "
                        f"confidence={segment.confidence:.2f}, duration={duration:.1f}s, "
                        f"score={composite_score:.3f}")
            
            if composite_score > best_score:
                best_score = composite_score
                best_segment = segment
        
        logger.info(f"Selected best segment: {best_segment.start_time:.1f}-{best_segment.end_time:.1f}s "
                   f"(confidence: {best_segment.confidence:.2f}, score: {best_score:.3f})")
        
        return best_segment

    def load_all_characters_in_scene(self, characters_dir: str) -> List[Dict]:
        """
        Load all character information from the characters directory
        
        Args:
            characters_dir: Directory containing character JSON files
            
        Returns:
            List of character information dictionaries
        """
        characters = []
        
        if not os.path.exists(characters_dir):
            logger.warning(f"Characters directory not found: {characters_dir}")
            return characters
        
        try:
            # Load character registry to get list of characters
            registry_file = os.path.join(characters_dir, "character_registry.json")
            if os.path.exists(registry_file):
                with open(registry_file, 'r', encoding='utf-8') as f:
                    registry = json.load(f)
                
                for character_name in registry.keys():
                    character_info = self.load_character_info(characters_dir, character_name)
                    characters.append(character_info)
            else:
                # Fallback: scan for JSON files in the directory
                for filename in os.listdir(characters_dir):
                    if filename.endswith('.json') and filename != 'character_registry.json' and filename != 'character_vocal_mapping.json':
                        character_name = filename[:-5]  # Remove .json extension
                        character_info = self.load_character_info(characters_dir, character_name)
                        characters.append(character_info)
            
            logger.info(f"Loaded {len(characters)} characters from {characters_dir}")
            return characters
            
        except Exception as e:
            logger.error(f"Failed to load characters from {characters_dir}: {e}")
            return []
    
    def process_shot_audio_sync(
        self,
        video_path: str,
        audio_path: str,
        shot_info: Dict,
        characters_dir: str,
        output_path: str,
        temp_dir: Optional[str] = None
    ) -> str:
        """
        Process a single shot to synchronize audio with video
        
        Args:
            video_path: Path to the video file
            audio_path: Path to the generated audio file
            shot_info: Shot information from JSON file
            characters_dir: Directory containing character information
            output_path: Path for the synchronized output video
            temp_dir: Directory for temporary files
            
        Returns:
            Path to the synchronized video file
        """
        try:
            logger.info(f"Processing audio sync for shot with speaker: {shot_info.get('speaker', 'Unknown')}")
            
            # Check if shot has speaker and dialogue
            if not shot_info.get('speaker') or not shot_info.get('line'):
                logger.info("Shot has no speaker/dialogue, copying original video")
                import shutil
                shutil.copy2(video_path, output_path)
                return output_path
            
            # Load character information
            characters_info = self.load_all_characters_in_scene(characters_dir)
            
            if not characters_info:
                logger.warning("No character information found, using fallback timing")
                # Use fallback timing based on shot duration
                duration_str = shot_info.get('duration', '5s')
                duration = float(duration_str.replace('s', ''))
                
                speech_segments = [SpeechSegment(
                    speaker=shot_info['speaker'],
                    start_time=0.5,
                    end_time=min(duration - 0.5, duration * 0.8),
                    confidence=0.5
                )]
            else:
                # Analyze video to get speech timing
                logger.info("Analyzing video for speech timing...")
                speech_segments = self.video_analyzer.analyze_video_speech(
                    video_path=video_path,
                    characters_info=characters_info,
                    shot_info=shot_info
                )
                
                # Save the analysis result
                analysis_output_path = os.path.join(os.path.dirname(video_path), f"{os.path.splitext(os.path.basename(video_path))[0]}_speech_analysis.json")
                self.video_analyzer.save_analysis_result(analysis_output_path)
            
            if not speech_segments:
                logger.warning("No speech segments detected, using fallback timing")
                duration_str = shot_info.get('duration', '5s')
                duration = float(duration_str.replace('s', ''))
                
                speech_segments = [SpeechSegment(
                    speaker=shot_info['speaker'],
                    start_time=0.5,
                    end_time=min(duration - 0.5, duration * 0.8),
                    confidence=0.5
                )]
            
            # Select the best speech segment for synchronization
            speech_segment = self._select_best_speech_segment(speech_segments, shot_info)
            logger.info(f"Selected speech segment from {speech_segment.start_time:.2f}s to {speech_segment.end_time:.2f}s (confidence: {speech_segment.confidence:.2f})")
            
            if len(speech_segments) > 1:
                logger.info(f"Multiple speech segments detected ({len(speech_segments)}), selected the best one based on confidence and duration")
            
            # Synchronize audio with video
            synchronized_video = self.audio_synchronizer.sync_audio_with_video(
                video_path=video_path,
                audio_path=audio_path,
                start_time=speech_segment.start_time,
                end_time=speech_segment.end_time,
                output_path=output_path,
                temp_dir=temp_dir
            )
            
            logger.info(f"Successfully synchronized audio for shot, output: {synchronized_video}")
            return synchronized_video
            
        except Exception as e:
            logger.error(f"Failed to process shot audio sync: {e}")
            # Fallback: copy original video
            logger.warning("Falling back to original video without audio sync")
            import shutil
            shutil.copy2(video_path, output_path)
            return output_path
    
    def process_multiple_shots(
        self,
        shots_dir: str,
        working_dir: str,
        temp_dir: Optional[str] = None
    ) -> List[str]:
        """
        Process multiple shots for audio synchronization
        
        Args:
            shots_dir: Directory containing shot files and videos
            working_dir: Working directory containing character info and audio files
            temp_dir: Directory for temporary files
            
        Returns:
            List of synchronized video file paths
        """
        try:
            if temp_dir is None:
                temp_dir = os.path.join(working_dir, "temp_sync")
            
            os.makedirs(temp_dir, exist_ok=True)
            
            characters_dir = os.path.join(working_dir, "characters")
            synchronized_videos = []
            
            shot_idx = 0
            while True:
                # Check for shot files
                shot_file = os.path.join(shots_dir, f"{shot_idx}.json")
                video_file = os.path.join(shots_dir, f"{shot_idx}_video.mp4")
                audio_file = os.path.join(shots_dir, f"shot_{shot_idx}_vocal.wav")
                
                if not os.path.exists(shot_file):
                    break
                
                logger.info(f"Processing shot {shot_idx}...")
                
                # Load shot information
                with open(shot_file, 'r', encoding='utf-8') as f:
                    shot_info = json.load(f)
                
                # Check if video exists
                if not os.path.exists(video_file):
                    logger.warning(f"Video file not found for shot {shot_idx}: {video_file}")
                    shot_idx += 1
                    continue
                
                # Output path for synchronized video
                output_video = os.path.join(shots_dir, f"{shot_idx}_video_synced.mp4")
                
                # Check if shot has audio to sync
                if os.path.exists(audio_file) and shot_info.get('speaker') and shot_info.get('line'):
                    # Process audio synchronization
                    self.process_shot_audio_sync(
                        video_path=video_file,
                        audio_path=audio_file,
                        shot_info=shot_info,
                        characters_dir=characters_dir,
                        output_path=output_video,
                        temp_dir=temp_dir
                    )
                else:
                    # No audio to sync, just copy the original video
                    logger.info(f"Shot {shot_idx} has no audio to sync, using original video")
                    import shutil
                    shutil.copy2(video_file, output_video)
                
                synchronized_videos.append(output_video)
                shot_idx += 1
            
            logger.info(f"Processed {len(synchronized_videos)} shots for audio synchronization")
            
            # Save a summary of all speech analysis results
            self._save_analysis_summary(shots_dir, temp_dir)
            
            return synchronized_videos
            
        except Exception as e:
            logger.error(f"Failed to process multiple shots: {e}")
            raise
    
    def _save_analysis_summary(self, shots_dir: str, temp_dir: str):
        """Save a summary of all speech analysis results"""
        try:
            summary = {
                "analysis_timestamp": __import__("datetime").datetime.now().isoformat(),
                "shots_analyzed": [],
                "total_shots": 0,
                "total_speech_segments": 0
            }
            
            # Collect all analysis files
            analysis_files = [f for f in os.listdir(shots_dir) if f.endswith('_speech_analysis.json')]
            
            for analysis_file in analysis_files:
                analysis_path = os.path.join(shots_dir, analysis_file)
                try:
                    with open(analysis_path, 'r', encoding='utf-8') as f:
                        analysis_data = json.load(f)
                    
                    shot_summary = {
                        "analysis_file": analysis_file,
                        "video_path": analysis_data.get('video_path', ''),
                        "speech_segments_count": len(analysis_data.get('speech_segments', [])),
                        "speech_segments": analysis_data.get('speech_segments', []),
                        "analysis_notes": analysis_data.get('parsed_result', {}).get('analysis_notes', '')
                    }
                    
                    summary["shots_analyzed"].append(shot_summary)
                    summary["total_speech_segments"] += shot_summary["speech_segments_count"]
                    
                except Exception as e:
                    logger.warning(f"Failed to read analysis file {analysis_file}: {e}")
            
            summary["total_shots"] = len(summary["shots_analyzed"])
            
            # Save summary
            summary_path = os.path.join(shots_dir, "speech_analysis_summary.json")
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Speech analysis summary saved to {summary_path}")
            logger.info(f"Summary: {summary['total_shots']} shots, {summary['total_speech_segments']} speech segments")
            
        except Exception as e:
            logger.error(f"Failed to save analysis summary: {e}")

    def cleanup_temp_files(self, temp_dir: str):
        """Clean up temporary files"""
        try:
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to clean up temp directory {temp_dir}: {e}")
