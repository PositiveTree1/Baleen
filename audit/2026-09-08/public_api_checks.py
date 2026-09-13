"""Small public GET-only contract probes; never loads app secrets or writes accounts/orders."""
import asyncio
from datetime import datetime, timezone
import json
import httpx

async def main():
    out=[]
    async with httpx.AsyncClient(timeout=15) as client:
        async def get(name,url,params):
            try:
                r=await client.get(url,params=params)
                try: data=r.json()
                except Exception: data=None
                row={'name':name,'url':str(r.url),'status':r.status_code,
                     'count':len(data) if isinstance(data,list) else None,
                     'keys':sorted(data[0].keys()) if isinstance(data,list) and data and isinstance(data[0],dict) else None}
                if r.status_code>=400: row['error']=r.text[:180]
                out.append(row)
                return data,row
            except Exception as e:
                row={'name':name,'error':type(e).__name__+': '+str(e)}
                out.append(row)
                return None,row
        _,_=await get('legacy_leaderboard','https://data-api.polymarket.com/leaderboard',{'timePeriod':'ALL','limit':1})
        lb,_=await get('v1_leaderboard','https://data-api.polymarket.com/v1/leaderboard',{'timePeriod':'ALL','limit':1})
        if isinstance(lb,list) and lb:
            wallet=lb[0].get('proxyWallet')
            if wallet:
                for sort in ('timestamp','TIMESTAMP'):
                    await get('closed_sort_'+sort,'https://data-api.polymarket.com/closed-positions',{'user':wallet,'limit':2,'sortBy':sort})
        trades,_=await get('recent_trades','https://data-api.polymarket.com/trades',{'limit':2})
        if isinstance(trades,list) and trades:
            cid=trades[0].get('conditionId')
            wallet=trades[0].get('proxyWallet')
            for param in ('conditionId','market'):
                d,r=await get('trade_filter_'+param,'https://data-api.polymarket.com/trades',{param:cid,'limit':3})
                if isinstance(d,list): r['all_match_requested_market']=all(t.get('conditionId')==cid for t in d)
            for param in ('condition_id','condition_ids'):
                d,r=await get('gamma_filter_'+param,'https://gamma-api.polymarket.com/markets',{param:cid,'limit':2})
                if isinstance(d,list): r['all_match_requested_market']=all(t.get('conditionId')==cid for t in d)
            if wallet:
                for param in ('maker_address','user'):
                    d,r=await get('wallet_filter_'+param,'https://data-api.polymarket.com/trades',{param:wallet,'limit':3})
                    if isinstance(d,list): r['all_match_requested_wallet']=all(t.get('proxyWallet','').lower()==wallet.lower() for t in d)
    print(json.dumps({'checked_at':datetime.now(timezone.utc).isoformat(),'scope':'Public GET-only sample; not exhaustive API certification','results':out},indent=2))

if __name__=='__main__': asyncio.run(main())
