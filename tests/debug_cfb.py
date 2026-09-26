
import os
from test_cfb_prototype import parse_cfb

auto_dir = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Recent\AutomaticDestinations")
files = os.listdir(auto_dir)
for f in files[:3]:
    fp = os.path.join(auto_dir, f)
    res = parse_cfb(fp)
    print(f"File {f}: streams count={len(res)}")
    for k, v in res.items():
        print(f"  Stream '{k}': {len(v)} bytes, magic={v[:8].hex() if len(v)>=8 else ''}")
