#!/usr/bin/env python3
"""Read a GitHub Projects v2 board and bake it into data/board.json. Read-only.
Config: board.config.json (see README). Needs GH_TOKEN (or BOARD_TOKEN) with read access to the project."""
import json, os, subprocess, sys, datetime
CFG = os.environ.get('BOARD_CONFIG', 'board.config.json')
try: cfg = json.load(open(CFG))
except FileNotFoundError: sys.exit('Config error: %s not found. Copy board.config.json from the README and set owner and project.' % CFG)
except ValueError as e: sys.exit('Config error: %s is not valid JSON (%s).' % (CFG, e))
for k in ('owner', 'project'):
    if not cfg.get(k): sys.exit('Config error: "%s" is missing in %s.' % (k, CFG))
if not str(cfg['project']).isdigit(): sys.exit('Config error: "project" must be the project number, for example 1. Got %r.' % cfg['project'])
OWNER = cfg['owner']; NUM = int(cfg['project']); KIND = 'organization' if cfg.get('ownerType', 'user') == 'org' or cfg.get('ownerType') == 'organization' else 'user'
SF = cfg.get('statusField', 'Status'); GF = cfg.get('groupField'); EL = cfg.get('epicLabel', 'epic')
EF = cfg.get('estimateField')
HIDE = set(cfg.get('hideStatuses', ['Done']))
est = ('es:fieldValueByName(name:"%s"){... on ProjectV2ItemFieldNumberValue{number}}' % EF) if EF else ''
grp = ('gr:fieldValueByName(name:"%s"){... on ProjectV2ItemFieldSingleSelectValue{name}}' % GF) if GF else ''
Q = '''query($a:String){%s(login:"%s"){projectV2(number:%d){title url
 fields(first:60){nodes{... on ProjectV2FieldCommon{name}}}
 field(name:"%s"){... on ProjectV2SingleSelectField{options{name}}}
 items(first:100,after:$a){pageInfo{hasNextPage endCursor} nodes{
 st:fieldValueByName(name:"%s"){... on ProjectV2ItemFieldSingleSelectValue{name}} %s %s
 content{... on Issue{number title url state stateReason closedAt updatedAt labels(first:8){nodes{name}} parent{number} subIssuesSummary{total completed}}
         ... on PullRequest{number title url state updatedAt labels(first:8){nodes{name}}}
         ... on DraftIssue{title}}}}}}}''' % (KIND, OWNER, NUM, SF, SF, grp, est)
def gql(after):
    cmd = ['gh', 'api', 'graphql', '-f', 'query=' + Q] + (['-f', 'a=' + after] if after else [])
    env = dict(os.environ); env['GH_TOKEN'] = os.environ.get('BOARD_TOKEN') or os.environ.get('GH_TOKEN', '')
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if r.returncode and 'Could not resolve' in r.stderr: sys.exit('Config error: a field name in the config does not exist on project %s (statusField "%s", groupField "%s", estimateField "%s"). GitHub said: %s' % (NUM, SF, GF, EF, r.stderr.strip()[:160]))
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
            group=(n.get('gr') or {}).get('name') if GF else None, estimate=(n.get('es') or {}).get('number') if EF else None, epic=epic, parent=(c.get('parent') or {}).get('number'),
            closed=c.get('closedAt'), reason=c.get('stateReason'), total=sub.get('total', 0), done=sub.get('completed', 0), updated=c.get('updatedAt'), labels=labels))
    if not p['items']['pageInfo']['hasNextPage']: break
    after = p['items']['pageInfo']['endCursor']
FN = [f['name'] for f in (proj.get('fields') or {}).get('nodes', []) if f]
for key in ('statusField', 'groupField', 'estimateField'):
    v = cfg.get(key) or ('Status' if key == 'statusField' else None)
    if v and FN and v not in FN: sys.exit('Config error: "%s" is "%s" but project %s has these fields: %s.' % (key, v, NUM, ', '.join(FN)))
order = [o['name'] for o in ((proj.get('field') or {}).get('options') or [])]
if not order: sys.exit('Config error: field "%s" has no options. It must be a single select field.' % SF)
for key in ('hideStatuses', 'needsMe', 'building'):
    bad = [x for x in cfg.get(key, []) if x not in order]
    if bad: sys.exit('Config error: "%s" lists %s, but the %s options are: %s.' % (key, ', '.join(bad), SF, ', '.join(order)))
hidden = [i for i in items if i['status'] in HIDE or i['state'] in ('CLOSED', 'MERGED')]
live = [i for i in items if i not in hidden]
done = sorted([i for i in hidden if i.get('closed') and i.get('reason') != 'NOT_PLANNED' and not i['epic'] and i['status'] in HIDE], key=lambda i: i['closed'])
last_closed = ({k: done[-1][k] for k in ('number', 'title', 'url', 'closed')} if done else None)
recent_done = [{k: i[k] for k in ('number', 'title', 'url', 'closed')} for i in reversed(done[-6:])]
working = None
RUNNAME = cfg.get('workRunName', 'Daily')
try:
    repo = cfg.get('workRepo', 'hn-1m-explorer')
    runs = json.loads(subprocess.run(['gh', 'api', 'repos/%s/%s/actions/runs?per_page=10' % (OWNER, repo)], capture_output=True, text=True, check=True).stdout)['workflow_runs']
    now = datetime.datetime.now(datetime.timezone.utc)
    for r in runs:
        if not RUNNAME or RUNNAME not in r['name']: continue
        st = datetime.datetime.strptime(r['run_started_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc)
        if r['status'] in ('in_progress', 'queued') or (now - st).total_seconds() < 600:
            working = dict(name=r['name'], url=r['html_url'], started=r['run_started_at'], status=r['status']); break
except Exception as e:
    print('runs unavailable', e)
if not working:
    dev = [i for i in live if i['status'] == 'Dev' and not i['epic']]
    if dev: working = dict(name='#%d %s' % (dev[0]['number'], dev[0]['title']), url=dev[0]['url'], started=None, status='dev')
counts = {}
for i in live: counts[i['status'] or 'No status'] = counts.get(i['status'] or 'No status', 0) + 1
out = dict(generated=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), title=cfg.get('title', proj['title']),
    project=proj['title'], project_url=proj['url'], statuses=order, group_order=cfg.get('groupOrder', []), needs_me=cfg.get('needsMe', []),
    building=cfg.get('building', []), group_field=GF, hidden_count=len(hidden), hidden_tasks=len([i for i in hidden if not i['epic']]), counts=counts, tiles=cfg.get('tiles'), last_closed=last_closed, recent_done=recent_done, working=working, items=live)
os.makedirs('data', exist_ok=True)
json.dump(out, open('data/board.json', 'w'), indent=1)
print('items', len(items), 'live', len(live), 'hidden', len(hidden), counts)
