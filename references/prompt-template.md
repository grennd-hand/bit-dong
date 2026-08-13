# 生图提示词模板

每张图单独生成。根据正文内容替换变量，不要把多张图拼在一起。

每次调用前，固定加载身份、角色设计与鞋子三个参考：

```text
assets/character-reference/bitdong-portrait.jpg
assets/character-reference/bitdong-character-sheet.png
assets/character-reference/shoes/bitdong-shoes-reference-board.jpg
```

再根据叙事选择一张情绪表：

```text
# 工作、风险、卡点、顿悟、结果
assets/character-reference/bitdong-expression-sheet-v1.png

# 好奇、疲惫、无奈、失望、尴尬、同理、期待、自信
assets/character-reference/bitdong-social-expression-sheet-v1.png
```

中景、全身、状态转变、小漫画或身体姿态承担主要意思时，加上：

```text
assets/character-reference/bitdong-body-language-sheet-v1.png
```

原照片是身份和脸部参考；角色卡是动漫造型、服饰、成人比例与渲染参考；所选情绪表是当前情绪范围参考；身体语言表是重心、脊柱、肩胸、步态、手势与空间距离参考；鞋子板是鞋型、定制配色、图案与“BIT / DONG”的权威参考。不要无原因同时加载两张情绪表。

```text
Generate one standalone 16:9 horizontal Chinese article illustration.

Visual DNA:
Pure white background. Bit东 is rendered as a polished modern adult anime character with precise expressive ink lines and restrained 1-2 level cel shading. Surrounding objects and conceptual machinery use sparse black hand-drawn line art with slightly imperfect pen lines, so the mature anime character feels inserted into a clean absurd whiteboard world. Lots of empty white space. Sparse red/orange/blue handwritten Chinese annotations. No environmental gradients, realistic cast shadows, paper texture, complex background, commercial vector style, PPT infographic look, cute mascot poster, children's illustration, or realistic UI.

Reference image roles:
The portrait is the identity and facial reference for Bit东. The modern anime character sheet is the definitive character design, outfit, adult-proportion, ink-line and cel-shading reference. The selected emotion sheet defines the adult emotional range needed by this narrative beat. If supplied, the full-body language sheet defines center of gravity, spine, shoulder/chest openness, stance or gait, hand language and spatial distance. The shoe board is authoritative for his exact customized high-top silhouette, color blocking, handmade markings and split BIT / DONG lettering; never copy its desk, monitor, keyboard, lighting or photo background. Preserve the same recognizable adult Chinese man; do not reproduce the portrait's room, lighting or selfie framing.

Recurring personal character required:
Bit东, a recognizable polished modern anime adult Chinese man matching all four references. Preserve all five identity anchors in every appearance: short spiky black hair with tapered sides, oversized dark rectangular eyeglasses, a rich muted coral-pink crewneck sweatshirt, a simple silver chain necklace, and his exact personalized black leather high-top sneakers. The shoes have black laces, warm off-white midsoles, thin black outsoles, distressed bright-blue curved side marks, coral-red/pink toe typography and repeating symbols, small purple side marks, yellow-orange cartoon heel drawings, subtle pink piping, and pale-blue hand-drawn BIT / DONG lettering split across the two outer ankle panels. Keep an angular oval face, natural adult-sized eyes, and charcoal relaxed trousers. Use mature natural proportions around 7-7.5 heads tall, precise ink lines, and restrained cel shading. Bit东 must perform the core conceptual action, not decorate the scene. Make his selected adult emotion clearly readable and narratively motivated while keeping him grounded, recognizable, and never cute or generic.

Theme:
{正文配图主题}

Structure type:
{结构类型：Workflow / 系统局部 / 前后对比 / 角色状态 / 概念隐喻 / 方法分层 / 地图路线 / 小漫画分镜}

Core idea:
{这张图要表达的核心意思}

Narrative beat and emotion:
{情绪类型；强度 0-3；触发原因；眉眼嘴、头部与肩颈的联动。除非画面表达观察或停顿，否则不要使用中性脸}

Body-language direction:
{重心；脊柱；肩胸开合；站距或步态；手的高度、掌心和离身体距离；人物与目标的空间距离。至少明确四项}

Composition:
{具体画面：Bit东在哪里、正在做什么、主要物件是什么、信息如何流动}

Suggested elements:
{元素1} / {元素2} / {元素3} / {元素4}

Chinese handwritten labels:
{标注词1} / {标注词2} / {标注词3} / {标注词4} / {可选标注词5}

Color use:
Black for main line art, hair, glasses, objects, and labels. Rich muted coral-pink for Bit东's signature sweatshirt, with one darker pink cel-shadow tone. Charcoal for trousers. Cool gray for restrained character shading and the silver chain. Orange for main flow/path/arrows. Red only for key warnings/problems/results. Blue only for secondary notes or feedback/system state, except the fixed distressed-blue markings on Bit东's shoes. The shoes' small red-pink, purple, blue, and yellow-orange customized markings are identity details and do not count as annotation colors.

Constraints:
One image explains only one core structure. Keep the main subject around 40%-60% of the canvas. Preserve at least 35% blank white space. Use at most 5-8 short handwritten Chinese labels. Keep Bit东's face, glasses, hair, outfit, customized high-top shoes, adult proportions, and anime rendering visually consistent across all scenes and panels. Make the chosen emotion readable at thumbnail size through coordinated face, center of gravity, spine, shoulder/chest openness, stance or gait, hands and spatial distance; the pose should remain partly readable when the face is covered. Do not change only the mouth or arms, do not reuse a generic upright stance, and do not fall back to calm neutrality unless the narrative calls for it. Whenever the feet are visible, preserve the black high-top silhouette, cream midsoles, blue side accents, red-pink toe markings, and asymmetric handmade character of the shoe pair; in close or full-body views also preserve the BIT / DONG ankle lettering, purple side marks, and yellow-orange heel drawings. Never replace them with generic sneakers or low-tops. Do not transform his body into a machine, funnel, blob, or icon. Do not render him as chibi, moe, a teenager, a school-uniform character, a generic anime pretty boy, a 3D figure, or a traced photo sketch. Do not imitate any named anime character, studio, or artist. Do not include 小黑, a solid-black creature, white-dot-eyed mascot, or any unrelated character. Do not write a title in the top-left corner. Do not write the structure type on the image. Do not make it a formal diagram, course slide, or dense explainer. Do not copy prior examples or reuse known case compositions unless explicitly requested; invent a fresh visual metaphor for this specific article. It should be clear but not instructional, emotionally legible but not theatrical, stylish but not childish, strange but clean.
```

## 图像编辑提示

去掉左上角标题：

```text
Edit the provided image. Remove only the handwritten title "{要删除的文字}" and its underline from the top-left corner. Fill that area with the same clean white background, matching the surrounding blank paper. Preserve everything else exactly: characters, labels, paths, line style, composition, aspect ratio, and image quality. Do not add any new text or objects.
```

增强怪诞感：

```text
Regenerate this illustration with the same core meaning and simple layout, but make Bit东 more central to the conceptual action. Match the supplied definitive anime character sheet, selected adult emotion sheet, optional body-language sheet, and shoe reference board: preserve his recognizable short spiky black hair, dark rectangular glasses, coral-pink crewneck sweatshirt, silver chain, charcoal trousers, personalized black high-top shoes with cream midsoles, blue side accents, red-pink toe markings and BIT / DONG ankle lettering, mature 7-7.5-head proportions, precise ink lines, and restrained cel shading. Give him {情绪类型与强度} because {触发原因}; express it through coordinated eyebrows, eyelids, gaze, mouth, jaw, head angle, center of gravity, spine, shoulder/chest openness, stance or gait, hands and spatial distance rather than changing only the mouth or arms. Bit东 should be doing the strange work that explains the idea, not standing beside the diagram. Remove any solid-black creature or unrelated mascot. Keep the surrounding scene clean, sparse, hand-drawn, emotionally legible, and never chibi or cute.
```
