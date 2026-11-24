#!/usr/bin/env python3
"""Plot the retained exact reference-model results and create native ODG objects."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from build_draw_figures import build_native

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);a=p.parse_args();root=a.root
 (root/'01_editable_odg').mkdir(parents=True,exist_ok=True);(root/'05_validation').mkdir(parents=True,exist_ok=True)
 data_path=root/'04_sources/FIGURE4_DATA.json';data=json.loads(data_path.read_text())
 for b in data['source_bindings']:
  path=root/'04_sources/reference_audit'/b['path'];assert sha256(path.read_bytes()).hexdigest()==b['sha256']
 scope=json.loads((root/'04_sources/reference_audit/REFERENCE_SCOPE_COMPARISON_F3.json').read_text())
 assert scope['status']=='PASS'
 assert data['panel_a']['budget']==scope['budget']
 assert data['panel_a']['conflict_query_case_id']==scope['conflict_query_case_id']
 assert data['panel_a']['global_centres']==scope['branches']['S']['global_engine']['joint_centres']
 assert data['panel_a']['contextwise_centres']==scope['branches']['S']['contextwise_engine']['joint_centres']
 for branch in ['S','V']:
  for model in ['global_engine','contextwise_engine','casewise_product_comparator']:
   expected={key:int(value) for key,value in scope['branches'][branch][model]['interval'].items()}
   assert data['panel_a']['intervals'][branch][model]==expected
 for r in data['panel_b']['all_certificates']:
  f=root/'04_sources/reference_audit'/r['certificate_file'];assert sha256(f.read_bytes()).hexdigest()==r['certificate_sha256']
  result=json.loads(f.read_text());assert result['minimum_query_count']==r['minimum_queries'] and result['budget']==r['budget']
 assert data['panel_b']['both_admissibility_choices_equal']
 restricted=[r for r in data['panel_b']['all_certificates'] if r['admissibility']=='restricted_local_prediction_union']
 broad=[r for r in data['panel_b']['all_certificates'] if r['admissibility']=='broad_S_V_U']
 assert data['panel_b']['points']==restricted
 assert [(r['budget'],r['minimum_queries']) for r in restricted]==[(r['budget'],r['minimum_queries']) for r in broad]
 request=json.loads((root/'04_sources/reference_audit/BASE_REQUEST_restricted.json').read_text())
 assert data['panel_b']['frame_size']==len(request['matrix']['payload']['cases'])
 assert data['panel_b']['threshold']==int(request['threshold'])
 assert data['panel_b']['prior_observations']==len(request['observations'])==0
 assert data['panel_b']['model_scope']==request['model_scope']['kind']=='global'
 assert all(c['weight']=='1' and c['exception_eligible'] for c in request['matrix']['payload']['cases'])
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.titlesize':10.5,'axes.labelsize':9,'xtick.labelsize':8.5,'ytick.labelsize':9,'svg.fonttype':'none','pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.7,'savefig.facecolor':'white'})
 fig=plt.figure(figsize=(174/25.4,145/25.4))
 ax=fig.add_axes([.265,.565,.69,.32]); bx=fig.add_axes([.135,.135,.82,.29])
 fig.text(.035,.965,'A  Reference bounds by coherence scope',fontsize=11,fontweight='bold',va='top')
 fig.text(.265,.918,'One conflict query, no departures (k = 0)',fontsize=8.7)
 specs=[('global_engine',f"Global\n({data['panel_a']['global_centres']} centres)"),('contextwise_engine',f"Contextwise\n({data['panel_a']['contextwise_centres']} centres)"),('casewise_product_comparator','Full casewise\nprediction product')]
 colours={'S':'#0072b2','V':'#d55e00'}; objects=[]
 for i,(scope,label) in enumerate(specs):
  cy=2-i
  for branch,dy in [('S',.19),('V',-.19)]:
   row=data['panel_a']['intervals'][branch][scope];lo,hi=row['lower'],row['upper'];y=cy+dy
   line=ax.plot([lo,hi],[y,y],color=colours[branch],linewidth=2.0,marker='o' if branch=='S' else 's',markersize=3.8,solid_capstyle='butt')[0]
   line.set_gid(f'F4_INTERVAL_{scope}_{branch}')
   text=ax.text((lo+hi)/2,y+(0.13 if branch=='S' else -.13),f'[{lo}, {hi}]',ha='center',va='bottom' if branch=='S' else 'top',fontsize=8.5,color=colours[branch])
   text.set_gid(f'F4_BOUND_LABEL_{scope}_{branch}')
   objects.append({'id':line.get_gid(),'scope':scope,'branch':branch,'x_values':[lo,hi],'y_values':[y,y],'label':f'[{lo}, {hi}]'})
 ax.set_ylim(-.6,2.6);ax.set_xlim(-2,50);ax.set_yticks([2,1,0],[r[1] for r in specs]);ax.tick_params(axis='y',length=0,pad=10)
 ax.spines['left'].set_visible(False);ax.set_xticks([0,8,16,24,32,40,48]);ax.grid(axis='x',color='#e0e3e5',linewidth=.6);ax.set_axisbelow(True)
 ax.set_xlabel('Shared-error count C',labelpad=5)
 legend=[Line2D([0],[0],color=colours['S'],lw=1.5,marker='o',markersize=3.8,label='Stipulated S'),Line2D([0],[0],color=colours['V'],lw=1.5,marker='s',markersize=3.8,label='Stipulated V')]
 ax.legend(handles=legend,loc='lower right',bbox_to_anchor=(1,1.005),frameon=False,ncols=2,fontsize=8.5,borderaxespad=0,columnspacing=1.2)
 fig.text(.035,.485,'B  Minimum queries for the threshold decision',fontsize=11,fontweight='bold',va='top')
 rows=data['panel_b']['points'];k=[r['budget'] for r in rows];q=[r['minimum_queries'] for r in rows]
 blue=bx.plot(k,q,color='#0072b2',lw=1,marker='o',markersize=5,markerfacecolor='white',label='Local prediction union')[0];blue.set_gid('F4_QMIN_RESTRICTED')
 orange=bx.plot(k,q,color='#d55e00',linestyle='none',marker='x',markersize=4,markeredgewidth=1,label='S/V/U admissibility')[0];orange.set_gid('F4_QMIN_BROAD')
 for x,y in zip(k,q,strict=True):
  txt=bx.text(x,y+1.4,str(y),ha='center',va='bottom',fontsize=8.5);txt.set_gid(f'F4_QMIN_LABEL_K{x}')
 bx.set_xlim(-.35,max(k)+.35);bx.set_ylim(0,38);bx.set_xticks(k);bx.set_yticks([0,8,16,24,32]);bx.grid(axis='y',color='#e0e3e5',linewidth=.6);bx.set_axisbelow(True)
 bx.set_xlabel('Departure budget k',labelpad=5);bx.set_ylabel('Minimum fixed queries',labelpad=6)
 bx.legend(loc='upper left',frameon=False,fontsize=8.5,handletextpad=.6,borderaxespad=.2)
 fig.text(.135,.035,f"{data['panel_b']['frame_size']} cases, unit weights, K = {data['panel_b']['threshold']}; all positions eligible",fontsize=8.5)
 stem=root/'04_sources/F4_REFERENCE_AUDIT'
 fig.savefig(stem.with_suffix('.svg'),metadata={'Creator':'Matplotlib '+matplotlib.__version__,'Date':None})
 fig.savefig(stem.with_suffix('.pdf'),metadata={'Title':'Exact reference bounds and fixed-query minima','Author':'Antonio Clim','CreationDate':None,'ModDate':None})
 plt.close(fig)
 odg=root/'01_editable_odg/JSS_Figure_4_Reference_Audit.odg'
 counts,labels=build_native(stem.with_suffix('.svg'),stem.with_suffix('.pdf'),odg,'JSS Figure 4 Reference Audit')
 captions=json.loads((root/'04_sources/CAPTIONS_EN_GB.json').read_text());assert '4' in captions
 report={'status':'PASS_SOURCE_REPORT_BINDINGS_AND_NATIVE_ODG_BUILD','data_sha256':sha256(data_path.read_bytes()).hexdigest(),'display_width_mm':174,'display_height_mm':145,'minimum_font_pt':8.5,'matplotlib_version':matplotlib.__version__,'interval_objects':objects,'qmin_k':k,'qmin_values':q,'native_build_objects':dict(counts),'native_text_labels':labels,'query_points_read_from_certificates':True,'formula_generated_query_points':False,'source_svg_sha256':sha256(stem.with_suffix('.svg').read_bytes()).hexdigest(),'source_pdf_sha256':sha256(stem.with_suffix('.pdf').read_bytes()).hexdigest(),'script_sha256':sha256(Path(__file__).read_bytes()).hexdigest()}
 (root/'05_validation/F4_FIGURE4_SOURCE_BUILD.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k not in ['interval_objects','native_text_labels']},indent=2))

if __name__=='__main__':main()
