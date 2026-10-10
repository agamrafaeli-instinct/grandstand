#!/usr/bin/env python3
"""Bake the HN explorer roadmap project (GitHub Projects v2) into data/board.json.
Needs GH_TOKEN with read access to the project and the repo. Done items are counted, not listed."""
import json, os, subprocess, sys, datetime
OWNER = os.environ.get('BOARD_OWNER', 'agamrafaeli-instinct'); NUM = int(os.environ.get('BOARD_NUMBER', '1'))
Q = '''query($a:String){user(login:"%s"){projectV2(number:%d){title url items(first:100,after:$a){pageInfo{hasNextPage endCursor} nodes{
 st:fieldValueByName(name:"Status"){... on ProjectV2ItemFieldSingleSelectValue{name}}
 hz:fieldValueByName(name:"Horizon"){... on ProjectV2ItemFieldSingleSelectValue{name}}
 content{... on Issue{number title url state updatedAt closedAt labels(first:8){nodes{name}} parent{number} subIssuesSummary{total completed}}}}}}}}''' % (OWNER, NUM)
def gql(after):
    cmd = ['gh', 'api', 'graphql', '-f', 'query=' + Q] + (['-f', 'a=' + after] if after else [])
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode: sys.exit('graphql failed: ' + r.stderr[:300])
    return json.loads(r.stdout)['data']['user']['projectV2']
items, after, proj = [], None, None
while True:
    p = gql(after); proj = p
    for n in p['items']['nodes']:
        c = n['content']
        if not c: continue
        labels = [l['name'] for l in c['labels']['nodes']]
        t = c['title']; epic = 'epic' in labels or t.startswith('[Epic]')
        sub = c.get('subIssuesSummary') or {}
        items.append(dict(number=c['number'], title=t, url=c['url'], state=c['state'], status=(n['st'] or {}).get('name'),
            horizon=(n['hz'] or {}).get('name'), epic=epic, parent=(c.get('parent') or {}).get('number'),
            total=sub.get('total', 0), done=sub.get('completed', 0), updated=c['updatedAt'], labels=labels))
    if not p['items']['pageInfo']['hasNextPage']: break
    after = p['items']['pageInfo']['endCursor']
done = [i for i in items if i['status'] == 'Done' or i['state'] == 'CLOSED']
live = [i for i in items if i not in done]
counts = {}
for i in live: counts[i['status'] or 'None'] = counts.get(i['status'] or 'None', 0) + 1
out = dict(generated=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), project=proj['title'], project_url=proj['url'],
    done_count=len(done), done_tasks=len([i for i in done if not i['epic']]), counts=counts, items=live)
os.makedirs('data', exist_ok=True)
json.dump(out, open('data/board.json', 'w'), indent=1)
print('items', len(items), 'live', len(live), 'done', len(done), counts)
