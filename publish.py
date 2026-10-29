#!/usr/bin/env python3
"""Publish today's (IST) scheduled Instagram post for a slot.
usage: IG_TOKEN=... python3 publish.py 1100 [--dry] [--date YYYY-MM-DD]"""
import os,sys,json,time,urllib.request,urllib.parse,datetime
IG='17841439656187228'; V='v21.0'; G=f'https://graph.facebook.com/{V}'
SCHED='https://raw.githubusercontent.com/sanketdiyora/spider-media/main/schedule.json'
def call(path,params=None,method='GET'):
    params=dict(params or {}); params['access_token']=os.environ['IG_TOKEN']
    data=urllib.parse.urlencode(params).encode()
    url=f'{G}/{path}'+('?'+data.decode() if method=='GET' else '')
    try:
        r=urllib.request.urlopen(urllib.request.Request(url,data=None if method=='GET' else data,method=method),timeout=120)
        return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {'error':json.loads(e.read() or b'{}')}
def wait(cid,tries=40):
    for _ in range(tries):
        s=call(cid,{'fields':'status_code,status'}); sc=s.get('status_code')
        if sc=='FINISHED': return True
        if sc in('ERROR','EXPIRED') or 'error' in s: print('container',s); return False
        time.sleep(8)
    return False
def main():
    slot=sys.argv[1]; dry='--dry' in sys.argv
    ist=datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(hours=5,minutes=30)
    date=sys.argv[sys.argv.index('--date')+1] if '--date' in sys.argv else ist.strftime('%Y-%m-%d')
    sched=json.loads(urllib.request.urlopen(SCHED+f'?t={int(time.time())}',timeout=60).read())
    items=[s for s in sched if s['date']==date and s['slot']==slot]
    if not items: print(f'NOTHING scheduled for {date} {slot}'); return 0
    it=items[0]; cap=it['caption']
    print(date,slot,it['type'],len(it['media']),'files')
    if dry:
        for u in it['media']:
            r=urllib.request.urlopen(urllib.request.Request(u,method='HEAD'),timeout=60); print('  ok',r.status,u.split('/')[-1],r.headers.get('content-length'))
        return 0
    recent=call(f'{IG}/media',{'fields':'caption,timestamp','limit':'12'}).get('data',[])
    if any((m.get('caption') or '').strip()==cap.strip() for m in recent):
        print('SKIP: already posted (caption match)'); return 0
    if it['type']=='reel':
        c=call(f'{IG}/media',{'media_type':'REELS','video_url':it['media'][0],'caption':cap,'share_to_feed':'true'},'POST')
        cid=c.get('id')
    else:
        kids=[]
        for u in it['media']:
            c=call(f'{IG}/media',{'image_url':u,'is_carousel_item':'true'},'POST')
            if 'id' not in c: print('child fail',c); return 1
            kids.append(c['id'])
        for k in kids:
            if not wait(k): return 1
        c=call(f'{IG}/media',{'media_type':'CAROUSEL','children':','.join(kids),'caption':cap},'POST'); cid=c.get('id')
    if not cid: print('create fail',c); return 1
    if not wait(cid): return 1
    p=call(f'{IG}/media_publish',{'creation_id':cid},'POST')
    if 'id' not in p: print('publish fail',p); return 1
    pm=call(p['id'],{'fields':'permalink'}); print('PUBLISHED',p['id'],pm.get('permalink'))
    return 0
sys.exit(main())
