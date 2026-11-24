#!/usr/bin/env python3
"""Seal or verify the exact files in a figure delivery (integrity, not science)."""
import argparse
import hashlib
import json
from pathlib import Path

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--seal',action='store_true');a=p.parse_args();r=a.root.resolve();m=r/'FIGURE_KIT_MANIFEST.json'
 current={}
 for f in sorted(r.rglob('*')):
  assert not f.is_symlink(),'Symbolic links are outside the delivered file set'
  if f.is_file() and f!=m:current[str(f.relative_to(r))]={'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
 if a.seal:
  m.write_text(json.dumps({'schema':'nsc-figure-manifest/1','version':'1.0.0','figures':4,'files':current},ensure_ascii=False,indent=2)+'\n')
 expected=json.loads(m.read_text())['files'];assert expected==current,'Figure file manifest differs from current files'
 print(json.dumps({'status':'PASS_FILE_INTEGRITY','files_verified':len(current),'manifest_sha256':hashlib.sha256(m.read_bytes()).hexdigest(),'scope':'Byte identity only; not author acceptance, scientific validation or rights clearance.'},indent=2))

if __name__=='__main__':main()
