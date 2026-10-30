# Bit东｜图像与视频提示词模板

先读 `character-canon.json`、`bitdong-character.md` 和 `../assets/asset-manifest.json`；按登记状态选择当前动画母版，未通过定稿验收的参考不得宣称已定稿。只选本镜头需要的参考，不再默认同时上传真人照片、角色拼板、鞋板及多张情绪表。

上传前查看图片；上传后把下列花括号替换成实际素材标签和镜头内容。标签必须对应真实上传文件，不能凭空写一个平台 ID。单张角色图负责外形，场景图负责构图，动作参考只负责动作；产生冲突时依当前选定动画母版与角色规范处理，不用原照片重新解释脸。

保持固定身份：成年中国男性、短刺黑发、深色粗框矩形眼镜、珊瑚粉圆领卫衣、银链、炭黑长裤、定制黑色高帮鞋。英文使用 **crewneck sweatshirt**。近景无需为了出现鞋子改成全身；可见细节按母版保持，未见部分不得随意设计。

中文与英文是两份等价交付，按平台选择其一。参数在界面或 API 中单独设置，不假设提示中的“4K”“8秒”等文字会设置真实参数。平台适配见 `model-adapters.md`。

## 1. 母版候选 / 镜头首帧图像生成

每次只生成一张独立图片。制作母版候选时选中性表情、清晰轮廓与所需单一视角；制作首帧时直接使用剧情场景和起始动作。只有明确要求对照板时才输出拼板。

**中文**
```text
以{角色参考标签}为Bit东的动画造型基准，生成一张{用途：单视角母版候选/镜头首帧}。保持同一成年男性的脸型、短刺黑发、矩形粗框眼镜、珊瑚粉圆领卫衣、银链、炭黑长裤与定制黑色高帮鞋，以及参考中的成人比例、墨线和赛璐璐明暗。{细节参考标签与职责，仅在需要时填写}。视角与景别：{视角、景别}。场景与光线：{场景、光线}。表情和起始姿态：{表情、姿态}。构图与画幅：{构图、画幅}。呈现单一连贯画面，人物完整保留在所选景别内。
```

**English**
```text
Use {character reference label} as Bitdong's animated character design. Create one {single-view master candidate / opening shot frame}. Keep the same adult face, short spiky black hair, dark rectangular glasses, coral-pink crewneck sweatshirt, silver chain, charcoal trousers, and custom black high-top sneakers. Match the reference's adult proportions, ink lines, and cel shading. {Optional detail reference and its role}. View and framing: {view, shot size}. Setting and lighting: {setting, lighting}. Expression and starting pose: {expression, pose}. Composition and aspect ratio: {composition, ratio}. Render one coherent scene with the character framed as specified.
```

## 2. 主体参考生视频

用于确认支持角色/主体参考的入口。明确每张图用途；参考仅定义身份时，不要求照搬其背景或站姿。

**中文**
```text
{角色参考标签}定义同一个Bit东的脸、发型、眼镜、服装、成人比例与动画画风；{其他素材标签及各自职责}。场景：{场景}。Bit东从{起始状态}开始，{一个主要动作及自然次要动作}，最后{结束状态}。情绪由{起始情绪}变为{结束情绪}，眉眼、嘴型和身体重心自然协调。镜头{运镜}，节奏{节奏}。整个镜头保持同一角色设计、眼镜结构、服装与鞋子，光照随环境自然变化。
```

**English**
```text
{Character reference label} defines the same Bitdong: his face, hair, glasses, clothing, adult proportions, and animation style. {Other reference labels and their roles}. Setting: {setting}. He starts {starting state}, {one main action with natural secondary motion}, and ends {ending state}. His expression shifts from {starting emotion} to {ending emotion}, with coordinated facial movement and body weight. The camera {camera movement}. The pacing is {pacing}. Keep his character design, glasses, outfit, and shoes consistent as the lighting responds naturally to the scene.
```

## 3. 首帧图生视频：运动提示

输入必须是检查通过的单张场景首帧。让首帧承担外形与构图，文字集中写运动；Runway 等要求正向描述的入口优先使用这一简短结构。

**中文**
```text
人物{主要动作}，同时{自然次要动作}。镜头{运镜或固定机位}。环境中{必要的环境运动}。动作以{速度与节奏}展开，结束时{最终姿态与停留}。眼镜贴合面部，角色和服装延续首帧的设计。
```

**English**
```text
The character {main action} while {natural secondary motion}. The camera {camera movement or locked framing}. {Necessary environmental motion}. The movement unfolds at {pace}, ending with {final pose and hold}. His glasses stay fitted to his face, and his design and clothing remain consistent with the opening frame.
```

## 4. 首尾帧过渡

先确认两帧为同一角色版本、同一服装和可连续的空间；若不匹配，修正帧后再生成。使用当前入口真实首帧/尾帧字段，不把两张图都当普通角色参考。

**中文**
```text
从已指定首帧过渡到已指定尾帧。Bit东通过{可执行的动作路径}到达尾帧的姿态和位置；人物、服装、道具与空间连续。镜头{连续运镜}，动作{节奏}，结尾{停留方式}。以自然身体运动完成过渡，保持脸、眼镜和四肢结构稳定。
```

**English**
```text
Move continuously from the designated first frame to the designated last frame. Bitdong {physically plausible action path}, arriving at the pose and position shown in the final frame. Keep the character, clothing, props, and spatial layout continuous. The camera {continuous camera movement}. The action proceeds at {pace}, ending with {final hold}. Use natural body movement throughout, preserving his face, glasses, and anatomy.
```

## 5. 局部修复：先修帧，再重跑受影响镜头

输入待修图片及最相关母版/细节参考。一次明确一个问题和可修改区域；静帧修复不等于整段视频已修复。眼镜遮挡眼部时保留正确遮挡，不添加透过镜框的重复眼睛。

**中文**
```text
编辑{待修图片}，只修正{区域}的{具体错误}，以{当前动画母版或细节参考}为准。将该区域恢复为{准确目标，例如双眼视线一致、镜框完整且贴合脸部}。保持其他面部特征、表情、头部角度、身体、服装、背景、光线、构图和画幅不变。匹配原图的墨线与赛璐璐明暗，边缘自然衔接。
```

**English**
```text
Edit {image to repair}. Correct only {specific error} within {area}, using {current animation master or detail reference}. Restore {precise target, such as aligned gaze and intact glasses fitted to the face}. Preserve the other facial features, expression, head angle, body, clothing, background, lighting, composition, and aspect ratio. Match the original ink lines and cel shading, with clean, seamless edges.
```

## 6. 旧插画模式：中文文章正文配图

仅本模式读取 `style-dna.md`、`composition-patterns.md`；白底、16:9、批注和怪诞隐喻不传播到视频模式。角色仍沿用当前动画母版，不恢复旧照片描边或小黑角色。

**中文**
```text
生成一张16:9中文文章正文配图，纯白背景，至少35%留白。以{当前动画母版}保持同一个Bit东，让他亲自{核心动作}，表达{唯一核心观点}。采用{新的物理隐喻和构图}；人物使用利落动漫墨线与克制赛璐璐，物件使用稀疏黑色手绘线条。情绪为{情绪与原因}，脸部和重心一致表达。少量红、橙、蓝短批注：{需要的文字，最多5—8处}。保持画面清爽，顶部留白不写类型标题。
```

**English**
```text
Create one 16:9 illustration for a Chinese-language article, with a pure white background and at least 35% negative space. Match Bitdong to {current animation master}. He personally {core action}, expressing {one central idea} through {fresh physical metaphor and composition}. Use crisp anime ink lines and restrained cel shading for him, with sparse black hand-drawn lines for objects. Show {emotion and cause} through his face and body weight. Add only these brief handwritten Chinese notes, using restrained red, orange, and blue: {labels, up to 5–8}. Keep the layout uncluttered and the upper margin free of category headings.
```
