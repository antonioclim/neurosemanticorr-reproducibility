"""Bounded stdlib-only P5 UNIT reviewer path. Never invokes a P4 identity."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
import types

sys.dont_write_bytecode = True
KIT = Path(__file__).resolve().parents[1]
ARMS = ('T_FULL', 'B_ASSERT', 'A0_SYNTAX', 'A1_STRUCTURE', 'A2_LOCAL', 'A3_PROVENANCE')
LOG_LIMIT = 65536
REPORT_LIMIT = 1048576
OUTPUT_LIMIT = 268435456
STOP_REQUESTED = False

class ReviewStop(RuntimeError):
    pass

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('Duplicate JSON key: ' + key)
        result[key] = value
    return result

def finite_float(token):
    value=float(token)
    if not math.isfinite(value):
        raise ValueError('Nonfinite JSON float')
    return value

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=pairs, parse_float=finite_float,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON token')))

def exclusive_json(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')

def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n', encoding='utf-8')

def safe_files(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Expected a real directory')
    result = []
    for base, dirs, files in os.walk(root, followlinks=False):
        for name in dirs:
            if (Path(base) / name).is_symlink():
                raise ValueError('Directory symlink is not allowed')
        for name in files:
            path = Path(base) / name
            if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
                raise ValueError('Nonregular input is not allowed')
            result.append(path)
    return sorted(result)

def bundle_binding(bundle):
    rows = []
    for path in safe_files(bundle):
        data = path.read_bytes()
        rows.append({'path':path.relative_to(bundle).as_posix(), 'bytes':len(data), 'sha256':hashlib.sha256(data).hexdigest()})
    total = sum(row['bytes'] for row in rows)
    if total > REPORT_LIMIT:
        raise ValueError('Fixture bundle exceeds1MiB')
    encoded = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    return {'sha256':hashlib.sha256(encoded).hexdigest(), 'bytes':total, 'files':rows}

def refresh_inventory(bundle):
    members = []
    for path in safe_files(bundle):
        relative = path.relative_to(bundle).as_posix()
        if relative == 'inventory.json':
            continue
        data = path.read_bytes()
        members.append({'path':relative, 'bytes':len(data), 'sha256':hashlib.sha256(data).hexdigest()})
    write_json(Path(bundle)/'inventory.json', {'members':members})

def verify_manifest(kit):
    manifest_path = kit/'KIT_MANIFEST.json'
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ValueError('KIT_MANIFEST.json is required; use only a sealed release kit')
    if manifest_path.stat().st_size>1048576:
        raise ValueError('Kit manifest exceeds1MiB')
    document = read(manifest_path)
    rows = document['files']
    if not isinstance(rows, list) or len(rows) > 5000:
        raise ValueError('Invalid or excessive kit manifest')
    if any(not isinstance(row,dict) or set(row)!={'path','bytes','sha256'} or type(row['bytes']) is not int or row['bytes']<0 or not isinstance(row['sha256'],str) or re.fullmatch('[a-f0-9]{64}',row['sha256']) is None for row in rows):
        raise ValueError('Manifest row type or hash syntax mismatch')
    if sum(row['bytes'] for row in rows)>67108864:
        raise ValueError('Sealed kit payload exceeds64MiB')
    expected = set()
    for row in rows:
        rel = row['path']
        if not isinstance(rel, str) or not rel or '\\' in rel or ':' in rel or rel.startswith('/') or any(p in ('', '.', '..') for p in rel.split('/')):
            raise ValueError('Unsafe manifest member')
        if rel == 'KIT_MANIFEST.json' or rel in expected:
            raise ValueError('Recursive or duplicate manifest member')
        expected.add(rel)
        path = kit/rel
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(kit.resolve()):
            raise ValueError('Missing or unsafe kit member: '+rel)
        if path.stat().st_size != row['bytes'] or sha(path) != row['sha256']:
            raise ValueError('Kit hash/size mismatch: '+rel)
    actual = set()
    for base, dirs, files in os.walk(kit, followlinks=False):
        dirs[:] = [d for d in dirs if d not in ('.git', '__pycache__')]
        for d in dirs:
            if (Path(base)/d).is_symlink():
                raise ValueError('Kit directory symlink')
        for name in files:
            if name.endswith(('.pyc', '.pyo')) or Path(base)/name == manifest_path:
                continue
            path = Path(base)/name
            if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
                raise ValueError('Nonregular kit member')
            actual.add(path.relative_to(kit).as_posix())
    if actual != expected:
        raise ValueError('Kit membership differs from sealed manifest')
    return {'status':'PASS_BYTES_ONLY', 'files':len(rows), 'manifest_sha256':sha(manifest_path), 'bindings':{row['path']:row['sha256'] for row in rows}}

def stop_child(process):
    """Kill a still-owned unreaped child/group; never signal a reaped PID."""
    signalled = False
    # returncode is set by poll only after reaping. If None, PID remains reserved
    # by this child (live or zombie), so no unrelated recycled group is signalled.
    if process.returncode is None:
        if os.name == 'posix':
            try:
                os.killpg(process.pid, signal.SIGKILL)
                signalled = True
            except ProcessLookupError:
                pass
        else:
            process.kill()
            signalled = True
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        raise ReviewStop('Direct child did not terminate within cleanup allowance')
    return {'direct_child_reaped':process.returncode is not None, 'kill_sent':signalled,
            'scope':'While owner PID was unreaped, POSIX process group KILL was permitted. A normally exited child is not signalled. Descendants after normal owner exit are not enumerated or certified.' if os.name=='posix' else 'Direct child only; Windows subtree cleanup unqualified.'}

def run_process(argv, directory, timeout, phase_deadline, report_path=None):
    """Record a bounded child observation. Output byte ceilings are sampled, not OS-hard limits."""
    directory = Path(directory)
    directory.mkdir(exist_ok=False)
    start = time.monotonic()
    stdout_path, stderr_path = directory/'stdout.txt', directory/'stderr.txt'
    reason = None
    with stdout_path.open('xb') as out, stderr_path.open('xb') as err:
        process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                   shell=False, start_new_session=(os.name == 'posix'))
        while True:
            now = time.monotonic()
            if STOP_REQUESTED:
                reason = 'STOP_REQUESTED'
            elif now >= phase_deadline:
                reason = 'PHASE_DEADLINE'
            elif now-start >= timeout:
                reason = 'CHILD_DEADLINE'
            elif stdout_path.stat().st_size > LOG_LIMIT or stderr_path.stat().st_size > LOG_LIMIT:
                reason = 'LOG_BYTE_LIMIT'
            elif report_path is not None and Path(report_path).exists() and Path(report_path).stat().st_size > REPORT_LIMIT:
                reason = 'REPORT_BYTE_LIMIT'
            if reason is not None or process.poll() is not None:
                break
            time.sleep(0.01)
        cleanup = stop_child(process)
    elapsed = time.monotonic()-start
    return {'argv':argv, 'exit_code':process.returncode, 'stop_reason':reason,
            'elapsed_seconds':elapsed, 'cleanup':cleanup,
            'stdout_bytes':stdout_path.stat().st_size, 'stdout_sha256':sha(stdout_path),
            'stderr_bytes':stderr_path.stat().st_size, 'stderr_sha256':sha(stderr_path),
            'byte_limit_scope':'Sampled with <=10ms nominal polling; not a hard filesystem or aggregate-tree limit.',
            'timing_scope':'Operational UNIT elapsed time, not an algorithm speed measurement.'}

def validate_report(report, case_id, invocation_id, arm):
    keys = {'schema','case_id','invocation_id','arm_id','obligation_vector','coverage_mask','aggregate','diagnostics'}
    obligations = {f'O{i:02d}' for i in range(1,17)}
    if not isinstance(report,dict) or set(report)!=keys or report['schema']!='nsc-p4-checker-report/2':
        raise ValueError('Report root/schema mismatch')
    if (report['case_id'],report['invocation_id'],report['arm_id'])!=(case_id,invocation_id,arm):
        raise ValueError('Report identity mismatch')
    vector,mask=report['obligation_vector'],report['coverage_mask']
    if not isinstance(vector,dict) or set(vector)!=obligations or any(type(v) is not str or v not in ('S','V','U') for v in vector.values()):
        raise ValueError('Report vector mismatch')
    if not isinstance(mask,dict) or set(mask)!=obligations or any(type(v) is not bool for v in mask.values()):
        raise ValueError('Report coverage mismatch')
    aggregate='REJECT' if 'V' in vector.values() else 'INDETERMINATE' if 'U' in vector.values() else 'ALLOW_WITHIN_SCOPE'
    if report['aggregate']!=aggregate or not isinstance(report['diagnostics'],list):
        raise ValueError('Report aggregate/diagnostics mismatch')
    required={'obligation_id','predicate_instance_id','kind','node_id','edge_id','path','json_pointer','reason_code','observed','expected','numerical_policy'}
    for d in report['diagnostics']:
        if not isinstance(d,dict) or not required<=set(d) or d['obligation_id'] not in obligations or d['kind'] not in ('DIRECT_VIOLATION','DEPENDENCY_U','NOT_EVALUATED_BY_ABLATION','SATISFIED'):
            raise ValueError('Report diagnostic shape mismatch')
        if not isinstance(d['predicate_instance_id'],str) or not isinstance(d['reason_code'],str) or not d['reason_code']:
            raise ValueError('Report diagnostic identifier mismatch')
        if any(d[k] is not None and not isinstance(d[k],str) for k in ('node_id','edge_id','path','json_pointer','numerical_policy')):
            raise ValueError('Report diagnostic locator type mismatch')
    for oid in obligations:
        if not mask[oid] and not any(d['kind']=='NOT_EVALUATED_BY_ABLATION' and d['obligation_id']==oid for d in report['diagnostics']):
            raise ValueError('Missing omission witness')
        if vector[oid]=='V' and not any(d['kind']=='DIRECT_VIOLATION' and d['obligation_id']==oid for d in report['diagnostics']):
            raise ValueError('Missing direct witness')
    return report

class Context:
    def __init__(self, kit, out, mode, phase_limit, child_limit, started):
        self.kit, self.out, self.mode = Path(kit), Path(out), mode
        self.phase_limit, self.child_limit = phase_limit, child_limit
        self.started, self.deadline = started, started+phase_limit
        self.counter, self.receipts = 0, []
        self.run_token=hashlib.sha256(str(self.out.resolve()).encode('utf-8')).hexdigest()[:16]
        self.profile = self.kit/'profiles/FIXED_PROFILE.json'
        self.profile_sha256 = sha(self.profile)
        (self.out/'fixtures').mkdir()
        (self.out/'attempts').mkdir()
    def __getitem__(self,key):
        if key not in ('kit','out','mode','invoke','make_bundle','refresh_inventory'):
            raise KeyError(key)
        return getattr(self,key)
    def get(self,key,default=None):
        try:
            return self[key]
        except KeyError:
            return default
    def budget(self):
        if STOP_REQUESTED:
            raise ReviewStop('STOP_REQUESTED')
        if time.monotonic() >= self.deadline:
            raise ReviewStop('PHASE_DEADLINE')
        total = sum(p.stat().st_size for p in self.out.rglob('*') if p.is_file() and not p.is_symlink())
        if total > OUTPUT_LIMIT:
            raise ReviewStop('OUTPUT_BYTE_LIMIT')
    def make_bundle(self, workflow, label):
        self.budget()
        if workflow not in ('W1', 'W2'):
            raise ValueError('Unsupported UNIT workflow')
        slug = re.sub('[^A-Za-z0-9_-]', '-', str(label))[:90]
        if not slug:
            raise ValueError('Fixture label is empty')
        target = self.out/'fixtures'/f'P5UNIT-{workflow}-{slug}'
        source=self.kit/'examples'/workflow
        if source.is_symlink():
            raise ValueError('Example root symlink')
        ignored=shutil.ignore_patterns('.git','__pycache__','*.pyc','*.pyo')
        for base,dirs,files in os.walk(source,followlinks=False):
            skip=ignored(base,dirs+files)
            dirs[:]=[name for name in dirs if name not in skip]
            for name in dirs+[f for f in files if f not in skip]:
                path=Path(base)/name
                if path.is_symlink():
                    raise ValueError('Nonignored example symlink')
        shutil.copytree(source,target,ignore=ignored)
        return target
    @staticmethod
    def refresh_inventory(bundle):
        refresh_inventory(Path(bundle))
    def identity(self, workflow, arm, label, counter):
        slug=re.sub('[^A-Za-z0-9_-]', '-', str(label))[:90]
        case_id=f'P5UNIT-{self.run_token}-{workflow}-{slug}'
        return case_id,f'{case_id}__{arm}__U{counter:04d}__A001'
    def invoke(self, bundle, workflow, arm, label, expected_exit=0, extra_args=None):
        self.budget()
        if arm not in ARMS or workflow not in ('W1','W2'):
            raise ValueError('Unknown arm/workflow')
        bundle = Path(bundle).resolve()
        before = bundle_binding(bundle)
        self.counter += 1
        case_id,invocation_id=self.identity(workflow,arm,label,self.counter)
        directory = self.out/'attempts'/invocation_id
        result_path = directory/'result.json'
        checker = self.kit/'checkers'/('b_assert' if arm=='B_ASSERT' else 't_full')/'checker.py'
        checker_sha = sha(checker)
        argv = [sys.executable,'-I','-B',str(checker),'--case-bundle',str(bundle),'--profile',str(self.profile),
                '--case-id',case_id,'--invocation-id',invocation_id,'--arm-id',arm,'--output',str(result_path)]
        if extra_args:
            argv += list(extra_args)
        observation = run_process(argv, directory, min(self.child_limit, max(0.001,self.deadline-time.monotonic())), self.deadline, result_path)
        report, report_error = None, None
        if result_path.exists():
            try:
                if result_path.is_symlink() or result_path.stat().st_size > REPORT_LIMIT:
                    raise ValueError('Unsafe/oversize result')
                report = read(result_path)
                validate_report(report,case_id,invocation_id,arm)
            except (ValueError,OSError,RecursionError) as exc:
                report_error = type(exc).__name__+':'+str(exc)
        if observation['stop_reason']:
            status = 'STOP_RETAINED'
        elif observation['exit_code'] != expected_exit:
            status = 'EXPECTED_EXIT_MISMATCH'
        elif expected_exit == 0 and (report is None or report_error):
            status = 'REPORT_INVALID'
        else:
            status = 'COMPLETED' if expected_exit==0 else 'CONTROLLED_NEGATIVE_COMPLETED'
        after = bundle_binding(bundle)
        if after != before or sha(checker)!=checker_sha or sha(self.profile)!=self.profile_sha256:
            status = 'INPUT_OR_SOURCE_DRIFT'
        receipt = {'schema':'nsc-p5-unit-invocation/1','case_id':case_id,'invocation_id':invocation_id,'arm_id':arm,
                   'execution_status':status, 'run_token':self.run_token, 'expected_exit':expected_exit, **observation,
                   'report_error':report_error, 'report_sha256':sha(result_path) if result_path.is_file() else None,
                   'source_sha256':checker_sha,'profile_sha256':self.profile_sha256,'bundle':before,
                   'input_unchanged':after==before,'interpreter':str(Path(sys.executable).resolve()),
                   'interpreter_sha256':sha(Path(sys.executable).resolve())}
        exclusive_json(directory/'receipt.json',receipt)
        self.receipts.append({'invocation_id':invocation_id,'receipt_path':str((directory/'receipt.json').relative_to(self.out)),
                              'receipt_sha256':sha(directory/'receipt.json'),'execution_status':status})
        if observation['stop_reason']:
            raise ReviewStop(observation['stop_reason'])
        return {'report':report,'receipt':receipt,'result_path':result_path}

def load_suite(path, name, expected_sha256=None):
    # Compile the exact verified source bytes. SourceFileLoader may execute an
    # unmanifested timestamp-valid pyc even when dont_write_bytecode is true.
    source = Path(path).read_bytes()
    if expected_sha256 is not None and hashlib.sha256(source).hexdigest()!=expected_sha256:
        raise ValueError('Suite source differs from sealed manifest')
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = ''
    exec(compile(source,str(path),'exec'),module.__dict__)
    return module


def stop_signal(signum, frame):
    global STOP_REQUESTED
    STOP_REQUESTED = True

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mode', choices=('smoke','full'), required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--phase-limit',type=float)
    ap.add_argument('--child-limit',type=float,default=5.)
    ap.add_argument('--unsealed-development', action='store_true', help='Internal pre-seal controls only; not the release reviewer path')
    args = ap.parse_args()
    started = time.monotonic()
    limit = args.phase_limit if args.phase_limit is not None else (300. if args.mode=='smoke' else 1800.)
    if not 0 < limit <= (300. if args.mode=='smoke' else 1800.) or not 0 < args.child_limit <= 5:
        ap.error('Limits must be positive and may only lower the fixed caps')
    out = args.out.absolute()
    if out.resolve().is_relative_to(KIT.resolve()):
        ap.error('Output must be outside the sealed kit')
    if out.exists() or out.is_symlink():
        ap.error('Output path exists; evidence is never overwritten')
    out.mkdir(parents=True, exist_ok=False)
    exclusive_json(out/'COMMAND.json',{'argv':[sys.executable]+sys.argv,'mode':args.mode,'phase_limit_seconds':limit,'child_limit_seconds':args.child_limit})
    exclusive_json(out/'ENVIRONMENT.json',{'python':sys.version,'executable':str(Path(sys.executable).resolve()),'invoked_executable':sys.executable,'clock':'time.monotonic','suspend_boundary':'No suspend-inclusive clock guarantee; elapsed runtime is not a production time-budget certification.','interpreter_sha256':sha(Path(sys.executable).resolve()),'platform':platform.platform(),'machine':platform.machine(),'implementation':platform.python_implementation(),'isolated_flag':sys.flags.isolated,'no_site_flag':sys.flags.no_site,'prefix':sys.prefix,'base_prefix':sys.base_prefix,'stdlib_only_expected':True,'scope':'This records one actual environment. No clean-OS, different-version or native-Windows execution is implied.'})
    checks, issue, context, seal = [], None, None, None
    old = {}
    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            old[sig] = signal.signal(sig,stop_signal)
        if not sys.platform.startswith('linux') or not all(hasattr(os,k) for k in ('O_NOFOLLOW','O_EXCL','killpg','setsid')):
            raise ValueError('SUPPORTED_HOST_REQUIRED: Linux with O_NOFOLLOW, O_EXCL and process-group controls; other OS profiles are not qualified')
        seal = {'status':'UNSEALED_DEVELOPMENT_ONLY'} if args.unsealed_development else verify_manifest(KIT)
        context = Context(KIT,out,args.mode,limit,args.child_limit,started)
        probe_code='import sys,json;print(json.dumps({"executable":sys.executable,"prefix":sys.prefix,"base_prefix":sys.base_prefix,"isolated":sys.flags.isolated,"sys_path":sys.path}))'
        probe=run_process([sys.executable,'-I','-B','-c',probe_code],out/'environment_probe',min(5.,max(.001,context.deadline-time.monotonic())),context.deadline)
        exclusive_json(out/'environment_probe/OBSERVATION.json',probe)
        if probe['stop_reason'] or probe['exit_code']!=0:
            raise ReviewStop('ENVIRONMENT_PROBE_FAILED')
        child_environment=read(out/'environment_probe/stdout.txt')
        exclusive_json(out/'CHILD_ENVIRONMENT.json',child_environment)
        core = load_suite(KIT/'tests/core_claims.py','nsc_p5_core_claims',seal.get('bindings',{}).get('tests/core_claims.py'))
        checks.extend(core.run_suite(context, args.mode))
        alias = load_suite(KIT/'tests/alias_contract.py','nsc_p5_alias_contract',seal.get('bindings',{}).get('tests/alias_contract.py'))
        checks.extend(alias.run_suite(context))
        context.budget()
        if not args.unsealed_development:
            verify_manifest(KIT)
    except (ReviewStop, OSError, ValueError, ImportError, KeyError, TypeError, AssertionError) as exc:
        issue = type(exc).__name__+':'+str(exc)
    finally:
        for sig, handler in old.items():
            signal.signal(sig,handler)
    elapsed = time.monotonic()-started
    valid = all(c.get('ok') is True for c in checks)
    completed = context is not None and all(r['execution_status'] in ('COMPLETED','CONTROLLED_NEGATIVE_COMPLETED') for r in context.receipts)
    status = 'PASS_UNIT_REVIEW' if checks and valid and completed and issue is None else 'FAIL_RETAINED'
    summary = {'schema':'nsc-p5-reviewer-summary/1','status':status,'mode':args.mode,'elapsed_seconds':elapsed,
               'phase_limit_seconds':limit,'child_limit_seconds':args.child_limit,'issue':issue,
               'passed':sum(c.get('ok') is True for c in checks),'total':len(checks),'checks':checks,
               'manifest':seal,'run_token':context.run_token if context else None,'invocations':context.receipts if context else [],
               'candidate_invocations':len(context.receipts) if context else 0,
               'no_retry':True,'clock':'time.monotonic','environment_probe_count':1 if (out/'CHILD_ENVIRONMENT.json').exists() else 0,'execution_domain':'Deterministic fresh P5UNIT synthetic checks only. No P4 identity is executed.',
               'limits':'Cooperative phase/child monotonic deadlines, with up to2s child reap allowance and final evidence-write overhead; no suspend-inclusive guarantee; sampled output byte limits. No production resume, host-death survival or complete process-tree RSS claim.',
               'main_benchmark':'Not rerun; original P4 conformance FAIL_CLOSED is unchanged.'}
    exclusive_json(out/'SUMMARY.json',summary)
    print(json.dumps({k:summary[k] for k in ('status','passed','total','candidate_invocations','elapsed_seconds','issue')}))
    return 0 if status=='PASS_UNIT_REVIEW' else 1

if __name__=='__main__':
    raise SystemExit(main())
