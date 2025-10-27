import requests
import sqlite3

# 连接到数据库
conn = sqlite3.connect('questions.db')
cursor = conn.cursor()

# 删除所有解析规则
cursor.execute("DELETE FROM parse_rules")
conn.commit()

# 删除所有题目
cursor.execute("DELETE FROM questions")
conn.commit()

# 关闭数据库连接
conn.close()

print("已重置数据库，删除所有解析规则和题目")