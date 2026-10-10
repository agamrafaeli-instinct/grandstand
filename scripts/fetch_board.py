#!/usr/bin/env python3
"""Read a GitHub Projects v2 board and bake it into data/board.json. Read-only.
Config: board.config.json (see README). Needs GH_TOKEN (or BOARD_TOKEN) with read access to the project."""
import json, os, subprocess, sys, datetime
cfg = json.load(open(os.environ.get('BOARD_CONFIG', 'board.config.json')))
OWNER = cfg['owner']; NUM = int(cfg['project']); KIND = 'organization' if cfg.get('ownerType', 'user') == 'org' or cfg.get('ownerType') == 'organization' else 'user'
SF = cfg.get('statusField', 'Status'); GF = cfg.get('groupField'); EL = cfg.get('epicLabel', 'epic')
HIDE = set(cfg.get('hideStatuses', ['Done']))
grp = ('gr:fieldValueByName(name:"%s"){... on ProjectV2ItemFieldSingleSelectValue{name}}' % GF) if GF else ''
Q = '''query($a:String){%s(login:"%s"){projectV2(number:%d){title url
 field(name:"%s"){... on ProjectV2SingleSelectField{options{name}}}
 items(first:100,after:$a){pageInfo{hasNextPage endCursor} nodes{
 st:fieldValueByName(name:"%s"){... on ProjectV2ItemFieldSingleSelectValue{name}} %s
 content{... on Issue{number title url state updatedAt labels(first:8){nodes{name}} parent{number} subIssuesSummary{total completed}}
         ... on PullRequest{number title url state updatedAt labels(first:8){nodes{name}}}
         ... on DraftIssue{title}}}}}}}''' % (KIND, OWNER, NUM, SF, SF, grp)
def gql(after):
    cmd = ['gh', 'api', 'graphql', '-f', 'query=' + Q] + (['-f', 'a=' + after] if after else [])
    env = dict(os.environ); env['GH_TOKEN'] = os.environ.get('BOARD_TOKEN') or os.environ.get('GH_TOKEN', '')
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if r.returncode: sys.exit('GitHub API call failed: ' + r.stderr.strip()[:300])
    d = json.loads(r.stdout)
    if not d.get('data') or not d['data'].get(KIND) or not d['data'][KIND].get('projectV2'): sys.exit('Project not found or token cannot read it: ' + r.stdout[:300])
    return d['data'][KIND]['projectV2']
items, after, proj = [], None, None
while True:
    p = gql(after); proj = proj or p
    for n in p['items']['nodes']:
        c = n['content']
        if not c: continue
        labels = [l['name'] for l in (c.get('labels') or {}).get('nodes', [])]
        sub = c.get('subIssuesSummary') or {}
        epic = EL in labels or c['title'].startswith('[Epic]') or sub.get('total', 0) > 0
        items.append(dict(number=c.get('number'), title=c['title'], url=c.get('url'), state=c.get('state', 'OPEN'), status=(n['st'] or {}).get('name'),
            group=(n.get('gr') or {}).get('name') if GF else None, epic=epic, parent=(c.get('parent') or {}).get('number'),
            total=sub.get('total', 0), done=sub.get('completed', 0), updated=c.get('updatedAt'), labels=labels))
    if not p['items']['pageInfo']['hasNextPage']: break
    after = p['items']['pageInfo']['endCursor']
order = [o['name'] for o in ((proj.get('field') or {}).get('options') or [])]
hidden = [i for i in items if i['status'] in HIDE or i['state'] in ('CLOSED', 'MERGED')]
live = [i for i in items if i not in hidden]
counts = {}
for i in live: counts[i['status'] or 'No status'] = counts.get(i['status'] or 'No status', 0) + 1
out = dict(generated=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), title=cfg.get('title', proj['title']),
    project=proj['title'], project_url=proj['url'], statuses=order, group_order=cfg.get('groupOrder', []), needs_me=cfg.get('needsMe', []),
    building=cfg.get('building', []), group_field=GF, hidden_count=len(hidden), hidden_tasks=len([i for i in hidden if not i['epic']]), counts=counts, items=live)
os.makedirs('data', exist_ok=True)
json.dump(out, open('data/board.json', 'w'), indent=1)
print('items', len(items), 'live', len(live), 'hidden', len(hidden), counts)
