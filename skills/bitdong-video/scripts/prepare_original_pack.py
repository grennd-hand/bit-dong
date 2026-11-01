#!/usr/bin/env python3
"""Export unchanged original references and bilingual preproduction, not a video."""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from identity_guard import load_policy, load_json, verify_originals, inspect_asset, IdentityError
from prepare_video_pack import validate_pack, PackError, write_json

CORE = ['identity-photo', 'source-character-sheet', 'source-shoe-board']
EMOTIONS = {'work': 'performance-work', 'social': 'performance-social'}


def prepare(root, plan, output, emotion='social', body=False):
    root, output = Path(root).resolve(), Path(output).absolute()
    if emotion not in EMOTIONS or type(body) is not bool:
        raise PackError('Invalid performance reference selection')
    if not isinstance(plan, dict) or any(s.get('mode') != 'text_only' for s in plan.get('shots', []) if isinstance(s, dict)):
        raise PackError('Preproduction expects text_only planning shots, not submitted video inputs')
    checked = validate_pack(root, plan, allow_draft=True)
    policy = load_policy(root)
    original_report = verify_originals(root, policy)
    registry = {a['id']: a for a in load_json(root / 'assets/asset-manifest.json')['assets']}
    selected = CORE + [EMOTIONS[emotion]] + (['performance-body'] if body else [])
    if output.is_symlink() or output.exists():
        raise PackError('Output already exists; use a new directory')
    if output.resolve().is_relative_to(root):
        raise PackError('Keep generated handoff output outside the source repository')
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.bitdong-original-', dir=output.parent))
    try:
        rows = []
        for index, asset_id in enumerate(selected, 1):
            inspect_asset(root, registry, asset_id, policy)
            a = registry[asset_id]
            path = 'references/' + f'{index:02d}-' + Path(a['path']).name
            destination = temporary / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / a['path'], destination)
            if hashlib.sha256(destination.read_bytes()).hexdigest() != a['sha256']:
                raise PackError('Source changed while copying: ' + asset_id)
            rows.append({'upload_index': index, 'asset_id': asset_id, 'file': path,
                         'role': a['role'], 'sha256': a['sha256'],
                         'width': a['width'], 'height': a['height']})
        zh = ('只使用本包原始参考：图1负责本人身份和脸部；图2负责原版动漫造型、服装、比例、墨线及明暗；'
              '图3只负责定制鞋。图4只负责表情，存在图5时它只负责身体语言。'
              '不能以粉衣、黑框等配饰相同代替人物相同，不能重新设计脸型或人物气质。'
              '单一人物、完整场景；不复制参考拼板的布局、标题和格子。\n')
        en = ('Use only the original references in this pack. Image 1 anchors identity and facial features. '
              'Image 2 controls the original animated design, outfit, proportions, linework, and shading. '
              'Image 3 controls only the custom shoes. Image 4 guides expression; Image 5, when included, '
              'guides body language only. Preserve the actual character, not just the pink top and glasses. '
              'Create one character in one scene, not a reference sheet.\n')
        template = json.loads(json.dumps(plan, ensure_ascii=False))
        for index, shot in enumerate(plan['shots'], 1):
            directory = temporary / f'shots/shot-{index:03d}'
            directory.mkdir(parents=True)
            start = json.dumps(shot['continuity_in'], ensure_ascii=False)
            (directory / 'keyframe.zh.txt').write_text(zh + shot.get('frame_prompt_zh', '') + '\n起始状态：' + start + '\n', encoding='utf-8')
            (directory / 'keyframe.en.txt').write_text(en + shot.get('frame_prompt_en', '') + '\nStarting state: ' + start + '\n', encoding='utf-8')
            (directory / 'motion.zh.txt').write_text(shot['prompt_zh'] + '\n', encoding='utf-8')
            (directory / 'motion.en.txt').write_text(shot['prompt_en'] + '\n', encoding='utf-8')
            write_json(directory / 'shot.json', shot)
            template['shots'][index-1].update(mode='first_frame', reference_ids=[],
                                             first_frame_id=f'REGISTER_SCENE_FRAME_{index:02d}', last_frame_id=None)
        write_json(temporary / 'video-plan.template.json', template)
        write_json(temporary / 'upload-map.json', {'stage': 'image_reference_preparation_not_video_input', 'inputs': rows})
        write_json(temporary / 'pack.json', {'status': 'original_reference_preproduction', 'generation_executed': False,
                   'visual_approval_granted': False, 'video_tested': False, 'original_integrity': original_report,
                   'plan': plan, 'references': rows, 'warnings': checked['warnings']})
        (temporary / 'README.md').write_text(
            '# BIT东｜原版IP视频准备包\n\n'
            '原图逐字节复制，没有裁切、重绘、放大或换脸。这个包是实际素材和提示，不是已生成的视频。\n\n'
            '1. 按 upload-map.json 核对参考职责。原版拼板用于图像生成的身份/表演参考，不直接当视频首帧。'
            '参考数量受具体平台限制时，先制作单角色场景首帧，不能删掉身份依据并猜人。\n'
            '2. 用每镜头 keyframe.zh.txt 或 keyframe.en.txt 制作场景首帧，和原版对照审查脸、眼镜、发型、身体轮廓、服饰及画风。'
            '不要使用被否定的 video-v2-candidates。\n'
            '3. 用仓库 register_frame.py 登记真实首帧和真正使用的参考ID；新增图先为candidate。'
            '把登记ID填入 video-plan.template.json。REGISTER_SCENE_FRAME_XX 不是可用素材ID。\n'
            '4. 候选试用由 prepare_video_pack.py --allow-draft 导出；正式使用需要真实批准记录和当前平台能力记录。'
            '视频平台仅接收对应首帧和 motion 提示。不能把本地计划JSON直接当任何厂商API请求。\n'
            '5. 检查真实视频的首、中、尾帧、眨眼、转头、遮挡恢复及跨镜头衔接。未运行项目保持not_run。\n\n'
            '每镜头时长、画幅、模型ID和参考上限均为待核验项；本包没有调用收费平台。\n', encoding='utf-8')
        temporary.rename(output)
        return output
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--emotion', choices=sorted(EMOTIONS), default='social')
    parser.add_argument('--body', action='store_true')
    args = parser.parse_args(argv)
    try:
        output = prepare(Path(__file__).resolve().parents[1], load_json(args.plan), args.out, args.emotion, args.body)
        print('EXPORTED ORIGINAL REFERENCES:', output)
        return 0
    except (IdentityError, PackError, OSError) as exc:
        print('ERROR:', exc, file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
