#!/usr/bin/env python3
"""Internal copy/adaptation step for safe-skills-update.sh; no updater, model, Git commit or service calls."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import datetime,timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
sys.dont_write_bytecode=True

STAMP='.openclaw-copy.json'
VERSION=1
DEPENDENCIES=('AGENTS.md','.agents/tools/scoped-changes/change_guard.py','.agents/tools/scoped-changes/README.md',
 '.agents/tools/vault-records/record_guard.py','.agents/workflows/wiki/wiki-ingest.md',
 '.agents/contracts/record-contract.md','.agents/skills/vault-index-maintain/SKILL.md','.agents/vault-workflows.json',
 'assets/templates/Properties.md','assets/templates/wiki-source.md','assets/templates/wiki-concept.md','assets/templates/wiki-entity.md',
 '5-wiki/schema.md','5-wiki/ledger.md')

class Conflict(ValueError):pass
def sha(raw):return hashlib.sha256(raw).hexdigest()
def packed(data):return json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2)+'\n'
def cache(rel):return '__pycache__' in Path(rel).parts or Path(rel).name=='.DS_Store'
def metadata(rel):return Path(rel).parts[0]=='.clawhub' or cache(rel)
def state(root):
    if root.is_symlink() or not root.is_dir():raise Conflict('OpenClaw target must already be a real copy directory: '+str(root))
    result={}
    for p in [root,*sorted(root.rglob('*'))]:
        rel='.' if p==root else p.relative_to(root).as_posix();s=p.lstat()
        if p.is_symlink():raise Conflict('Unexpected symlink inside skill: '+str(p))
        item={'mode':stat.S_IMODE(s.st_mode),'mtime_ns':s.st_mtime_ns}
        if p.is_dir():item['kind']='directory'
        elif p.is_file():item.update(kind='file',sha256=sha(p.read_bytes()))
        else:raise Conflict('Unexpected file type: '+str(p))
        result[rel]=item
    return result

def payloads(root):
    result={}
    for p in sorted(root.rglob('*')):
        rel=p.relative_to(root).as_posix()
        if cache(rel):continue
        if p.is_symlink():raise Conflict('Canonical skill has an internal symlink: '+str(p))
        if p.is_file():result[rel]={'data':p.read_bytes(),'mode':stat.S_IMODE(p.stat().st_mode)}
    return result

def signatures(files):return {p:{'sha256':sha(x['data']),'mode':x['mode']} for p,x in files.items()}
def check_dependencies(source,python):
    if source.name!='knowledge-clip' or source.parent.name!='skills' or source.parent.parent.name!='.agents':
        raise Conflict('knowledge-clip source must retain the canonical Vault/.agents/skills layout')
    vault=source.parents[2]
    for relative in DEPENDENCIES:
        p=vault/relative
        if not p.is_file():raise Conflict('Required Vault dependency missing: '+str(p))
        with p.open('rb') as handle:handle.read(1)
    config=json.loads((vault/'.agents/vault-workflows.json').read_text())
    if config.get('vault_root') and Path(config['vault_root']).expanduser().resolve()!=vault:raise Conflict('Vault profile selects another checkout')
    for field in ['record_contract','weekly_execution_contract','parenting_boundary_contract']:
        if config.get(field):
            rel=Path(config[field])
            if rel.is_absolute() or '..' in rel.parts or not (vault/rel).is_file():raise Conflict('Broken Vault contract reference: '+field)
    code="import json,sys,yaml; assert sys.version_info >= (3,10); assert yaml.__version__.split('.')[0]=='6'; print(json.dumps({'python':sys.executable,'yaml':yaml.__version__}))"
    probe=subprocess.run([str(python),'-B','-c',code],cwd='/',capture_output=True,text=True)
    if probe.returncode:raise Conflict('Selected Python/PyYAML dependency check failed: '+probe.stderr.strip())
    return vault,json.loads(probe.stdout)

def adapted(files,source,vault,python,plugin_name):
    output={k:dict(v) for k,v in files.items()};text=files['SKILL.md']['data'].decode('utf-8');front=re.match(r'\A---\r?\n.*?\r?\n---(?:\r?\n|$)',text,re.S)
    if not front or not re.search(r'^name:\s*[\"\']?knowledge-clip[\"\']?\s*$',front[0],re.M):raise Conflict('Skill name/frontmatter mismatch')
    note=('\n## OpenClaw 本机路径适配\n\n'
      '本目录保持独立副本；运行脚本使用本目录 scripts/clip_flow.py 的薄委派，复用已存在的 Vault 实现。\n'
      f'已校验源码/依赖所在 Vault：`{vault}`；默认目标仍由 find_vault.py 输出并核对实际 Git 根。\n'
      '按目标 Vault 的绝对路径读取 AGENTS.md、.agents/workflows/wiki/wiki-ingest.md、.agents/tools/scoped-changes/README.md、Properties 和 schema/ledger；不要按 OpenClaw workspace 拼接这些项目路径。\n'
      '先用当前 OpenClaw 文件工具确认源码与所需依赖可访问。任何明确访问拒绝都必须停止并报告，不得改用 exec、其他路径或本委派绕过，也不修改允许根/权限/服务配置。\n'
      '技能发现根限制与实际文件访问权限分别核对；本适配不授予任何新访问权限。\n'
      f'委派入口：`{source/"scripts/clip_flow.py"}`；固定使用已校验的 Python：`{python}`。\n'
      '默认仍自动 raw→Wiki→必要索引，只有最终具体 diff 确认后才 commit；实际归属歧义/人工冲突按原契约停止。\n')
    output['SKILL.md']['data']=(text[:front.end()]+note+text[front.end():]).encode()
    wrapper=('#!/usr/bin/env python3\n"""Generated by safe-skills-update.sh; do not hand-edit this copy adapter."""\n'
      'from pathlib import Path\nimport os,runpy,sys\n'
      f'UPSTREAM=Path({str(source/"scripts/clip_flow.py")!r})\nPYTHON=Path({str(python)!r})\n'
      'if not UPSTREAM.is_file():raise SystemExit("Canonical clip entry unavailable; stop and report access/path failure: "+str(UPSTREAM))\n'
      'if __name__=="__main__":\n'
      '    os.execv(str(PYTHON),[str(PYTHON),"-B",str(UPSTREAM),*sys.argv[1:]])\n'
      'else:\n    globals().update(runpy.run_path(str(UPSTREAM),run_name=__name__))\n')
    output['scripts/clip_flow.py']={'data':wrapper.encode(),'mode':files['scripts/clip_flow.py']['mode']}
    stamp={'version':VERSION,'skill':'knowledge-clip','canonical_source':str(source),'python':str(python),
      'pluginName':plugin_name,'source_files':signatures(files),'owned_files':signatures(output),'vault_dependencies':list(DEPENDENCIES)}
    output[STAMP]={'data':packed(stamp).encode(),'mode':0o644};return output

def prepare(canonical_dir,openclaw_dir,name,python=None,post_update=False):
    if name!='knowledge-clip':raise Conflict('This adaptation is limited to knowledge-clip')
    entry=Path(canonical_dir).expanduser()/name;source=entry.resolve(strict=True);target=Path(openclaw_dir).expanduser()/name
    if source==target.resolve():raise Conflict('Canonical and OpenClaw directories must be separate')
    python=Path(python or sys.executable).expanduser().absolute();before=state(target);source_state=state(source);files=payloads(source)
    if 'scripts/clip_flow.py' not in files:raise Conflict('Canonical clip flow script missing')
    vault,probe=check_dependencies(source,python)
    lock=Path(canonical_dir).expanduser().parent/'.skill-lock.json';lock_hash=sha(lock.read_bytes()) if lock.is_file() else None
    plugin_name=json.loads(lock.read_text()).get('skills',{}).get(name,{}).get('pluginName') if lock.is_file() else None
    desired=adapted(files,source,vault,python,plugin_name);previous=json.loads((target/STAMP).read_text()) if (target/STAMP).is_file() else None
    old_owned=previous.get('owned_files',{}) if previous else {}
    if previous and (previous.get('version')!=VERSION or previous.get('skill')!=name):raise Conflict('Unknown adapter ownership; inspect before overwrite')
    current_files={p:{'sha256':v['sha256'],'mode':v['mode']} for p,v in before.items() if v['kind']=='file'}
    if previous and not post_update:
        missing=[rel for rel in old_owned if rel in files and rel not in current_files]
        if missing:raise Conflict('Owned OpenClaw files were removed; preserved current state: '+', '.join(missing))
    for rel,current in current_files.items():
        if rel==STAMP:continue
        if metadata(rel):
            desired[rel]={'data':(target/rel).read_bytes(),'mode':current['mode']};continue
        if previous:
            accepted=[old_owned.get(rel)]
            if post_update:accepted.extend([previous.get('source_files',{}).get(rel),signatures(files).get(rel)])
            if current not in accepted:raise Conflict('Manual/unowned OpenClaw change; preserved: '+rel)
        elif rel not in files:raise Conflict('Unowned OpenClaw file; preserved: '+rel)
    wanted=signatures(desired);changes=sorted(p for p in set(current_files)|set(wanted) if current_files.get(p)!=wanted.get(p))
    return {'name':name,'entry':entry,'source':source,'target':target,'before':before,'source_state':source_state,'desired':desired,'changed_paths':changes,'lock':lock,'lock_hash':lock_hash,'python':python,'python_probe':probe,'post_update':post_update}

@contextmanager
def lock_target(target):
    p=Path('/tmp')/('openclaw-copy-'+str(os.getuid())+'-'+sha(str(target).encode())[:20]+'.lock')
    fd=os.open(p,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);yield
    finally:os.close(fd)

def backup_target(plan,backup_root):
    root=Path(backup_root).expanduser().resolve()
    if root.is_relative_to(plan['target']) or root.is_relative_to(plan['source']):raise Conflict('Backup must stay outside source/skill roots')
    root.mkdir(parents=True,exist_ok=True);folder=Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-knowledge-clip-',dir=root));archive=folder/'before.tar.gz'
    with tarfile.open(archive,'w:gz') as tar:tar.add(plan['target'],arcname='knowledge-clip',recursive=True)
    with tarfile.open(archive) as tar:
        for rel,item in plan['before'].items():
            member=tar.getmember('knowledge-clip' if rel=='.' else 'knowledge-clip/'+rel)
            if member.mode!=item['mode']:raise Conflict('Backup mode mismatch')
            if item['kind']=='file' and sha(tar.extractfile(member).read())!=item['sha256']:raise Conflict('Backup content mismatch')
    info={'target':str(plan['target']),'before':plan['before'],'archive_sha256':sha(archive.read_bytes()),'canonical_source':str(plan['source'])}
    (folder/'manifest.json').write_text(packed(info));return folder

def apply(plan,backup_root):
    with lock_target(plan['target']):
        if state(plan['target'])!=plan['before'] or state(plan['source'])!=plan['source_state'] or plan['entry'].resolve()!=plan['source']:raise Conflict('Concurrent source/target change; re-run preview')
        check_dependencies(plan['source'],plan['python'])
        if not plan['changed_paths']:return {'status':'up-to-date','skill':plan['name'],'changed_paths':[],'backup':None}
        folder=backup_target(plan,backup_root);stage=Path(tempfile.mkdtemp(prefix='.knowledge-clip-stage-',dir=plan['target'].parent));old=stage.parent/(stage.name+'-previous')
        try:
            for rel,entry in plan['before'].items():
                if entry['kind']=='directory':(stage/rel).mkdir(parents=True,exist_ok=True);(stage/rel).chmod(entry['mode'])
            for rel,item in plan['desired'].items():
                p=stage/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(item['data']);p.chmod(item['mode'])
            if state(plan['target'])!=plan['before'] or state(plan['source'])!=plan['source_state'] or plan['entry'].resolve()!=plan['source']:raise Conflict('Concurrent change before replacement')
            check_dependencies(plan['source'],plan['python'])
            if plan['lock_hash'] is not None and sha(plan['lock'].read_bytes())!=plan['lock_hash']:raise Conflict('Skill metadata lock changed; re-run preview')
            os.rename(plan['target'],old)
            try:os.rename(stage,plan['target'])
            except Exception:
                if not plan['target'].exists():os.rename(old,plan['target'])
                raise
            actual=state(plan['target']);actual_files={p:{'sha256':x['sha256'],'mode':x['mode']} for p,x in actual.items() if x['kind']=='file'}
            if actual_files!=signatures(plan['desired']):raise Conflict('Post-write verification failed; inspect target and backup')
            data=json.loads((folder/'manifest.json').read_text());data['after']=actual;(folder/'manifest.json').write_text(packed(data))
            shutil.rmtree(old)
            return {'status':'synced','skill':plan['name'],'changed_paths':plan['changed_paths'],'backup':str(folder),'canonical_source':str(plan['source']),'python':plan['python_probe']}
        finally:
            if stage.exists():shutil.rmtree(stage)
            # A leftover -previous directory is retained after uncertain outcomes, never force-removed.

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--skill',action='append',choices=['knowledge-clip'],required=True)
    p.add_argument('--canonical-dir',default=str(Path.home()/'.agents/skills'));p.add_argument('--openclaw-dir',default=str(Path.home()/'.openclaw/skills'));p.add_argument('--backup-dir',default=str(Path.home()/'.openclaw/backups/skill-sync'));p.add_argument('--python');p.add_argument('--post-update',action='store_true')
    mode=p.add_mutually_exclusive_group();mode.add_argument('--apply',action='store_true');mode.add_argument('--dry-run',action='store_true');a=p.parse_args()
    try:
        if len(a.skill)!=len(set(a.skill)):raise Conflict('Duplicate selection')
        plans=[prepare(a.canonical_dir,a.openclaw_dir,name,a.python,a.post_update) for name in a.skill]
        results=[apply(plan,a.backup_dir) if a.apply else {'status':'dry-run','skill':plan['name'],'changed_paths':plan['changed_paths'],'canonical_source':str(plan['source']),'dependencies':'readable','python':plan['python_probe']} for plan in plans]
        print(packed({'results':results,'network':False,'config_or_lock_modified':False}),end='');return 0
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print(packed({'status':'stopped','error':str(exc)}),file=sys.stderr,end='');return 2

if __name__=='__main__':raise SystemExit(main())
