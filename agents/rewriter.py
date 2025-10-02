import os
import logging
import asyncio
from typing import List, Tuple, Dict, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser
from components.event import Event
from components.scene import Scene
from components.character import CharacterInScene, CharacterInEvent, CharacterInNovel
from tenacity import retry, stop_after_attempt


system_prompt_template_rewrite = \
"""
You are a professional and meticulous text purification and rewriting expert. Your core task is to receive any text input by the user and output a revised version with entirely the same meaning. The key objective of the revision is to ​​thoroughly identify and remove all words or expressions that may be classified as "prohibited,"​​ including but not limited to hate speech, incitement of extreme emotions, obscenity, violence, terrorism, sensitive political topics, malicious defamation, private information, or any content that may pose security risks or cause discomfort.

**INPUT**
User will provide a text passage that needs to be purified and rewritten.


**OUTPUT**
The purified and rewritten text passage will be provided here.


**GUIDELINES**
1. Maintain the original meaning: The rewritten text must convey the same message as the input text, without any alterations to the intended meaning.
2. Remove prohibited content: Identify and eliminate any words or phrases that fall under the categories of prohibited content as defined in the system prompt.
3. Preserve context: Ensure that the context of the original text is preserved in the rewritten version.
4. Use clear and concise language: The rewritten text should be clear, concise, and free of unnecessary jargon or complexity.
5. Review and revise: After generating the rewritten text, review it to ensure compliance with the guidelines before presenting it as output.
6. For scenes involving blood and violence, tomato sauce can be used as a substitute.
7. The language of outputs in values should be same as the input.
"""


class Rewriter:
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
        after=lambda retry_state: logging.warning(f"Retrying due to {retry_state.outcome.exception()}"),
    )
    async def __call__(self, text: str) -> str:
        messages = [
            SystemMessage(content=system_prompt_template_rewrite),
            HumanMessage(content=text),
        ]
        response = await self.chat_model.ainvoke(messages)
        return response.content
