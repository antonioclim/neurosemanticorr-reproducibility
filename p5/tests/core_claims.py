"""Literal and metamorphic P5 checks; never imports either checker implementation."""
from pathlib import Path
import hashlib
import json

PRIMARY = ('T_FULL','B_ASSERT')
OBLIGATIONS = tuple(f'O{i:02d}' for i in range(1,17))

def get(bundle,path):
    return json.loads((Path(bundle)/path).read_text(encoding='utf-8'))

def put(bundle,path,value):
    (Path(bundle)/path).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n',encoding='utf-8')

def require_report(value):
    if value['receipt']['execution_status']!='COMPLETED' or not isinstance(value['report'],dict):
        raise AssertionError('A semantic fixture did not complete with a valid report: '+value['receipt']['execution_status'])
    return value['report']

def all_s(report):
    return report['aggregate']=='ALLOW_WITHIN_SCOPE' and report['obligation_vector']=={o:'S' for o in OBLIGATIONS} and all(report['coverage_mask'].values())

def diagnostics_at(report, oid, path, pointer):
    return any(d['kind']=='DIRECT_VIOLATION' and d['obligation_id']==oid and d['path']==path and d['json_pointer']==pointer for d in report['diagnostics'])

def rational_scale(value, factor):
    if isinstance(value,dict):
        if set(value)=={'numerator','denominator'}:
            return {'numerator':value['numerator']*factor,'denominator':value['denominator']*factor}
        return {k:rational_scale(v,factor) for k,v in value.items()}
    if isinstance(value,list):
        return [rational_scale(v,factor) for v in value]
    return value

def run_suite(context, mode):
    checks=[]
    def check(name,ok,detail):
        checks.append({'id':'CORE_'+name,'ok':bool(ok),'detail':detail})
    def invoke(bundle,w,arm,label):
        return require_report(context.invoke(bundle,w,arm,label))
    clean={}
    for w in ('W1','W2'):
        bundle=context.make_bundle(w,'CORE-CLEAN')
        for arm in PRIMARY:
            r=invoke(bundle,w,arm,'CORE-CLEAN-'+arm)
            clean[(w,arm)]=r
            check(w+'_CLEAN_'+arm,all_s(r),{'expected':'all16S','vector':r['obligation_vector']})
    expected_coverage={'A0_SYNTAX':0,'A1_STRUCTURE':0,'A2_LOCAL':3,'A3_PROVENANCE':10}
    bundle=context.make_bundle('W1','CORE-ABLATIONS')
    for arm,n in expected_coverage.items():
        r=invoke(bundle,'W1',arm,'CORE-ABLATIONS-'+arm)
        omitted={d['obligation_id'] for d in r['diagnostics'] if d['kind']=='NOT_EVALUATED_BY_ABLATION'}
        incomplete={o for o in OBLIGATIONS if not r['coverage_mask'][o]}
        check('ABLATION_'+arm,sum(r['coverage_mask'].values())==n and r['aggregate']=='INDETERMINATE' and 'V' not in r['obligation_vector'].values() and incomplete<=omitted,
              {'fully_covered_obligations':sum(r['coverage_mask'].values()),'expected':n,'aggregate':r['aggregate']})
    if mode=='smoke':
        return checks
    for arm in PRIMARY:
        # A declarative contradiction independent of all numerical values.
        b=context.make_bundle('W1','CORE-OPERATION-'+arm);x=get(b,'records/R10_design_profile.json');x['causal_claim']=True;put(b,'records/R10_design_profile.json',x);context.refresh_inventory(b)
        r=invoke(b,'W1',arm,'CORE-OPERATION-'+arm)
        check('OPERATION_'+arm,r['obligation_vector']['O10']=='V' and r['aggregate']=='REJECT',{'target':'O10','vector':r['obligation_vector']})
        # Missing scientific relation is U, while readable inventory closure is V.
        b=context.make_bundle('W1','CORE-MISSING-'+arm);(b/'records/R09_estimand.json').unlink();context.refresh_inventory(b)
        r=invoke(b,'W1',arm,'CORE-MISSING-'+arm)
        check('MISSING_'+arm,r['obligation_vector']['O09']=='U' and r['obligation_vector']['O02']=='V',{'target_U':'O09','custody_V':'O02','vector':r['obligation_vector']})
        # Boolean is not an integer count.
        b=context.make_bundle('W1','CORE-BOOL-'+arm);x=get(b,'records/R13.json');x['reported_attempted_denominator']=True;put(b,'records/R13.json',x);context.refresh_inventory(b)
        r=invoke(b,'W1',arm,'CORE-BOOL-'+arm)
        check('BOOL_NOT_INT_'+arm,r['obligation_vector']['O01']=='V' and diagnostics_at(r,'O01','records/R13.json','/reported_attempted_denominator'),{'expected_pointer':'/reported_attempted_denominator'})
        # Duplicate-key and nonfinite admission use actual field/token pointers.
        b=context.make_bundle('W1','CORE-DUPKEY-'+arm);v=get(b,'records/R01.json')['semantic_digest'];raw=json.dumps(v,separators=(',',':'));(b/'records/R01.json').write_text('{"semantic_digest":'+raw+',"semantic_digest":'+raw+'}\n');context.refresh_inventory(b)
        r=invoke(b,'W1',arm,'CORE-DUPKEY-'+arm)
        check('DUPLICATE_KEY_'+arm,r['obligation_vector']['O01']=='V' and diagnostics_at(r,'O01','records/R01.json','/semantic_digest'),{'expected_pointer':'/semantic_digest'})
        b=context.make_bundle('W1','CORE-NONFINITE-'+arm);x=get(b,'records/R13.json');x['tasks'][0]['status']=float('nan');(b/'records/R13.json').write_text(json.dumps(x,separators=(',',':'))+'\n');context.refresh_inventory(b)
        r=invoke(b,'W1',arm,'CORE-NONFINITE-'+arm)
        check('NONFINITE_'+arm,r['obligation_vector']['O01']=='V' and diagnostics_at(r,'O01','records/R13.json','/tasks/0/status'),{'expected_pointer':'/tasks/0/status'})
        # A retained rational denominator may not be zero.
        b=context.make_bundle('W2','CORE-RATIONAL-ZERO-'+arm);x=get(b,'records/R11_result.json');x['values']['ratio']['denominator']=0;put(b,'records/R11_result.json',x);context.refresh_inventory(b)
        r=invoke(b,'W2',arm,'CORE-RATIONAL-ZERO-'+arm)
        check('RATIONAL_ZERO_'+arm,r['obligation_vector']['O01']=='V' and diagnostics_at(r,'O01','records/R11_result.json','/values/ratio/denominator'),{'expected_pointer':'/values/ratio/denominator'})
        # Multiplying rational components preserves the exact represented values.
        for factor in (2,3):
            b=context.make_bundle('W2',f'CORE-NONREDUCED-{factor}-'+arm)
            for path in ('records/R11_result.json','records/R12_consumer.json','records/R15_claims.json'):
                put(b,path,rational_scale(get(b,path),factor))
            context.refresh_inventory(b);r=invoke(b,'W2',arm,f'CORE-NONREDUCED-{factor}-'+arm)
            check(f'NONREDUCED_{factor}_'+arm,all_s(r),{'factor':factor,'vector':r['obligation_vector']})
        # Whitespace and object order are presentation only; raw inventory is refreshed.
        b=context.make_bundle('W1','CORE-REFORMAT-'+arm)
        def reverse_keys(x):
            if isinstance(x,dict):return {k:reverse_keys(x[k]) for k in reversed(list(x))}
            if isinstance(x,list):return [reverse_keys(v) for v in x]
            return x
        for path in b.rglob('*.json'):
            if path.name!='inventory.json':path.write_text(json.dumps(reverse_keys(json.loads(path.read_text())),ensure_ascii=False,indent=3)+'\n',encoding='utf-8')
        context.refresh_inventory(b);r=invoke(b,'W1',arm,'CORE-REFORMAT-'+arm)
        check('REFORMAT_'+arm,all_s(r) and r['obligation_vector']==clean[('W1',arm)]['obligation_vector'],{'invariant':'canonical semantic values, refreshed raw inventory'})
        # Optional notes are explicitly admitted, not arbitrary membership.
        b=context.make_bundle('W1','CORE-OPTIONAL-'+arm);(b/'notes').mkdir(exist_ok=True);(b/'notes/README.txt').write_text('P5UNIT documentary note.\n');context.refresh_inventory(b)
        r=invoke(b,'W1',arm,'CORE-OPTIONAL-'+arm);check('OPTIONAL_NOTE_'+arm,all_s(r),{'vector':r['obligation_vector']})
        b=context.make_bundle('W1','CORE-STALE-INVENTORY-'+arm);(b/'records/R02_aux.txt').write_text('Changed UNIT documentary bytes.\n')
        r=invoke(b,'W1',arm,'CORE-STALE-INVENTORY-'+arm);check('STALE_INVENTORY_'+arm,r['obligation_vector']['O02']=='V',{'target':'O02'})
        # Nonfinite arithmetic is typed undefined, not a spurious zero.
        b=context.make_bundle('W2','CORE-ZERO-DIVISION-'+arm);x=get(b,'records/R11_result.json');row=x['operands']['rows'][0];row['total.rev']=0;x['values']['turnover_ratio'][row['id']]={'status':'UNDEFINED','reason':'ZERO_DENOMINATOR'};put(b,'records/R11_result.json',x);c=get(b,'records/R12_consumer.json');c['values']=x['values'];put(b,'records/R12_consumer.json',c);context.refresh_inventory(b)
        r=invoke(b,'W2',arm,'CORE-ZERO-DIVISION-'+arm);check('ZERO_DIVISION_UNDEFINED_'+arm,all_s(r),{'vector':r['obligation_vector']})
        # Empty and repeated support have literal counts, not an invented mean.
        for empty in (True,False):
            label='CORE-EMPTY-SUPPORT-' if empty else 'CORE-REPEATED-SUPPORT-'
            b=context.make_bundle('W1',label+arm);x=get(b,'records/R11_result.json');labels=[] if empty else ['Not ready at all','Not ready at all'];x['operands']['selected_labels']=labels
            x['values']['denominator']=len(labels)
            for category in x['values']['counts']:
                count=0 if empty else (2 if category=='Not ready at all' else 0)
                x['values']['counts'][category]=count
                x['values']['proportions'][category]={'status':'UNDEFINED','reason':'EMPTY_SUPPORT'} if empty else {'numerator':count,'denominator':2}
            put(b,'records/R11_result.json',x);c=get(b,'records/R12_consumer.json');c['values']=x['values'];put(b,'records/R12_consumer.json',c)
            if empty:
                c=get(b,'records/R15_claims.json');c['claims'][0]['value']=0;c['claims'][0]['denominator']=0;put(b,'records/R15_claims.json',c)
                e=get(b,'records/R15_edges.json')
                for m in e['field_metadata'].values():m['denominator']=0
                put(b,'records/R15_edges.json',e)
            context.refresh_inventory(b);r=invoke(b,'W1',arm,label+arm)
            check(('EMPTY_SUPPORT_' if empty else 'REPEATED_SUPPORT_')+arm,all_s(r),{'literal_retained_denominator':len(labels),'vector':r['obligation_vector']})
        # Exact local arithmetic and consumer consistency are distinct obligations.
        b=context.make_bundle('W2','CORE-PROPAGATED-ERROR-'+arm);x=get(b,'records/R11_result.json');x['values']['ratio']={'numerator':5,'denominator':25};put(b,'records/R11_result.json',x);c=get(b,'records/R12_consumer.json');c['values']=x['values'];put(b,'records/R12_consumer.json',c);context.refresh_inventory(b)
        r=invoke(b,'W2',arm,'CORE-PROPAGATED-ERROR-'+arm);check('PROPAGATED_ERROR_'+arm,r['obligation_vector']['O11']=='V' and r['obligation_vector']['O12']=='S',{'expected':'O11V,O12S','vector':r['obligation_vector']})
        # Known local state contradiction survives an unavailable separate premise.
        b=context.make_bundle('W1','CORE-COMPOUND-'+arm);x=get(b,'data/rows.json');x['rows'][0]['readiness']='NOT-A-CATEGORY';put(b,'data/rows.json',x);(b/'data/states_or_change_facts.json').unlink();context.refresh_inventory(b)
        r=invoke(b,'W1',arm,'CORE-COMPOUND-'+arm);check('COMPOUND_LOCAL_V_'+arm,r['obligation_vector']['O07']=='V',{'target':'O07','vector':r['obligation_vector']})
        # Invalid header context must yield a report, not an unhashable-key crash.
        b=context.make_bundle('W1','CORE-HEADER-'+arm);x=get(b,'bundle.json');x['workflow']=[];put(b,'bundle.json',x);context.refresh_inventory(b)
        r=invoke(b,'W1',arm,'CORE-HEADER-'+arm);check('INVALID_HEADER_'+arm,r['obligation_vector']['O01']=='V' and r['obligation_vector']['O03']=='U' and diagnostics_at(r,'O01','bundle.json','/workflow'),{'vector':r['obligation_vector']})
        # CLI collision cannot overwrite a prior file.
        b=context.make_bundle('W1','CORE-COLLISION-'+arm);target=context.out/('retained-'+arm+'.json');target.write_bytes(b'{"retained":true}\n');before=hashlib.sha256(target.read_bytes()).hexdigest()
        v=context.invoke(b,'W1',arm,'CORE-COLLISION-'+arm,expected_exit=2,extra_args=['--output',str(target)])
        check('CLI_COLLISION_'+arm,v['receipt']['execution_status']=='CONTROLLED_NEGATIVE_COMPLETED' and hashlib.sha256(target.read_bytes()).hexdigest()==before,{'original_bytes_preserved':True})
        b=context.make_bundle('W1','CORE-BAD-ARM-'+arm);v=context.invoke(b,'W1',arm,'CORE-BAD-ARM-'+arm,expected_exit=2,extra_args=['--arm-id','P5UNIT-UNKNOWN-ARM'])
        check('CLI_INVALID_ARM_'+arm,v['receipt']['execution_status']=='CONTROLLED_NEGATIVE_COMPLETED',{'expected_exit':2})
    return checks
