import sqlite3
import json

# 连接到数据库
conn = sqlite3.connect('questions.db')
cursor = conn.cursor()

# 查看解析规则表结构
try:
    cursor.execute("PRAGMA table_info(parse_rules);")
    columns = cursor.fetchall()
    print("解析规则表结构:")
    for col in columns:
        print(f"  {col[1]}: {col[2]}")
    print()
except Exception as e:
    print(f"查看表结构失败: {e}")

# 查看所有解析规则
try:
    cursor.execute("SELECT * FROM parse_rules;")
    rules = cursor.fetchall()
    print(f"找到 {len(rules)} 条解析规则:")
    for rule in rules:
        print(f"规则ID: {rule[0]}")
        print(f"  名称: {rule[1]}")
        print(f"  描述: {rule[2]}")
        print(f"  类型: {rule[3]}")
        print(f"  模式: {rule[4]}")
        print(f"  题目索引: {rule[5]}")
        print(f"  选项索引: {rule[6]}")
        print(f"  答案索引: {rule[7]}")
        print(f"  题目类型: {rule[8]}")
        print(f"  答案格式: {rule[9]}")
        print(f"  是否激活: {rule[10]}")
        print()
except Exception as e:
    print(f"查看规则失败: {e}")

# 查看题目表结构
try:
    cursor.execute("PRAGMA table_info(questions);")
    columns = cursor.fetchall()
    print("题目表结构:")
    for col in columns:
        print(f"  {col[1]}: {col[2]}")
    print()
except Exception as e:
    print(f"查看题目表结构失败: {e}")

# 查看题目表
try:
    cursor.execute("SELECT COUNT(*) FROM questions;")
    count = cursor.fetchone()[0]
    print(f"题目总数: {count}")
    
    # 搜索特定题目
    search_term = "尼葛洛庞蒂"
    cursor.execute("SELECT * FROM questions WHERE question LIKE ?;", (f"%{search_term}%",))
    results = cursor.fetchall()
    print(f"\n搜索包含'{search_term}'的题目，找到 {len(results)} 条:")
    for row in results:
        print(f"ID: {row[0]}")
        print(f"问题: {row[1]}")
        print(f"选项: {row[2]}")
        print(f"类型: {row[3]}")
        print(f"答案: {row[4]}")
        print()
    
    # 如果没有找到，查看前5个题目
    if len(results) == 0:
        print("\n查看前5个题目:")
        cursor.execute("SELECT * FROM questions LIMIT 5;")
        first_five = cursor.fetchall()
        for row in first_five:
            print(f"ID: {row[0]}")
            print(f"问题: {row[1]}")
            print(f"选项: {row[2]}")
            print(f"类型: {row[3]}")
            print(f"答案: {row[4]}")
            print()
            
except Exception as e:
    print(f"查看题目数量失败: {e}")

conn.close()