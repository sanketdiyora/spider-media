#!/usr/bin/env python3
"""Read-only IG stats: last N media + per-reel insights -> insights/ig_<utc-date>.json (no token in output)."""
import os, json, time, urllib.parse, urllib.request
IG='17841439656187228'; G='https://graph.facebook.com/v21.0'
def call(path, p):
    p = dict(p); p['access_token'] = os.environ['IG_TOKEN']
    try: return json.load(urllib.request.urlopen(f'{G}/{path}?' + urllib.parse.urlencode(p), timeout=60))
    except urllib.error.HTTPError as e:
        try: return {'error': json.load(e).get('error', {}).get('message', str(e))}
        except Exception: return {'error': str(e)}
acc = call(IG, {'fields': 'followers_count,media_count,username'})
media = call(f'{IG}/media', {'fields': 'id,caption,media_type,media_product_type,timestamp,permalink,like_count,comments_count', 'limit': 60}).get('data', [])
M = ['views', 'reach', 'likes', 'comments', 'shares', 'saved', 'total_interactions', 'ig_reels_avg_watch_time', 'ig_reels_video_view_total_time']
out = []
for m in media:
    row = {k: m.get(k) for k in ('id', 'timestamp', 'permalink', 'media_product_type', 'like_count', 'comments_count')}
    row['caption'] = (m.get('caption') or '')[:90]
    ins = {}
    for k in M:
        r = call(f"{m['id']}/insights", {'metric': k})
        if 'data' in r and r['data']: ins[k] = r['data'][0]['values'][0]['value'] if 'values' in r['data'][0] else r['data'][0].get('total_value', {}).get('value')
        else: ins[k] = None
    row['ins'] = ins; out.append(row)
json.dump({'utc': int(time.time()), 'account': {k: acc.get(k) for k in ('username', 'followers_count', 'media_count')}, 'media': out}, open(f"insights/ig_{time.strftime('%Y-%m-%d_%H%M', time.gmtime())}.json", 'w'), indent=1, ensure_ascii=False)
print('ok', len(out), acc.get('followers_count'))
