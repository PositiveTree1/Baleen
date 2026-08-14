import glob
import os
import re

files = glob.glob('C:/Users/arthu/Downloads/polymarketV3-main/polymarketV3-main/ScriptsTitan/*.py')
print(f"Found {len(files)} python files in ScriptsTitan.")
for f in sorted(files):
    with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
        content = fp.read()
    urls = set(re.findall(r'https?://[^\s"\'\)]+', content))
    if urls:
        print(f"\n=== {os.path.basename(f)} ===")
        for u in sorted(urls):
            print(f"  {u}")
