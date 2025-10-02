from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Tuple



class Shot(BaseModel):
    idx: int = Field(
        description="The index of the shot in the sequence, starting from 0."
    )
    is_last: bool = Field(
        description="Whether this is the last shot in the sequence. If True, no more shots will be planned after this one."
    )

    duration: str = Field(
        description="The estimated duration of the shot, typically between 3 to 10 seconds.",
    )

    # visual
    first_frame: str = Field(
        ...,
        description="Detail the static first frame of the shot (composition, characters, setting, lighting, color, etc.), emphasizing visual details. For example, 'A close-up shot of a woman's face positioned on the left side of the frame, with a window on the right, as she gazes toward the window.'"
    )
    visual_content: str = Field(
        ...,
        description="Describe the dynamic visual changes within the shot (camera movement and the movement of elements within the frame) no more than 100 words."
    )
    last_frame: Optional[str] = Field(
        default=None,
       description="When there is a significant difference between the last frame and the first frame, particularly if a new character appears in the last frame, it is necessary to provide a description of the last frame. Otherwise, this field can be left empty."
    )


    # audio
    sound_effect: Optional[str] = Field(
        default=None,
        description="The sound effects used in the shot. For example, a door creaking or footsteps approaching."
    )
    speaker: Optional[str] = Field(
        default=None,
        description="The speaker in the shot, if applicable. Not more than one. The speaker identifier must match one of the character identifiers."
    )
    line: Optional[str] = Field(
        default=None,
        description="The dialogue or monologue in the shot, if applicable. Avoid outputting punctuation marks other than commas, periods, question marks, and exclamation marks."
    )
    emotion: Optional[str] = Field(
        default=None,
        description="The emotion of the speaker in the shot, if applicable. Can only choose one from the following emotions: affectionate, angry, chat, excited, happy, neutral, sad, warm."
    )
    # Runtime attributes (not part of the original model)
    # frame_paths: Optional[List[str]] = Field(
    #     default=None,
    #     description="List of frame image paths generated for this shot, used for video generation."
    # )


    def __str__(self):
        s = f"Shot {self.idx}:"
        s += f"\n\tDuration: {self.duration}"
        # s += f"\n\tCamera Type: {self.camera_type}"
        # s += f"\n\tCamera Angle: {self.camera_angle}"
        # s += f"\n\tCamera Movement: {self.camera_movement}"
        # s += f"\n\tVisual Description: {self.visual_description}"
        # s += f"\n\tFirst Frame Visual Description: {self.first_frame_visual_description}"
        s += f"\n\tVisual Content: {self.visual_content}"
        # s += f"\n\tLast Frame Visual Description: {self.last_frame_visual_description}"
        s += f"\n\tSound Effects: {self.sound_effect}"
        s += f"\n\tSpeaker: {self.speaker}"
        s += f"\n\tLine: {self.line}"
        s += f"\n\tEmotion: {self.emotion}"
        return s

    def __repr__(self):
        return self.__str__()

