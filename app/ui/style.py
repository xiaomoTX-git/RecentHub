"""
RecentHub 现代化无界毛玻璃设计规范 (Raycast / Spotlight / Fluent 顶流桌面美学)
- 彻底去除生硬分割横线与分类筛选按钮，回归极简纯粹桌面检索
- 58% 通透冰霜微冷白亚克力 (rgba(246, 248, 252, 0.58)) + 纯白高光微折射边缘 (1px solid rgba(255, 255, 255, 0.88))
- 16px 现代大圆角卡片景深
- 舒展无边框大字号搜索栏 + 极简透白悬停长胶囊列表
"""

STYLE_WHITE_GLASS = """
/* 全局基础文字设置 */
QWidget {
    color: #181824;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI Variable Text", "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    font-size: 13px;
    outline: none;
}

/* 主卡片容器：58% 透明度通透纯净毛玻璃，16px 优雅大圆角，折射微边缘 */
#CentralCard {
    background-color: rgba(246, 248, 252, 0.58);
    border: 1px solid rgba(255, 255, 255, 0.88);
    border-radius: 16px;
}

/* 顶部搜索框行容器：自然呼吸留白 */
#SearchRow {
    background: transparent;
    padding: 0px;
}

/* 大气极简无边框搜索框 */
#SearchInput {
    background: transparent;
    border: none;
    color: #12121c;
    font-size: 16px;
    font-weight: 400;
    padding: 4px 6px;
    selection-background-color: rgba(0, 103, 192, 0.22);
    selection-color: #000000;
}

#SearchInput:focus {
    outline: none;
}

/* 右上角纯线条玻璃图标按钮 */
#ModeActionBtn {
    background-color: rgba(255, 255, 255, 0.40);
    border: 1px solid rgba(255, 255, 255, 0.75);
    border-radius: 7px;
    min-width: 26px;
    max-width: 26px;
    min-height: 26px;
    max-height: 26px;
    padding: 3px;
}

#ModeActionBtn:hover {
    background-color: rgba(255, 255, 255, 0.85);
    border-color: rgba(255, 255, 255, 0.98);
}

/* 结果表格视图 (无边框、无分割横线、纯净悬浮) */
QTableView {
    background-color: transparent;
    border: none;
    gridline-color: transparent;
    selection-background-color: transparent;
    selection-color: #12121c;
    outline: none;
}

QTableView:focus {
    outline: none;
}

QTableView::item {
    padding: 4px 8px;
    border: none;
    color: #181824;
}

/* 表头样式 (Mode B 工作台 - 彻底去除底部硬分割线，极简浅灰自然点缀) */
QHeaderView {
    background-color: transparent;
    border: none;
}

QHeaderView::section {
    background-color: transparent;
    color: #828292;
    padding: 4px 8px;
    border: none;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.5px;
}

/* 彻底隐藏与清除所有滚动条 */
QScrollBar:horizontal, QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 0px;
    height: 0px;
    margin: 0px;
}

QScrollBar::handle:horizontal, QScrollBar::handle:vertical {
    background: transparent;
    width: 0px;
    height: 0px;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    width: 0px;
    height: 0px;
}

/* 底部状态栏微型容器：自然漂浮 */
#StatusBar {
    background: transparent;
    color: #727282;
    font-size: 11px;
    padding: 2px 2px;
}

/* 现代 85% 半透明高透玻璃右键与托盘菜单 */
QMenu {
    background-color: rgba(255, 255, 255, 0.88);
    border: 1px solid rgba(255, 255, 255, 0.96);
    border-radius: 10px;
    padding: 5px 4px;
}

QMenu::item {
    background-color: transparent;
    color: #181824;
    font-size: 12px;
    padding: 6px 24px 6px 12px;
    border-radius: 6px;
    margin: 1px 2px;
}

QMenu::item:selected {
    background-color: rgba(255, 255, 255, 0.88);
    color: #000000;
}

QMenu::separator {
    height: 1px;
    background-color: rgba(0, 0, 0, 0.05);
    margin: 4px 6px;
}
"""
