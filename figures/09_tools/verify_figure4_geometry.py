#!/usr/bin/env python3
"""Compare the final native Draw export with source SVG data coordinates."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import fitz
from lxml import etree as E
from svgpathtools import parse_path

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);a=p.parse_args();r=a.root
 svg=r/'04_sources/F4_REFERENCE_AUDIT.svg';pdf=r/'02_publication_pdf/JSS_Figure_4_Reference_Audit.pdf'
 t=E.parse(str(svg));source=json.loads((r/'05_validation/F4_FIGURE4_SOURCE_BUILD.json').read_text())
 with fitz.open(pdf) as d:drawings=d[0].get_drawings();labels=Counter(' '.join(s['text'].split()) for b in d[0].get_text('dict')['blocks'] if 'lines'in b for l in b['lines'] for s in l['spans'])
 assert labels==Counter(' '.join(s.split()) for s in source['native_text_labels'])
 errors=[];used=set()
 def points(d):
  result=[]
  for item in d['items']:
   if item[0]!='l':return None
   if not result:result.append(tuple(item[1]))
   result.append(tuple(item[2]))
  return result
 for row in source['interval_objects']:
  group=t.xpath('//*[@id=$id]',id=row['id'])[0]
  node=group.xpath('./*[local-name()="path"]')[0];path=parse_path(node.get('d'))
  expected=[(path.start.real,path.start.imag),(path.end.real,path.end.imag)]
  colour=(0,114,178) if row['branch']=='S' else (213,94,0)
  candidates=[]
  for i,d in enumerate(drawings):
   got=points(d)
   if i in used or got is None or len(got)!=2 or d.get('color') is None:continue
   if tuple(round(v*255) for v in d['color'])!=colour or abs(d['width']-2)>.05:continue
   error=max(abs(u-v) for x,y in zip(expected,got,strict=True) for u,v in zip(x,y,strict=True))
   candidates.append((error,i))
  error,index=min(candidates);assert error<.04,(row['id'],error);used.add(index);errors.append(error)
 group=t.xpath('//*[@id="F4_QMIN_RESTRICTED"]')[0]
 node=group.xpath('./*[local-name()="path"]')[0];path=parse_path(node.get('d'))
 expected=[(path.start.real,path.start.imag)]+[(s.end.real,s.end.imag) for s in path]
 assert len(expected)==len(source['qmin_values'])==9
 candidates=[]
 for i,d in enumerate(drawings):
  got=points(d)
  if got is None or len(got)!=9 or d.get('color') is None:continue
  if tuple(round(v*255) for v in d['color'])!=(0,114,178):continue
  error=max(abs(u-v) for x,y in zip(expected,got,strict=True) for u,v in zip(x,y,strict=True));candidates.append((error,i))
 error,index=min(candidates);assert error<.06,error;errors.append(error)
 report={'status':'PASS_FIGURE4_NATIVE_RENDERED_DATA_GEOMETRY','source_svg_sha256':sha256(svg.read_bytes()).hexdigest(),'native_pdf_sha256':sha256(pdf.read_bytes()).hexdigest(),'conditional_interval_segments':6,'fixed_query_curve_vertices':9,'matching_rendered_text_spans':sum(labels.values()),'maximum_coordinate_displacement_pt':max(errors),'tolerance_pt':.06,'tolerance_reason':'Two-stage ODF path-coordinate and native geometry rounding to hundredths of a millimetre; 0.06 pt is approximately 0.0212 mm. Numerical labels and source values remain exact.','method':'Match final native PDF path endpoints and all nine query-curve vertices to source SVG data paths; rendered labels match the source text inventory.'}
 (r/'05_validation/F4_FIGURE4_GEOMETRY_QA.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
