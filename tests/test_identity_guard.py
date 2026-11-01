"""Regression tests for original-IP locks, deny rules and unchanged handoffs."""
import copy
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from identity_guard import IdentityError, load_policy, verify_originals, inspect_asset
from prepare_original_pack import prepare
from register_frame import register
from prepare_video_pack import validate_pack, export_pack, PackError
from test_prepare_video_pack import png


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding='utf-8')


class IdentityGuardTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'repo'
        self.root.mkdir()
        self.assets = []
        locked = []
        ids = ['identity-photo', 'source-character-sheet', 'source-shoe-board', 'performance-social', 'performance-work', 'performance-body']
        for i, aid in enumerate(ids):
            data = png(i + 2, 3)
            path = f'assets/{aid}.png'
            (self.root / 'assets').mkdir(exist_ok=True)
            (self.root / path).write_bytes(data)
            self.assets.append({'id':aid, 'path':path, 'status':'source', 'role':'design_source',
                                'width':i+2,'height':3,'sha256':hashlib.sha256(data).hexdigest(), 'provenance':{}})
            locked.append({'path':path,'git_blob_sha':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()})
        write(self.root / 'references/original-ip-lock.json', {'baseline':'test-only','files':locked})
        self.policy = {'schema_version':'1.0','original_lock':'references/original-ip-lock.json',
                       'blocked_sets':['rejected-set'],'blocked_ids':['rejected-id'],
                       'blocked_paths':['assets/rejected.png'],
                       'blocked_sha256':[hashlib.sha256(png(8,9)).hexdigest()],
                       'required_source_ids':ids[:3]}
        write(self.root/'references/identity-policy.json', self.policy)
        self.canon = {'schema_version':'1.0','character_id':'bitdong','design_version':'1.0-inherited',
                      'source_revision':'test-only','identity_policy_path':'references/identity-policy.json',
                      'approved_master_set':None}
        self.plan = json.loads((ROOT/'templates/shot-plan.example.json').read_text())
        self.save()

    def save(self):
        write(self.root/'references/character-canon.json', self.canon)
        write(self.root/'assets/asset-manifest.json', {'schema_version':'1.0','character_id':'bitdong','assets':self.assets})

    def add_frame(self, **changes):
        data = png(10,11)
        (self.root/'assets/frame.png').write_bytes(data)
        a={'id':'frame','path':'assets/frame.png','role':'shot_frame','status':'candidate','set_id':'original-derived',
           'single_subject':True,'sha256':hashlib.sha256(data).hexdigest(),'width':10,'height':11,
           'provenance':{'source_asset_ids':self.policy['required_source_ids']}}
        a.update(changes)
        self.assets.append(a)
        self.save()
        self.plan['shots'] = self.plan['shots'][:1]
        self.plan['shots'][0].update(mode='first_frame', first_frame_id=a['id'])
        return a

    def test_original_lock_passes(self):
        self.assertEqual(verify_originals(self.root)['checked_files'], 6)

    def test_original_change_is_detected(self):
        (self.root/self.assets[0]['path']).write_bytes(b'changed')
        with self.assertRaisesRegex(IdentityError,'Original IP file changed'):
            verify_originals(self.root)

    def test_missing_policy_fails_closed(self):
        (self.root/'references/identity-policy.json').unlink()
        with self.assertRaises(IdentityError): load_policy(self.root)

    def test_missing_lock_fails_closed(self):
        (self.root/'references/original-ip-lock.json').unlink()
        with self.assertRaises(IdentityError): verify_originals(self.root)

    def test_rejected_id_even_in_draft(self):
        self.add_frame(id='rejected-id')
        with self.assertRaisesRegex(PackError,'Rejected'):
            validate_pack(self.root,self.plan,True)

    def test_rejected_set_even_in_draft(self):
        self.add_frame(set_id='rejected-set')
        with self.assertRaisesRegex(PackError,'Rejected'):
            validate_pack(self.root,self.plan,True)

    def test_rejected_path(self):
        a=self.add_frame()
        shutil.copyfile(self.root/a['path'],self.root/'assets/rejected.png')
        a['path']='assets/rejected.png';self.save()
        with self.assertRaisesRegex(PackError,'Rejected'):
            validate_pack(self.root,self.plan,True)

    def test_hash_blocks_renamed_copy(self):
        a=self.add_frame()
        raw=png(8,9)
        (self.root/a['path']).write_bytes(raw)
        a.update(sha256=hashlib.sha256(raw).hexdigest(),width=8,height=9);self.save()
        with self.assertRaisesRegex(PackError,'Rejected image content'):
            validate_pack(self.root,self.plan,True)

    def test_rejected_parent(self):
        a=self.add_frame()
        a['provenance']['source_asset_ids'].append('rejected-id')
        parent=copy.deepcopy(a);parent['id']='rejected-id';self.assets.append(parent);self.save()
        with self.assertRaisesRegex(PackError,'Rejected'):
            validate_pack(self.root,self.plan,True)

    def test_ancestry_cycle(self):
        a=self.add_frame();a['provenance']['source_asset_ids']=['frame'];self.save()
        with self.assertRaisesRegex(PackError,'cycle'):
            validate_pack(self.root,self.plan,True)

    def test_missing_identity_ancestry(self):
        a=self.add_frame();a['provenance']['source_asset_ids']=['source-character-sheet'];self.save()
        with self.assertRaisesRegex(PackError,'lacks declared original'):
            validate_pack(self.root,self.plan,True)

    def test_valid_derived_draft_and_export(self):
        self.add_frame()
        checked=validate_pack(self.root,self.plan,True)
        self.assertTrue(checked['identity_policy_enforced'])
        out=Path(self.temp.name)/'video-pack';export_pack(checked,out)
        self.assertFalse(json.loads((out/'pack.json').read_text())['generation_executed'])

    def test_export_rechecks_originals(self):
        self.add_frame();checked=validate_pack(self.root,self.plan,True)
        (self.root/self.assets[0]['path']).write_bytes(b'changed')
        with self.assertRaisesRegex(PackError,'Original IP file changed'):
            export_pack(checked,Path(self.temp.name)/'bad')

    def test_dropped_continuity_key_is_not_allowed(self):
        del self.plan['shots'][1]['continuity_in']['lighting']
        with self.assertRaisesRegex(PackError,'continuity keys dropped'):
            validate_pack(self.root,self.plan,True)

    def test_dropped_end_state_is_not_allowed(self):
        del self.plan['shots'][0]['continuity_out']['lighting']
        with self.assertRaisesRegex(PackError,'end state drops'):
            validate_pack(self.root,self.plan,True)

    def test_original_pack_copies_bytes_and_two_shots(self):
        out=Path(self.temp.name)/'handoff';prepare(self.root,self.plan,out,body=True)
        p=json.loads((out/'pack.json').read_text())
        self.assertEqual(len(p['references']),5)
        self.assertFalse(p['generation_executed'])
        for a in p['references']:
            original=next(x for x in self.assets if x['id']==a['asset_id'])
            self.assertEqual((out/a['file']).read_bytes(),(self.root/original['path']).read_bytes())
        template=json.loads((out/'video-plan.template.json').read_text())
        with self.assertRaisesRegex(PackError,'unknown asset id'):
            validate_pack(self.root,template,True)

    def test_handoff_never_overwrites(self):
        out=Path(self.temp.name)/'handoff';out.mkdir()
        with self.assertRaises(PackError): prepare(self.root,self.plan,out)

    def test_handoff_not_written_into_source(self):
        with self.assertRaises(PackError): prepare(self.root,self.plan,self.root/'output')

    def test_register_candidate_without_approval(self):
        source=Path(self.temp.name)/'scene.png';source.write_bytes(png(12,13))
        prompt=Path(self.temp.name)/'prompt.txt';prompt.write_text('actual test prompt')
        a=register(self.root,source,'scene-01','set-01',self.policy['required_source_ids'],prompt)
        self.assertEqual(a['status'],'candidate');self.assertIsNone(a['provenance']['approved_by'])
        self.assertEqual((self.root/a['path']).read_bytes(),source.read_bytes())
        self.assertFalse((self.root/'assets/.register-frame.lock').exists())
        with self.assertRaises(PackError): register(self.root,source,'scene-01','set-01',self.policy['required_source_ids'],prompt)

    def test_register_rejected_content(self):
        source=Path(self.temp.name)/'scene.png';source.write_bytes(png(8,9))
        prompt=Path(self.temp.name)/'prompt.txt';prompt.write_text('actual test prompt')
        with self.assertRaisesRegex(PackError,'Rejected redesign'):
            register(self.root,source,'scene','set',self.policy['required_source_ids'],prompt)

    def test_register_does_not_relabel_source_sheet(self):
        prompt=Path(self.temp.name)/'prompt.txt';prompt.write_text('actual test prompt')
        with self.assertRaisesRegex(PackError,'already registered'):
            register(self.root,self.root/self.assets[1]['path'],'scene','set',self.policy['required_source_ids'],prompt)

    def test_existing_registration_lock_preserved(self):
        source=Path(self.temp.name)/'scene.png';source.write_bytes(png(12,13))
        prompt=Path(self.temp.name)/'prompt.txt';prompt.write_text('actual test prompt')
        lock=self.root/'assets/.register-frame.lock';lock.write_text('other writer')
        with self.assertRaisesRegex(PackError,'registration is in progress'):
            register(self.root,source,'scene','set',self.policy['required_source_ids'],prompt)
        self.assertEqual(lock.read_text(),'other writer')


class RepositoryIntegrityTest(unittest.TestCase):
    def test_real_original_files_preserved(self):
        self.assertEqual(verify_originals(ROOT)['checked_files'],34)

    def test_real_rejected_candidate_is_blocked(self):
        plan=json.loads((ROOT/'templates/shot-plan.example.json').read_text())
        plan['shots']=plan['shots'][:1]
        plan['shots'][0].update(mode='subject_reference',reference_ids=['master-front-candidate'])
        with self.assertRaisesRegex(PackError,'Rejected'):
            validate_pack(ROOT,plan,True)

    def test_standalone_originals_and_no_rejected_assets(self):
        companion=ROOT/'skills/bitdong-video'
        self.assertEqual(verify_originals(companion)['checked_files'],16)
        manifest=json.loads((companion/'assets/asset-manifest.json').read_text())
        self.assertEqual(len(manifest['assets']),10)
        self.assertTrue(all(a['status']=='source' for a in manifest['assets']))

    def test_standalone_can_export_without_parent_repository(self):
        with tempfile.TemporaryDirectory() as d:
            copied=Path(d)/'bitdong-video'
            shutil.copytree(ROOT/'skills/bitdong-video',copied,ignore=shutil.ignore_patterns('__pycache__'))
            out=Path(d)/'independent'
            plan=json.loads((copied/'templates/shot-plan.example.json').read_text())
            prepare(copied,plan,out,body=True)
            self.assertEqual(len(json.loads((out/'pack.json').read_text())['references']),5)

    def test_self_contained_build_matches(self):
        import subprocess
        subprocess.run([sys.executable,'-B',str(ROOT/'scripts/build_video_skill.py'),'--check'],check=True,capture_output=True)

    def test_real_two_shot_original_handoff(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'handoff'
            plan=json.loads((ROOT/'templates/shot-plan.example.json').read_text())
            prepare(ROOT,plan,out,body=True)
            p=json.loads((out/'pack.json').read_text())
            self.assertEqual(len(p['references']),5)
            self.assertEqual(len(p['plan']['shots']),2)


if __name__ == '__main__': unittest.main()
