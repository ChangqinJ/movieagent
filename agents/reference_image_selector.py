import logging
from typing import List, Tuple
from tenacity import retry, stop_after_attempt
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain.chat_models import init_chat_model
from utils.image import image_path_to_b64

system_prompt_template_select_reference_images = \
"""
You are a professional visual creation assistant skilled in multimodal image analysis and reasoning.

**Task**
Your core task is to intelligently select the most suitable reference images from a provided reference image library (including multiple character reference images and existing scene images from prior frames) based on the user's text description (describing the target frame), ensuring that the subsequently generated image meets the following key consistencies:

(1) Character Consistency: The appearance (eg. gender, ethnicity, age, facial features, hairstyle, body shape), clothing, expression, posture, etc., of the generated character should highly match the reference images.

(2) Environmental Consistency: The scene of the generated image (e.g., background, lighting, atmosphere, layout) should remain coherent with the existing images from prior frames.

(3) Style Consistency: The visual style of the generated image (e.g., realistic, cartoon, film-like, color tone) should harmonize with the reference images and existing images.

**Input**
You will receive a text description of the target frame, along with a set of reference images. The text description of the target frame is enclosed within <FRAME_DESCRIPTION_START> and <FRAME_DESCRIPTION_END>. Each reference image is provided with a brief text description. The reference images are indexed starting from 0.

**Output**
You need to select the most relevant reference images based on the user's description and put the corresponding indices in the `ref_image_indices` field of the output. At the same time, you should generate a text prompt that describes the image to be created, specifying which elements in the generated image should reference which image (and which elements within it).

{format_instructions}


**Note**
1. The reference images may depict the same character from different angles, in different outfits, or in different scenes. Identify the image closest to the version described by the user.
2. Ensure maximum visual consistency across character appearance, environmental context, and stylistic elements. Enable coherent visual storytelling across sequential images
3. Prioritize images with similar compositions (frame by the same camera).
4. Choose reference images that are as concise as possible and avoid including duplicate information. Not more than 5 images should be selected.
5. Ensure that the language of all output values(not include keys) matches that used in the frame description.
"""


human_prompt_template_select_reference_images = \
"""
<FRAME_DESCRIPTION_START>
{frame_description}
<FRAME_DESCRIPTION_END>
"""

system_prompt_template_select_reference_images_on_text = \
"""
You are a professional visual creation assistant skilled in multimodal image analysis and reasoning.

**Task**
Your core task is to intelligently select the most suitable reference images from a provided set of reference image descriptions (including multiple character reference images and existing scene images from prior frames) based on the user's text description (describing the target frame), ensuring that the subsequently generated image meets the following key consistencies:

(1) Character Consistency: The appearance (eg. gender, ethnicity, age, facial features, hairstyle, body shape), clothing, expression, posture, etc., of the generated character should highly match the reference image descriptions.

(2) Environmental Consistency: The scene of the generated image (e.g., background, lighting, atmosphere, layout) should remain coherent with the existing image descriptions from prior frames.

(3) Style Consistency: The visual style of the generated image (e.g., realistic, cartoon, film-like, color tone) should harmonize with the reference image descriptions.

**Input**
You will receive a text description of the target frame, along with a set of reference image descriptions. The text description of the target frame is enclosed within <FRAME_DESCRIPTION_START> and <FRAME_DESCRIPTION_END>. Each reference image is provided with a brief text description. The reference images are indexed starting from 0.

**Output**
You need to select up to 8 of the most relevant reference images based on the user's description and put the corresponding indices in the ref_image_indices field of the output. At the same time, you should generate a text prompt that describes the image to be created, specifying which elements in the generated image should reference which image description (and which elements within it).

{format_instructions}

**Note**
1.The reference image descriptions may depict the same character from different angles, in different outfits, or in different scenes. Identify the description closest to the version described by the user.
2.Ensure maximum visual consistency across character appearance, environmental context, and stylistic elements based on the textual descriptions. Enable coherent visual storytelling across sequential images.
3.Prioritize image descriptions with similar compositions (frame by the same camera).
4.Choose reference image descriptions that are as concise as possible and avoid including duplicate information. Select at most **8** optimal reference image descriptions.
5.Ensure that the language of all output values(not include keys) matches that used in the frame description.
"""



class RefImageIndicesAndTextPrompt(BaseModel):
    ref_image_indices: List[int] = Field(
        ...,
        description="Indices of reference images selected from the provided images. For example, [0, 2, 5] means selecting the first, third, and sixth images. The indices should be 0-based."
    )
    text_prompt: str = Field(
        ...,
        description="Text description to guide the image generation. You need to describe the image to be generated, specifying which elements in the generated image should reference which image (and which elements within it). For example, 'Create an image following the given description: \nThe man is standing in the landscape. The man should reference the Image 0. The landscape should reference the Image 1.' Here, the index of the reference image should refer to its position in the ref_image_indices list, not the sequence number in the provided image list."
    )



class ReferenceImageSelector:
    def __init__(
        self,
        chat_model: str,
        base_url: str,
        api_key: str,
    ):
        self.base_url = base_url
        self.api_key = api_key

        self.chat_model = init_chat_model(
            model=chat_model,
            model_provider="openai",
            base_url=base_url,
            api_key=api_key,
        )


    @retry(
        stop=stop_after_attempt(3),
        after=lambda retry_state: logging.warning(f"Retrying extracting characters due to {retry_state.outcome.exception()}"),
    )
    def __call__(
        self,
        available_image_path_and_text_pairs: List[Tuple[str, str]],
        frame_description: str,
    ):
        filter_content = []
        for idx, (image_url, text) in enumerate(available_image_path_and_text_pairs):
            filter_content.append({
                "type": "text",
                "text": f"Image {idx}: {text}"
            })
            logging.info(f"Image idx:{idx}, Text:{text}")
        filter_content.append({
            "type": "text",
            "text": human_prompt_template_select_reference_images.format(frame_description=frame_description)
        })
        parser = PydanticOutputParser(pydantic_object=RefImageIndicesAndTextPrompt)

        messages = [
            SystemMessage(content=system_prompt_template_select_reference_images_on_text.format(format_instructions=parser.get_format_instructions())),
            HumanMessage(content=filter_content)
        ]

        chain = self.chat_model | parser

        try:
            ref = chain.invoke(messages)

        except Exception as e:
            logging.error(f"Error get image prompt: \n{e}")
            raise e

        filtered_idx = ref.ref_image_indices

        filtered_image_path_and_text_pairs = [available_image_path_and_text_pairs[i] for i in filtered_idx]
        logging.info(f"Filtered image idx:{filtered_idx}")
        human_content = []
        for idx, (image_url, text) in enumerate(filtered_image_path_and_text_pairs):
            human_content.append({
                "type": "text",
                "text": f"Image {idx}: {text}"
            })
            human_content.append({
                "type": "image_url",
                "image_url": {"url": image_path_to_b64(image_url)}
            })
        human_content.append({
            "type": "text",
            "text": human_prompt_template_select_reference_images.format(frame_description=frame_description)
        })

        parser = PydanticOutputParser(pydantic_object=RefImageIndicesAndTextPrompt)

        messages = [
            SystemMessage(content=system_prompt_template_select_reference_images.format(format_instructions=parser.get_format_instructions())),
            HumanMessage(content=human_content)
        ]

        chain = self.chat_model | parser

        try:
            response = chain.invoke(messages)        
            response.ref_image_indices = [filtered_idx[i] for i in response.ref_image_indices]
        except Exception as e:
            logging.error(f"Error get image prompt: \n{e}")
            raise e


        return {
            "reference_image_path_and_text_pairs": [available_image_path_and_text_pairs[i] for i in response.ref_image_indices],
            "text_prompt": response.text_prompt,
        }
