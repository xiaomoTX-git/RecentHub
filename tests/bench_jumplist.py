
import os
import time
from test_cfb_prototype import parse_cfb
from app.parsers.lnk_parser import LnkParser

auto_dir = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Recent\AutomaticDestinations")
target_file = os.path.join(auto_dir, "f01b4d95cf55d32a.automaticDestinations-ms")

t0 = time.perf_counter()
res = parse_cfb(target_file)
valid_targets = []
for k, v in res.items():
    if k != 'DestList' and len(v) >= 76:
        lnk = LnkParser.parse_bytes(v)
        if lnk.target_path:
            valid_targets.append(lnk)
t1 = time.perf_counter()
print(f"Parsed CFB + 60 LNKs in {(t1 - t0)*1000:.2f}ms")
