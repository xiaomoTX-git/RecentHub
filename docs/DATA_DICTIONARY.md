# RecentHub 数据字典与存储规范 (DATA_DICTIONARY)
版本：v1.1

---

## 1. 内存核心实体模型 (Python 数据结构)

为了追求极致轻量和内存扁平化，内存实体避免使用重量级 ORM 模型，定义为带有 `__slots__` 的结构体：

```python
class RecentItem:
    __slots__ = (
        'id',             # int: 数据库自增主键 (可选)
        'display_name',   # str: 显示标题 (如 '年度经营分析.xlsx')
        'target_path',    # str: 规范化绝对路径 (如 'D:\Work\Docs\年度经营分析.xlsx')
        'arguments',      # str: 启动参数 (如有)
        'item_type',      # str: 'file' | 'app' | 'folder' | 'url'
        'extension',      # str: 扩展名小写 (如 '.xlsx', '.exe')
        'pinyin_initials',# str: 拼音首字母紧凑串 (如 'ndjyfx')
        'last_used_at',   # int: Unix 时间戳 (秒)
        'use_count',      # int: 累计打开/使用频次
        'exists_status',  # bool: 目标文件当前是否存在 (延迟探测)
        'pinned',         # bool: 是否置顶固定
        'sources',        # list[str]: 来源集合，如 ['recent_lnk', 'jumplist']
    )
```

---

## 2. 关系数据库表结构 (SQLite 3 + FTS5)

### 2.1 主表：`items`
存储规范化去重后的全局记录清单。

| 字段名 | 类型 | 约束 | 默认值 | 业务含义说明 |
| :--- | :--- | :--- | :--- | :--- |
| **id** | INTEGER | PRIMARY KEY AUTOINCREMENT | - | 唯一自增主键 |
| **display_name** | TEXT | NOT NULL | - | 文件名或应用名称，用于界面高亮渲染 |
| **target_path** | TEXT | NOT NULL UNIQUE | - | 规范化绝对路径（小写比较），核心去重键 |
| **arguments** | TEXT | - | `''` | 运行附加参数（如浏览器 URL 或程序入参） |
| **item_type** | TEXT | NOT NULL | `'file'` | 类型标记：`file`, `app`, `folder`, `url` |
| **extension** | TEXT | - | `''` | 扩展名小写格式（如 `.docx`） |
| **pinyin_initials**| TEXT | - | `''` | 拼音首字母简码（如“工作报告”存 `gzbg`） |
| **last_used_at** | INTEGER | NOT NULL | 0 | 最后使用时间的 Unix 秒级时间戳（用于倒序排） |
| **use_count** | INTEGER | NOT NULL | 1 | 累计使用次数，每次重新发现则根据源累加 |
| **exists_status**| INTEGER | NOT NULL | 1 | 1=存在，0=目标文件已删除或失效 |
| **pinned** | INTEGER | NOT NULL | 0 | 1=固定置顶，0=普通流转 |
| **created_at** | INTEGER | NOT NULL | strftime('%s') | 本条目首次收录时间戳 |

**关键索引**：
- `CREATE INDEX idx_items_last_used ON items(last_used_at DESC);`
- `CREATE INDEX idx_items_item_type ON items(item_type);`
- `CREATE INDEX idx_items_extension ON items(extension);`

---

### 2.2 倒排全文检索虚表：`items_fts`
利用 SQLite 原生 FTS5 实现任意子串与前缀的高性能即时检索。

```sql
CREATE VIRTUAL TABLE items_fts USING fts5(
    display_name,
    target_path,
    extension,
    pinyin_initials,
    content='items',
    content_rowid='id',
    tokenize='trigram'
);
```

**Trigram 分词机制说明**：
- 将任意文本按 3 字符滑窗切片，彻底免去中文第三方结巴分词依赖；
- 原生支持任意长度（>=1 字符）的前缀、后缀及中段模糊匹配；
- 极佳支持英文扩展名（如 `xlsx`）及拼音首字母片段。

---

### 2.3 来源关联表：`item_sources`
追踪每个条目是由哪些 Windows 轨迹点贡献的，方便用户查看与调试。

| 字段名 | 类型 | 约束 | 说明 |
| :--- | :--- | :--- | :--- |
| **id** | INTEGER | PRIMARY KEY AUTOINCREMENT | 自增主键 |
| **item_id** | INTEGER | REFERENCES items(id) | 关联主表条目 |
| **source_type** | TEXT | NOT NULL | `recent_lnk`, `jumplist`, `office_mru`, `userassist` |
| **source_detail**| TEXT | - | 原始文件路径或注册表项名称 |
| **discovered_at**| INTEGER | - | 本次采集命中时间戳 |

---

### 2.4 排除规则表：`excluded_rules`
支持用户在界面右键“隐藏此项目”或设置中配置的屏蔽黑名单。

| 字段名 | 类型 | 约束 | 示例值 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| **id** | INTEGER | PRIMARY KEY | - | 自增主键 |
| **rule_type** | TEXT | NOT NULL | `path_prefix` | 规则类型：`path_prefix`, `extension`, `name_contains` |
| **pattern** | TEXT | NOT NULL | `C:\Users\...\AppData\Local\Temp` | 匹配模式（自动转小写） |
