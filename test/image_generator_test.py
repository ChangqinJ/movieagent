import os
import asyncio
from PIL import Image
from tools.image_generator.nanobanana import NanoBananaImageGenerator
from tools.image_generator.gemini import GeminiImageGenerator
from tools.image_generator.gpt4o import GPT4oImageGenerator


api_key = "sk-7Z55m4gaQXFmvL2jbGqW6CWb0kMiDQe1qkutjeTsxbVTodwY"
base_url = "https://yunwu.ai"


prompt = "A cute magical cat, digital art, watching the stars, running on the beach."
reference_image_paths = ["example_inputs/images/魔法猫咪.png"]

# prompt = "Two cute cats, digital art, watching the stars, running on the beach. One refers to the first image, the other refers to the second image."
# reference_image_paths = [
#     "example_inputs/images/魔法猫咪.png",
#     "example_inputs/images/小八.png"
# ]


# save_prefix = "example_inputs/images/gpt4o_output"
# image_generator = GPT4oImageGenerator(
#     api_key=api_key,
#     base_url=base_url,
#     model="gpt-image-1-all",
# )

save_prefix = "example_inputs/images/gemini_output"
image_generator = GeminiImageGenerator(
    api_key=api_key,
    base_url=base_url,
    model="gemini-2.5-flash-image-preview",
)

# save_prefix = "example_inputs/images/nanobanana_output"
# image_generator = NanoBananaImageGenerator(
#     api_key=api_key,
#     base_url=base_url,
#     model="nano-banana",
# )

image = asyncio.run(
    image_generator.generate_single_image(
        prompt=prompt,
        reference_image_paths=reference_image_paths,
        size="1536x1024",
    )
)
os.makedirs(save_prefix, exist_ok=True)
save_path = f"{save_prefix}/one_cat.png" if len(reference_image_paths) == 1 else f"{save_prefix}/two_cats.png"
image.save(save_path)

