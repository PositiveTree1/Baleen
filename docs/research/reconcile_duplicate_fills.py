"""Explain identical API rows using separate signed orders in Polygon logs."""
from collections import Counter
import json
from pathlib import Path
import urllib.request
from eth_utils import keccak

root=Path(__file__).parent/'wallet_audit_2026-09-16'
rpc='https://polygon-bor-rpc.publicnode.com'
def call(method,params):
    req=urllib.request.Request(rpc,data=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode(),headers={'Content-Type':'application/json','User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(req,timeout=20) as r:
        response=json.load(r)
        if response.get('error') or response.get('result') is None:raise ValueError(str(response))
        return response['result']

assert int(call('eth_chainId',[]),16)==137
topic='0x'+keccak(text='OrderFilled(bytes32,address,address,uint8,uint256,uint256,uint256,uint256,bytes32,bytes32)').hex()
exchanges={'0xe111180000d2663c0091e4f400237545b87b996b','0xe2222d279d744050d28e00520010520000310f59'}
checks=[]
for path in root.glob('0x*.json'):
    record=json.loads(path.read_text());address=record['screen']['address']
    counts=Counter(json.dumps(row,sort_keys=True) for row in record['capabilities']['trades_30d']['rows'])
    for encoded,count in counts.items():
        if count<2:continue
        row=json.loads(encoded);receipt=call('eth_getTransactionReceipt',[row['transaction_hash']])
        assert receipt['transactionHash'].lower()==row['transaction_hash'].lower() and receipt['status']=='0x1'
        block=call('eth_getBlockByNumber',[receipt['blockNumber'],False])
        assert block['hash']==receipt['blockHash'] and int(block['timestamp'],16)==row['timestamp']
        matched=[]
        for log in receipt['logs']:
            topics=log.get('topics',[])
            if log['address'].lower() not in exchanges or len(topics)!=4 or topics[0]!=topic:continue
            if '0x'+topics[2][-40:]!=address:continue
            raw=log['data'][2:]
            if len(raw)!=448:continue
            side,token,making,taking,fee,*_= [int(raw[i:i+64],16) for i in range(0,len(raw),64)]
            shares,cash=(taking,making) if side==0 else (making,taking)
            if str(token)==row['token_id'] and ('BUY' if side==0 else 'SELL')==row['side'] and abs(shares/1e6-row['size'])<1e-7 and abs(cash/shares-row['price'])<1e-7:
                matched.append({'log_index':int(log['logIndex'],16),'order_hash':topics[1],'shares':shares/1e6,'cash':cash/1e6})
        checks.append({'wallet':address,'transaction':row['transaction_hash'],'api_multiplicity':count,
            'separate_chain_fills':matched,'explained':len(matched)==count and len({m['log_index'] for m in matched})==count,
            'receipt':receipt,'block_hash':block['hash']})
(root/'duplicate-reconciliation.json').write_text(json.dumps(checks,indent=2))
print(json.dumps([{k:v for k,v in c.items() if k!='receipt'} for c in checks],indent=2))
assert all(c['explained'] for c in checks)
