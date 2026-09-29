# RecentHub

**Windows 极轻量"最近使用记录"秒搜与重开工具。**

启动 < 300ms · 内存 < 30MB · 检索延迟 < 6ms —— 不做全盘扫描，而是直接解析 Windows 已经为你留存好的活动轨迹。

---

## ⬇️ 下载

| 版本 | 形态 | 说明 | 下载 |
| :--- | :--- | :--- | :--- |
| **v1.2.0** | 安装包 | Windows 10/11 64 位，免管理员权限 | **[RecentHub_Setup_v1.2.0.exe](https://github.com/xiaomoTX-git/RecentHub/releases/latest)** |
| **v1.2.0** | 便携版 | 免安装 zip，解压即用，数据随目录走 | **[RecentHub_portable_v1.2.0.zip](https://github.com/xiaomoTX-git/RecentHub/releases/latest)** |

全部版本见 [Releases](https://github.com/xiaomoTX-git/RecentHub/releases)，逐版本改动见 [CHANGELOG](CHANGELOG.md)。安装包为**当前用户级安装**，全程无 UAC 弹窗；桌面快捷方式与开机自启默认勾选（自启为静默驻留托盘，不弹窗打扰）。

> 卸载时用户数据（`%APPDATA%\RecentHub` 的配置与数据库）默认保留，便于重装后无缝续用。

**便携版用法**：解压到任意目录（含 U 盘），双击其中的 `RecentHub.exe` 即可。目录内的 `portable.flag` 标记文件让配置 / 数据库 / 日志全部就地写入 `data\` 子目录——删除整个目录即为彻底卸载，不留任何注册表与系统痕迹。

> 已知边界：便携版与已安装版同时运行会因单实例互斥而相互接管，建议只保留其中一种形态。

---

## 为什么不用 Everything

Everything 的强项是"扫描全盘"，代价是首次建索引慢、常驻监控占用文件句柄。而 **"最近用过什么"这件事，Windows 早就替你记好了**：

- `%APPDATA%\Microsoft\Windows\Recent` 的 .lnk 快捷方式
- Jump Lists（AutomaticDestinations / CustomDestinations）
- UserAssist 注册表（含启动次数与最后使用时间）
- Office 14.0 / 15.0 / 16.0 MRU

RecentHub 只读这些既有痕迹，**零全盘遍历、零文件系统监控器、零后台 I/O 负担**。

---

## 核心技术

### 1. 零三方依赖的纯二进制流式解析
彻底弃用 `win32com` COM 组件与 `olefile`，用 Python 原生 `struct` 直接实现 **MS-SHLLINK (.lnk)** 与 **MS-CFB (Jump List)** 的零拷贝解析，单文件解析耗时压到 **0.08ms**。

### 2. 中文拼音首字母双轨检索
- **短查询（1~2 字符）**：走内置 GB2312 区间映射 + 常用字补丁构成的紧凑双数组二分索引，`wz` 即可命中 `文字记录.txt`，吞吐 **33 万词/秒**；
- **长查询（≥3 字符）**：走 SQLite 原生 **FTS5 Trigram** 倒排索引，万级记录检索 **4~6ms**。

### 3. 惰性增量扫描（Lazy Polling）
不挂载常驻系统的文件系统监控器（零后台 CPU 占用与句柄消耗）。仅在窗口真实唤出或键入搜索时做 `mtime` 比对，无变动直接复用缓存，即 **0 I/O 开销**。

### 4. 双模态融合界面
- **Mode A · 极简胶囊**：居中无边框悬浮条，失焦或 `Esc` 即刻隐藏，`Enter` 秒开，方向键无缝穿透导航；
- **Mode B · 详细工作台**：`Tab` 一键展开为多列表格，点击「名称 / 类型 / 最后使用 / 完整路径」表头即可排序，顶部「全部 / 文档 / 表格 / PDF / 代码 / 应用 / 文件夹」药丸一键过滤；
- **高对比纯色主题**：深色为纯黑底白字、浅色为纯白底黑字，底色完全不透明，不受壁纸与身后窗口影响；长路径单行省略号截断，绝不折行破版。

### 5. 惰性接力式深度检索
本地轨迹未命中时才按需接力 Everything (`es.exe`) 与 Windows Search 做全盘检索，检索期间在搜索行下方居中显示旋转指示器与文字提示，并带 5 秒兜底超时——**平时零开销，极端情况下也不会卡住界面**。

### 6. 全局唤出与免打扰
双击 `Ctrl`（或自定义热键）随时唤出；检测到全屏游戏 / 观影 / PPT 放映时自动静默不打扰，且不会误判纯桌面场景。

---

## ⚡ 性能实测（10,000 条记录基准）

| 测评项目 | 目标 | 实测 | 结论 |
| :--- | :--- | :--- | :--- |
| 拼音首字母引擎吞吐量 | > 50,000 词/秒 | **333,830 词/秒** | 达标 6.6 倍 |
| 存储层批量建库 + FTS5 索引 | < 1,000ms | **218.97ms**（0.022ms/条） | 极速入库 |
| 拼音首字母搜索（`wx`） | < 15ms | **4.24ms** | 瞬时响应 |
| 拼音多字简码（`kfxm`） | < 15ms | **6.48ms** | 瞬时响应 |
| 中文词汇全文匹配（`需求分析`） | < 15ms | **5.87ms** | 瞬时响应 |
| 置顶空查询排序 | < 10ms | **2.22ms** | 瞬时响应 |
| 真实系统全源扫描 | < 200ms | **28.33ms**（75 条真实轨迹） | 极佳 |

---

## 搜索语法

除自然语言关键词外，搜索框支持叠加精确过滤（可自由组合，纯语法串亦可单独使用）：

| 语法 | 含义 | 示例 |
| :--- | :--- | :--- |
| `ext:xxx` | 限定扩展名，逗号分隔多个 | `报告 ext:pdf`、`ext:png,jpg` |
| `type:xxx` | 限定类型：`word` / `excel` / `pdf` / `code` / `doc` / `app` / `folder` / `url` | `type:excel 预算` |
| `>Nd` / `>Nh` / `>Nm` / `>Nw` | 限定「最近使用时间」在 N 天/小时/分钟/周以内 | `>7d 项目`、`>30m` |

> 例：`ext:xlsx >30d` 返回一个月内用过的 Excel 表格；仅输入 `ext:pdf` 则直接列出最近的 PDF。

---

## 数据与日志位置

| 形态 | 配置 | 数据库 | 日志 |
| :--- | :--- | :--- | :--- |
| 安装版 | `%APPDATA%\RecentHub` | `%LOCALAPPDATA%\RecentHub` | `%APPDATA%\RecentHub\logs` |
| 便携版 | `exe\data` | `exe\data` | `exe\data\logs` |
| 源码运行 | `data\` | `%LOCALAPPDATA%\RecentHub` | `data\logs` |

日志为滚动文件（`recenthub.log`，单文件 1MB × 4 份），在「设置 → 诊断 → 打开日志目录」可一键直达，便于自助排障。

---

## 快捷键

| 按键 | 行为 |
| :--- | :--- |
| `Tab` | 在极简胶囊与详细工作台之间切换 |
| `Enter` | 打开当前选中项 |
| `Alt + Enter` | 在资源管理器中定位并高亮该文件 |
| `↑` / `↓` | 直接切换选中条目（支持长按连续巡航） |
| `Esc` | 隐藏窗口，退避至托盘常驻 |
| 右键 | 上下文菜单：管理员运行 / 打开目录 / 复制路径 / 置顶 / 删除记录 |

---

## 从源码运行与构建

```bash
# 1. 运行（首次会自动创建 .venv 并安装依赖）
run.bat

# 2. 打包为独立 exe（PyInstaller onedir）
.venv\Scripts\pyinstaller.exe --noconfirm --clean RecentHub.spec

# 3. 生成安装包（需 Inno Setup 6）
"$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" installer\RecentHub.iss

# 4. 生成便携绿色版 zip（自动写入 portable.flag 并压缩）
build_portable.bat
```

运行时路径策略：资源只读（源码 `app\resources` / 打包 `_MEIPASS\resources`），用户数据可写（源码 `data\` / 安装版 `%APPDATA%\RecentHub` / 便携版 `exe\data`）；数据库统一落 `%LOCALAPPDATA%\RecentHub`，便携版例外。

依赖：`PySide6`、`pywin32`、`pypinyin`（见 [requirements.txt](requirements.txt)）。

---

## 项目结构

```text
RecentHub/
├── app/
│   ├── parsers/       # 零依赖二进制解析：.lnk / CFB JumpList / UserAssist / 拼音引擎
│   ├── collectors/    # 惰性增量采集：Recent / JumpList / UserAssist / Office MRU
│   ├── aggregator/    # 规范化与去重合并
│   ├── storage/       # SQLite 3 + FTS5 Trigram
│   ├── services/      # 打开、图标、扫描、热键、全屏免打扰
│   └── ui/            # 双模态界面、主题系统与托盘
├── installer/         # Inno Setup 脚本与版本资源
└── main.py            # 单实例主入口
```

---

## License

[MIT](LICENSE)