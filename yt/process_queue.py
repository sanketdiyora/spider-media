#!/usr/bin/env python3
"""Upload every yt/queue/*.json reel to YouTube Shorts once (done marker in yt/done/). Runs in GitHub Actions only."""
import json, os, glob, subprocess, sys, tempfile, urllib.request
D=os.path.dirname(os.path.abspath(__file__)); R=os.path.dirname(D)
os.makedirs(os.path.join(D,'done'),exist_ok=True); changed=[]
for q in sorted(glob.glob(os.path.join(D,'queue','*.json'))):
    name=os.path.basename(q); done=os.path.join(D,'done',name)
    j=json.load(open(q))
    if os.path.exists(done): os.remove(q); changed.append(q); print('already done',name); continue
    cap=j['caption']; first=next((l for l in cap.splitlines() if l.strip()),'SPIDER trade setup')
    title=(first.strip()[:88]+' #Shorts')
    desc=cap+'\n\n#Shorts'
    tmp=tempfile.mkdtemp(); f=os.path.join(tmp,'v.mp4'); df=os.path.join(tmp,'d.txt'); open(df,'w').write(desc)
    urllib.request.urlretrieve(j['media'],f)
    r=subprocess.run([sys.executable,os.path.join(D,'yt.py'),'upload',f,title,df],capture_output=True,text=True)
    print(r.stdout.strip(), r.stderr.strip()[-500:])
    if r.returncode!=0 or 'YT_UPLOADED' not in r.stdout: print('UPLOAD FAILED',name); continue
    vid=r.stdout.split('YT_UPLOADED')[1].split()[0]
    json.dump({**j,'yt':vid,'url':f'https://youtube.com/shorts/{vid}'},open(done,'w'),ensure_ascii=False)
    os.remove(q); changed+= [q,done]
if changed:
    g=['git','-C',R]
    subprocess.run(g+['add','-A','yt']); subprocess.run(g+['-c','user.name=spider-bot','-c','user.email=spider-bot@users.noreply.github.com','commit','-qm','yt uploaded [skip ci]'])
    for _ in range(3):
        if subprocess.run(g+['push','-q']).returncode==0: break
        subprocess.run(g+['pull','-q','--rebase','--autostash'])
