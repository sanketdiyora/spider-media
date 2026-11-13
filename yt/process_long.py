#!/usr/bin/env python3
"""Upload every yt/long/*.json (long-form) once; marker yt/done/long_<name>.json. GitHub Actions only."""
import json, os, glob, subprocess, sys
D=os.path.dirname(os.path.abspath(__file__)); R=os.path.dirname(D); ch=False
for q in sorted(glob.glob(os.path.join(D,'long','*.json'))):
    name=os.path.basename(q); done=os.path.join(D,'done','long_'+name)
    if os.path.exists(done): print('already done',name); continue
    j=json.load(open(q)); p=lambda k: os.path.join(R,j[k])
    r=subprocess.run([sys.executable,os.path.join(D,'yt.py'),'uploadlong',p('video'),j['title'],p('desc'),p('thumb')],capture_output=True,text=True)
    print(r.stdout.strip(), r.stderr.strip()[-500:])
    if r.returncode!=0 or 'YT_UPLOADED' not in r.stdout: print('UPLOAD FAILED',name); continue
    a=r.stdout.split('YT_UPLOADED')[1].split(); extra=[]
    cfg=json.load(open(os.path.join(D,'config.json'))); pl=cfg.get('playlists',{}).get(j.get('playlist_key',''))
    for op in ([['plitem',pl,a[0]]] if pl else [])+([['caption',a[0],'en','English',p('srt')]] if j.get('srt') else []):
        x=subprocess.run([sys.executable,os.path.join(D,'yt.py')]+op,capture_output=True,text=True); print(op[0],x.stdout.strip() or x.stderr.strip()[-300:]); extra.append([op[0],x.stdout.strip()[:40]])
    json.dump({**j,'yt':a[0],'privacy':a[1] if len(a)>1 else '','thumb_ok':'THUMB_OK' in r.stdout,'extra':extra,'url':f'https://youtu.be/{a[0]}'},open(done,'w'),ensure_ascii=False); ch=True
if ch:
    g=['git','-C',R]
    subprocess.run(g+['add','-A','yt/done']); subprocess.run(g+['-c','user.name=spider-bot','-c','user.email=spider-bot@users.noreply.github.com','commit','-qm','yt long uploaded [skip ci]'])
    for _ in range(3):
        if subprocess.run(g+['push','-q','origin','HEAD:main']).returncode==0: break
        subprocess.run(g+['pull','-q','--rebase','--autostash','origin','main'])
