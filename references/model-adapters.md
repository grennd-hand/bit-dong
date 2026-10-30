# Bit东｜视频模型适配

最后核验：2026-10-30。以下是生成流程适配，不代表已完成 API 集成或跨模型实拍验证。运行时重新检查所选入口、模型变体、当前官方文档及账户可用能力；文档快照不构成永久参数承诺。

## 共同执行规则

1. 先确定平台、具体模型和入口：官方网页、官方 API、第三方代理服务分别记录。不能把网页能力直接写成 API 参数。
2. 只上传同一角色版本的有效参考；先验收镜头首帧，再生成运动。多视图拼板用于查设定，默认不作为视频首帧。
3. 区分素材职责：角色身份、服饰细节、场景构图、动作、运镜、首帧和尾帧。不要让动作视频中的人物覆盖 Bit东外形。
4. 按平台真实上传顺序生成映射；上传后读取实际素材标签或 ID，再写提示。`@Image1`、`@[Image 1]`、资产 ID 和 API 字段不能跨平台照搬。
5. 仅在当前模型明确支持时使用负面提示字段。其余情况用正向外观约束和生成后检查，不把一大段禁词堆进视频提示。
6. 时长、画幅、分辨率、参考数量及可组合模式均需核验。用户目标与模型能力冲突时，拆镜头或说明调整，不静默删改需求。
7. 固定角色参考版本与文件哈希；seed 只记录为运行参数，不把它当成角色身份或跨平台一致性的保证。
8. 每次交付区分“素材与提示已备好”“已上传”“任务已提交”“已取得视频”“视频已检查”，只报告实际完成的状态。

## 未指定模型：generic 默认交付

直接提供：① 按顺序排列的参考文件与职责；② 中文视频提示；③ 自然美式英语视频提示；④ 首帧/尾帧需要的素材及待核实参数。不要臆造 API 请求或要求先安装整套软件。

主体参考模式的提示结构：`参考映射 → 同一 Bit东身份与服饰 → 场景 → 一个主要动作 → 镜头 → 节奏 → 结束状态`。
已有镜头首帧时，压缩重复外观描述，以动作和镜头为主。文字提示中写文件名不等于模型收到图片，须实际上传或在请求中传入该入口支持的媒体资源。

通用动作示例，须与实际首帧匹配：

- 中文：Bit东轻轻微笑，抬起一只手向镜头打招呼，再自然放下。镜头缓慢推进。眼镜稳定贴合面部，人物造型和服装沿用已上传参考。动作结束后停留片刻。
- English: Bitdong smiles gently, raises one hand in greeting, and lowers it naturally. The camera slowly moves closer. His glasses stay fitted to his face, and his design and clothing remain consistent with the uploaded reference. He holds the final pose briefly.

## 可灵 Kling

**入口与已核验范围：** Kling 4.0 官方网页指南、Element 管理 API；不要套用旧 3.0 的全部限制。

- 长期使用优先建立可复用 Bit东 Element。图像元素 API 要求一张正面图及 1–3 张不同角度或特写；生成的新角度须先检查。
- **Omni Reference：** 用角色、场景、动作等参考组合镜头。素材按上传顺序编号，逐项写明职责，例如 `@Image1` 固定角色外形、`@Video1` 仅提供动作节奏。
- **Keyframes：** 使用已定稿的首帧、尾帧或中间关键帧控制镜头。不要把角色参考图误指定为剧情结束帧。
- Element API 的 `reference_type: image_refer`、`element_image_list.frontal_image`、`refer_images[].image_url` 属于可灵字段；只有实际创建成功后才能使用返回的元素 ID。
- 不把官网对一致性的营销表述当作验收结果；按当前模型重查参考输入总量与时长等限制。

官方来源（2026-10-30 核验）：

- https://kling.ai/quickstart/kling-4-model-user-guide
- https://kling.ai/document-api/apiReference/model/element
- https://kling.ai/quickstart/klingai-element-library-3-user-guide

## 即梦 / Seedance

**入口与已核验范围：** 火山方舟 Seedance 2.0 系列与 2.5 的官方 API 文档；即梦网页/客户端的具体按钮、权限、参数不可由此推定。

- 用户使用即梦界面时，提供中文可粘贴提示、上传映射和应选的输入模式；按实际界面核验支持项，不输出未经验证的 API JSON。
- 方舟 API 的首帧、首尾帧、全模态参考是互斥场景，不混用三种 `role`。
- 首帧模式：一张 `image_url`，显式填写 `role: first_frame`。上传完成构图的镜头首帧，不依赖不同版本对省略 role 的默认行为。
- 首尾帧模式：两张图片分别标记 `first_frame`、`last_frame`。保持角色、服装、镜头方向及空间连续。
- 全模态参考模式：参考图片标记 `reference_image`，在提示中逐一指定角色、场景与动作职责。
- 全模态提示中写“图1作为首帧”与结构化首帧约束并不等价。需要严格首尾构图时优先使用官方首尾帧模式。
- 2.0 与 2.5 的参考数量限制不同；每次按实际版本核查，不设“所有 Seedance 通用”的固定上限。

官方来源（2026-10-30 核验）：

- https://docs.volcengine.com/docs/ark/create-video-generation-task-api?lang=zh
- https://console.volcengine.com/ark/region%3Acn-beijing/docs/create-video-generation-task-api
- https://seed.bytedance.com/en/seedance2_0

## Runway

**入口与已核验范围：** Gen-4 Image References、Gen-4 Video 网页指南及当前 API 入门；不要把 Runway 平台内不同厂商模型的能力混为一体。

- 默认流程：Bit东母版 → 用 Image References 制作镜头首帧 → 检查首帧 → 视频入口生成动作。
- Gen-4 Image References 支持单次最多三张 active References；它是图像生成入口，不能据此宣称所有 Runway 视频模型支持三图输入。
- Gen-4 Video 的输入图承担首帧与外观信息。文字集中写主体动作、环境运动和镜头；使用正向描述，避免负面提示及重复长篇外形说明。
- 保存角色参考名称供复用；真正上传后使用界面生成的标签，不把其他平台的 `@Image1` 当作固定语法。
- API 入门当前示例使用 `gen4.5`、`promptImage`、`promptText`、`ratio`、`duration`；按实际模型重新查参数，不照抄为通用请求。

官方来源（2026-10-30 核验）：

- https://help.runwayml.com/hc/en-us/articles/40042718905875-Creating-with-Gen-4-Image-References
- https://help.runwayml.com/hc/en-us/articles/39789879462419-Gen-4-Video-Prompting-Guide
- https://docs.dev.runwayml.com/guides/using-the-api/

## Google Veo

**入口与已核验范围：** Google Cloud 的 Veo 模型卡和主体参考教程；必须与 Gemini API 区分。

- Gemini API 的三个 Veo 3.1 Preview 型号已于 2026-10-22 停用，旧教程仍可能残留示例。不能把旧 Preview ID 输出为当前可执行配置。
- Google Cloud 当前模型卡列有 `veo-3.1-generate-001`、`veo-3.1-fast-generate-001`；运行前重查可用性、区域与具体版本，不据此保证账户可调用。
- 主体参考模式选择同一 Bit东的 1–3 张有效图片；当前 Cloud 文档使用 `referenceImages` 与 `referenceType: asset`，参考模式按 8 秒镜头编排。
- 首尾帧与主体参考不是相同输入语义；是否可组合按当前型号文档确认。不要把 `referenceImages` 偷换成首帧字段。
- Cloud 文档列有 `negativePrompt`，仅对已确认支持的请求使用；不能推导其他厂商也支持此字段。
- 优先当前模型卡和 API 定义；发现教程示例与模型状态不一致时，标记冲突并重新核实，不能仅改一个 ID 后声称已验证。

官方来源（2026-10-30 核验）：

- https://ai.google.dev/gemini-api/docs/deprecations
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/veo/3-1-generate
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/video/generate-videos-from-references

## Sora / Pika / Luma / 海螺 / Wan 及其他未核验入口

本文件未核验这些入口的当前可用性及接口，不宣称原生兼容。先交付 generic 包；执行前读取该平台官方资料，确定是否支持单图首帧、主体参考、首尾帧或角色资产。只支持单图时使用检查通过的场景首帧；只支持文本时明确角色一致性证据不足，不承诺复现。无法核验时保留为“待适配”，不杜撰模型 ID、上传语法、角色功能或参数。

## 工作记录不是厂商请求

使用唯一工作记录模板 [`../templates/shot-plan.example.json`](../templates/shot-plan.example.json)，保持其 `schema_version`、`character_id`、`design_version`、`provider`、`provider_surface`、`model`、`capabilities_verified_at`、`official_sources`、`aspect_ratio` 与 `shots` 字段结构，不另造一套字段。

该 JSON 是镜头规划与交付记录，不能直接发送到任一视频 API。`null` 表示尚未核实，不代表支持；实际请求另按目标入口当前 schema 构造。

上传后的实际素材标签、顺序、职责与文件哈希记录到本次运行的 `upload-map`；平台元素 ID、上传 URL、任务 ID 也属于运行记录，不冒充跨平台角色身份。
