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
SP='/tmp/claude-0/-home-claude/db1e54d3-1de6-5de9-93cd-e5a4b7a6b6c7/scratchpad'
TGSTATE='/home/claude/tg_sent.json'
def tg(it,date,slot,link):
    """Mirror the post to the Telegram channel (once). Never breaks the IG flow."""
    try:
        tok=os.environ.get('TG_TOKEN') or open(SP+'/.tg_token').read().strip(); ch=os.environ.get('TG_CHAT') or open(SP+'/.tg_chat').read().strip()
    except Exception: print('TG: no credentials, skipped'); return
    try: st=json.load(open(TGSTATE))
    except Exception: st={}
    key=f'{date}_{slot}'
    if key in st: print('TG: already sent'); return
    lines=[l for l in it['caption'].split('\n') if not l.strip().startswith('#')]
    cap='\n'.join(lines).strip()+(f'\n🔗 {link}' if link else '')
    if len(cap)>1020: cap=cap[:1015]+'...'
    def api(m,body):
        r=urllib.request.urlopen(urllib.request.Request(f'https://api.telegram.org/bot{tok}/{m}',data=json.dumps({'chat_id':ch,**body}).encode(),headers={'Content-Type':'application/json'}),timeout=120); return json.load(r)
    try:
        if it['type']=='reel': r=api('sendVideo',{'video':it['media'][0],'caption':cap,'supports_streaming':True,'width':1080,'height':1920})
        else: r=api('sendMediaGroup',{'media':[{'type':'photo','media':u,**({'caption':cap} if i==0 else {})} for i,u in enumerate(it['media'])]})
        if r.get('ok'): st[key]=True; json.dump(st,open(TGSTATE,'w')); print('TG: sent')
        else: print('TG: fail',r)
    except Exception as e: print('TG: error',e)
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
    recent=call(f'{IG}/media',{'fields':'caption,timestamp,permalink','limit':'12'}).get('data',[])
    hit=[m for m in recent if (m.get('caption') or '').strip()==cap.strip()]
    if hit:
        print('SKIP: already posted (caption match)'); tg(it,date,slot,hit[0].get('permalink')); return 0
    if it['type']=='reel':
        c=call(f'{IG}/media',{'media_type':'REELS','video_url':it['media'][0],'caption':cap,'share_to_feed':'true','thumb_offset':str(it.get('thumb_offset',1500))},'POST')
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
    pm=call(p['id'],{'fields':'permalink'}); print('PUBLISHED',p['id'],pm.get('permalink')); tg(it,date,slot,pm.get('permalink'))
    return 0
sys.exit(main())
