
import win32com.client

try:
    conn = win32com.client.Dispatch("ADODB.Connection")
    conn.Open("Provider=Search.CollatorDSO;Extended Properties='Application=Windows';")
    print("Windows Search OLE DB Connection opened successfully!")
    
    rs = win32com.client.Dispatch("ADODB.Recordset")
    # 查询包含 hosts 的文件
    sql = "SELECT System.ItemName, System.ItemPathDisplay, System.DateModified FROM SystemIndex WHERE System.ItemName LIKE '%hosts%'"
    rs.Open(sql, conn)
    
    count = 0
    while not rs.EOF:
        name = rs.Fields.Item("System.ItemName").Value
        path = rs.Fields.Item("System.ItemPathDisplay").Value
        print(f"[{count+1}] {name} -> {path}")
        count += 1
        rs.MoveNext()
        if count >= 10:
            break
    print(f"Total results fetched from Windows Search: {count}")
    conn.Close()
except Exception as e:
    print("Windows Search error:", e)
