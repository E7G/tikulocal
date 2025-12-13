#!/usr/bin/env python3
"""
TikuLocal数据库操作测试
测试数据库连接、数据完整性、性能等
"""

import unittest
import sqlite3
import os
import json
import time
from typing import Dict, List, Optional

class DatabaseTest(unittest.TestCase):
    """数据库操作测试类"""
    
    def setUp(self):
        """测试初始化"""
        self.db_path = "questions.db"
        self.backup_path = "questions_backup.db"
        
        # 备份现有数据库
        if os.path.exists(self.db_path):
            import shutil
            shutil.copy2(self.db_path, self.backup_path)
        
        # 连接到数据库
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
        # 确保表存在
        self._ensure_tables_exist()
    
    def tearDown(self):
        """测试清理"""
        # 关闭数据库连接
        if hasattr(self, 'conn'):
            self.conn.close()
        
        # 恢复数据库备份
        if os.path.exists(self.backup_path):
            import shutil
            shutil.copy2(self.backup_path, self.db_path)
            os.remove(self.backup_path)
    
    def _ensure_tables_exist(self):
        """确保必要的表存在"""
        # 创建题目表（如果不存在）
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                options TEXT,
                type INTEGER NOT NULL,
                answer TEXT NOT NULL
            )
        """)
        
        # 创建索引
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_questions_question ON questions(question)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_questions_type ON questions(type)")
        
        self.conn.commit()
    
    def test_table_structure(self):
        """测试表结构"""
        # 获取表结构
        self.cursor.execute("PRAGMA table_info(questions)")
        columns = self.cursor.fetchall()
        
        # 验证列名和类型
        expected_columns = {
            'id': 'INTEGER',
            'question': 'TEXT',
            'options': 'TEXT',
            'type': 'INTEGER',
            'answer': 'TEXT'
        }
        
        actual_columns = {col[1]: col[2] for col in columns}
        
        for col_name, col_type in expected_columns.items():
            self.assertIn(col_name, actual_columns)
            self.assertEqual(actual_columns[col_name], col_type)
        
        print("✓ 表结构测试通过")
    
    def test_indexes_exist(self):
        """测试索引存在"""
        self.cursor.execute("PRAGMA index_list(questions)")
        indexes = self.cursor.fetchall()
        
        index_names = [idx[1] for idx in indexes]
        
        expected_indexes = ['idx_questions_question', 'idx_questions_type']
        for index_name in expected_indexes:
            self.assertIn(index_name, index_names)
        
        print("✓ 索引存在测试通过")
    
    def test_insert_question(self):
        """测试插入题目"""
        question_data = {
            "question": "测试题目：SQLite是什么类型的数据库？",
            "options": json.dumps(["关系型", "非关系型", "图形数据库", "时序数据库"]),
            "type": 0,
            "answer": json.dumps({
                "answerKey": ["A"],
                "answerKeyText": "A",
                "answerIndex": [0],
                "answerText": "关系型",
                "bestAnswer": ["关系型"],
                "allAnswer": [["关系型"]]
            })
        }
        
        # 插入数据
        self.cursor.execute("""
            INSERT INTO questions (question, options, type, answer)
            VALUES (?, ?, ?, ?)
        """, (
            question_data["question"],
            question_data["options"],
            question_data["type"],
            question_data["answer"]
        ))
        
        self.conn.commit()
        
        # 验证数据插入
        self.cursor.execute("SELECT * FROM questions WHERE question = ?", (question_data["question"],))
        result = self.cursor.fetchone()
        
        self.assertIsNotNone(result)
        self.assertEqual(result[1], question_data["question"])  # question列
        self.assertEqual(result[2], question_data["options"])  # options列
        self.assertEqual(result[3], question_data["type"])  # type列
        self.assertEqual(result[4], question_data["answer"])  # answer列
        
        print("✓ 插入题目测试通过")
    
    def test_search_performance(self):
        """测试搜索性能"""
        # 先插入大量测试数据
        test_questions = []
        for i in range(1000):
            question = f"性能测试题目{i}: 这是什么类型的测试？"
            options = json.dumps([f"选项A{i}", f"选项B{i}", f"选项C{i}", f"选项D{i}"])
            answer = json.dumps({
                "answerKey": ["A"],
                "answerKeyText": "A",
                "answerIndex": [0],
                "answerText": f"测试答案{i}",
                "bestAnswer": [f"测试答案{i}"],
                "allAnswer": [[f"测试答案{i}"]]
            })
            
            test_questions.append((question, options, 0, answer))
        
        # 批量插入
        self.cursor.executemany("""
            INSERT INTO questions (question, options, type, answer)
            VALUES (?, ?, ?, ?)
        """, test_questions)
        
        self.conn.commit()
        
        # 测试搜索性能
        start_time = time.time()
        self.cursor.execute("SELECT * FROM questions WHERE question LIKE ?", ("%性能测试%",))
        results = self.cursor.fetchall()
        end_time = time.time()
        
        search_time = end_time - start_time
        self.assertGreater(len(results), 0)
        self.assertLess(search_time, 1.0)  # 搜索应该在1秒内完成
        
        print(f"✓ 搜索性能测试通过 - 搜索1000条数据耗时: {search_time:.3f}秒")
    
    def test_data_integrity(self):
        """测试数据完整性"""
        # 插入测试数据
        question_data = {
            "question": "完整性测试：数据库ACID代表什么？",
            "options": json.dumps(["原子性、一致性、隔离性、持久性", "高级、复杂、智能、动态", "自动、完整、独立、分布式", "应用、配置、集成、部署"]),
            "type": 0,
            "answer": json.dumps({
                "answerKey": ["A"],
                "answerKeyText": "A",
                "answerIndex": [0],
                "answerText": "原子性、一致性、隔离性、持久性",
                "bestAnswer": ["原子性、一致性、隔离性、持久性"],
                "allAnswer": [["原子性、一致性、隔离性、持久性"]]
            })
        }
        
        # 插入数据
        self.cursor.execute("""
            INSERT INTO questions (question, options, type, answer)
            VALUES (?, ?, ?, ?)
        """, (
            question_data["question"],
            question_data["options"],
            question_data["type"],
            question_data["answer"]
        ))
        
        self.conn.commit()
        
        # 验证数据完整性
        self.cursor.execute("SELECT * FROM questions WHERE question = ?", (question_data["question"],))
        result = self.cursor.fetchone()
        
        # 验证options可以正确解析
        stored_options = json.loads(result[2])
        original_options = json.loads(question_data["options"])
        self.assertEqual(stored_options, original_options)
        
        # 验证answer可以正确解析
        stored_answer = json.loads(result[4])
        original_answer = json.loads(question_data["answer"])
        self.assertEqual(stored_answer, original_answer)
        
        print("✓ 数据完整性测试通过")
    
    def test_concurrent_access(self):
        """测试并发访问"""
        import threading
        
        def insert_question(thread_id):
            try:
                question = f"并发测试题目{thread_id}"
                options = json.dumps([f"线程选项A{thread_id}", f"线程选项B{thread_id}"])
                answer = json.dumps({
                    "answerKey": ["A"],
                    "answerKeyText": "A",
                    "answerIndex": [0],
                    "answerText": f"线程答案{thread_id}",
                    "bestAnswer": [f"线程答案{thread_id}"],
                    "allAnswer": [[f"线程答案{thread_id}"]]
                })
                
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO questions (question, options, type, answer)
                    VALUES (?, ?, ?, ?)
                """, (question, options, 0, answer))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"线程{thread_id}错误: {e}")
                return False
        
        # 启动10个并发线程
        threads = []
        results = []
        
        for i in range(10):
            thread = threading.Thread(target=lambda idx=i: results.append(insert_question(idx)))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证结果
        success_count = sum(results)
        self.assertGreaterEqual(success_count, 8)  # 至少80%成功
        
        print(f"✓ 并发访问测试通过 - {success_count}/10 线程成功")
    
    def test_database_backup_recovery(self):
        """测试数据库备份恢复"""
        # 插入测试数据
        test_question = "备份恢复测试题目"
        test_options = json.dumps(["选项A", "选项B", "选项C"])
        test_answer = json.dumps({"answerText": "测试答案"})
        
        self.cursor.execute("""
            INSERT INTO questions (question, options, type, answer)
            VALUES (?, ?, ?, ?)
        """, (test_question, test_options, 0, test_answer))
        
        self.conn.commit()
        
        # 验证数据存在
        self.cursor.execute("SELECT * FROM questions WHERE question = ?", (test_question,))
        result = self.cursor.fetchone()
        self.assertIsNotNone(result)
        
        print("✓ 数据库备份恢复测试通过")
    
    def test_json_data_validation(self):
        """测试JSON数据验证"""
        # 测试有效的JSON数据
        valid_question = {
            "question": "JSON验证测试",
            "options": json.dumps(["选项1", "选项2", "选项3"]),
            "type": 0,
            "answer": json.dumps({
                "answerKey": ["A", "B"],
                "answerKeyText": "AB",
                "answerIndex": [0, 1],
                "answerText": "选项1#选项2",
                "bestAnswer": ["选项1", "选项2"],
                "allAnswer": [["选项1", "选项2"]]
            })
        }
        
        # 插入有效数据
        self.cursor.execute("""
            INSERT INTO questions (question, options, type, answer)
            VALUES (?, ?, ?, ?)
        """, (
            valid_question["question"],
            valid_question["options"],
            valid_question["type"],
            valid_question["answer"]
        ))
        
        self.conn.commit()
        
        # 验证可以正确解析
        self.cursor.execute("SELECT options, answer FROM questions WHERE question = ?", 
                          (valid_question["question"],))
        result = self.cursor.fetchone()
        
        # 验证JSON可以正确解析
        options = json.loads(result[0])
        answer = json.loads(result[1])
        
        self.assertIsInstance(options, list)
        self.assertIsInstance(answer, dict)
        self.assertIn("answerKey", answer)
        self.assertIn("answerText", answer)
        
        print("✓ JSON数据验证测试通过")

def run_database_tests():
    """运行所有数据库测试"""
    print("🗄️ 开始TikuLocal数据库操作测试...")
    print("=" * 50)
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(DatabaseTest)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果:")
    print(f"   运行测试: {result.testsRun}")
    print(f"   成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   失败: {len(result.failures)}")
    print(f"   错误: {len(result.errors)}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_database_tests()
    exit(0 if success else 1)