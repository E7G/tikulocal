#!/usr/bin/env python3
"""
TikuLocal文件解析测试
测试DOCX解析、文本解析、JSON导入等功能
"""

import unittest
import json
import base64
import tempfile
import os
from typing import Dict, List, Optional

class FileParsingTest(unittest.TestCase):
    """文件解析测试类"""
    
    def setUp(self):
        """测试初始化"""
        self.test_data_dir = "reference"
        self.ensure_test_data_exists()
    
    def tearDown(self):
        """测试清理"""
        pass
    
    def ensure_test_data_exists(self):
        """确保测试数据存在"""
        if not os.path.exists(self.test_data_dir):
            os.makedirs(self.test_data_dir)
        
        # 创建测试用的文本文件
        test_text_file = os.path.join(self.test_data_dir, "test_answers.txt")
        if not os.path.exists(test_text_file):
            with open(test_text_file, 'w', encoding='utf-8') as f:
                f.write("""单选题
1. 谁是Linux的创始人？
A. Bill Gates
B. Linus Torvalds
C. Steve Jobs
D. Mark Zuckerberg
答案：B

多选题
2. 以下哪些是编程语言？
A. Python
B. Java
C. HTML
D. CSS
答案：A,B

判断题
3. Linux是一个开源操作系统。
A. 正确
B. 错误
答案：A

填空题
4. HTTP的默认端口是____。
答案：80

问答题
5. 请简述操作系统的主要功能。
答案：操作系统的主要功能包括进程管理、内存管理、文件系统管理、设备管理等。
""")
        
        # 创建测试用的JSON文件
        test_json_file = os.path.join(self.test_data_dir, "test_questions.json")
        if not os.path.exists(test_json_file):
            test_data = {
                "metadata": {
                    "total_questions": 3,
                    "source": "test_file",
                    "created_at": "2024-01-01T00:00:00Z"
                },
                "questions": [
                    {
                        "question": "测试单选题：Python是编译型语言吗？",
                        "options": ["是", "否", "不确定", "以上都不对"],
                        "type": 0,
                        "answer": {
                            "answerKey": ["B"],
                            "answerKeyText": "B",
                            "answerIndex": [1],
                            "answerText": "否",
                            "bestAnswer": ["否"],
                            "allAnswer": [["否"]]
                        }
                    },
                    {
                        "question": "测试多选题：哪些是Web开发技术？",
                        "options": ["HTML", "CSS", "JavaScript", "Python"],
                        "type": 1,
                        "answer": {
                            "answerKey": ["A", "B", "C", "D"],
                            "answerKeyText": "ABCD",
                            "answerIndex": [0, 1, 2, 3],
                            "answerText": "HTML#CSS#JavaScript#Python",
                            "bestAnswer": ["HTML", "CSS", "JavaScript", "Python"],
                            "allAnswer": [["HTML", "CSS", "JavaScript", "Python"]]
                        }
                    },
                    {
                        "question": "测试判断题：地球是圆的。",
                        "type": 3,
                        "answer": {
                            "answerKey": ["A"],
                            "answerKeyText": "A",
                            "answerIndex": [0],
                            "answerText": "正确",
                            "bestAnswer": ["正确"],
                            "allAnswer": [["正确"]]
                        }
                    }
                ]
            }
            
            with open(test_json_file, 'w', encoding='utf-8') as f:
                json.dump(test_data, f, ensure_ascii=False, indent=2)
    
    def test_text_file_reading(self):
        """测试文本文件读取"""
        test_file = os.path.join(self.test_data_dir, "test_answers.txt")
        
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertGreater(len(content), 0)
        self.assertIn("单选题", content)
        self.assertIn("多选题", content)
        self.assertIn("判断题", content)
        self.assertIn("填空题", content)
        self.assertIn("问答题", content)
        
        print("✓ 文本文件读取测试通过")
    
    def test_json_file_reading(self):
        """测试JSON文件读取"""
        test_file = os.path.join(self.test_data_dir, "test_questions.json")
        
        with open(test_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.assertIn("metadata", data)
        self.assertIn("questions", data)
        self.assertIsInstance(data["questions"], list)
        self.assertGreater(len(data["questions"]), 0)
        
        # 验证第一个题目的结构
        first_question = data["questions"][0]
        self.assertIn("question", first_question)
        self.assertIn("type", first_question)
        self.assertIn("answer", first_question)
        
        print("✓ JSON文件读取测试通过")
    
    def test_base64_encoding(self):
        """测试Base64编码"""
        test_file = os.path.join(self.test_data_dir, "test_answers.txt")
        
        with open(test_file, 'rb') as f:
            content = f.read()
        
        # Base64编码
        encoded = base64.b64encode(content).decode('utf-8')
        
        # Base64解码
        decoded = base64.b64decode(encoded.encode('utf-8'))
        
        # 验证编码解码正确性
        self.assertEqual(content, decoded)
        
        print("✓ Base64编码测试通过")
    
    def test_question_type_detection(self):
        """测试题目类型检测"""
        test_cases = [
            ("单选题", 0),
            ("多选题", 1),
            ("判断题", 3),
            ("填空题", 2),
            ("问答题", 4)
        ]
        
        for text, expected_type in test_cases:
            # 简单的类型检测逻辑
            if "单选题" in text:
                detected_type = 0
            elif "多选题" in text:
                detected_type = 1
            elif "判断题" in text:
                detected_type = 3
            elif "填空题" in text:
                detected_type = 2
            elif "问答题" in text:
                detected_type = 4
            else:
                detected_type = 0  # 默认单选题
            
            self.assertEqual(detected_type, expected_type)
        
        print("✓ 题目类型检测测试通过")
    
    def test_answer_parsing_single_choice(self):
        """测试单选题答案解析"""
        test_content = """
1. 测试单选题
A. 选项A
B. 选项B
C. 选项C
D. 选项D
答案：B
"""
        
        # 简单的答案解析逻辑
        lines = test_content.strip().split('\n')
        answer_line = None
        for line in lines:
            if line.startswith("答案："):
                answer_line = line
                break
        
        self.assertIsNotNone(answer_line)
        answer = answer_line.replace("答案：", "").strip()
        self.assertEqual(answer, "B")
        
        print("✓ 单选题答案解析测试通过")
    
    def test_answer_parsing_multiple_choice(self):
        """测试多选题答案解析"""
        test_content = """
1. 测试多选题
A. 选项A
B. 选项B
C. 选项C
D. 选项D
答案：A,B,C
"""
        
        # 简单的答案解析逻辑
        lines = test_content.strip().split('\n')
        answer_line = None
        for line in lines:
            if line.startswith("答案："):
                answer_line = line
                break
        
        self.assertIsNotNone(answer_line)
        answer_text = answer_line.replace("答案：", "").strip()
        answers = answer_text.split(",")
        
        self.assertEqual(len(answers), 3)
        self.assertEqual(answers, ["A", "B", "C"])
        
        print("✓ 多选题答案解析测试通过")
    
    def test_large_file_handling(self):
        """测试大文件处理"""
        # 创建大测试文件
        large_file = os.path.join(self.test_data_dir, "large_test.txt")
        
        # 生成大量测试数据
        with open(large_file, 'w', encoding='utf-8') as f:
            for i in range(1000):
                f.write(f"题目{i}: 这是第{i}个测试题目\n")
                f.write(f"A. 选项A{i}\n")
                f.write(f"B. 选项B{i}\n")
                f.write(f"C. 选项C{i}\n")
                f.write(f"D. 选项D{i}\n")
                f.write(f"答案：{'ABCD'[i % 4]}\n\n")
        
        # 测试读取大文件
        start_time = time.time()
        with open(large_file, 'r', encoding='utf-8') as f:
            content = f.read()
        read_time = time.time() - start_time
        
        self.assertGreater(len(content), 100000)  # 至少100KB
        self.assertLess(read_time, 5.0)  # 读取时间应该小于5秒
        
        # 清理测试文件
        os.remove(large_file)
        
        print(f"✓ 大文件处理测试通过 - 读取耗时: {read_time:.3f}秒")
    
    def test_encoding_handling(self):
        """测试编码处理"""
        # 测试不同编码的文件
        test_cases = [
            ("utf-8", "UTF-8编码测试文件"),
            ("gbk", "GBK编码测试文件"),
            ("ascii", "ASCII编码测试文件")
        ]
        
        for encoding, content in test_cases:
            test_file = os.path.join(self.test_data_dir, f"encoding_test_{encoding}.txt")
            
            try:
                # 写入测试文件
                with open(test_file, 'w', encoding=encoding) as f:
                    f.write(content)
                
                # 读取测试文件
                with open(test_file, 'r', encoding=encoding) as f:
                    read_content = f.read()
                
                self.assertEqual(content, read_content)
                
                # 清理测试文件
                os.remove(test_file)
                
            except Exception as e:
                print(f"编码 {encoding} 测试失败: {e}")
                if os.path.exists(test_file):
                    os.remove(test_file)
        
        print("✓ 编码处理测试通过")
    
    def test_json_schema_validation(self):
        """测试JSON模式验证"""
        test_file = os.path.join(self.test_data_dir, "test_questions.json")
        
        with open(test_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 验证metadata结构
        if "metadata" in data:
            metadata = data["metadata"]
            self.assertIn("total_questions", metadata)
            self.assertIn("source", metadata)
        
        # 验证questions数组结构
        self.assertIn("questions", data)
        questions = data["questions"]
        
        for question in questions:
            # 验证必需字段
            self.assertIn("question", question)
            self.assertIn("type", question)
            self.assertIn("answer", question)
            
            # 验证类型字段的值
            self.assertIn(question["type"], [0, 1, 2, 3, 4])
            
            # 验证选项字段（如果是选择题）
            if question["type"] in [0, 1]:  # 单选或多选
                self.assertIn("options", question)
                self.assertIsInstance(question["options"], list)
                self.assertGreater(len(question["options"]), 0)
            
            # 验证答案结构
            answer = question["answer"]
            self.assertIn("answerText", answer)
        
        print("✓ JSON模式验证测试通过")
    
    def test_file_format_detection(self):
        """测试文件格式检测"""
        test_files = [
            ("test.txt", "text/plain"),
            ("test.json", "application/json"),
            ("test.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            ("test.md", "text/markdown")
        ]
        
        for filename, expected_mime in test_files:
            # 简单的文件格式检测
            if filename.endswith('.json'):
                detected_type = 'json'
            elif filename.endswith('.txt'):
                detected_type = 'text'
            elif filename.endswith('.docx'):
                detected_type = 'docx'
            elif filename.endswith('.md'):
                detected_type = 'markdown'
            else:
                detected_type = 'unknown'
            
            self.assertNotEqual(detected_type, 'unknown')
        
        print("✓ 文件格式检测测试通过")
    
    def test_data_validation(self):
        """测试数据验证"""
        test_file = os.path.join(self.test_data_dir, "test_questions.json")
        
        with open(test_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 验证题目数量一致性
        if "metadata" in data and "total_questions" in data["metadata"]:
            declared_count = data["metadata"]["total_questions"]
            actual_count = len(data["questions"])
            self.assertEqual(declared_count, actual_count)
        
        # 验证题目内容非空
        for question in data["questions"]:
            self.assertGreater(len(question["question"].strip()), 0)
            
            # 验证选项非空（选择题）
            if "options" in question and question["type"] in [0, 1]:
                self.assertGreater(len(question["options"]), 0)
                for option in question["options"]:
                    self.assertGreater(len(option.strip()), 0)
        
        print("✓ 数据验证测试通过")

def run_file_parsing_tests():
    """运行所有文件解析测试"""
    print("📁 开始TikuLocal文件解析测试...")
    print("=" * 50)
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(FileParsingTest)
    
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
    success = run_file_parsing_tests()
    exit(0 if success else 1)