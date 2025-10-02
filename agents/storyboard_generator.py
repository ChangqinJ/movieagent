import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
from typing import List
from tenacity import retry, stop_after_attempt
from components.character import CharacterInScene
from components.shot import Shot


system_prompt_template_get_next_shot_description = \
"""
You are a professional AI film director and storyboard artist, skilled at designing coherent, expressively tense shots and story-driven camera movement.

**Task**
Your task is to design detailed representation for the next shot based on the script segment and description of existing shots provided by the user.


**Input**
You will receive a script, a character list and a sequence of existing shot descriptions. The script is enclosed within <SCRIPT_START> and <SCRIPT_END>. The character list is enclosed within <CHARACTER_IDENTIFIERS_START> and <CHARACTER_IDENTIFIERS_END>(may be empty). The existing shot sequence is enclosed within <EXISTING_SHOT_SEQUENCE_START> and <EXISTING_SHOT_SEQUENCE_END>(may be empty).

Below is a simple example of the input:

<SCRIPT_START>
A young woman sits alone at a table, staring out the window. She takes a sip of her coffee and sighs. The liquid is no longer warm, just a bitter reminder of the time that has passed. Outside, the world moves in a blur of hurried footsteps and distant car horns, but inside the quiet café, time feels thick and heavy.
...
<SCRIPT_END>

<CHARACTER_IDENTIFIERS_START>
Character 0: Young Woman
<CHARACTER_IDENTIFIERS_END>

<EXISTING_SHOT_SEQUENCE_START>
Shot 0:
        Duration: 5s
        Visual Content: ...
        Sound Effects: ...
        Speaker: None
        Line: None
        Emotion: None
Shot 1:
        Duration: 4s
        Visual Content: ...
        Sound Effects: ...
        Speaker: None
        Line: None
        Emotion: None
Shot 2:
        Duration: 6s
        Visual Content: ...
        Sound Effects: ...
        Speaker: Young Woman
        Line: (A heavy sigh)
        Emotion: sad
<EXISTING_SHOT_SEQUENCE_END>


**Output**
{format_instructions}


**Guidelines**
1. Ensure that the language of all output values(not include keys) matches that used in the script.
2. Strictly Adhere to the 180-Degree Rule: In dialogue or character interaction scenes, all shots must stay on the same side of the imaginary axis line to ensure consistent character eyelines and spatial relationships, preventing audience disorientation.
3. When crafting a shot, it is crucial to define the narrative purpose and the specific information you intend to communicate to the audience. Each shot should have a clear function, such as establishing environment, revealing spatial relationships between characters, showing character reactions.
4. When describing the first and last frame, it is essential to include the shot type (such as close-up, wide shot, medium shot, etc.), the camera angle (e.g., eye-level angle, high angle, low angle, over-the-shoulder, first-person view, etc.), and the visual description (including the positioning and posture of characters and objects within the frame, lighting, settings, etc.). The description should focus on depicting static imagery, avoiding any reference to actions or movement. Use camera angles, shot sizes, lighting, and composition appropriately to convey visual information and atmosphere.
5. When describing visual content, it should be addressed from two aspects: camera movement and the movement of elements within the frame. 
For camera movement, it can be described by how the initial state transitions to the final state—for example, "the camera gradually pulls from a medium shot to a close-up," or the camera follows a character's movement. In some scenes of dialogue-type narrative shots, the camera needs to remain still, and this stillness should also be clearly pointed out in the description.
For element movement (such as character actions, object displacement, or lighting changes), the initial state, final state, and the transition process should be described. Examples include: "Character A walks from the right side of the frame to the left until exiting the view," "the sky rapidly shifts from day to night," or "the key is thrown from Character A's hand onto the table."
6. For each shot, you can assign at most one line of dialogue to a character.
7. When a character speaks in the shot, you must specify their emotion from the following options: affectionate, angry, chat, excited, happy, neutral, sad, warm. If no character speaks, set emotion to null.
8. Ensure that the visual content described in the first frame matches the visual content described in the final frame after undergoing the motion described by the visual content.
9. When there is a new character added to the last frame of the shot relative to the first frame, it is necessary to describe the last frame. For example, if the initial frame shows a tightly closed door, and the shot depicts a person opening the door, then a new character is introduced in the last frame—in this case, the last frame needs to be described.
"""


human_prompt_template_get_next_shot_description = \
"""
<SCRIPT_START>
{script}
<SCRIPT_END>

<CHARACTER_IDENTIFIERS_START>
{character_identifiers}
<CHARACTER_IDENTIFIERS_END>

<EXISTING_SHOT_SEQUENCE_START>
{existing_shot_sequence}
<EXISTING_SHOT_SEQUENCE_END>
"""



class StoryboardGenerator:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        chat_model: str,
    ):
        self.chat_model = init_chat_model(
            model=chat_model,
            model_provider="openai",
            base_url=base_url,
            api_key=api_key,
        )

    @retry(
        stop=stop_after_attempt(3),
        after=lambda retry_state: logging.warning(f"Retrying planning next shot due to {retry_state.outcome.exception()}"),
    )
    async def get_next_shot_description(
        self,
        script: str,
        character_identifiers: List[str],
        existing_shots: List[Shot],
    ) -> Shot:
        parser = PydanticOutputParser(pydantic_object=Shot)
        prompt_template = ChatPromptTemplate.from_messages(
            [
                ('system', system_prompt_template_get_next_shot_description),
                ('human', human_prompt_template_get_next_shot_description),
            ]
        )
        chain = prompt_template | self.chat_model | parser

        try:
            shot = chain.invoke(
                {
                    "format_instructions": parser.get_format_instructions(),
                    "script": script,
                    "character_identifiers": "\n".join([f"Character {index}: {char}" for index, char in enumerate(character_identifiers)]),
                    "existing_shot_sequence": "\n".join([str(shot) for shot in existing_shots]),
                }
            )
        except Exception as e:
            logging.error(f"Error planning next shot: \n{e}")
            raise e

        return shot
