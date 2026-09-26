
import os
import struct
from test_cfb_prototype import parse_cfb

auto_dir = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Recent\AutomaticDestinations")
target_file = os.path.join(auto_dir, "f01b4d95cf55d32a.automaticDestinations-ms")
res = parse_cfb(target_file)
dl = res.get('DestList', b'')

offset = 32
for i in range(5):
    if offset + 128 > len(dl):
        break
    stream_num = struct.unpack_from('<I', dl, offset + 88)[0] # let's check offsets
    # let's search for stream number in range offset .. offset+128
    # Since streams are "1", "2", "3", etc.
    str_len = struct.unpack_from('<H', dl, offset + 114)[0] if offset + 116 <= len(dl) else 0
    print(f"Entry {i} at offset {offset}: stream_id candidates:")
    for probe in range(80, 110, 4):
        val = struct.unpack_from('<I', dl, offset + probe)[0]
        if 1 <= val <= 100:
            print(f"  candidate at +{probe}: {val}")
    
    # check string length
    if offset + 116 <= len(dl):
        # In Win 10, length of Unicode string (character count) is at offset + 114
        u16_chars = struct.unpack_from('<H', dl, offset + 114)[0]
        u16_str = dl[offset + 116 : offset + 116 + u16_chars * 2].decode('utf-16-le', errors='replace')
        print(f"  String at +114: ({u16_chars} chars) '{u16_str}'")
        offset = offset + 116 + u16_chars * 2 + 4 # 4 extra bytes at end
    else:
        break
