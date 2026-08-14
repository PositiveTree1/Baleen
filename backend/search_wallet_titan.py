import glob
import re

files = glob.glob('C:/Users/arthu/Downloads/polymarketV3-main/polymarketV3-main/ScriptsTitan/*.py')
for f in files:
    with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
        lines = fp.readlines()
    for idx, l in enumerate(lines):
        if 'profile' in l.lower() or 'fetch_wallet' in l.lower() or 'activity' in l.lower() or 'positions' in l.lower():
            if any(k in l for k in ['http', 'url', 'polymarket.com', 'def ', 'data-api']):
                print(f"{f}:{idx+1}: {l.strip()}")
