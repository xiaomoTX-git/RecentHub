# RecentHub 研发与功能路线图 (ROADMAP)
版本：v1.1
状态：落地推进

---

## 1. 总体里程碑总览

| 里程碑 | 名称 | 核心目标 | 关键产出 | 性能目标 |
| :--- | :--- | :--- | :--- | :--- |
| **M0** | **极速核心验证** | 验证零三方二进制 LNK 解析、拼音首字母算法与 SQLite FTS5 原型 | 核心解析脚本与基准测试 | LNK 单条解析 < 0.1ms，拼音检索 < 5ms |
| **M1** | **轻量 MVP 引擎** | 实现 Recent 目录、UserAssist 注册表采集，AB 模态无缝切换 UI | 可运行的桌面程序 (Dev版) | 启动时间 < 400ms，列表承载 10,000+ 条 |
| **M2** | **全源聚合与精细化** | 接入 Jump Lists (CFB)、Office MRU，异步图标流，全局热键与托盘 | 完整功能内测版 | 内存常驻 < 40MB，搜索无感知延迟 |
| **M3** | **极致优化与便携发布** | 排除规则、FTS5 前缀优化、单实例互斥、PyInstaller 极简打包 | 绿色单文件 / 目录免安装包 | 安装包 < 25MB，零环境依赖 |
| **M4** | **高级特性扩展** | 历史热力图、一键导出、扩展名黑白名单、Everything 联动接口 | v1.x 正式版 | 稳定支撑 100,000 条混合索引 |

---

## 2. 详细演进步骤

### 阶段 M0：极轻量算法与协议攻坚 (1-2 天)
- [x] **架构设计**：完成 `TECH_DESIGN.md`、`ROADMAP.md`、`DATA_DICTIONARY.md`。
- [ ] **LnkBinaryParser**：纯 Python 标准库编写 76 字节 Header 校验与 LinkInfo 偏移切片，实现零 COM 组件依赖解析。
- [ ] **PinyinEngine**：编写紧凑拼音首字母生成器（双数组二分映射表，支持汉字 -> 首字母缩写）。
- [ ] **FTS5 Benchmark**：验证 Trigram 分词在中英混合模糊匹配下的召回率与耗时。

### 阶段 M1：MVP 骨架与双模态界面 (2-3 天)
- [ ] **采集层**：完成 `RecentCollector`（遍历 `%APPDATA%\...\Recent`）与 `UserAssistCollector`（ROT13 解密与 FILETIME 还原）。
- [ ] **聚合层**：实现路径规范化（环境变量展开、长路径转换、小写去重、多源时间戳取最大值）。
- [ ] **存储层**：封装轻量 SQLite DAO，支持 WAL 模式高并发只读。
- [ ] **展现层**：
  - 构建 `MainWindow` 支持 Mode A (Spotlight 极速悬浮条) 与 Mode B (Everything 级完整多列大表) 一键平滑切换。
  - 实现基于 `QAbstractTableModel` 的纯虚拟滚动模型。
  - 接入 150ms 搜索防抖与 `Enter` 快速唤起。

### 阶段 M2：全源接驳与交互闭环 (3-5 天)
- [ ] **JumpListParser**：实现 MS-CFB 复合文档轻量解析，提取 `DestList` 与内嵌 LNK 流。
- [ ] **OfficeMruCollector**：读取 Office 2013/2016/2019/365 注册表 MRU 条目。
- [ ] **IconService**：基于 Win32 `SHGetFileInfoW` 的多线程异步图标提取与内存 LRU 缓存。
- [ ] **HotkeyService**：基于 Win32 `RegisterHotKey` 的原生全局热键唤出 (默认 `Alt+Space`)，失焦自动沉降。
- [ ] **TrayService**：系统托盘常驻、右键菜单、一键显示/隐藏。

### 阶段 M3：生产级加固与打包 (2-3 天)
- [ ] **数据与隐私**：一键清空记录、敏感路径前缀过滤（如 Temp、隐私文件夹）。
- [ ] **单实例检测**：通过 Windows 命名管道或 QLocalServer 保证单进程运行，二次启动激活已有窗口。
- [ ] **PyInstaller 瘦身打包**：
  - 剥离 PySide6 未使用组件 (如 WebEngine, 3D, Qml, Multimedia 等)，将包体积压缩至极限。
  - 提供绿色免安装目录与单文件两种分发形态。

---

## 3. 技术风险点与保障预案

| 风险点 | 影响面 | 保障预案 |
| :--- | :--- | :--- |
| **Windows 11 版本 Jump List 格式微调** | 部分应用最近项解析失败 | 采用流结构容错解析：遇到未识别格式跳过当前 entry，不阻断整体采集进程，并记入调试日志。 |
| **长路径或非常规字符路径** | 文件无法打开或路径规范化异常 | 统一采用 `ctypes.windll.kernel32.GetLongPathNameW` 与 `os.path.normpath` 保证绝对宽字符路径正确。 |
| **拼音多音字漏搜** | 中文搜索体验不一致 | 核心首字母表为常用字建立全排列简码（例如“长”预置 `c` 与 `z`），两字母都计入索引。 |
| **杀毒软件对全局快捷键警惕** | 误报为按键记录器 | 坚决不使用全局键盘钩子 (`SetWindowsHookEx`)，严格使用微软官方标准 `RegisterHotKey` API。 |
