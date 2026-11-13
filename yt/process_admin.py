#!/usr/bin/env python3
"""Run yt/admin/*.json op lists once ({"ops":[["playlist","T","D"],["plitem","$PL","VID"],...]}); result -> yt/done/admin_<name>.json. $PL = playlist id (created in this run or yt/config.json 'playlists'[key])."""
import json, os, glob, subprocess, sys
D=os.path.dirname(os.path.abspath(__file__)); R=os.path.dirname(D); cfgp=os.path.join(D,'config.json'); cfg=json.load(open(cfgp)); ch=False
for q in sorted(glob.glob(os.path.join(D,'admin','*.json'))):
    name=os.path.basename(q); done=os.path.join(D,'done','admin_'+name)
    if os.path.exists(done): continue
    j=json.load(open(q)); pl=cfg.get('playlists',{}).get(j.get('playlist_key',''),''); out=[]
    for op in j['ops']:
        a=[(pl if x=='$PL' else (os.path.join(R,x) if x.startswith('yt/') else x)) for x in op[1:]]
        r=subprocess.run([sys.executable,os.path.join(D,'yt.py'),op[0]]+a,capture_output=True,text=True)
        res=(r.stdout.strip() or r.stderr.strip()[-300:]); print(op[0],res); out.append([op[0],res])
        if 'PLAYLIST ' in r.stdout:
            pl=r.stdout.split('PLAYLIST ')[1].split()[0]; cfg.setdefault('playlists',{})[j.get('playlist_key','default')]=pl
    json.dump({'results':out},open(done,'w'),ensure_ascii=False,indent=1); json.dump(cfg,open(cfgp,'w'),indent=1); ch=True
if ch:
    g=['git','-C',R]
    subprocess.run(g+['add','-A','yt/done','yt/config.json']); subprocess.run(g+['-c','user.name=spider-bot','-c','user.email=spider-bot@users.noreply.github.com','commit','-qm','yt admin done [skip ci]'])
    for _ in range(3):
        if subprocess.run(g+['push','-q','origin','HEAD:main']).returncode==0: break
        subprocess.run(g+['pull','-q','--rebase','--autostash','origin','main'])
