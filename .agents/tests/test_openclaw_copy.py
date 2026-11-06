import hashlib,importlib.util,json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

BASE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('copy_adapter',BASE/'openclaw-copy-adapter.py');copy=importlib.util.module_from_spec(spec);spec.loader.exec_module(copy)

class CopyFixture(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='openclaw-copy-fixture-');self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name).resolve();self.home=self.base/'home';self.vault=self.base/'Vault with spaces';self.source=self.vault/'.agents/skills/knowledge-clip';self.source.mkdir(parents=True)
        self.canonical=self.home/'.agents/skills';self.canonical.mkdir(parents=True);(self.canonical/'knowledge-clip').symlink_to(self.source)
        self.oc=self.home/'.openclaw/skills';self.target=self.oc/'knowledge-clip';self.target.mkdir(parents=True);self.backups=self.base/'backups'
        self.write(self.target/'SKILL.md','---\nname: knowledge-clip\n---\nLegacy opt-in.\n')
        self.write(self.target/'.clawhub/origin.json','{"id":"preserved-fixture-id","pluginName":"Personal"}\n')
        self.write(self.oc/'clawfeed/SKILL.md','OpenClaw-only fixture.\n');self.write(self.oc/'other/SKILL.md','Untouched fixture.\n')
        self.write(self.source/'SKILL.md','---\nname: knowledge-clip\ndescription: Fixture automatic raw to Wiki, confirm exact diff before commit.\nmetadata:\n  pluginName: Personal\n---\n# Fixture\n')
        self.write(self.source/'scripts/clip_flow.py','import json,sys\nif __name__=="__main__":print(json.dumps({"file":__file__,"argv":sys.argv[1:],"python":sys.executable}))\n')
        self.write(self.source/'references/fixture.md','Fixture resource.\n')
        for rel in copy.DEPENDENCIES:self.write(self.vault/rel,'Fixture dependency.\n')
        self.write(self.vault/'.agents/vault-workflows.json',json.dumps({'version':1,'vault_root':str(self.vault)}))
        self.lock=self.home/'.agents/.skill-lock.json';self.write(self.lock,'{"skills":{"knowledge-clip":{"source":"fixture/local","pluginName":"Personal","sourceType":"local"}},"fixture":"preserve bytes"}\n')
        self.install_entry()
    def write(self,p,text):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text);return p
    def install_entry(self):
        self.agents=self.home/'.agents'
        for name in ['safe-skills-update.sh','openclaw-copy-adapter.py']:shutil.copy2(BASE/name,self.agents/name)
    def plan(self,post=False):return copy.prepare(self.canonical,self.oc,'knowledge-clip',post_update=post)
    def apply(self):return copy.apply(self.plan(),self.backups)
    def tree(self,root):
        return {str(p.relative_to(root)):(hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mode&0o777) for p in root.rglob('*') if p.is_file() and not p.is_symlink()}
    def shell(self,*args,status=0):
        env=dict(os.environ,HOME=str(self.home),PYTHONDONTWRITEBYTECODE='1',FAKE_NPX_STATUS=str(status),PATH=str(self.home/'bin')+os.pathsep+os.environ['PATH'])
        return subprocess.run(['bash',str(self.agents/'safe-skills-update.sh'),*args],env=env,capture_output=True,text=True)
    def fake_npx(self):
        p=self.write(self.home/'bin/npx','#!/usr/bin/env python3\nimport os,shutil\nfrom pathlib import Path\nh=Path.home();s=h/".agents/skills/knowledge-clip";t=h/".openclaw/skills/knowledge-clip"\nfor p in ["SKILL.md","scripts/clip_flow.py"]:shutil.copy2(s/p,t/p)\n(h/"npx-called").write_text("called")\nraise SystemExit(int(os.environ.get("FAKE_NPX_STATUS","0")))\n');p.chmod(0o755)
        self.write(self.agents/'apply-pluginName-overrides.py','from pathlib import Path\n(Path.home()/"overrides-called").write_text("called")\n')
class CopyTests(CopyFixture):
    def test_targeted_dry_run_is_readonly_and_never_calls_updater(self):
        self.fake_npx();before=self.tree(self.home);result=self.shell('--sync-openclaw','--skill','knowledge-clip','--dry-run')
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(before,self.tree(self.home));self.assertFalse(self.backups.exists());self.assertFalse((self.home/'npx-called').exists())
    def test_copy_preserves_metadata_locks_other_skills_and_frontmatter(self):
        before_other=self.tree(self.oc/'other');clawfeed=self.tree(self.oc/'clawfeed');lock=self.lock.read_bytes();origin=(self.target/'.clawhub/origin.json').read_bytes();result=self.apply()
        self.assertEqual(result['status'],'synced');self.assertFalse(self.target.is_symlink());self.assertEqual(self.tree(self.oc/'other'),before_other);self.assertEqual(self.tree(self.oc/'clawfeed'),clawfeed);self.assertEqual(self.lock.read_bytes(),lock);self.assertEqual((self.target/'.clawhub/origin.json').read_bytes(),origin)
        front=lambda p:p.read_text().split('---',2)[1]
        self.assertEqual(front(self.source/'SKILL.md'),front(self.target/'SKILL.md'));self.assertIn('pluginName: Personal',front(self.target/'SKILL.md'))
        self.assertEqual((self.source/'references/fixture.md').read_bytes(),(self.target/'references/fixture.md').read_bytes());self.assertTrue((Path(result['backup'])/'before.tar.gz').is_file())
    def test_repeat_is_noop_and_canonical_update_rebuilds_adapter(self):
        self.apply();before=copy.state(self.target);backups=len(list(self.backups.iterdir()));result=self.apply()
        self.assertEqual(result['status'],'up-to-date');self.assertEqual(before,copy.state(self.target));self.assertEqual(len(list(self.backups.iterdir())),backups)
        self.write(self.source/'references/fixture.md','Updated canonical reference.\n');self.apply();self.assertEqual((self.target/'references/fixture.md').read_text(),'Updated canonical reference.\n');self.assertIn('UPSTREAM=Path(', (self.target/'scripts/clip_flow.py').read_text())
    def test_wrapper_uses_canonical_path_and_selected_python(self):
        self.apply();result=subprocess.run([sys.executable,'-B',str(self.target/'scripts/clip_flow.py'),'--fixture','value with spaces'],capture_output=True,text=True,check=True);data=json.loads(result.stdout)
        self.assertEqual(Path(data['file']),self.source/'scripts/clip_flow.py');self.assertEqual(data['argv'],['--fixture','value with spaces'])
        (self.source/'scripts/clip_flow.py').unlink();result=subprocess.run([sys.executable,'-B',str(self.target/'scripts/clip_flow.py')],capture_output=True,text=True);self.assertNotEqual(result.returncode,0);self.assertIn('unavailable',result.stderr)
    def test_missing_dependency_and_access_denial_stop_before_writes(self):
        before=copy.state(self.target);(self.vault/'.agents/tools/scoped-changes/change_guard.py').unlink()
        with self.assertRaises(copy.Conflict):self.plan()
        self.assertEqual(before,copy.state(self.target))
        with patch.object(copy,'check_dependencies',side_effect=PermissionError('explicit fixture access denied')):
            with self.assertRaises(PermissionError):self.plan()
        self.assertEqual(before,copy.state(self.target))
    def test_concurrent_target_source_and_metadata_changes_are_protected(self):
        plan=self.plan();self.write(self.target/'SKILL.md','Concurrent manual text.\n')
        with self.assertRaises(copy.Conflict):copy.apply(plan,self.backups)
        self.assertEqual((self.target/'SKILL.md').read_text(),'Concurrent manual text.\n')
        plan=self.plan();self.write(self.source/'references/fixture.md','Concurrent source.\n')
        with self.assertRaises(copy.Conflict):copy.apply(plan,self.backups)
    def test_owned_manual_edits_and_unknown_files_are_preserved(self):
        self.apply();self.write(self.target/'SKILL.md',(self.target/'SKILL.md').read_text()+'Manual edit.\n')
        with self.assertRaises(copy.Conflict):self.plan()
        self.assertIn('Manual edit.',(self.target/'SKILL.md').read_text())
    def test_missing_owned_file_and_unknown_initial_file_stop(self):
        self.write(self.target/'local-note.md','Unowned.\n')
        with self.assertRaises(copy.Conflict):self.plan()
        (self.target/'local-note.md').unlink();self.apply();(self.target/'references/fixture.md').unlink()
        with self.assertRaises(copy.Conflict):self.plan()
    def test_second_rename_failure_restores_original_target(self):
        before=copy.state(self.target);original=os.rename;calls=0
        def interrupted(*args,**kwargs):
            nonlocal calls;calls+=1
            if calls==2:raise OSError('fixture interruption')
            return original(*args,**kwargs)
        with patch.object(copy.os,'rename',side_effect=interrupted):
            with self.assertRaises(OSError):copy.apply(self.plan(),self.backups)
        self.assertEqual(before,copy.state(self.target))
    def test_targeted_apply_changes_only_selected_skill_and_no_updater(self):
        self.fake_npx();other=self.tree(self.oc/'other');lock=self.lock.read_bytes();result=self.shell('--sync-openclaw','--skill','knowledge-clip','--apply','--backup-dir',str(self.backups))
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(other,self.tree(self.oc/'other'));self.assertEqual(lock,self.lock.read_bytes());self.assertFalse((self.home/'npx-called').exists());self.assertFalse((self.home/'overrides-called').exists())
    def test_selection_is_required_and_unrelated_skill_rejected(self):
        before=self.tree(self.home)
        for args in [('--sync-openclaw','--dry-run'),('--sync-openclaw','--skill','clawfeed','--apply')]:
            result=self.shell(*args);self.assertNotEqual(result.returncode,0)
        self.assertEqual(before,self.tree(self.home))
    def test_regular_update_reapplies_adapter_even_if_target_stays_copy(self):
        self.apply();self.fake_npx();other=self.tree(self.oc/'other');result=self.shell()
        self.assertEqual(result.returncode,0,result.stderr);self.assertTrue((self.home/'npx-called').exists());self.assertFalse(self.target.is_symlink());self.assertIn('UPSTREAM=Path(',(self.target/'scripts/clip_flow.py').read_text());self.assertIn('OpenClaw 本机路径适配',(self.target/'SKILL.md').read_text());self.assertEqual(other,self.tree(self.oc/'other'))
    def test_failed_upstream_update_still_restores_adapter_and_exit_status(self):
        self.apply();self.fake_npx();result=self.shell(status=7)
        self.assertEqual(result.returncode,7,result.stderr);self.assertIn('UPSTREAM=Path(',(self.target/'scripts/clip_flow.py').read_text());self.assertTrue((self.home/'overrides-called').exists())

class ClipIntegration(CopyFixture):
    def test_real_clip_flow_uses_fixture_and_waits_for_exact_commit_approval(self):
        canonical=Path('/Users/liuchunlei/Code/Obsidian Vault')
        # Repository implementation files only; all note/schema/ledger content below is synthetic.
        shutil.rmtree(self.source);shutil.copytree(canonical/'.agents/skills/knowledge-clip',self.source,ignore=shutil.ignore_patterns('__pycache__','.DS_Store'))
        for rel in ['.agents/tools/scoped-changes/change_guard.py','.agents/tools/vault-records/record_guard.py']:
            shutil.copy2(canonical/rel,self.vault/rel)
        self.write(self.vault/'assets/templates/Properties.md','---\nstatus: [In Progress]\ntype: [文章]\ncategory: [科学与技术]\nmedia: [网络]\n---\n')
        self.write(self.vault/'5-wiki/schema.md','# Fixture schema\n');self.write(self.vault/'5-wiki/.ledger.md','# Ledger\n')
        def git(*args):return subprocess.check_output(['git','-C',str(self.vault),*args],stderr=subprocess.STDOUT).decode().strip()
        for a in [('init','-q'),('config','user.name','Fixture'),('config','user.email','fixture@example.invalid'),('add','.'),('commit','-qm','Fixture baseline')]:git(*a)
        self.apply();entry=self.target/'scripts/clip_flow.py';run=self.base/'run.json';raw=self.base/'raw.json';ingest=self.base/'ingest.json';source='https://example.invalid/fixture'
        raw.write_text(json.dumps({'source':source,'original_content':'Original fixture article.','raw_path':'4-knowledge_hub/Clippings/[文章] Fixture.md','note':'---\nstatus: [In Progress]\ntype: [文章]\ncategory: [科学与技术]\nmedia: [网络]\nsource: '+source+'\n---\n\n## 原文\nOriginal fixture article.\n'}))
        def cli(*args):return subprocess.run([sys.executable,'-B',str(entry),'--vault-root',str(self.vault),*args],capture_output=True,text=True)
        head=git('rev-parse','HEAD');before=self.tree(self.vault);r=cli('raw','--request',str(raw));self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(before,self.tree(self.vault));self.assertFalse(run.exists())
        r=cli('raw','--request',str(raw),'--run',str(run),'--apply');self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(git('rev-parse','HEAD'),head);self.assertNotEqual(cli('review','--run',str(run)).returncode,0)
        ingest.write_text(json.dumps({'edits':[{'path':'5-wiki/concepts/fixture.md','create':'# Fixture\nCompiled fixture knowledge.\n'},{'path':'5-wiki/.ledger.md','patches':[{'old':'# Ledger\n','new':'# Ledger\nFixture ingested.\n'}]}]}))
        r=cli('ingest','--request',str(ingest),'--run',str(run),'--apply');self.assertEqual(r.returncode,0,r.stderr);r=cli('review','--run',str(run));self.assertEqual(r.returncode,0,r.stderr);receipt=json.loads(r.stdout);self.assertEqual(git('rev-parse','HEAD'),head);self.assertEqual(git('diff','--cached','--name-only'),'')
        self.assertNotEqual(cli('commit','--run',str(run),'--approval','wrong','--message','No').returncode,0);self.assertEqual(git('rev-parse','HEAD'),head)
        r=cli('commit','--run',str(run),'--approval',receipt['approval_token'],'--message','Fixture exact commit');self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(set(git('show','--format=','--name-only','HEAD').splitlines()),{'4-knowledge_hub/Clippings/[文章] Fixture.md','5-wiki/concepts/fixture.md','5-wiki/.ledger.md'})

if __name__=='__main__':unittest.main()
