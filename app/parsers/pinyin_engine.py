"""
RecentHub 拼音首字母引擎 (零外部三方依赖)
采用 GB2312 编码区间二分查找 + 常用二级扩展字补丁
实现微秒级中文汉字转换为拼音首字母简码及模糊匹配
"""

import bisect
from typing import Tuple

# GB2312 一级常用字编码边界表 (拼音升序排列)
# 格式: (编码起始, 拼音首字母)
_GBK_BOUNDARY_STARTS = (
    0xB0A1,  # a
    0xB0C5,  # b
    0xB2C1,  # c
    0xB4EE,  # d
    0xB6EA,  # e
    0xB7A2,  # f
    0xB8C1,  # g
    0xB9FE,  # h
    0xBBF7,  # j
    0xBFA6,  # k
    0xC0AC,  # l
    0xC2E8,  # m
    0xC4C3,  # n
    0xC5B6,  # o
    0xC5BE,  # p
    0xC6DA,  # q
    0xC8BB,  # r
    0xC8F6,  # s
    0xCBFA,  # t
    0xCDDA,  # w
    0xCEF4,  # x
    0xD1B9,  # y
    0xD4D1,  # z
    0xD7FA,  # 结束哨兵 (超过GB2312一级字库)
)

_INITIALS = (
    'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'j', 'k', 'l', 'm',
    'n', 'o', 'p', 'q', 'r', 's', 't', 'w', 'x', 'y', 'z'
)

# 常见二级字与生僻字补丁字典 (Unicode -> initial)
_SUPPLEMENTAL_MAP = {
    '怡': 'y', '鑫': 'x', '琪': 'q', '粤': 'y', '晖': 'h', '晟': 's',
    '睿': 'r', '瑜': 'y', '皓': 'h', '喆': 'z', '琦': 'q', '瀚': 'h',
    '煊': 'x', '萱': 'x', '淼': 'm', '焱': 'y', '恺': 'k', '奕': 'y',
    '琛': 'c', '宸': 'c', '潼': 't', '涵': 'h', '沐': 'm', '沛': 'p',
    '泽': 'z', '润': 'r', '洛': 'l', '汐': 'x', '梵': 'f', '楠': 'n',
    '槿': 'j', '桦': 'h', '栩': 'x', '炜': 'w', '煜': 'y', '熙': 'x',
    '熹': 'x', '瑶': 'y', '瑾': 'j', '璨': 'c', '璞': 'p', '璟': 'j'
}


def get_char_initial(char: str) -> str:
    """获取单个字符的拼音首字母或原始字母/数字"""
    if not char:
        return ''
    c = char[0]
    if c.isascii():
        return c.lower() if c.isalnum() else ''
    
    if c in _SUPPLEMENTAL_MAP:
        return _SUPPLEMENTAL_MAP[c]
    
    try:
        gbk = c.encode('gbk')
        if len(gbk) != 2:
            return ''
        code = (gbk[0] << 8) | gbk[1]
        
        # 二分查找对应的拼音起始边界
        idx = bisect.bisect_right(_GBK_BOUNDARY_STARTS, code) - 1
        if 0 <= idx < len(_INITIALS):
            return _INITIALS[idx]
    except Exception:
        pass
    
    return ''


def get_initials(text: str) -> str:
    """
    提取文本中所有字符的拼音首字母简码
    例如: "工作报告 2026.docx" -> "gzbg2026docx"
    """
    if not text:
        return ''
    res = []
    for ch in text:
        init = get_char_initial(ch)
        if init:
            res.append(init)
    return ''.join(res)


def get_pinyin_full(text: str) -> str:
    """
    提取文本的全拼串与常用品牌/英文别名 (支持空格分词与无缝连拼)
    例如: "米哈游启动器" -> "mihayouqidongqi mi ha you qi dong qi mihoyo miho mhy"
    """
    if not text:
        return ''
    try:
        import pypinyin
        py_list = pypinyin.lazy_pinyin(text)
        full_no_space = "".join(py_list).lower()
        full_spaced = " ".join(py_list).lower()
        res = f"{full_no_space} {full_spaced}"
        if "米哈" in text:
            res += " mihoyo miho mhy"
        return res
    except Exception:
        return get_initials(text)


def is_subsequence(sub: str, s: str) -> bool:
    """
    双指针极速判断 sub 是否为 s 的子序列
    """
    if not sub:
        return True
    if not s or len(sub) > len(s):
        return False
    
    it = iter(s)
    return all(c in it for c in sub)


def match_score(text: str, pinyin_initials: str, query: str) -> int:
    """
    多策略匹配打分 (0 表示不匹配，最高 100 分):
    1. 完全一致: 100
    2. 前缀完全匹配: 90
    3. 子串连续包含: 75
    4. 拼音首字母完全一致: 80
    5. 拼音首字母前缀匹配: 70
    6. 拼音首字母子串包含: 60
    7. 拼音首字母子序列匹配: 40
    """
    if not query:
        return 50  # 空查询默认匹配
    
    t_lower = text.lower()
    q_lower = query.lower().strip()
    if not q_lower:
        return 50
    
    # 策略 1: 文本直接全等
    if t_lower == q_lower:
        return 100
    
    # 策略 2: 文本直接前缀
    if t_lower.startswith(q_lower):
        return 90
    
    # 策略 3: 文本直接连续包含
    if q_lower in t_lower:
        return 75
    
    # 若拼音首字母未传入，动态提取
    p_initials = pinyin_initials if pinyin_initials else get_initials(text)
    
    # 策略 4: 拼音首字母全等
    if p_initials == q_lower:
        return 80
    
    # 策略 5: 拼音首字母前缀匹配
    if p_initials.startswith(q_lower):
        return 70
    
    # 策略 6: 拼音首字母子串连续包含
    if q_lower in p_initials:
        return 60
    
    # 策略 7: 拼音首字母子序列匹配 (如 gzbg 匹配 gzb)
    if is_subsequence(q_lower, p_initials):
        return 40
        
    return 0
