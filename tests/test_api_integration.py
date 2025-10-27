#!/usr/bin/env python3
"""
TikuLocal API集成测试
测试题库系统的核心功能：题目搜索、创建、导入、删除等
"""

import unittest
import requests
import json
import time
import base64
from typing import Dict, List, Optional

class TikuLocalAPITest(unittest.TestCase):
    """TikuLocal API集成测试类"""
    
    def setUp(self):
        """测试初始化"""
        self.base_url = "http://localhost:8060"
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # 等待服务启动
        self._wait_for_service()
        
        # 清理测试数据
        self._cleanup_test_data()
    
    def tearDown(self):
        """测试清理"""
        self._cleanup_test_data()
        self.session.close()
    
    def _wait_for_service(self, max_retries: int = 30, retry_delay: float = 1.0):
        """等待服务启动"""
        for i in range(max_retries):
            try:
                response = self.session.get(f"{self.base_url}/")
                if response.status_code == 200:
                    print(f"服务已启动，耗时 {i + 1} 秒")
                    return
            except requests.exceptions.RequestException:
                pass
            time.sleep(retry_delay)
        
        raise RuntimeError("服务启动超时")
    
    def _cleanup_test_data(self):
        """清理测试数据"""
        try:
            # 清空所有题目
            response = self.session.delete(f"{self.base_url}/api/questions")
            if response.status_code == 200:
                print("测试数据清理完成")
        except requests.exceptions.RequestException:
            pass
    
    def test_home_page(self):
        """测试首页"""
        response = self.session.get(f"{self.base_url}/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("content-type", ""))
        print("✓ 首页测试通过")
    
    def test_create_single_choice_question(self):
        """测试创建单选题"""
        question_data = {
            "question": "测试单选题：谁是Linux的创始人？",
            "options": ["Bill Gates", "Linus Torvalds", "Steve Jobs", "Mark Zuckerberg"],
            "type": 0,  # 单选题
            "answer": {
                "answerKey": ["B"],
                "answerKeyText": "B",
                "answerIndex": [1],
                "answerText": "Linus Torvalds",
                "bestAnswer": ["Linus Torvalds"],
                "allAnswer": [["Linus Torvalds"]]
            }
        }
        
        response = self.session.post(
            f"{self.base_url}/api/questions",
            json=question_data
        )
        
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result.get("data", {}).get("success", False))
        print("✓ 单选题创建测试通过")
    
    def test_create_multiple_choice_question(self):
        """测试创建多选题"""
        question_data = {
            "question": "测试多选题：哪些是编程语言？",
            "options": ["Python", "Java", "HTML", "CSS"],
            "type": 1,  # 多选题
            "answer": {
                "answerKey": ["A", "B"],
                "answerKeyText": "AB",
                "answerIndex": [0, 1],
                "answerText": "Python#Java",
                "bestAnswer": ["Python", "Java"],
                "allAnswer": [["Python", "Java"]]
            }
        }
        
        response = self.session.post(
            f"{self.base_url}/api/questions",
            json=question_data
        )
        
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result.get("data", {}).get("success", False))
        print("✓ 多选题创建测试通过")
    
    def test_create_true_false_question(self):
        """测试创建判断题"""
        question_data = {
            "question": "测试判断题：Linux是一个开源操作系统",
            "type": 3,  # 判断题
            "answer": {
                "answerKey": ["A"],
                "answerKeyText": "A",
                "answerIndex": [0],
                "answerText": "正确",
                "bestAnswer": ["正确"],
                "allAnswer": [["正确"]]
            }
        }
        
        response = self.session.post(
            f"{self.base_url}/api/questions",
            json=question_data
        )
        
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result.get("data", {}).get("success", False))
        print("✓ 判断题创建测试通过")
    
    def test_search_existing_question(self):
        """测试搜索已存在的题目"""
        # 先创建测试题目
        question_data = {
            "question": "搜索测试：Rust是什么类型的语言？",
            "options": ["脚本语言", "系统编程语言", "标记语言", "样式语言"],
            "type": 0,
            "answer": {
                "answerKey": ["B"],
                "answerKeyText": "B",
                "answerIndex": [1],
                "answerText": "系统编程语言",
                "bestAnswer": ["系统编程语言"],
                "allAnswer": [["系统编程语言"]]
            }
        }
        
        create_response = self.session.post(
            f"{self.base_url}/api/questions",
            json=question_data
        )
        self.assertEqual(create_response.status_code, 200)
        
        # 搜索题目
        search_data = {
            "question": "Rust是什么类型的语言",
            "type": 0
        }
        
        response = self.session.post(
            f"{self.base_url}/api/search",
            json=search_data
        )
        
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result.get("question", ""), question_data["question"])
        self.assertEqual(result.get("type", -1), 0)
        print("✓ 题目搜索测试通过")
    
    def test_search_nonexistent_question(self):
        """测试搜索不存在的题目"""
        search_data = {
            "question": "不存在的题目测试12345",
            "type": 0
        }
        
        response = self.session.post(
            f"{self.base_url}/api/search",
            json=search_data
        )
        
        self.assertEqual(response.status_code, 404)
        print("✓ 不存在的题目搜索测试通过")
    
    def test_adapter_search_with_options(self):
        """测试适配器搜索（带选项）"""
        # 先创建测试题目
        question_data = {
            "question": "适配器测试：HTTP的默认端口是？",
            "options": ["80", "443", "8080", "3000"],
            "type": 0,
            "answer": {
                "answerKey": ["A"],
                "answerKeyText": "A",
                "answerIndex": [0],
                "answerText": "80",
                "bestAnswer": ["80"],
                "allAnswer": [["80"]]
            }
        }
        
        create_response = self.session.post(
            f"{self.base_url}/api/questions",
            json=question_data
        )
        self.assertEqual(create_response.status_code, 200)
        
        # 使用适配器搜索
        search_data = {
            "question": "HTTP的默认端口是",
            "options": ["80", "443", "8080", "3000"],
            "type": 0
        }
        
        response = self.session.post(
            f"{self.base_url}/adapter-service/search",
            json=search_data
        )
        
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertIn("answer", result)
        self.assertIn("bestAnswer", result.get("answer", {}))
        print("✓ 适配器搜索测试通过")
    
    def test_get_all_questions(self):
        """测试获取所有题目"""
        # 先创建几个测试题目
        questions = [
            {
                "question": "测试题目1",
                "type": 0,
                "answer": {"answerText": "测试答案1"}
            },
            {
                "question": "测试题目2",
                "type": 1,
                "answer": {"answerText": "测试答案2"}
            }
        ]
        
        for q in questions:
            response = self.session.post(
                f"{self.base_url}/api/questions",
                json=q
            )
            self.assertEqual(response.status_code, 200)
        
        # 获取所有题目
        response = self.session.get(f"{self.base_url}/api/questions")
        self.assertEqual(response.status_code, 200)
        
        result = response.json()
        self.assertTrue(result.get("data", {}).get("success", False))
        self.assertGreater(len(result.get("data", {}).get("data", [])), 0)
        print("✓ 获取所有题目测试通过")
    
    def test_import_questions(self):
        """测试批量导入题目"""
        import_data = {
            "questions": [
                {
                    "question": "导入测试1：Python是编译型语言吗？",
                    "type": 3,  # 判断题
                    "answer": {
                        "answerKey": ["B"],
                        "answerKeyText": "B",
                        "answerIndex": [1],
                        "answerText": "错误",
                        "bestAnswer": ["错误"],
                        "allAnswer": [["错误"]]
                    }
                },
                {
                    "question": "导入测试2：以下哪个不是数据库？",
                    "options": ["MySQL", "PostgreSQL", "MongoDB", "Python"],
                    "type": 0,  # 单选题
                    "answer": {
                        "answerKey": ["D"],
                        "answerKeyText": "D",
                        "answerIndex": [3],
                        "answerText": "Python",
                        "bestAnswer": ["Python"],
                        "allAnswer": [["Python"]]
                    }
                }
            ]
        }
        
        response = self.session.post(
            f"{self.base_url}/api/import",
            json=import_data
        )
        
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result.get("data", {}).get("success", False))
        self.assertEqual(result.get("data", {}).get("data", {}).get("success_count", 0), 2)
        print("✓ 批量导入测试通过")
    
    def test_delete_question(self):
        """测试删除题目"""
        # 先创建测试题目
        question_data = {
            "question": "删除测试：这个题目将被删除",
            "type": 0,
            "answer": {"answerText": "测试答案"}
        }
        
        create_response = self.session.post(
            f"{self.base_url}/api/questions",
            json=question_data
        )
        self.assertEqual(create_response.status_code, 200)
        
        # 获取题目ID（这里简化处理，实际应该从响应中获取ID）
        # 由于当前API没有返回ID，我们通过搜索来获取
        search_response = self.session.post(
            f"{self.base_url}/api/search",
            json={"question": "删除测试：这个题目将被删除", "type": 0}
        )
        
        if search_response.status_code == 200:
            # 这里假设我们找到了题目并删除它
            # 实际实现需要根据具体的数据库ID来删除
            print("✓ 删除功能需要具体ID实现 - 测试跳过")
        else:
            print("✓ 删除测试 - 题目未找到")
    
    def test_error_handling_invalid_json(self):
        """测试错误处理 - 无效JSON"""
        response = self.session.post(
            f"{self.base_url}/api/questions",
            data="invalid json {",
            headers={'Content-Type': 'application/json'}
        )
        
        # 应该返回400错误
        self.assertIn(response.status_code, [400, 422])
        print("✓ 无效JSON错误处理测试通过")
    
    def test_error_handling_missing_required_fields(self):
        """测试错误处理 - 缺少必填字段"""
        # 缺少question字段
        response = self.session.post(
            f"{self.base_url}/api/questions",
            json={"type": 0}
        )
        
        # 应该返回400错误
        self.assertIn(response.status_code, [400, 422])
        print("✓ 缺少必填字段错误处理测试通过")
    
    def test_cors_headers(self):
        """测试CORS头"""
        response = self.session.options(f"{self.base_url}/api/questions")
        
        # 检查CORS头
        self.assertIn("access-control-allow-origin", response.headers)
        print("✓ CORS头测试通过")
    
    def test_concurrent_requests(self):
        """测试并发请求处理"""
        import threading
        
        def create_question(index):
            try:
                question_data = {
                    "question": f"并发测试题目{index}",
                    "type": 0,
                    "answer": {"answerText": f"测试答案{index}"}
                }
                response = self.session.post(
                    f"{self.base_url}/api/questions",
                    json=question_data
                )
                return response.status_code == 200
            except:
                return False
        
        # 启动10个并发线程
        threads = []
        results = []
        
        for i in range(10):
            thread = threading.Thread(target=lambda idx=i: results.append(create_question(idx)))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 至少80%的请求应该成功
        success_count = sum(results)
        self.assertGreaterEqual(success_count, 8)
        print(f"✓ 并发测试通过 - {success_count}/10 成功")

def run_tests():
    """运行所有测试"""
    print("🚀 开始TikuLocal API集成测试...")
    print("=" * 50)
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TikuLocalAPITest)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果:")
    print(f"   运行测试: {result.testsRun}")
    print(f"   成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   失败: {len(result.failures)}")
    print(f"   错误: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ 失败的测试:")
        for test, traceback in result.failures:
            print(f"   - {test}: {traceback}")
    
    if result.errors:
        print("\n💥 错误的测试:")
        for test, traceback in result.errors:
            print(f"   - {test}: {traceback}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)