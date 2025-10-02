import http.client
import json
import base64
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SpeechSegment:
    """Represents a speech segment in a video"""
    speaker: str
    start_time: float  # in seconds
    end_time: float    # in seconds
    confidence: float  # confidence score 0-1

class VideoSpeechAnalyzer:
    """Analyzes video to identify when speakers are talking"""
    
    def __init__(self, api_key: str, auth_token: str = "<token>"):
        self.api_key = api_key
        self.auth_token = auth_token
        
    def _encode_video_to_base64(self, video_path: str) -> str:
        """Convert video file to base64 string"""
        try:
            with open(video_path, "rb") as video_file:
                video_bytes = video_file.read()
                base64_encoded = base64.b64encode(video_bytes).decode('utf-8')
                return base64_encoded
        except Exception as e:
            logger.error(f"Failed to encode video {video_path}: {e}")
            raise
    
    def _build_prompt(self, characters_info: List[Dict], shot_info: Dict) -> str:
        """Build the prompt for the multimodal model"""
        
        # Build character descriptions
        character_descriptions = []
        for char in characters_info:
            desc = f"- {char['identifier_in_scene']}: {char['static_features']}"
            if char.get('dynamic_features'):
                desc += f" Currently: {char['dynamic_features']}"
            character_descriptions.append(desc)
        
        characters_text = "\n".join(character_descriptions)
        
        # Expected speaker and dialogue
        expected_speaker = shot_info.get('speaker', 'Unknown')
        expected_line = shot_info.get('line', '')
        
        prompt = f"""Analyze this video to identify when the speaker is talking. 

CHARACTERS IN THIS SCENE:
{characters_text}

EXPECTED DIALOGUE:
Speaker: {expected_speaker}
Line: "{expected_line}"

TASK: 
1. Identify the exact start and end timestamps (in seconds) when the speaker "{expected_speaker}" is actively speaking in the video
2. Look for mouth movements, facial expressions, and body language that indicate speech
3. Consider the character's physical description to correctly identify them

IMPORTANT NOTES:
- Focus on identifying the specific character "{expected_speaker}" based on their physical features
- Return timestamps with precision to 0.1 seconds (e.g., 1.2, 3.7)
- If the speaker talks multiple times, identify all speech segments
- Consider lip sync and natural speech patterns

Please respond in JSON format:
{{
    "speaker": "{expected_speaker}",
    "speech_segments": [
        {{
            "start_time": 0.0,
            "end_time": 2.5,
            "confidence": 0.9
        }}
    ],
    "analysis_notes": "Brief description of what you observed"
}}"""
        
        return prompt
    
    def analyze_video_speech(self, video_path: str, characters_info: List[Dict], shot_info: Dict) -> List[SpeechSegment]:
        """
        Analyze video to identify speech segments
        
        Args:
            video_path: Path to the video file
            characters_info: List of character information dicts from character.json files
            shot_info: Shot information dict from shot.json file
            
        Returns:
            List of SpeechSegment objects with timing information
        """
        try:
            # Encode video to base64
            logger.info(f"Encoding video {video_path} to base64...")
            video_base64 = self._encode_video_to_base64(video_path)
            
            # Build prompt
            prompt = self._build_prompt(characters_info, shot_info)
            
            # Prepare API request
            payload = json.dumps({
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "inline_data": {
                                    "mime_type": "video/mp4",
                                    "data": video_base64
                                }
                            },
                            {
                                "text": prompt
                            }
                        ]
                    }
                ]
            })
            
            headers = {
                'Authorization': f'Bearer {self.auth_token}',
                'Content-Type': 'application/json'
            }
            
            # Make API request
            logger.info("Sending request to multimodal model...")
            conn = http.client.HTTPSConnection("yunwu.ai")
            conn.request("POST", f"/v1beta/models/gemini-2.5-pro:generateContent?key={self.api_key}", payload, headers)
            res = conn.getresponse()
            data = res.read()
            
            response_text = data.decode("utf-8")
            logger.info(f"API response received: {response_text[:200]}...")
            
            # Parse response
            try:
                response_json = json.loads(response_text)
                
                # Extract the actual response content
                if 'candidates' in response_json and len(response_json['candidates']) > 0:
                    content = response_json['candidates'][0]['content']['parts'][0]['text']
                    
                    # Try to parse the JSON from the content
                    # The model might return the JSON wrapped in markdown code blocks
                    if '```json' in content:
                        json_start = content.find('```json') + 7
                        json_end = content.find('```', json_start)
                        json_content = content[json_start:json_end].strip()
                    elif '{' in content and '}' in content:
                        # Extract JSON from the response
                        json_start = content.find('{')
                        json_end = content.rfind('}') + 1
                        json_content = content[json_start:json_end]
                    else:
                        raise ValueError("No JSON content found in response")
                    
                    analysis_result = json.loads(json_content)
                    
                    # Convert to SpeechSegment objects
                    speech_segments = []
                    for segment in analysis_result.get('speech_segments', []):
                        speech_segment = SpeechSegment(
                            speaker=analysis_result.get('speaker', shot_info.get('speaker', 'Unknown')),
                            start_time=float(segment['start_time']),
                            end_time=float(segment['end_time']),
                            confidence=float(segment.get('confidence', 0.8))
                        )
                        speech_segments.append(speech_segment)
                    
                    logger.info(f"Successfully analyzed video, found {len(speech_segments)} speech segments")
                    
                    # Store the full analysis result for later use
                    self._last_analysis_result = {
                        'video_path': video_path,
                        'raw_response': content,
                        'parsed_result': analysis_result,
                        'speech_segments': [
                            {
                                'speaker': seg.speaker,
                                'start_time': seg.start_time,
                                'end_time': seg.end_time,
                                'confidence': seg.confidence
                            } for seg in speech_segments
                        ]
                    }
                    
                    return speech_segments
                    
                else:
                    raise ValueError("No candidates found in API response")
                    
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.error(f"Failed to parse API response: {e}")
                logger.error(f"Raw response: {response_text}")
                
                # Fallback: return a default segment based on shot duration
                logger.warning("Using fallback speech timing based on shot duration")
                duration_str = shot_info.get('duration', '5s')
                duration = float(duration_str.replace('s', ''))
                
                return [SpeechSegment(
                    speaker=shot_info.get('speaker', 'Unknown'),
                    start_time=0.5,  # Start slightly after beginning
                    end_time=min(duration - 0.5, duration * 0.8),  # End before the end
                    confidence=0.5  # Low confidence for fallback
                )]
                
        except Exception as e:
            logger.error(f"Failed to analyze video speech: {e}")
            raise
    
    def get_last_analysis_result(self) -> Optional[Dict]:
        """Get the last analysis result with full details"""
        return getattr(self, '_last_analysis_result', None)
    
    def save_analysis_result(self, output_path: str) -> None:
        """Save the last analysis result to a JSON file"""
        result = self.get_last_analysis_result()
        if result is None:
            logger.warning("No analysis result to save")
            return
        
        try:
            import os
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Analysis result saved to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to save analysis result: {e}")
            raise
