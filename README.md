# 使用说明

1.   环境安装

     环境依赖在pyproject.toml里，请大家自行安装

     uv管理的可以直接 uv sync



2.   将剧本放入一个txt文件中，然后在main.py里面修改script_path 和 working_dir

     working_dir会保存输出的文本、图像、视频结果

     视频风格可以通过style进行描述







# 代码架构

## components

将小说、电影、视频这些拆成几个要素，包括角色、环境、事件、关键物品、场景、镜头

小说>事件>场景>镜头

角色、环境、关键物品等全局信息划分为3个等级，scene-level，event-level，novel-level。novel-level为最基本的信息，会先生成对应的图像，让scene-level作为参考





下面说明每个类的属性

### characters

```
CharacterInScene
index: 编号
identifier_in_scene：在该场景中的名字，如果没有具体名字（龙套），会用一个可以指示该角色的代词，比如一个奇怪的陌生人、一个医生
is_visible：是否可见（可能是画外音）
static_features: 静态特征（不容易变化的，比如职业、脸部特征、身材等）
dynamic_features: 动态特征（在全局范围内容易变化，但在场景内不容易变化的，比如服化道）
```



```
CharacterInEvent
index: 编号
identifier_in_event：在该事件中的名字
active_scenes：在该事件中的什么场景出现过，是一个字典，key为场景编号，value为该角色在对应场景的名字（比如场景1的名字为Musk，场景2的名字Elon Musk，指向同一个人，但是不同名字）
static_features：由不同场景的static_features聚合而成
```



```
CharacterInNovel
index: 编号
identifier_in_novel：在该小说中的名字
active_events：与上面的active_scenes类似
static_features：由不同事件的static_features聚合而成。这里static_features会用来生成最基本的角色形象，作为其它场景内角色的参考图像。
```





### *environment*

这里与character类似，都是全局信息，待实现

```

```





### event

从小说中提取的事件

```
Event
index：编号
is_last：是否为最后一个事件
description：str, 事件的简单描述
process_chain：List[str]，事件的详细描述，将事件拆分多个具体的过程，比如起因、经过、结果。在使用rag检索小说原文时，用每一个过程作为query
```



### scene

```
idx: 编号
is_last：是否为最后一个场景
environment: EnvironmentInScene，环境描述
characters: List[CharacterInScene]，所有出场的角色
script：剧本
```



### shot

场景的每一个镜头

```
idx: 编号
is_last：是否为最后一个镜头
duration：估计时长
first_frame：首帧描述，偏向于静态描述
visual_content：镜头内容，偏向与动态描述
sound_effect：音效描述
speaker：说话人
line：台词
```



## agents

与LLM或MLLM交互的agents



原本与图像相关的CharacterImageGenerator和FrameCandidatesImageGenerator被移除了，现在图像生成类只作为工具，放在tools文件夹下面



### *BestImageSelector*

从多张候选图中选择与目标描述、参考图像最一致的图片

```
函数名: __call__

Input:
ref_image_path_and_text_pairs:一个列表，列表内每个元素为一个元组，元组第一个为参考图像的本地地址，元组第二个为参考图像的描述
target_description: 字符串，目标描述
candidate_image_paths: 所有候选图的本地地址


Output:
best_image_path: 最好、最一致的图片的本地地址
```



### *CharacterExtractor*

从给定的剧本或故事中，抽取所有出现的角色

```
函数名: __call__

Input:
script: 字符串，用户输入的剧本（短）

Output:
characters: List[CharacterInScene]，列表里每个元素是一个scene-level的角色
```



### *EventExtractor*

从给定的小说或故事中，抽取下一个事件

```
函数名：extract_next_event

Input:
novel_text：字符串，小说或者故事（中长，不要超过LLM的context上限）
extracted_events: List[Event]，已经提取的事件列表

Output:
event: Event类型
```



### *GlobalInformationPlanner*

全局信息的融合(现在只实现了角色的融合),从scene-level到event-level再到novel-level

例如场景A提取了角色Musk,场景B提取了Elon Musk，它们的identifier不同，但指向同一个人，所以需要融合

```
函数名:merge_characters_across_scenes_in_event
说明: 针对一个事件内的不同场景（场景不多）进行角色融合，根据角色的static_features进行融合，例如年龄、脸部特征等

Input:
event_idx: int,事件的编号
scenes: List[Scene], 事件中包含的所有场景

Output:
characters: List[CharacterInEvent],列表中每个元素是一个event-level的角色
```



```
函数名: merge_characters_to_existing_characters_in_novel
说明：处理方式与针对一个事件内的不同场景 不同，因为一个事件内最多10来个场景，在context length内，但一个小说里的事件可能很多（三体提取了大概30个事件）。
使用时会维护一个全局的角色列表（novel-level），对于所有事件进行线性处理，从头到尾将当前事件的角色融合到全局角色列表中

Input:
event_idx: 事件编号
existing_characters_in_novel: List[CharacterInNovel]，全局的角色列表
characters_in_event: List[CharacterInEvent]，当前事件的角色列表

Output:
existing_characters_in_novel: List[CharacterInNovel]，更新后的全局角色列表，更新内容包括新角色以及旧角色的static features
```





### *NovelCompressor*

小说压缩器，对小说进行分块，每个分块进行压缩，压缩分块再合并。

压缩后的小说要在LLM的context length里，方便EventExtractor提取事件

```
函数名：split
说明：NovelCompressor有个初始化参数chunk size，一般来说，chunk size越大，压缩的力度越大，但保留的细节可能就不够

Input:
novel_text: 原小说内容

Output:
chunks: 小说分块，分块大小不超过chunk size
```



```
函数名：compress
说明：对每个分块进行压缩
```



```
函数名：aggregate
说明：将所有压缩分块合并成连续的小说（压缩版），因为chunk_overlap参数会使得分块之间可能有重复的文本
```





### *ReferenceImageSelector*

参考图像选择器，根据图像描述，从图像库中选择合适的图像作为参照，以保持一致性

```
函数名：__call__

Input:
available_image_path_and_text_pairs: 一个列表，表示图像库，每个图像都有对应的文本描述
frame_description: str，文本描述

Output:
reference_image_path_and_text_pairs: 一个列表，每个元素为选择的参考图像地址和文本描述
text_prompt：str,指导生成图像如何根据参考图进行修改
```





### Rewriter

文本重写器，去除违禁词

```
函数名：__call__
剩下懒得写了
```



### *SceneExtractor*

场景提取器，根据rag检索的小说原文片段设计场景（包括出场角色和剧本）

说明：这里采用线性提取，可以考虑一次性全部提取，现在这个方法如果不在prompt里限定场景数量，或者LLM的context length不够长，很容易一次性设计超多场景。

```
函数名：get_next_scene

Input:
relevant_chunks: List[str]，小说原文片段列表
event：Event类型，包括事件描述，以及因果链（过程链）
previous_scenes：List[Scene]，已经提取的场景

Output:
scene：Scene类型
```



### *ScriptEnhancer*

待补充



### *ScriptPlanner*

待补充



### *StoryboardGenerator*

根据剧本和已有的镜头描述，设计下一个镜头

```
函数名：get_next_shot_description

Input:
script: 剧本
character_identifiers：角色名称列表，镜头shot里出现的角色一定要在该列表内
existing_shots:  List[Shot]，前面已经设计的镜头

Output:
shot: Shot，下一个镜头描述
```







## configs

配置文件，采用yaml，用于初始pipeline。

（参考了lightning库的训练配置文件，还不太完善）



示例：

```
script_planner:
  class_path: agents.script_planner.ScriptPlanner
  init_args:
    api_key: sk-RsgJVQohu9e1HBMgdYsy9mQFKs3ue4fZXL2iGMjiiupiViQB
    base_url: https://yunwu.ai/v1
    chat_model: gpt-5-nano-2025-08-07
```

在初始化时，script_planner为pipeline中的变量名，class_path为对应的类，init_args为类的初始化参数



另外，也可以在pipeline中使用另一个pipeline，配置如下所示：

```
script2video_pipeline:
  class_path: pipelines.script2video_pipeline.Script2VideoPipeline
  config_path: configs/script2video.yaml
```

script2video_pipeline为pipeline中的变量名，class_path为对应的pipeline类，config_path为初始化pipeline要用的config地址



## pipelines

在base.py中定义了一个BasePipeline，该类定义了初始化的方式

每个pipeline的内容待补充



## tools

tools目前包含了embedding、image_generator、rerank、和video_generator，这些工具会被agents直接调用，

像下载图片这些就放在utils里面了



### embedding

rag的embedding模型
未实现，agents现在直接使用langchain提供的embedding

后面可以放一些本地的embedding模型



### image_generator

在base文件定义了异步生成图像的方法，派生类只需要实现如何获取一张图片就行，BaseImageGenerator定义了异步获取多张图片的方法（从1个prompt中获取N张图片，从M个prompt中获取M×N张图片）



现在实现了gemini和falai的nanobanana，gpt4o待实现（4o滚吧）



即梦4.0的图像生成待实现



### video_generator

与image_generator类似

现在实现了veo



kling待测试



即梦、wan2.2(runninghub版本)等待实现





### rerank

重排序模型，用于rerank，现在只实现了silicon格式的



## utils

包括下载图片、视频、转base64等方法。
