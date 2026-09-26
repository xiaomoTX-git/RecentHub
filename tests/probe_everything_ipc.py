
import win32gui
import win32con

# 检查是否有类名为 EVERYTHING 的隐藏通信窗口
hwnd = win32gui.FindWindow("EVERYTHING", None)
print("FindWindow EVERYTHING:", hwnd)

# 检查是否有类名为 EVERYTHING_TASKBAR_NOTIFICATION 的窗口
hwnd2 = win32gui.FindWindow("EVERYTHING_TASKBAR_NOTIFICATION", None)
print("FindWindow EVERYTHING_TASKBAR_NOTIFICATION:", hwnd2)

# 搜索全系统标题或类名包含 everything 的窗口
def enum_cb(h, _):
    title = win32gui.GetWindowText(h)
    cls = win32gui.GetClassName(h)
    if "everything" in title.lower() or "everything" in cls.lower():
        print(f"Found window: hwnd={h}, title={title!r}, class={cls!r}")
win32gui.EnumWindows(enum_cb, None)
