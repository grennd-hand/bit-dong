---
name: bitdong-video
description: 用用户原有的 Bit东个人动漫IP制作短剧、口播、广告和连续视频镜头；只扩展视频制作流程，绝不重新设计人物。适用于“Bit东视频”“用原来的Bit东拍短剧”“Bit东角色一致性”“给视频模型准备原图、首帧和提示词”。保留原版脸型、发型、眼镜、服装、定制鞋、线条、阴影、表情和身体语言。与原来的 bitdong-illustrations 插画 Skill 独立共存。
---

# Bit东视频｜原版形象，不换人

## 先看原图，再制作

每次先读取 `references/bitdong-character.md`、`references/emotion-system.md`、`references/qa-checklist.md`，并实际查看下面三张原始参考，不能只看文件名或凭文字记忆重画人物：

- `assets/character-reference/bitdong-portrait.jpg`：本人身份与脸部来源。
- `assets/character-reference/bitdong-character-sheet.png`：原版动漫造型、比例、服装、线条和明暗；不是新立绘，不直接当成视频首帧。
- `assets/character-reference/shoes/bitdong-shoes-reference-board.jpg`：定制鞋设计；不能继承照片背景。

按任务只选一张原表情表；需要全身表演时再选原身体语言表。鞋子特写才查看四张原鞋照。所有参考均保存在本 Skill 内，不依赖仓库外相对路径。

**服饰标志相同不等于同一个人。** 保持原图的脸部关系、发型轮廓、镜框、身体轮廓和人物气质。不要变成通用动漫帅哥、模特立绘、写实人物或新的卡通角色；不要通过变脸、拉长身体、增加密集衣褶来冒充高清。

原插画规范中的16:9白底和中文批注只适用于插画模式；视频画幅、环境与运镜按用户故事决定，不把场景差异解释为角色可重新设计。其余身份与画风规则继续生效。

## 明确拒绝的素材

2026-10-30的视频新候选套装和后续被用户否定的三分之四立绘不能作为身份母版或父参考。`references/identity-policy.json` 登记拒绝的ID、套装、路径和内容哈希；草案也不能绕过。身份来源只允许回到本包原图，不追找所谓“缺失8张新图”作为前置条件。

## 执行顺序

1. 从用户要求提取剧情、台词、画幅、时长和平台。缺非关键项时先做明确标注的策划，不虚构当前模型参数。每镜头一个主要动作。
2. 输出分镜和原图职责映射，明确首帧状态、末帧状态和接镜关系。原版照片、角色卡、鞋板不能混成三个竞争的人物设计。
3. 做单角色场景首帧。用户要求生成时调用实际可用的图像工具，并真正提供参考图；不能假称一个本地路径就已经上传，也不要虚构工具的参数名。先检查首帧是否还是原来的Bit东，再做其他镜头；失败就修失败镜头，不重新定版整个人物。
4. 用 `scripts/register_frame.py` 登记真实新帧、真正使用的参考ID与实际提示。默认 `candidate`，不自动批准。登记只检查文件/来源记录，不是视觉相似度识别。
5. 依据所选平台的当前官方文档和账户界面核验具体型号、上传格式、参考上限、时长、画幅、分辨率、首尾帧和负面提示支持。平台没有确认的字段保持null，计划JSON不是厂商API请求。
6. 按平台支持的模式提交已检查场景帧和运动提示。跨镜头继承身份、服饰、道具、手位、视线、方向和光线；有意变化要记录切镜原因。只继承检查通过的尾帧。
7. 取得真实视频后检查首、中、尾及眨眼、转头、遮挡恢复、手脚接触和镜头衔接。未生成视频就写not_run，不能拿静态动画或脚本测试冒充模型实测。

## 可直接运行的准备包

在本 Skill 目录执行（仅需Python标准库）：

```bash
python3 scripts/identity_guard.py
python3 scripts/prepare_original_pack.py --plan templates/shot-plan.example.json --out /tmp/bitdong-original-handoff --body
```

输出原图原字节副本、职责映射、两镜头中英文首帧提示和运动提示、连续性记录以及待填真实帧ID的计划。`REGISTER_SCENE_FRAME_XX` 是占位符，会被视频导出器拒绝；不是伪造的图片。输出目录必须是新的、位于Skill目录之外。

真实场景帧生成后再执行（路径换成实际文件；parents必须是真正用过的参考）：

```bash
python3 scripts/register_frame.py --source /path/to/scene.png --id scene-01 --set-id original-scene-v1 --parents identity-photo source-character-sheet source-shoe-board --prompt-file /path/to/actual-prompt.txt
python3 scripts/prepare_video_pack.py --plan /path/to/filled-video-plan.json --out /tmp/bitdong-video-draft --allow-draft
```

正式包去掉 `--allow-draft`，需真实批准记录和平台能力记录。程序不负责调用收费API，不声称已经上传、生成或验收。

## 交付与保护

原始设计文件以 `references/original-ip-lock.json` 锁定。先做程序完整性检查，再做实际图像与视频审查；两者不能互相替代。保持原图原文件，不覆盖素材、不插值冒充新增细节、不新增未经确认的鞋子/手表设定。用户要求视频只是授权改用途，不是授权改IP。
