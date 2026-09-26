"""
RecentHub MS-CFB (Compound File Binary) 纯二进制解析器
专用于解析 Windows AutomaticDestinations-ms Jump Lists
完全基于标准库 struct 实现，零外部依赖，极速提取内嵌 LNK 流
"""

import struct
from typing import Dict, List, Tuple
from app.parsers.lnk_parser import LnkParser, LnkInfo


class CfbParser:
    """纯 Python 高性能复合文档流提取器"""

    @staticmethod
    def extract_streams(data: bytes) -> Dict[str, bytes]:
        """从 CFB 二进制数据中解包所有 Stream 数据流 (以流名称为字典键)"""
        streams = {}
        if len(data) < 512 or data[:8] != b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
            return streams

        try:
            sector_shift = struct.unpack_from('<H', data, 30)[0]
            mini_shift = struct.unpack_from('<H', data, 32)[0]
            sector_size = 1 << sector_shift
            mini_sector_size = 1 << mini_shift

            dir_start_sid = struct.unpack_from('<I', data, 48)[0]
            mini_cutoff = struct.unpack_from('<I', data, 56)[0]
            minifat_start_sid = struct.unpack_from('<I', data, 60)[0]
            minifat_cnt = struct.unpack_from('<I', data, 64)[0]

            # 读取 DIFAT (前109个扇区索引)
            difat = [struct.unpack_from('<I', data, 76 + i * 4)[0] for i in range(109)]
            fat_sids = [sid for sid in difat if sid < 0xFFFFFFFC]

            # 加载 FAT 分配表
            fat = []
            for sid in fat_sids:
                pos = (sid + 1) * sector_size
                s_data = data[pos:pos + sector_size]
                entries = struct.unpack_from(f'<{len(s_data) // 4}I', s_data)
                fat.extend(entries)

            def get_chain(start_sid: int, is_mini: bool = False) -> List[int]:
                chain = []
                visited = set()
                curr = start_sid
                cur_fat = minifat if is_mini else fat
                while curr < 0xFFFFFFFC and curr < len(cur_fat):
                    # 防御环状 FAT 链：畸形文件会导致无限循环挂死扫描线程
                    if curr in visited:
                        break
                    visited.add(curr)
                    chain.append(curr)
                    curr = cur_fat[curr]
                return chain

            # 加载 MiniFAT
            minifat = []
            if minifat_start_sid < 0xFFFFFFFC and minifat_cnt > 0:
                for sid in get_chain(minifat_start_sid):
                    pos = (sid + 1) * sector_size
                    s_data = data[pos:pos + sector_size]
                    entries = struct.unpack_from(f'<{len(s_data) // 4}I', s_data)
                    minifat.extend(entries)

            # 读取目录流
            dir_chain = get_chain(dir_start_sid)
            dir_data = bytearray()
            for sid in dir_chain:
                pos = (sid + 1) * sector_size
                dir_data.extend(data[pos:pos + sector_size])

            if len(dir_data) < 128:
                return streams

            # 获取 Mini-stream 起始扇区与总大小
            root_start_sid = struct.unpack_from('<I', dir_data, 116)[0]
            mini_stream = bytearray()
            if root_start_sid < 0xFFFFFFFC:
                for sid in get_chain(root_start_sid):
                    pos = (sid + 1) * sector_size
                    mini_stream.extend(data[pos:pos + sector_size])

            def read_stream_data(start_sid: int, size: int) -> bytes:
                if size < mini_cutoff and mini_stream:
                    stream_bytes = bytearray()
                    for msid in get_chain(start_sid, is_mini=True):
                        mpos = msid * mini_sector_size
                        stream_bytes.extend(mini_stream[mpos:mpos + mini_sector_size])
                    return bytes(stream_bytes[:size])
                else:
                    stream_bytes = bytearray()
                    for sid in get_chain(start_sid, is_mini=False):
                        pos = (sid + 1) * sector_size
                        stream_bytes.extend(data[pos:pos + sector_size])
                    return bytes(stream_bytes[:size])

            # 遍历目录项 (每项 128 字节)
            entry_count = len(dir_data) // 128
            for i in range(entry_count):
                epos = i * 128
                raw_name = dir_data[epos:epos + 64]
                name_len = struct.unpack_from('<H', dir_data, epos + 64)[0]
                obj_type = dir_data[epos + 66]
                if name_len >= 4:
                    # name_len 含结尾 \x00\x00，需截去 2 字节并限制在 64 字节名称域内
                    usable = (min(name_len - 2, 64) // 2) * 2
                    name = raw_name[:usable].decode('utf-16-le', errors='replace')
                else:
                    name = ""
                start_sid = struct.unpack_from('<I', dir_data, epos + 116)[0]
                size = struct.unpack_from('<Q', dir_data, epos + 120)[0]
                
                # obj_type == 2 为 Stream 流
                if obj_type == 2 and size > 0:
                    streams[name] = read_stream_data(start_sid, size)

        except Exception:
            pass

        return streams

    @classmethod
    def parse_jumplist_file(cls, file_path: str) -> List[Tuple[str, LnkInfo]]:
        """
        解析 AutomaticDestinations-ms 文件，返回 [(stream_name, LnkInfo), ...]
        """
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            streams = cls.extract_streams(data)
            results = []
            for name, stream_bytes in streams.items():
                if name != 'DestList' and len(stream_bytes) >= 76:
                    lnk = LnkParser.parse_bytes(stream_bytes)
                    if lnk.is_valid:
                        results.append((name, lnk))
            return results
        except Exception:
            return []
