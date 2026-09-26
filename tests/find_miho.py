
import os
import subprocess

print("--- Searching for mihoyo or 米哈游 files ---")
# 1. Everything CLI 探测
es_candidates = [
    "es.exe",
    r"C:\Program Files\Everything\es.exe",
    r"C:\Program Files (x86)\Everything\es.exe",
    r"D:\Everything\es.exe",
    r"E:\Everything\es.exe"
]
es_bin = None
for c in es_candidates:
    try:
        r = subprocess.run([c, "-v"], capture_output=True, text=True, timeout=1)
        if r.returncode == 0:
            es_bin = c
            break
    except Exception:
        pass

print("Everything binary:", es_bin)
if es_bin:
    for query in ["mihoyo", "米哈游"]:
        r = subprocess.run([es_bin, "-n", "10", query], capture_output=True, text=True, encoding="utf-8")
        print(f"ES search '{query}':")
        for line in r.stdout.splitlines()[:10]:
            print("  ", line)

# 2. Windows Search OLE DB 探测
try:
    import win32com.client
    conn = win32com.client.Dispatch("ADODB.Connection")
    conn.Open("Provider=Search.CollatorDSO;Extended Properties='Application=Windows';")
    rs = win32com.client.Dispatch("ADODB.Recordset")
    for q in ["mihoyo", "米哈游"]:
        sql = f"SELECT TOP 5 System.ItemName, System.ItemPathDisplay FROM SystemIndex WHERE System.ItemName LIKE '%{q}%' OR System.ItemPathDisplay LIKE '%{q}%'"
        rs.Open(sql, conn)
        print(f"Windows Search '{q}':")
        while not rs.EOF:
            print("  ", rs.Fields("System.ItemName").Value, "-->", rs.Fields("System.ItemPathDisplay").Value)
            rs.MoveNext()
        rs.Close()
    conn.Close()
except Exception as e:
    print("Windows Search error:", e)
