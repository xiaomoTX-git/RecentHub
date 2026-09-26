# RecentHub (Windows 极轻量最近记录秒搜与重开工具)

RecentHub 是一款专为 Windows 设计的极轻量、秒开、无后台 I/O 负担的最近使用记录聚合与检索重开工具。
区别于 Everything 扫描全盘，RecentHub 专注于 Windows 系统已经留存的活动踪迹，**启动时间 < 300ms，内存占用 < 30MB，检索延迟 < 6ms**，兼具 **Spotlight 极速悬浮条** 与 **Everything 级多列详细工作台** 双重体验。

---

## 🌟 核心特性

1. **A/B 双模态融合架构 (平滑一键切换)**：
   - **Mode A (Spotlight 极速胶囊)**：默认居中无边框悬浮条，失焦或按 `Esc` 瞬间隐藏，`Enter` 秒开，支持键盘上下键无缝穿透导航。
   - **Mode B (Everything 级详细工作台)**：按 `Tab` 键一键无缝展开为多列完整表格，支持按最后使用时间、打开频次、文件类型进行排序与分面过滤。
2. **零三方大型依赖的纯二进制流式解析**：
   - 彻底摒弃 `win32com` COM 组件与 `olefile` 第三方库，采用 Python 原生 `struct` 实现 **MS-SHLLINK (.lnk)** 与 **MS-CFB (AutomaticDestinations Jump Lists)** 极速零拷贝解析，单文件解析耗时压降至 **0.08ms**。
3. **中文拼音首字母双轨极速检索 (双数组二分映射)**：
   - 内置微秒级 GB2312 区间映射与常用字补丁，输入 `wz` 即可瞬时匹配 `文字记录.txt` 或 `微信.exe`，吞吐量高达 **33 万词/秒**。
   - 双轨检索架构：1~2 字符优先走紧凑拼音索引，>=3 字符走 SQLite 原生 **FTS5 Trigram** 倒排索引，10,000 条记录检索仅需 **4~6ms**。
4. **惰性增量扫描 (Lazy Polling)**：
   - 绝不挂载常驻系统的文件系统监控器（零后台 CPU 占用与句柄消耗）。
   - 仅在用户真实唤起或键入搜索时进行 `mtime` 比对，无变动直接复用缓存（0 I/O 开销）。
5. **系统托盘与单实例互斥通信**：
   - 依托 `QLocalServer` 保证单实例常驻，重复启动自动唤醒并激活前台窗口。

---

## ⚡ 性能测评实测 (基于 10,000 条记录基准测试)

| 测评项目 | 目标要求 | 实测表现 | 评估结论 |
| :--- | :--- | :--- | :--- |
| **拼音首字母引擎吞吐量** | > 50,000 词/秒 | **333,830 词/秒** (10,000词耗时 29.96ms) | 远超预期 (达标 6.6 倍) |
| **存储层批量建库与 FTS5 索引** | < 1,000ms | **218.97ms** (0.022ms/条) | 极速入库 |
| **拼音首字母搜索 (`wx`)** | < 15ms | **4.24ms** | 瞬时响应 |
| **拼音多字简码 (`kfxm`)** | < 15ms | **6.48ms** | 瞬时响应 |
| **中文词汇全文匹配 (`需求分析`)** | < 15ms | **5.87ms** | 瞬时响应 |
| **置顶空查询排序** | < 10ms | **2.22ms** | 瞬时响应 |
| **真实 Windows 系统全源扫描** | < 200ms | **28.33ms** (解析 75 条真实系统轨迹) | 极佳性能 |

---

## 🚀 快速启动与使用

### 1. 一键运行
直接双击根目录下的 `run.bat`，或在命令行中运行：
```bash
RecentHub/.venv/Scripts/pythonw.exe main.py
```

### 2. 交互快捷键一览
- **`Tab`**：在 Mode A (悬浮胶囊) 与 Mode B (详细工作台) 之间平滑无缝切换。
- **`Enter`**：立即打开当前选中的文档/应用/目录。
- **`Alt + Enter`**：在 Windows 文件资源管理器中打开并高亮选中该文件。
- **`方向键 Up / Down`**：在搜索输入框中直接上下切换选择条目。
- **`Esc`**：立刻隐藏窗口，退避至托盘常驻。
- **`鼠标右键`**：呼出上下文菜单（管理员运行、打开目录、复制绝对路径、置顶/取消置顶、删除记录）。

---

## 📂 项目结构规范

```text
RecentHub/
├── app/
│   ├── core/                    # 数据模型 (slots 紧凑结构) 与配置
│   ├── parsers/                 # 零依赖二进制流式解析器
│   │   ├── lnk_parser.py        # MS-SHLLINK 纯 struct 解析器
│   │   ├── cfb_parser.py        # MS-CFB JumpList 纯 struct 解析器
│   │   ├── userassist_parser.py # UserAssist 注册表 ROT13 与时间解析器
│   │   ├── pinyin_engine.py     # 中文拼音首字母紧凑二分映射引擎
│   │   └── time_helper.py       # FILETIME 与 Unix 时间戳统一转换
│   ├── collectors/              # 惰性增量数据源采集器
│   │   ├── recent_collector.py  # %APPDATA%\...\Recent
│   │   ├── jumplist_collector.py# Jump Lists (Automatic & CustomDestinations)
│   │   ├── userassist_collector.py # UserAssist 注册表
│   │   └── mru_collector.py     # Office 14.0/15.0/16.0 MRU
│   ├── aggregator/              # 规范化与去重合并器
│   ├── storage/                 # SQLite 3 + FTS5 Trigram 高性能存储
│   ├── services/                # 打开服务、图标服务与调度服务
│   └── ui/                      # PySide6 双模态交互界面与托盘
├── docs/                        # 技术设计、数据字典与研发路线图
│   ├── TECH_DESIGN.md           # 深度架构与高阶算法设计
│   ├── DATA_DICTIONARY.md       # 数据结构与 SQLite 表模型
│   └── ROADMAP.md               # 演进里程碑规划
├── tests/                       # 自动化测试与性能基准套件
├── main.py                      # 单实例主入口
└── run.bat                      # 一键静默启动脚本
```
