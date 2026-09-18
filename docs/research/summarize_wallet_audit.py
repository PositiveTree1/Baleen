"""Validate saved API evidence and plot original provider curves (no rescaling)."""
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

root = Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).parent/'wallet_audit_2026-09-16'
summary=[]
checks=[]
def check(label, passed, detail=None):
    checks.append({'check':label,'passed':bool(passed),'detail':detail})

fig,axes=plt.subplots(3,2,figsize=(13,10),layout='constrained')
plot_names=['xifutloong3','ethanaz','Dreamlawn']
for path in sorted(root.glob('0x*.json')):
    record=json.loads(path.read_text(encoding='utf-8'))
    screen=record['screen']; c=record['capabilities']; address=screen['address']; name=screen['name']
    t=c['trades_30d']; a=c['activity_30d']; rows=t['rows']
    check(name+' trade cursor exhausted',t['coverage']['complete'])
    check(name+' activity cursor exhausted',a['coverage']['complete'])
    check(name+' trade identity/order/window',t['summary']['wrong_wallet']==0 and t['summary']['descending'] and t['summary']['outside_requested_window']==0)
    check(name+' trade diagnostic uniqueness',t['summary']['distinct_diagnostic_keys']==len(rows))
    trade_counts=Counter((r.get('transaction_hash'),r.get('token_id'),r.get('side'),r.get('size'),r.get('price'),r.get('timestamp')) for r in rows)
    activity_counts=Counter((r.get('transaction_hash'),r.get('token_id'),r.get('side'),r.get('size'),r.get('price'),r.get('timestamp')) for r in a['rows'] if r.get('type')=='TRADE')
    # An observed mismatch is retained, not hidden or forced into a passing assertion.
    matching=sum((trade_counts&activity_counts).values())
    points=c['curve_all'].get('data',{}).get('points',[])
    times=[p['timestamp'] for p in points]
    check(name+' curve timestamps ordered and unique',times==sorted(set(times)))
    identity_errors=[]
    for p in points:
        for total,parts in [('position_pnl',['realized_pnl','unrealized_pnl']),('economic_pnl',['position_pnl','wallet_income'])]:
            if all(isinstance(p.get(k),(int,float)) for k in [total]+parts):
                identity_errors.append(abs(p[total]-sum(p[k] for k in parts)))
    check(name+' P&L component identities',max(identity_errors,default=0)<0.01, max(identity_errors,default=0))
    for status in ('OPEN','REDEEMABLE','CLOSED'):
        v=c['positions_'+status]
        check(name+' '+status+' position cursor exhausted',v['coverage']['complete'])
        check(name+' '+status+' identity',all(r.get('proxy_wallet')==address for r in v['rows']))
    entry={'name':name,'address':address,'fills_7d':screen['trades']['rows'],'fills_30d':len(rows),
        'fills_per_calendar_day_30d':len(rows)/30,'max_daily_fills_30d':max(t['summary']['daily_fills'].values(),default=0),
        'active_dates_30d':len(t['summary']['daily_fills']), 'curve_points':len(points),
        'distinct_curve_source_blocks':len({p.get('source_block') for p in points}),
        'curve_first':min(times) if times else None,'curve_last':max(times) if times else None,
        'matching_activity_trades':matching,'activity_trade_rows':sum(activity_counts.values()),
        'activity_types':dict(Counter(r.get('type') for r in a['rows'])),
        'curve_source_fidelity':c['curve_all'].get('data',{}).get('source_fidelity')}
    summary.append(entry)
    if name in plot_names:
        idx=plot_names.index(name)
        dates=[datetime.fromtimestamp(p['timestamp'],timezone.utc) for p in points]
        for key,label in [('economic_pnl','Economic P&L'),('trade_pnl','Trade P&L')]:
            axes[idx,0].plot(dates,[p.get(key,float('nan'))/1000 for p in points],label=label,linewidth=1.5)
        axes[idx,0].set_title(name+' — provider cumulative P&L')
        axes[idx,0].set_ylabel('USD thousands')
        axes[idx,0].legend(fontsize=8)
        daily=t['summary']['daily_fills']; x=[datetime.strptime(d,'%Y-%m-%d') for d in daily]
        axes[idx,1].bar(x,list(daily.values()),width=.8,color='#277d8e')
        axes[idx,1].axhline(30,color='#a33a37',linestyle='--',label='30 fills/day')
        axes[idx,1].set_title(name+' — observed fills, last 30 days')
        axes[idx,1].set_ylabel('Raw fills (not grouped orders)')
        for ax in axes[idx]:
            ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3,maxticks=5))
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
            ax.grid(alpha=.15)
fig.suptitle('API evidence fixtures — not approved copy wallets\nOriginal series; trade P&L and economic P&L are different metrics',fontsize=13)
fig.savefig(root/'wallet-curves.png',dpi=150)
fig.savefig(root/'wallet-curves.svg')
requests=[]
for path in root.glob('*requests.json'):
    requests.extend(json.loads(path.read_text()))
result={'wallets':summary,'checks':checks,'passed':sum(c['passed'] for c in checks),'failed':sum(not c['passed'] for c in checks),'recorded_json_requests':len(requests),'statuses':dict(Counter(r.get('status','error') for r in requests))}
(root/'validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ('checks','wallets')},indent=2))
for c in checks:
    if not c['passed']:print(c)
for r in summary:print(json.dumps(r))
