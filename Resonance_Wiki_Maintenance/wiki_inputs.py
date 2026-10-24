"""Shared fail-closed source / authoring / product contract for tracked editions."""
import hashlib
import io
import json
from pathlib import Path
import subprocess

TEXT={'.py','.js','.css','.json','.md','.html','.txt','.hex'}
CANONICAL_RULE='Text CRLF/CR to LF only; preserve BOM and trailing newline; binary exact; raw capture retained separately'


def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(path,raw):return raw.replace(b'\r\n',b'\n').replace(b'\r',b'\n') if Path(path).suffix.lower() in TEXT or Path(path).name=='.gitattributes' else raw
def identity(path,raw):
    value=canonical(path,raw)
    return dict(raw_sha256=sha(raw),bytes=len(raw),canonical_sha256=sha(value),canonical_bytes=len(value))

def freshness(files):
    return {p:{k:v for k,v in row.items() if k in ('canonical_sha256','canonical_bytes','git_blob')} for p,row in files.items()}
def git(repo,*args):return subprocess.check_output(['git','-C',str(repo),*args])
def included(path,scope):return any(path==p or p.endswith('/') and path.startswith(p) for p in scope)


def reviewed_inputs(repo,config):
    """Compare scoped checkout paths (including additions) to real committed blobs.

    Text checkout normalization is explicit; build bindings also record raw bytes.
    A docs-only HEAD is permitted. Rebuilding never blesses unreviewed source.
    """
    revision=config['commit'];scope=config['source_scope']
    if not isinstance(scope,list) or not scope or any(not isinstance(p,str) or not p or '..' in Path(p).parts or Path(p).is_absolute() for p in scope):
        raise ValueError('invalid explicit source_scope')
    actual_revision=git(repo,'rev-parse',revision+'^{commit}').decode().strip()
    if actual_revision!=revision:raise ValueError('reviewed source must be a full immutable commit ID')
    entries={}
    for row in git(repo,'ls-tree','-rz',revision).split(b'\0'):
        if not row:continue
        meta,path=row.split(b'\t',1);name=path.decode('utf-8')
        if included(name,scope):entries[name]=meta.split()[2].decode()
    objects=sorted(set(entries.values()))
    stream=io.BytesIO(subprocess.run(['git','-C',str(repo),'cat-file','--batch'],input=('\n'.join(objects)+'\n').encode(),capture_output=True,check=True).stdout)
    blobs={}
    for oid in objects:
        size=int(stream.readline().split()[2]);blobs[oid]=stream.read(size);assert stream.read(1)==b'\n'
    present={p.decode('utf-8') for p in git(repo,'ls-files','--cached','--others','--exclude-standard','-z').split(b'\0') if p and included(p.decode('utf-8'),scope) and (repo/p.decode('utf-8')).is_file()}
    missing=sorted(set(entries)-present);added=sorted(present-set(entries));changed=[];files={}
    for path in sorted(set(entries)&present):
        raw=(repo/path).read_bytes();committed=blobs[entries[path]]
        if canonical(path,raw)!=canonical(path,committed):changed.append(path)
        files[path]=dict(identity(path,raw),git_blob=entries[path])
    if changed or added or missing:raise ValueError('unreviewed source mismatch: '+json.dumps(dict(changed=changed,added=added,missing=missing)))
    return dict(source_revision=revision,scope=scope,files=files,canonical_rule=CANONICAL_RULE)


def authoring_inputs(root,config):
    names={'wiki-config.json','wiki_inputs.py','build_wiki.py','validate_wiki.py','theme.css','reader.js','requirements-docs.txt','README.txt','verify_reader.py','verify_edition.py','test_wiki_inputs.py',config['reviewed_evidence']}
    # Bind all current/future project-owned verification helpers, including tests.
    # Products and historical audits are deliberately not inputs to themselves.
    names.update(p.name for p in root.iterdir() if p.is_file() and p.suffix in ('.py','.js','.css'))
    # Checkout policy is an authoring input; its removal/change invalidates the binding.
    if (root/'.gitattributes').is_file():names.add('.gitattributes')
    names.update(item['file'] for item in config['chapters'])
    for folder in ('chapters','examples','illustrations'):
        names.update(p.relative_to(root).as_posix() for p in (root/folder).rglob('*') if p.is_file())
    result={}
    for name in sorted(names):
        p=(root/name).resolve()
        if not p.is_relative_to(root.resolve()) or not p.is_file():raise ValueError('missing wiki authoring input '+name)
        raw=p.read_bytes();result[name]=identity(name,raw)
    return result


def bind_products(root,repo,config,source,output):
    binding=dict(schema=3,source=source,wiki=authoring_inputs(root,config),canonical_rule=CANONICAL_RULE,documentation_delivery_revision=git(repo,'rev-parse','HEAD').decode().strip(),
                 products={output.name:dict(sha256=sha(output.read_bytes()),bytes=output.stat().st_size)},
                 delivery_note='HEAD at build; subsequent metadata/product-only delivery commits may differ without changing reviewed source or wiki inputs.')
    (root/'source-manifest.json').write_text(json.dumps(binding,indent=2)+'\n',encoding='utf-8')
    return binding


def check_products(root,repo,config,output):
    source=reviewed_inputs(repo,config)
    binding=json.loads((root/'source-manifest.json').read_text(encoding='utf-8'))
    saved=binding.get('source',{})
    if (binding.get('schema')!=3 or binding.get('canonical_rule')!=CANONICAL_RULE or
        any(saved.get(k)!=source[k] for k in ('source_revision','scope','canonical_rule')) or
        freshness(saved.get('files',{}))!=freshness(source['files'])):raise ValueError('stale source build binding; review source and rebuild')
    if freshness(binding['wiki'])!=freshness(authoring_inputs(root,config)):raise ValueError('stale or missing wiki authoring input; rebuild reviewed edition')
    expected=binding['products'].get(output.name)
    if not output.is_file() or expected!=dict(sha256=sha(output.read_bytes()),bytes=output.stat().st_size):raise ValueError('missing or stale HTML product')
    return binding
