
import os
import struct
from test_cfb_prototype import parse_cfb

auto_dir = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Recent\AutomaticDestinations")
target_file = os.path.join(auto_dir, "f01b4d95cf55d32a.automaticDestinations-ms")
res = parse_cfb(target_file)
dest_list_bytes = res.get('DestList', b'')

print(f"DestList size: {len(dest_list_bytes)}")
if len(dest_list_bytes) >= 32:
    version, total_entries, pin_entries = struct.unpack_from('<III', dest_list_bytes, 0)
    print(f"Header: version={version}, total_entries={total_entries}, pin_entries={pin_entries}")
    
    # In Windows 10/11:
    # Header is 32 bytes.
    # Entries start at 32.
    # Let's inspect entry size. Common entry sizes are 114 bytes (Win 7/8), 128 bytes (Win 10), or variable with string length.
    # Let's see: (len(dest_list_bytes) - 32) / total_entries
    if total_entries > 0:
        entry_size = (len(dest_list_bytes) - 32) / total_entries
        print(f"Calculated entry size: {entry_size}")
