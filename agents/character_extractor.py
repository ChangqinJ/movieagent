import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
from typing import List
from tenacity import retry, stop_after_attempt
from components.character import CharacterInScene
from langchain_core.messages import HumanMessage, SystemMessage


system_prompt_template_extract_characters = \
"""
You are a top-tier movie script analysis expert.

**TASK**
Your task is to analyze the provided script and extract all relevant character information.

**INPUT**
You will receive a script enclosed within <SCRIPT_START> and <SCRIPT_END>.

Below is a simple example of the input:

<SCRIPT_START>
A young woman sits alone at a table, staring out the window. She takes a sip of her coffee and sighs. The liquid is no longer warm, just a bitter reminder of the time that has passed. Outside, the world moves in a blur of hurried footsteps and distant car horns, but inside the quiet café, time feels thick and heavy.
Her finger traces the rim of the ceramic mug, following the imperfect circle over and over. The decision she had to make was supposed to be simple—a mere checkbox on the form of her life. Yesor No. Stayor Go. Yet, it had rooted itself in her chest, a tangled knot of fear and longing.
<SCRIPT_END>

**OUTPUT**
{format_instructions}


**GUIDELINES**
1. Group all names referring to the same entity under one character. Select the most appropriate name as the character's identifier. If the person is a real famous person, the real person's name should be retained (e.g., Elon Musk, Bill Gates)
2. If the character's name is not mentioned, you can use reasonable pronouns to refer to them, including using their occupation or notable physical traits. For example, "the young woman" or "the barista".
3. For background characters in the script, you do not need to consider them as individual characters.
4. If a character's traits are not described or only partially outlined in the script, you need to design plausible features based on the context to make their characteristics more complete and detailed, ensuring they are vivid and evocative.
5. Ensure that the language of all output values(not include keys) matches that used in the script.
"""

human_prompt_template_extract_characters = \
"""
<SCRIPT_START>
{script}
<SCRIPT_END>
"""


class ExtractCharactersResponse(BaseModel):
    characters: List[CharacterInScene] = Field(
        ..., description="A list of characters extracted from the script."
    )



class CharacterExtractor:
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
        after=lambda retry_state: logging.warning(f"Retrying extracting characters due to {retry_state.outcome.exception()}"),
    )
    async def __call__(self, script: str) -> List[CharacterInScene]:

        parser = PydanticOutputParser(pydantic_object=ExtractCharactersResponse)
        
        messages = [
            SystemMessage(content=system_prompt_template_extract_characters.format(format_instructions=parser.get_format_instructions())),
            HumanMessage(content=human_prompt_template_extract_characters.format(script=script)),
        ]

        chain = self.chat_model | parser

        response: ExtractCharactersResponse = chain.invoke(messages)

        return response.characters

