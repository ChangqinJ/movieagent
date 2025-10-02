import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
from typing import List, Dict
from tenacity import retry, stop_after_attempt
from components.character import CharacterInScene


system_prompt_template_assign_vocal_mapping = \
"""
You are a professional audio casting director for film and television productions.

**TASK**
Your task is to assign appropriate voice types to characters based on their characteristics and the available voice options.

**INPUT**
You will receive:
1. A list of characters with their descriptions
2. A list of available voice types with their characteristics

**GUIDELINES**
1. Assign voice types based on character gender, age, and personality traits
2. Female characters should be assigned to Female voice types (Female1, Female2)
3. Male characters should be assigned to Male voice types (Male1, Male2, Male3)
4. Consider character personality and role importance when choosing specific voice types
5. Each character must be assigned exactly one voice type
6. Multiple characters can share the same voice type if necessary
7. Ensure diversity in voice assignment when possible

**AVAILABLE VOICE TYPES**
- Female1: warm, mature female voice
- Female2: young, energetic female voice
- Male1: deep, authoritative male voice
- Male2: smooth, charismatic male voice
- Male3: young, friendly male voice

**OUTPUT**
{format_instructions}
"""


human_prompt_template_assign_vocal_mapping = \
"""
Characters to assign:
{characters_info}
"""


class CharacterVocalMapping(BaseModel):
    character_name: str = Field(description="The character's identifier_in_scene")
    assigned_voice: str = Field(description="The assigned voice type key (Female1, Female2, Male1, Male2, or Male3)")
    reasoning: str = Field(description="Brief explanation for why this voice type was chosen")


class VocalMappingResponse(BaseModel):
    mappings: List[CharacterVocalMapping] = Field(
        description="List of character-to-voice assignments"
    )


class VocalMapper:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        chat_model: str,
    ):
        self.chat_model = init_chat_model(
            model=chat_model,
            model_provider="openai",
            api_key=api_key,
            base_url=base_url,
        )

    @retry(
        stop=stop_after_attempt(3),
        after=lambda retry_state: logging.warning(f"Retrying vocal mapping due to {retry_state.outcome.exception()}"),
    )
    async def assign_vocal_mapping(
        self, 
        characters: List[CharacterInScene]
    ) -> Dict[str, str]:
        """
        Assign vocal mapping for characters
        
        Args:
            characters: List of CharacterInScene objects
            
        Returns:
            Dict mapping character identifier_in_scene to voice type key
        """
        
        # Prepare character info for the prompt
        characters_info = []
        for char in characters:
            info = f"Character: {char.identifier_in_scene}\n"
            info += f"Static features: {char.static_features}\n"
            info += f"Dynamic features: {char.dynamic_features}\n"
            characters_info.append(info)
        
        characters_text = "\n".join(characters_info)
        
        parser = PydanticOutputParser(pydantic_object=VocalMappingResponse)
        
        prompt_template = ChatPromptTemplate.from_messages([
            ('system', system_prompt_template_assign_vocal_mapping),
            ('human', human_prompt_template_assign_vocal_mapping),
        ])
        
        chain = prompt_template | self.chat_model | parser
        
        try:
            response: VocalMappingResponse = chain.invoke({
                "format_instructions": parser.get_format_instructions(),
                "characters_info": characters_text,
            })
            
            # Convert to simple dict mapping
            mapping_dict = {}
            for mapping in response.mappings:
                mapping_dict[mapping.character_name] = mapping.assigned_voice
                logging.info(f"Assigned {mapping.character_name} -> {mapping.assigned_voice}: {mapping.reasoning}")
            
            return mapping_dict
            
        except Exception as e:
            logging.error(f"Error assigning vocal mapping: {e}")
            raise e
