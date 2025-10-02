import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
from typing import List, Optional
from tenacity import retry, stop_after_attempt


system_prompt_template_script_planner = \
"""
You are a world-class creative writing and screenplay development expert with extensive experience in story structure, character development, and narrative pacing.

**Task**
Your task is to transform a basic story idea into a comprehensive, engaging script with rich narrative detail, compelling character arcs, and cinematic storytelling elements.

**Input**
You will receive a basic story idea or concept enclosed within <BASIC_IDEA_START> and <BASIC_IDEA_END>.

Below is a simple example of the input:

<BASIC_IDEA_START>
A person discovers they can time travel but every time they change something, they lose a memory.
<BASIC_IDEA_END>

**Output**
{format_instructions}

**Guidelines**
No metaphors allowed!!! (eg. A gust of wind rustled through it, a ghostly touch. ; an F1 car that looks less like a vehicle and more like a fighter jet stripped of its wings)

1. **Story Structure**: Develop a clear three-act structure with proper setup, confrontation, and resolution. Include compelling plot points, rising action, climax, develop the content according to the plot timeline, maintain a clear main plotline, and maintain coherent narrative connections. Keep the plot moving forward. Avoid summarizing events and characters, and use dialogue between key characters appropriately.

2. **Character Development**: Create well-rounded characters with clear motivations, flaws, and character arcs. Ensure protagonists have relatable goals and face meaningful obstacles.

3. **Visual Storytelling**: Write with cinematic language that emphasizes visual elements, actions, and atmospheric details rather than exposition-heavy dialogue.

4. **Emotional Depth**: Incorporate emotional beats, internal conflicts, and character relationships that resonate with audiences.

5. **Pacing and Tension**: Build suspense and maintain engagement through proper scene transitions, conflict escalation, and strategic revelation of information.

6. **Genre Consistency**: Maintain appropriate tone, style, and conventions for the story's genre while adding unique creative elements.

7. **Dialogue Quality**: When you writing some dialogue, you should use the:" " symbols (eg. Peter says: "Everything is looking good. All systems are green, Elon. We're ready for takeoff."). Do not use voiceover format. Create natural, character-specific dialogue that advances plot and reveals personality without being overly expository. 

8. **Thematic Elements**: Weave in meaningful themes and subtext that give the story depth and universal appeal.

9. **Conflict and Stakes**: Establish clear external and internal conflicts with high stakes that matter to both characters and audience.

10. **Satisfying Resolution**: Ensure all major plot threads are resolved and character arcs reach meaningful conclusions.

11. **Each dialogue should not too short or too long, (eg."Everything is looking good. All systems are green, Elon. We're ready for takeoff." )


**Warnings**

Don't write any camera movement in the script (eg. cut to), you should write the script by using storyboard description, not camera view.
No metaphors allowed!!! (eg. A gust of wind rustled through it, a ghostly touch. ; an F1 car that looks less like a vehicle and more like a fighter jet stripped of its wings)


**Examples of narrative scripts**

The starry sky is vast, the Milky Way glittering.
On the beach, there's a fire, a portable dining table and chairs (three balloons tied to one corner, swaying in the wind), an SUV, and a camping tent. Next to the tent is an astronomical telescope. A man (Liu Peiqiang, 35, reserved) operates the telescope, while a little boy (Liu Qi, 4, Liu Peiqiang's son) observes under his father's guidance.
Liu Peiqiang (somewhat excitedly) Quick, quick, quick... Look, it's Jupiter... the largest planet in the solar system.
Adjusting the telescope's eyepiece's focus and position, Jupiter gradually comes into focus. Liu Qi: Dad, there's an eye on Jupiter.
Liu Peiqiang: That's not an eye, it's a massive storm on Jupiter's surface. Liu Qi: Why...?
Liu Peiqiang: (touching the boy's head, pointing to the balloons on the table) Jupiter is just a giant balloon, 90% hydrogen. Liu Qi: What is hydrogen?
An old man (Han Ziang, 59, Liu Peiqiang's father-in-law and Liu Qi's grandfather) walked out of the tent and stood silently beside Liu Peiqiang and his son.

Liu Peiqiang: Hydrogen... Hydrogen is the fuel for Dad's big rocket. The campfire flickered, and Han Ziang turned to look at Liu Peiqiang. Liu Qi: Why? Liu Peiqiang smiled and patted his son's head.

Liu Peiqiang (O.S.): When the day comes when you can see Jupiter without a telescope, Dad will be back.



**Examples of motion & speed immersion scripts** (should be accurate, technical, and explicit, Technical Explicitness: Consistently repeats “two seats F-18” in each stage direction. Prioritizes precision in identifying the aircraft type and location (front seat / rear seat). Reads almost like a technical report or aviation manual, ensuring no ambiguity.)

The gray deck of a nuclear aircraft carrier stretches across the ocean. Steam rises from catapult tracks. An two seats F-18 sits locked in place, engines growling.
In the cockpit front seat of two seats F-18, Elon Musk (50s, man, focused) runs through his controls.
In the rear seat of two seats F-18, LT. JAKE “SLING” SERESIN (younger, man) finishes checks, then raises a thumbs-up.
SLING: Everything's green. Ready for launch.
ELON: Understood. Let's go.
Elon grips the throttle with his left hand, stick with his right.
On deck, the Shooter drops to one knee. The two seats F-18 engines roar, the fuselage trembling with contained power.
First-person POV. The catapult slams forward, launching the two seats F-18. The deck blurs into streaks of motion.
A surge of afterburner. The F-18 climbs steeply, landing gear snapping shut.
Inside the two seats F-18 cockpit, Elon steadies the wings, visor flaring with sunlight, eyes steady on the open sky.
The two seats F-18 howls upward, slicing past the horizon — a sleek two seats F-18 of flight surging into freedom.

**Examples of superhero scripts**

Shinjuku streets, daytime. The sky is stained gray-yellow by smoke. Enormous footsteps shake the ground, accompanied by Godzilla's (G) deafening roars and the explosions of its atomic breath destroying buildings. People run and scream in terror.
Beside the rubble of a collapsed overpass, a little girl (about 5 years old) cries alone. In front of her, Godzilla's massive foot is slowly lifting, about to come down.
Little Girl: (Sobbing) Mommy… where are you, Mommy…
At this critical moment, a blue figure swoops down from the horizon at incredible speed!
Usa-chan: (Lighthearted but serious tone) Heave-ho~! Little one, it's dangerous here. Hold on tight!
Usa-chan, holding the little girl, nimbly weaves between collapsed buildings and Godzilla's swiping tail, like a blue lightning bolt. It delivers the girl safely into the hands of a rescue worker in the distance.
Rescue Worker: (Astonished) Th…thank you! Who are you?
Usa-chan: (Looking back, giving a thumbs-up with its signature smile) Ura~! (Immediately turns to face Godzilla, expression turning serious)
Godzilla notices this tiny yet annoying blue creature. It lets out an angry roar, blue-hot light gathering in its mouth—the atomic breath is charging up, aimed directly at an area where many people are still taking cover!
Usa-chan: (Clenching its fist) No way! I won't let you!
Usa-chan takes a deep breath, then lets out a low growl.
Usa-chan: Ura!!!
Usa-chan's body begins to glow with a dazzling blue light! Its muscles rapidly expand and bulge visibly, its size increasing multiple times, transforming from a cute rabbit into a muscular, powerful, fierce rabbit warrior! Its eyes become sharp and intense!
Usa-chan (Muscle Form): (Voice deep and powerful) Your opponent is me!
Godzilla's atomic breath blasts forth, a massive beam of energy shooting toward the crowd!



**Scriptwriting Guidelines End**


"""

human_prompt_template_script_planner = \
"""
<BASIC_IDEA_START>
{basic_idea}
<BASIC_IDEA_END>
"""


class PlannedScriptResponse(BaseModel):
    planned_script: str = Field(
        ...,
        description="The full planned script with rich narrative detail, character development, dialogue, and cinematic descriptions. Should be significantly more detailed and engaging than the original basic idea."
    )



class ScriptPlanner:
    def __init__(
        self,
        chat_model: str,
        base_url: str,
        api_key: str,
        model_provider: str = "openai",
    ):
        self.chat_model = init_chat_model(
            model=chat_model,
            model_provider=model_provider,
            base_url=base_url,
            api_key=api_key,
        )

    @retry(
        stop=stop_after_attempt(3),
        after=lambda retry_state: logging.warning(f"Retrying plan_script due to error: {retry_state.outcome.exception()}"),
    )
    async def plan_script(
        self,
        basic_idea: str,
    ) -> PlannedScriptResponse:
        """
        Plan a comprehensive script from a basic story idea.
        
        Args:
            basic_idea: A simple story concept or idea to be expanded
            
        Returns:
            PlannedScriptResponse: A comprehensive script with structure, characters, and narrative detail
        """
        parser = PydanticOutputParser(pydantic_object=PlannedScriptResponse)
        prompt_template = ChatPromptTemplate.from_messages(
            [
                ('system', system_prompt_template_script_planner),
                ('human', human_prompt_template_script_planner),
            ]
        )
        chain = prompt_template | self.chat_model | parser
        
        try:
            logging.info(f"Planning script from basic idea: {basic_idea[:100]}...")
            response: PlannedScriptResponse = await chain.ainvoke(
                {
                    "format_instructions": parser.get_format_instructions(),
                    "basic_idea": basic_idea,
                }
            )
            logging.info("Script planning completed.")
            return response.planned_script
        except Exception as e:
            logging.error(f"Error planning script: \n{e}")
            raise e

