"""
Windows FILETIME与Unix时间戳转换工具
Windows FILETIME: 自 1601-01-01 00:00:00 UTC 起的 100 纳秒间隔数
Unix Timestamp: 自 1970-01-01 00:00:00 UTC 起的秒数
"""

# 1601到1970年之间的纳秒偏移基数 (以100ns为单位)
# 116444736000000000 = 11644473600 秒 * 10,000,000
FILETIME_EPOCH_DIFF = 116444736000000000


def filetime_to_unix(filetime: int) -> int:
    """将64位FILETIME整数转换为Unix时间戳 (秒)"""
    if not filetime or filetime < FILETIME_EPOCH_DIFF:
        return 0
    return (filetime - FILETIME_EPOCH_DIFF) // 10_000_000


def unix_to_filetime(unix_ts: int) -> int:
    """将Unix时间戳转换为64位FILETIME整数"""
    if not unix_ts or unix_ts <= 0:
        return 0
    return (unix_ts * 10_000_000) + FILETIME_EPOCH_DIFF
