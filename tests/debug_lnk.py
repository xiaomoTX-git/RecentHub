
import os
from app.parsers.lnk_parser import LnkParser

path = r"C:\Users\Public\Desktop\微信.lnk"
print("Exists:", os.path.exists(path))
target = LnkParser.parse(path)
print("Target:", target)
if target:
    print("Target exists:", os.path.exists(target))
