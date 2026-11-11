#!/usr/bin/env python3
"""YouTube helper for GitHub Actions. Secret YT_CLIENT_JSON (Desktop OAuth client).
Refresh token is stored ENCRYPTED in yt/token.enc (repo is public) with key = sha256(client_secret).
  python3 yt/yt.py url            -> print consent URL (client_id is not secret)
  python3 yt/yt.py exchange CODE  -> exchange code, write yt/token.enc, print channel title
  python3 yt/yt.py upload FILE TITLE DESC_FILE -> upload a Short, print video id
  python3 yt/yt.py uploadlong FILE TITLE DESC_FILE [THUMB.jpg] -> upload a long-form video (+ thumbnail, non-fatal)
"""
import json, os, sys, hashlib, base64, subprocess, urllib.request, urllib.parse
D = os.path.dirname(os.path.abspath(__file__))
TOK = os.path.join(D, 'token.enc')
c = json.loads(os.environ['YT_CLIENT_JSON']); c = c.get('installed') or c.get('web') or c
CID, CS = c['client_id'], c['client_secret']
KEY = hashlib.sha256(('spider-yt|' + CS).encode()).hexdigest()
REDIR = 'http://localhost'
SCOPE = 'https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/youtube.force-ssl'

def post(url, data, headers=None):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(), headers=headers or {})
    try: return json.loads(urllib.request.urlopen(req, timeout=60).read())
    except urllib.error.HTTPError as e: sys.exit('HTTP %s %s' % (e.code, e.read()[:300]))

def enc(s):
    return subprocess.run(['openssl','enc','-aes-256-cbc','-pbkdf2','-a','-A','-pass','pass:'+KEY], input=s.encode(), capture_output=True, check=True).stdout.decode()
def dec(s):
    return subprocess.run(['openssl','enc','-d','-aes-256-cbc','-pbkdf2','-a','-A','-pass','pass:'+KEY], input=s.encode(), capture_output=True, check=True).stdout.decode()

def access():
    rt = dec(open(TOK).read().strip())
    r = post('https://oauth2.googleapis.com/token', {'client_id':CID,'client_secret':CS,'refresh_token':rt,'grant_type':'refresh_token'})
    return r['access_token']

def channel(at):
    req = urllib.request.Request('https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true', headers={'Authorization':'Bearer '+at})
    j = json.loads(urllib.request.urlopen(req, timeout=60).read())
    return [i['snippet']['title'] + ' ' + i['snippet'].get('customUrl','') for i in j.get('items',[])]

cmd = sys.argv[1]
if cmd == 'url':
    print('AUTH_URL https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode({'client_id':CID,'redirect_uri':REDIR,'response_type':'code','scope':SCOPE,'access_type':'offline','prompt':'consent'}))
elif cmd == 'exchange':
    code = sys.argv[2]
    if code.startswith('http'): code = urllib.parse.parse_qs(urllib.parse.urlparse(code).query)['code'][0]
    r = post('https://oauth2.googleapis.com/token', {'code':code,'client_id':CID,'client_secret':CS,'redirect_uri':REDIR,'grant_type':'authorization_code'})
    if 'refresh_token' not in r: sys.exit('no refresh_token in response: ' + ','.join(r.keys()))
    open(TOK,'w').write(enc(r['refresh_token']) + '\n')
    print('TOKEN SAVED; channel:', channel(r['access_token']))
elif cmd == 'check':
    print('CHANNEL', channel(access()))
elif cmd == 'upload':
    f, title, desc = sys.argv[2], sys.argv[3][:100], open(sys.argv[4]).read()[:4900]
    at = access()
    meta = {'snippet':{'title':title,'description':desc,'categoryId':'27','tags':['forex','trading','shorts']},
            'status':{'privacyStatus':'public','selfDeclaredMadeForKids':False}}
    req = urllib.request.Request('https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status',
        data=json.dumps(meta).encode(), headers={'Authorization':'Bearer '+at,'Content-Type':'application/json; charset=UTF-8',
        'X-Upload-Content-Type':'video/mp4','X-Upload-Content-Length':str(os.path.getsize(f))})
    try: loc = urllib.request.urlopen(req, timeout=60).headers['Location']
    except urllib.error.HTTPError as e: sys.exit('init HTTP %s %s' % (e.code, e.read()[:400]))
    up = urllib.request.Request(loc, data=open(f,'rb').read(), method='PUT', headers={'Content-Type':'video/mp4'})
    try: j = json.loads(urllib.request.urlopen(up, timeout=600).read())
    except urllib.error.HTTPError as e: sys.exit('upload HTTP %s %s' % (e.code, e.read()[:400]))
    print('YT_UPLOADED', j['id'], j.get('status',{}).get('privacyStatus'))
elif cmd == 'uploadlong':
    f, title, desc = sys.argv[2], sys.argv[3][:100], open(sys.argv[4]).read()[:4900]
    at = access()
    meta = {'snippet':{'title':title,'description':desc,'categoryId':'27','defaultLanguage':'hi','defaultAudioLanguage':'hi',
            'tags':['order flow','orderflow','order flow hindi','trading hindi','forex hindi','volume profile','footprint chart','price action','spider trades']},
            'status':{'privacyStatus':'public','selfDeclaredMadeForKids':False}}
    req = urllib.request.Request('https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status',
        data=json.dumps(meta).encode(), headers={'Authorization':'Bearer '+at,'Content-Type':'application/json; charset=UTF-8',
        'X-Upload-Content-Type':'video/mp4','X-Upload-Content-Length':str(os.path.getsize(f))})
    try: loc = urllib.request.urlopen(req, timeout=60).headers['Location']
    except urllib.error.HTTPError as e: sys.exit('init HTTP %s %s' % (e.code, e.read()[:400]))
    up = urllib.request.Request(loc, data=open(f,'rb').read(), method='PUT', headers={'Content-Type':'video/mp4'})
    try: j = json.loads(urllib.request.urlopen(up, timeout=900).read())
    except urllib.error.HTTPError as e: sys.exit('upload HTTP %s %s' % (e.code, e.read()[:400]))
    print('YT_UPLOADED', j['id'], j.get('status',{}).get('privacyStatus'))
    if len(sys.argv) > 5 and os.path.exists(sys.argv[5]):
        th = urllib.request.Request('https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId=' + j['id'] + '&uploadType=media',
            data=open(sys.argv[5],'rb').read(), method='POST', headers={'Authorization':'Bearer '+at,'Content-Type':'image/jpeg'})
        try: urllib.request.urlopen(th, timeout=120).read(); print('THUMB_OK')
        except urllib.error.HTTPError as e: print('THUMB_FAILED HTTP %s %s' % (e.code, e.read()[:300].decode('utf8','replace')))

def api(method, url, body=None, ctype='application/json; charset=UTF-8', raw=None):
    at = access()
    req = urllib.request.Request(url, data=raw if raw is not None else (json.dumps(body).encode() if body is not None else None), method=method, headers={'Authorization':'Bearer '+at,'Content-Type':ctype})
    try: return json.loads(urllib.request.urlopen(req, timeout=180).read() or b'{}')
    except urllib.error.HTTPError as e: sys.exit('HTTP %s %s' % (e.code, e.read()[:400].decode('utf8','replace')))
if cmd == 'playlist':     # playlist TITLE DESC -> PLAYLIST <id>
    j = api('POST','https://www.googleapis.com/youtube/v3/playlists?part=snippet,status',{'snippet':{'title':sys.argv[2],'description':sys.argv[3],'defaultLanguage':'hi'},'status':{'privacyStatus':'public'}})
    print('PLAYLIST', j['id'])
elif cmd == 'plitem':     # plitem PLAYLIST VIDEO
    j = api('POST','https://www.googleapis.com/youtube/v3/playlistItems?part=snippet',{'snippet':{'playlistId':sys.argv[2],'resourceId':{'kind':'youtube#video','videoId':sys.argv[3]}}})
    print('PLITEM_OK', j.get('id','')[:12])
elif cmd == 'caption':    # caption VIDEO LANG NAME FILE.srt
    b = 'spiderbound7f3a'; meta = json.dumps({'snippet':{'videoId':sys.argv[2],'language':sys.argv[3],'name':sys.argv[4],'isDraft':False}})
    raw = ('--%s\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n%s\r\n--%s\r\nContent-Type: application/octet-stream\r\n\r\n' % (b, meta, b)).encode() + open(sys.argv[5],'rb').read() + ('\r\n--%s--\r\n' % b).encode()
    j = api('POST','https://www.googleapis.com/upload/youtube/v3/captions?uploadType=multipart&part=snippet', ctype='multipart/related; boundary=' + b, raw=raw)
    print('CAPTION_OK', j.get('id','')[:12])
elif cmd == 'thumb':      # thumb VIDEO FILE.jpg
    api('POST','https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId=' + sys.argv[2] + '&uploadType=media', ctype='image/jpeg', raw=open(sys.argv[3],'rb').read())
    print('THUMB_OK')
elif cmd == 'vstatus':    # vstatus VIDEO
    at = access(); req = urllib.request.Request('https://www.googleapis.com/youtube/v3/videos?part=status,snippet,statistics&id=' + sys.argv[2], headers={'Authorization':'Bearer '+at})
    j = json.loads(urllib.request.urlopen(req, timeout=60).read()); i = j['items'][0]
    print('VSTATUS', i['status'].get('privacyStatus'), i['status'].get('uploadStatus'), i.get('statistics',{}).get('viewCount'))
