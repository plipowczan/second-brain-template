#!/usr/bin/env python3
import os, re, json
ROOT="content"
EXCLUDE_TOP={"_raw","_indexes","_outputs","templates","ATTACHMENTS",".obsidian"}
EXCLUDE_FILES={"WRITING_STYLE.md","WRITING_STYLE_ANALYSIS.md","_index.md"}
# build note index: basename and rel-path (no ext)
names=set(); paths=set(); notes=[]
for dp,dn,fns in os.walk(ROOT):
    rel=os.path.relpath(dp,ROOT)
    if rel!=".":
        top=rel.split(os.sep)[0]
        if top in EXCLUDE_TOP or top.startswith("."):
            dn[:]=[]; continue
    for fn in fns:
        if not fn.endswith(".md"): continue
        if fn.endswith(".template.md") or fn in EXCLUDE_FILES: continue
        p=os.path.join(dp,fn).replace("\\","/")
        relp=os.path.relpath(p,ROOT).replace("\\","/")[:-3]
        names.add(fn[:-3]); paths.add(relp); paths.add(relp.lower())
        notes.append((p,fn[:-3]))
names_l={n.lower() for n in names}

linkre=re.compile(r'\[\[([^\]]+)\]\]')
def strip_code(t):
    t = re.sub(r'```.*?```', '', t, flags=re.DOTALL)  # fenced blocks
    t = re.sub(r'`[^`\n]*`', '', t)                    # inline spans
    return t
broken={}; incoming=set(); outdeg={}
for p,name in notes:
    txt=strip_code(open(p,encoding="utf-8").read())
    for raw in linkre.findall(txt):
        tgt=raw.split("|")[0].split("#")[0].strip()
        if not tgt: continue
        base=tgt.split("/")[-1]
        ok = tgt in paths or tgt.lower() in paths or base in names or base.lower() in names_l \
             or tgt.startswith("templates/") or tgt.lower().endswith(".png") or tgt.lower().endswith(".pdf") \
             or "ATTACHMENTS" in tgt or tgt.lower().endswith((".jpg",".jpeg",".webm",".gif",".svg"))
        if not ok:
            broken.setdefault(p,[]).append(tgt)
        else:
            if base in names: incoming.add(base)
            elif base.lower() in names_l: incoming.add(base.lower())
            outdeg[name]=outdeg.get(name,0)+1

orphans=[n for _,n in notes if n not in incoming and n.lower() not in {x.lower() for x in incoming}]
print(json.dumps({"broken":broken,"orphan_count":len(orphans),"orphans":sorted(orphans)},indent=1,ensure_ascii=False))
