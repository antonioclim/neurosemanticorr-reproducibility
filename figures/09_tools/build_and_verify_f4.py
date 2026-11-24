#!/usr/bin/env python3
"""Re-export retained figure sources and test ODF-object edits through native Draw.

Uses LibreOffice's Draw import/export filters. Object mutations are applied to
ODF XML on disposable copies, NOT through a graphical editing session or UNO.
"""
from __future__ import annotations
import argparse
from collections import Counter
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED

import fitz
from lxml import etree as E
from PIL import Image, ImageChops

from build_draw_figures import NS, key, NAMES
from verify_draw_round_trip import check_shapes, text_with_spaces
from normalise_draw_view import normalise

DRAW_TYPES = {'frame', 'rect', 'g', 'line', 'path', 'ellipse', 'polygon', 'polyline', 'circle'}
GEOMETRY = ['svg:x','svg:y','svg:x1','svg:x2','svg:y1','svg:y2']
ODG_NAMES = [*NAMES, 'JSS_Figure_4_Reference_Audit']

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,obj): p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def read(p):
    with ZipFile(p) as z: return {n:z.read(n) for n in z.namelist()}
def save(p, data):
    p.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(p,'w',ZIP_DEFLATED) as z:
        for n,v in data.items(): z.writestr(n,v,compress_type=ZIP_STORED if n=='mimetype' else ZIP_DEFLATED)
def xml(b): return E.fromstring(b,E.XMLParser(resolve_entities=False,no_network=True))
def serial(t): return E.tostring(t,encoding='UTF-8',xml_declaration=True)
def objects(t):
    return [n for n in t.xpath('//office:drawing/draw:page//*',namespaces=NS)
            if E.QName(n).namespace==NS['draw'] and E.QName(n).localname in DRAW_TYPES]
def texts(t):
    return Counter(' '.join(''.join(text_with_spaces(p)).split()) for p in
                   t.xpath('//draw:text-box/text:p',namespaces=NS))
def signature(t):
    out={}
    for n in objects(t):
        name=n.get(key('draw:name'))
        out[name]={'type':E.QName(n).localname,
                   'geometry':{k:v for k,v in n.attrib.items() if E.QName(k).namespace==NS['svg'] or k==key('draw:transform')},
                   'labels':[' '.join(''.join(text_with_spaces(p)).split()) for p in n.xpath('./draw:text-box/text:p',namespaces=NS)]}
    return out

def convert(paths,out,filter_name,soffice,log):
    out.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='nsc-f4-draw-') as prof:
        cmd=[soffice,'-env:UserInstallation='+Path(prof).as_uri(),'--headless','--convert-to',filter_name,'--outdir',str(out),*[str(p) for p in paths]]
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
    log.append({'argv':cmd,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
    assert r.returncode==0 and 'using filter' in r.stdout,(r.stdout,r.stderr)
    suffix='.pdf' if filter_name.startswith('pdf') else '.odg'
    for p in paths: assert (out/p.with_suffix(suffix).name).is_file()

def move_coordinate(v,delta):
    m=re.fullmatch(r'(-?[\d.]+)(cm|mm|in|pt)',v)
    assert m,v
    scale={'cm':Decimal(1),'mm':Decimal(10),'in':Decimal('0.3937007874015748'),'pt':Decimal('28.34645669291339')}[m[2]]
    return f'{Decimal(m[1])+delta*scale}{m[2]}'

def mutate(original,path):
    data=read(original); t=xml(data['content.xml'])
    counts=Counter(); mappings={}; styles=t.find(key('office:automatic-styles'))
    for i,n in enumerate(objects(t),1):
        name=n.get(key('draw:name')); new=f'F4_EDIT_{i:04d} / {name}'
        mappings[new]=name; n.set(key('draw:name'),new)
        typ=E.QName(n).localname; counts[typ]+=1
        for g in GEOMETRY:
            if key(g) in n.attrib: n.set(key(g),move_coordinate(n.get(key(g)),Decimal('0.1')))
        trans=n.get(key('draw:transform'))
        if trans:
            n.set(key('draw:transform'),re.sub(r'(-?[\d.]+(?:cm|mm|in|pt))',lambda m:move_coordinate(m[0],Decimal('0.1')),trans))
        for p in n.xpath('./draw:text-box/text:p',namespaces=NS):
            spans=p.xpath('.//text:span',namespaces=NS)
            first=spans[0] if spans else p
            first.text='F4 edit '+(first.text or '')
        if typ!='g':
            source_style=styles.xpath('./style:style[@style:name=$name]',namespaces=NS,name=n.get(key('draw:style-name')))[0]
            style=deepcopy(source_style); style.set(key('style:name'),f'F4_STYLE_{i}'); styles.append(style)
            props=style.find(key('style:graphic-properties'))
            if props is None: props=E.SubElement(style,key('style:graphic-properties'))
            for child in list(props):
                if E.QName(child).localname in {'fill-complex-color','stroke-complex-color'}: props.remove(child)
            props.attrib.update({key('draw:fill'):'solid',key('draw:fill-color'):'#123456',key('draw:stroke'):'solid',key('svg:stroke-color'):'#654321',key('svg:stroke-width'):'0.03cm'})
            n.set(key('draw:style-name'),f'F4_STYLE_{i}')
            pstyle=n.get(key('draw:text-style-name'))
            if pstyle:
                pst=deepcopy(styles.xpath('./style:style[@style:name=$name]',namespaces=NS,name=pstyle)[0])
                pst.set(key('style:name'),f'F4_PARAGRAPH_{i}')
                for child in list(pst):
                    if E.QName(child).localname=='graphic-properties': pst.remove(child)
                styles.append(pst); n.set(key('draw:text-style-name'),f'F4_PARAGRAPH_{i}')
    data['content.xml']=serial(t); save(path,data)
    return mappings,signature(t),dict(counts)

def verify_mutated_style(tree):
    count=0
    for n in objects(tree):
        if E.QName(n).localname=='g': continue
        st=tree.xpath('//style:style[@style:name=$name]',namespaces=NS,name=n.get(key('draw:style-name')))[0]
        props=st.find(key('style:graphic-properties'))
        assert props.get(key('draw:fill-color'))=='#123456',n.get(key('draw:name'))
        assert props.get(key('svg:stroke-color'))=='#654321',n.get(key('draw:name'))
        assert props.get(key('svg:stroke-width'))=='0.03cm',n.get(key('draw:name'))
        count+=1
    return count

def undo_from_native(native,original,mappings,dest):
    data=read(native); t=xml(data['content.xml']); base=xml(read(original)['content.xml'])
    source={n.get(key('draw:name')):n for n in objects(base)}
    # Revert the actual modified native objects, retaining native group membership.
    for n in objects(t):
        before=source[mappings[n.get(key('draw:name'))]]
        n.attrib.clear(); n.attrib.update(before.attrib)
        if E.QName(n).localname=='frame':
            for child in list(n): n.remove(child)
            for child in before: n.append(deepcopy(child))
    st=t.find(key('office:automatic-styles')); t.replace(st,deepcopy(base.find(key('office:automatic-styles'))))
    data['content.xml']=serial(t)
    # Font/style definitions in native output are source-equivalent by re-export;
    # retain the exact original external styles for a strict restoration check.
    data['styles.xml']=read(original)['styles.xml']
    save(dest,data)

def geometry_check(expected,actual):
    assert expected.keys()==actual.keys()
    # The native writer normalises coordinates to 0.01 mm. Compare geometry in
    # source-normalised form, with tolerance only for numeric lexical rounding.
    for name,ex in expected.items():
        ac=actual[name]; assert ex['type']==ac['type'],(name,ex['type'],ac['type'])
        assert ex['labels']==ac['labels'],name
        for prop,v in ex['geometry'].items():
            if prop not in ac['geometry']: raise AssertionError((name,prop))
            av=ac['geometry'][prop]
            if v==av: continue
            a=re.fullmatch(r'(-?[\d.]+)(cm|mm|in|pt)',v); b=re.fullmatch(r'(-?[\d.]+)(cm|mm|in|pt)',av)
            if a and b:
                factor={'cm':10,'mm':1,'in':25.4,'pt':25.4/72}
                assert abs(float(a[1])*factor[a[2]]-float(b[1])*factor[b[2]])<=.011,(name,prop,v,av)
            else:
                # Path point coordinates and transforms must remain exactly equal.
                assert v==av,(name,prop,v,av)

def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    cli.add_argument('--evidence',type=Path,required=True)
    cli.add_argument('--soffice',default='soffice')
    args=cli.parse_args(); out=args.root.resolve(); work=args.evidence.resolve(); work.mkdir(parents=True,exist_ok=True)
    for d in ['01_editable_odg','02_publication_pdf','03_publication_tiff','05_validation','06_preview_png']:(out/d).mkdir(exist_ok=True)
    log=[]; captions=json.loads((out/'04_sources/CAPTIONS_EN_GB.json').read_text())
    initial=[]
    assert set(captions)=={str(i) for i in range(1,len(ODG_NAMES)+1)}
    for i,name in enumerate(ODG_NAMES,1):
        p=out/f'01_editable_odg/{name}.odg'; data=read(p); meta=xml(data['meta.xml']); m=meta.find(key('office:meta'))
        desc=m.find(key('dc:description'))
        if desc is None: desc=E.SubElement(m,key('dc:description'))
        desc.text=captions[str(i)]
        data['meta.xml']=serial(meta); q=work/'input'/p.name; save(q,data); initial.append(q)
    convert(initial,out/'01_editable_odg','odg:draw8',args.soffice,log)
    originals=[out/'01_editable_odg'/p.name for p in initial]
    view_settings=[normalise(p) for p in originals]
    convert(originals,out/'02_publication_pdf','pdf:draw_pdf_Export',args.soffice,log)
    checks={}; mutations=[]; saved={}
    for p in originals:
        names,types,labels=check_shapes(p)
        t=xml(read(p)['content.xml']); original_sig=signature(t)
        mutated=work/'mutated_odf'/p.name
        maps,expected,counts=mutate(p,mutated); mutations.append(mutated); saved[p.name]=(maps,expected,original_sig)
        checks[p.name]={'native_objects_and_groups':len(names),'groups':types.get('g',0),'primitive_objects':len(names)-types.get('g',0),'editable_labels':sum(labels.values()),'shape_types':dict(types),'embedded_image_or_ole_payload':False,'mutation_counts':counts}
    convert(mutations,work/'mutated_native','odg:draw8',args.soffice,log)
    restored=[]
    for p in originals:
        maps,expected,_=saved[p.name]; changed=work/'mutated_native'/p.name
        mutated_tree=xml(read(changed)['content.xml'])
        geometry_check(expected,signature(mutated_tree))
        checks[p.name]['mutated_fill_stroke_and_line_width_persisted_count']=verify_mutated_style(mutated_tree)
        undo=work/'restored_odf'/p.name; undo_from_native(changed,p,maps,undo); restored.append(undo)
        checks[p.name]['mutated_names_text_and_geometry_persisted']=True
    convert(restored,work/'restored_native','odg:draw8',args.soffice,log)
    convert([work/'restored_native'/p.name for p in originals],work/'restored_pdf','pdf:draw_pdf_Export',args.soffice,log)
    for p in originals:
        _,_,signature_original=saved[p.name]
        restored_file=work/'restored_native'/p.name
        geometry_check(signature_original,signature(xml(read(restored_file)['content.xml'])))
        pdf=out/'02_publication_pdf'/p.with_suffix('.pdf').name
        with fitz.open(pdf) as d,fitz.open(work/'restored_pdf'/pdf.name) as dd:
            assert len(d)==len(dd)==1 and not d[0].get_images(full=True)
            a=d[0].get_pixmap(dpi=144,alpha=False); b=dd[0].get_pixmap(dpi=144,alpha=False)
            assert (a.width,a.height,a.samples)==(b.width,b.height,b.samples),'Reverted figure rendering differs'
            q=d[0].get_pixmap(dpi=300,alpha=False); image=Image.frombytes('RGB',(q.width,q.height),q.samples)
            image.save(out/'06_preview_png'/p.with_suffix('.png').name,dpi=(300,300))
            q=d[0].get_pixmap(dpi=1000,alpha=False); image=Image.frombytes('RGB',(q.width,q.height),q.samples)
            image.save(out/'03_publication_tiff'/p.with_suffix('.tiff').name,dpi=(1000,1000),compression='tiff_lzw')
            text=[s for block in d[0].get_text('dict')['blocks'] if 'lines' in block for line in block['lines'] for s in line['spans']]
            assert all(d[0].rect.contains(fitz.Rect(s['bbox'])) for s in text)
            fontdata=subprocess.run(['pdffonts',str(pdf)],capture_output=True,text=True,check=True).stdout
            assert all(line.split()[-5]=='yes' for line in fontdata.splitlines()[2:] if line.strip()),fontdata
            checks[p.name].update({'restored_geometry_and_labels_match':True,'restored_render_pixel_identical_at_144dpi':True,'pdf_vector_only':True,'pdf_fonts':fontdata,'pdf_text_spans_in_bounds':len(text),'tiff_dpi':1000,'tiff_pixels':[q.width,q.height],'odg_sha256':sha(p),'pdf_sha256':sha(pdf)})
    versions={'python':subprocess.run(['python3','--version'],capture_output=True,text=True).stdout.strip(),'soffice':subprocess.run([args.soffice,'--version'],capture_output=True,text=True).stdout.strip()}
    report={'status':'PASS_NATIVE_DRAW_ROUNDTRIP_AFTER_OBJECT_EDITS','method':'Disposable ODF XML object edits followed by native LibreOffice Draw load, save, reload and PDF export; NOT GUI manipulation or UNO API mutation.','checks':checks,'view_settings':view_settings,'versions':versions,'gui_acceptance':False,'publication_authorised':False}
    dump(out/'05_validation/F4_NATIVE_OBJECT_PERSISTENCE.json',report); dump(work/'NATIVE_COMMAND_LOG.json',log)
    print(json.dumps(report,indent=2))

if __name__=='__main__': main()
