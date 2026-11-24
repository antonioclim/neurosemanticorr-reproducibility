#!/usr/bin/env python3
"""Bind Figure 4 to retained scope reports and replayed reference-audit certificates."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import sys
sys.dont_write_bytecode=True

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')

def main():
 p=argparse.ArgumentParser();p.add_argument('--software',type=Path,required=True,help='Root of the extracted software distribution containing r5_f3');p.add_argument('--f2-math',type=Path);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);a=p.parse_args()
 out=a.root/'04_sources/reference_audit';out.mkdir(parents=True,exist_ok=True)
 repo=a.software.resolve();runtime=repo/'r5_f3/reference_audit'
 frozen={str(x.relative_to(runtime)):sha(x) for x in runtime.rglob('*') if x.is_file()}
 sys.path.insert(0,str(repo.resolve()))
 from r5_f3.reference_audit.canonical_query import canonical_query_minimum
 scope_out=out/'REFERENCE_SCOPE_COMPARISON_F3.json';scope_in=scope_out
 scope=json.loads(scope_out.read_text());assert scope['status']=='PASS' and scope['budget']==0
 math_out=out/'MATH_CHECK_RESULTS_F2.json'
 if a.f2_math is not None and a.f2_math.resolve()!=math_out.resolve():shutil.copy2(a.f2_math,math_out)
 math=json.loads(math_out.read_text())['retained_frame']
 historical={r['k']:r['minimum_queries'] for r in math['robust_query_minima_k_0_to_7']}
 boundary=math['exact_boundary_result_k_8'];historical[boundary['k']]=boundary['minimum_queries']
 points=[];certificates=[];bindings=[{'path':scope_out.name,'sha256':sha(scope_out),'origin':scope_out.name},{'path':math_out.name,'sha256':sha(math_out),'origin':math_out.name}]
 for label,example in [('restricted','canonical_restricted_k0.json'),('broad','canonical_broad_k7.json')]:
  base_in=runtime/'examples'/example;base_out=out/('BASE_REQUEST_'+label+'.json');shutil.copy2(base_in,base_out)
  base=json.loads(base_out.read_text());bindings.append({'path':base_out.name,'sha256':sha(base_out),'origin':str(base_in.relative_to(repo))})
  for k in sorted(historical):
   request=deepcopy(base);request['budget']=k
   certificate=canonical_query_minimum(request)
   assert certificate['status']=='VERIFIED_CANONICAL_MINIMUM'
   assert certificate['minimum_query_count']==historical[k]
   assert certificate['threshold']=='24'
   name=f'QUERY_{label.upper()}_K{k}.json';dest=out/name;dump(dest,certificate)
   row={'budget':certificate['budget'],'minimum_queries':certificate['minimum_query_count'],'admissibility':certificate['admissibility'],'certificate_file':name,'certificate_sha256':sha(dest),'request_sha256':certificate['request_sha256']}
   certificates.append(row)
   if label=='restricted':points.append(row)
 counts={}
 for branch in ['S','V']:
  counts[branch]={}
  for model in ['global_engine','contextwise_engine','casewise_product_comparator']:
   item=scope['branches'][branch][model]
   counts[branch][model]={'lower':int(item['interval']['lower']),'upper':int(item['interval']['upper'])}
 assert frozen=={str(x.relative_to(runtime)):sha(x) for x in runtime.rglob('*') if x.is_file()},'Reference-audit runtime altered'
 result={'schema':'nsc-r5-f4-figure4-data/1','panel_a':{'budget':scope['budget'],'conflict_query_case_id':scope['conflict_query_case_id'],'global_centres':scope['branches']['S']['global_engine']['joint_centres'],'contextwise_centres':scope['branches']['S']['contextwise_engine']['joint_centres'],'intervals':counts,'full_casewise_engine_invocation':False,'method':scope['branches']['S']['casewise_product_comparator']['method']},'panel_b':{'frame_size':len(base['matrix']['payload']['cases']),'threshold':int(base['threshold']),'model_scope':base['model_scope']['kind'],'prior_observations':len(base['observations']),'points':points,'both_admissibility_choices_equal':all([r['minimum_queries'] for r in certificates if r['admissibility']==kind]==[r['minimum_queries'] for r in points] for kind in ['restricted_local_prediction_union','broad_S_V_U']),'all_certificates':certificates},'source_bindings':bindings,'scope':'Exact finite-model calculations, not confidence intervals or new prospective observations.'}
 dump(a.root/'04_sources/FIGURE4_DATA.json',result)
 dump(out/'F4_CERTIFICATE_REPLAY.json',{'status':'PASS_18_REPLAYED_F3_QUERY_CERTIFICATES','runtime_unchanged':True,'runtime_source_sha256':frozen,'certificate_count':len(certificates),'legacy_F2_point_match':True,'baseline_F3_version':'1.0.0','current_driver_sha256':sha(Path(__file__)),'original_checker_invocations':0,'new_prospective_observations':0})
 print(json.dumps({'status':'PASS','query_minima':[r['minimum_queries'] for r in points],'scope_report_sha256':sha(scope_out),'data_sha256':sha(a.root/'04_sources/FIGURE4_DATA.json')},indent=2))

if __name__=='__main__':main()
