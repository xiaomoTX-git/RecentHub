
import os
for d in ["C:\\", "D:\\", "E:\\", "F:\\"]:
    if os.path.exists(d):
        try:
            for item in os.listdir(d):
                if "wechat" in item.lower() or "weixin" in item.lower():
                    print("Found in", d, item)
        except Exception:
            pass
