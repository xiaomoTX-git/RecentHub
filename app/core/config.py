"""
RecentHub 运行时用户与现代设计系统配置管理模块
- 统一管理窗口尺寸、宽高比例与现代组件库 Design System Tokens
- 支持主题色、行高、胶囊圆角、快捷键微徽标等配置
- 自动写入持久化本地 JSON 配置文件 (data/config.json)
"""

import os
import json
from typing import Dict, Any
from app.core.paths import user_data_dir

# 可写数据目录：源码模式为 <项目根>\data，打包模式为 %APPDATA%\RecentHub
# (安装目录不可写，配置写在那里会被静默丢弃)
DATA_DIR = user_data_dir()
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

DEFAULT_CONFIG: Dict[str, Any] = {
    # 窗口与比例
    "window_width": 780,
    "workbench_height": 450,
    "dropdown_height": 380,
    "bar_height": 48,
    
    # 主题模式 (跟随系统 / 浅色 / 深色)
    "theme": "system",                      # system | light | dark

    # 全屏免打扰保护 (检测到打游戏、看电影等全屏状态时不被快捷键唤出)
    "fullscreen_dnd": True,

    # 现代组件库与设计系统 Tokens (Windows 11 Fluent + Raycast)
    "design_system": "fluent_acrylic",      # fluent_acrylic | raycast_glass | pure_minimal
    "accent_color": "#0067C0",              # Fluent 经典系统主色
    "accent_hover_color": "#1875D1",        # Fluent 悬停提亮色
    "row_height": 38,                       # 呼吸感现代行高 (标准 38px)
    "card_radius": 14,                      # 主窗口圆角
    "pill_radius": 6,                       # 条目胶囊圆角
    "enable_kbd_badges": True,              # 启用现代实体按键徽标
    "enable_row_indicator": True,           # 启用选中文档 Fluent 左侧立体指示条
    "acrylic_tint": "rgba(245, 246, 252, 0.52)",
    "border_specular": "rgba(255, 255, 255, 0.82)"
}


class ConfigManager:
    @staticmethod
    def _ensure_dir():
        if not os.path.exists(DATA_DIR):
            try:
                os.makedirs(DATA_DIR, exist_ok=True)
            except Exception:
                pass

    @classmethod
    def load(cls) -> Dict[str, Any]:
        """读取本地配置文件，具备字段默认值自动兜底"""
        cls._ensure_dir()
        if not os.path.exists(CONFIG_PATH):
            return DEFAULT_CONFIG.copy()
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                cfg = DEFAULT_CONFIG.copy()
                cfg.update(data)
                # 约束合法边界
                cfg["window_width"] = max(560, min(int(cfg.get("window_width", 780)), 1400))
                cfg["workbench_height"] = max(280, min(int(cfg.get("workbench_height", 450)), 900))
                cfg["dropdown_height"] = max(140, min(int(cfg.get("dropdown_height", 380)), 850))
                if cfg.get("theme") not in ("system", "light", "dark"):
                    cfg["theme"] = "system"
                cfg["bar_height"] = max(42, min(int(cfg.get("bar_height", 48)), 72))
                cfg["row_height"] = max(32, min(int(cfg.get("row_height", 38)), 48))
                return cfg
        except Exception:
            return DEFAULT_CONFIG.copy()

    @classmethod
    def save(cls, config_data: Dict[str, Any]):
        """持久化保存配置到本地文件"""
        cls._ensure_dir()
        try:
            current = cls.load()
            current.update(config_data)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(current, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    @classmethod
    def update(cls, key: str, value: Any):
        """便利更新单一配置项并持久化"""
        cfg = cls.load()
        cfg[key] = value
        cls.save(cfg)

    @classmethod
    def get_window_size(cls) -> tuple[int, int, int, int]:
        """获取窗口尺寸 (width, workbench_height, dropdown_height, bar_height)"""
        cfg = cls.load()
        return (
            int(cfg["window_width"]),
            int(cfg["workbench_height"]),
            int(cfg["dropdown_height"]),
            int(cfg["bar_height"])
        )

    @classmethod
    def save_window_size(cls, width: int, workbench_height: int, dropdown_height: int = 380, bar_height: int = 48):
        """快捷保存窗口所有宽高配置"""
        cls.save({
            "window_width": max(560, min(int(width), 1400)),
            "workbench_height": max(280, min(int(workbench_height), 900)),
            "dropdown_height": max(140, min(int(dropdown_height), 850)),
            "bar_height": max(42, min(int(bar_height), 72))
        })
