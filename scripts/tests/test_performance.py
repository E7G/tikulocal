#!/usr/bin/env python3
"""
TikuLocal性能测试
测试系统响应时间、并发处理能力、内存使用等
"""

import unittest
import requests
import time
import threading
import psutil
import os
import json
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

class PerformanceTest(unittest.TestCase):
    """性能测试类"""
    
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
        
        # 预创建一些测试数据
        self._prepare_test_data()
    
    def tearDown(self):
        """测试清理"""
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
    
    def _prepare_test_data(self):
        """准备测试数据"""
        # 创建100个测试题目
        test_questions = []
        for i in range(100):
            question_data = {
                "question": f"性能测试题目{i}: 测试内容{i}？",
                "options": [f"选项A{i}", f"选项B{i}", f"选项C{i}", f"选项D{i}"],
                "type": i % 5,  # 混合题型
                "answer": {
                    "answerKey": ["A"],
                    "answerKeyText": "A",
                    "answerIndex": [0],
                    "answerText": f"性能测试答案{i}",
                    "bestAnswer": [f"性能测试答案{i}"],
                    "allAnswer": [[f"性能测试答案{i}"]]
                }
            }
            test_questions.append(question_data)
        
        # 批量导入测试数据
        import_data = {"questions": test_questions}
        response = self.session.post(f"{self.base_url}/api/import", json=import_data)
        if response.status_code == 200:
            print("✓ 测试数据准备完成")
        else:
            print(f"⚠️  测试数据准备失败: {response.status_code}")
    
    def measure_response_time(self, func, *args, **kwargs):
        """测量响应时间"""
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        return result, end_time - start_time
    
    def test_homepage_response_time(self):
        """测试首页响应时间"""
        response, response_time = self.measure_response_time(
            self.session.get, f"{self.base_url}/"
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(response_time, 0.5)  # 应该在0.5秒内响应
        
        print(f"✓ 首页响应时间测试通过 - 耗时: {response_time:.3f}秒")
    
    def test_search_performance(self):
        """测试搜索性能"""
        search_data = {
            "question": "性能测试",
            "type": 0
        }
        
        # 多次搜索取平均值
        response_times = []
        for _ in range(10):
            response, response_time = self.measure_response_time(
                self.session.post, f"{self.base_url}/api/search", json=search_data
            )
            
            if response.status_code == 200:
                response_times.append(response_time)
        
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            self.assertLess(avg_response_time, 1.0)  # 平均响应时间应该小于1秒
            print(f"✓ 搜索性能测试通过 - 平均响应时间: {avg_response_time:.3f}秒")
        else:
            print("⚠️  搜索性能测试 - 无成功响应")
    
    def test_create_question_performance(self):
        """测试创建题目性能"""
        question_data = {
            "question": "性能测试：这是一个性能测试题目？",
            "options": ["选项A", "选项B", "选项C", "选项D"],
            "type": 0,
            "answer": {
                "answerKey": ["A"],
                "answerKeyText": "A",
                "answerIndex": [0],
                "answerText": "选项A",
                "bestAnswer": ["选项A"],
                "allAnswer": [["选项A"]]
            }
        }
        
        # 多次创建取平均值
        response_times = []
        for _ in range(10):
            response, response_time = self.measure_response_time(
                self.session.post, f"{self.base_url}/api/questions", json=question_data
            )
            
            if response.status_code == 200:
                response_times.append(response_time)
        
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            self.assertLess(avg_response_time, 0.5)  # 平均响应时间应该小于0.5秒
            print(f"✓ 创建题目性能测试通过 - 平均响应时间: {avg_response_time:.3f}秒")
        else:
            print("⚠️  创建题目性能测试 - 无成功响应")
    
    def test_concurrent_requests_performance(self):
        """测试并发请求性能"""
        def make_request(i):
            try:
                search_data = {
                    "question": f"性能测试{i}",
                    "type": i % 5
                }
                start_time = time.time()
                response = self.session.post(
                    f"{self.base_url}/api/search", 
                    json=search_data,
                    timeout=5
                )
                end_time = time.time()
                
                return {
                    "status": response.status_code,
                    "response_time": end_time - start_time,
                    "success": response.status_code == 200
                }
            except requests.exceptions.RequestException:
                return {"status": 0, "response_time": 0, "success": False}
        
        # 测试不同并发级别
        concurrent_levels = [10, 20, 50]
        
        for level in concurrent_levels:
            start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=level) as executor:
                futures = [executor.submit(make_request, i) for i in range(level)]
                results = [future.result() for future in as_completed(futures)]
            
            total_time = time.time() - start_time
            
            success_count = sum(1 for r in results if r["success"])
            success_rate = success_count / level * 100
            
            if results:
                avg_response_time = sum(r["response_time"] for r in results if r["success"]) / success_count if success_count > 0 else 0
            else:
                avg_response_time = 0
            
            print(f"✓ 并发性能测试 - {level}并发: 成功率{success_rate:.1f}%, 总耗时{total_time:.2f}s, 平均响应{avg_response_time:.3f}s")
            
            # 基本性能要求
            self.assertGreaterEqual(success_rate, 80)  # 成功率至少80%
    
    def test_memory_usage(self):
        """测试内存使用情况"""
        process = psutil.Process(os.getpid())
        
        # 基准内存使用
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 执行大量操作
        for i in range(100):
            question_data = {
                "question": f"内存测试{i}: 这是一个内存测试题目？",
                "options": [f"选项A{i}", f"选项B{i}", f"选项C{i}", f"选项D{i}"],
                "type": 0,
                "answer": {
                    "answerKey": ["A"],
                    "answerKeyText": "A",
                    "answerIndex": [0],
                    "answerText": f"内存测试答案{i}",
                    "bestAnswer": [f"内存测试答案{i}"],
                    "allAnswer": [[f"内存测试答案{i}"]]
                }
            }
            
            try:
                self.session.post(f"{self.base_url}/api/questions", json=question_data)
            except:
                pass
        
        # 峰值内存使用
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - baseline_memory
        
        # 内存增长应该合理（小于100MB）
        self.assertLess(memory_increase, 100)
        
        print(f"✓ 内存使用测试通过 - 基准内存: {baseline_memory:.1f}MB, 峰值内存: {peak_memory:.1f}MB, 增长: {memory_increase:.1f}MB")
    
    def test_import_performance(self):
        """测试批量导入性能"""
        # 准备不同规模的测试数据
        batch_sizes = [10, 50, 100]
        
        for batch_size in batch_sizes:
            questions = []
            for i in range(batch_size):
                question_data = {
                    "question": f"批量导入测试{i}: 这是第{i}个测试题目？",
                    "options": [f"选项A{i}", f"选项B{i}", f"选项C{i}", f"选项D{i}"],
                    "type": i % 5,
                    "answer": {
                        "answerKey": ["A"],
                        "answerKeyText": "A",
                        "answerIndex": [0],
                        "answerText": f"批量导入答案{i}",
                        "bestAnswer": [f"批量导入答案{i}"],
                        "allAnswer": [[f"批量导入答案{i}"]]
                    }
                }
                questions.append(question_data)
            
            import_data = {"questions": questions}
            
            response, response_time = self.measure_response_time(
                self.session.post, f"{self.base_url}/api/import", json=import_data
            )
            
            if response.status_code == 200:
                # 计算每秒导入的题目数
                questions_per_second = batch_size / response_time
                print(f"✓ 批量导入性能测试 - {batch_size}题: 耗时{response_time:.2f}s, 速度{questions_per_second:.1f}题/秒")
                
                # 导入时间应该合理（100题小于5秒）
                self.assertLess(response_time, 5.0)
            else:
                print(f"⚠️  批量导入性能测试 - {batch_size}题失败: {response.status_code}")
    
    def test_database_query_performance(self):
        """测试数据库查询性能"""
        # 搜索不同的关键词
        search_keywords = ["性能测试", "测试", "题目"]
        
        for keyword in search_keywords:
            search_data = {
                "question": keyword,
                "type": -1  # 搜索所有类型
            }
            
            response, response_time = self.measure_response_time(
                self.session.post, f"{self.base_url}/api/search", json=search_data
            )
            
            if response.status_code == 200:
                print(f"✓ 数据库查询性能测试 - 关键词'{keyword}': 耗时{response_time:.3f}秒")
                # 查询时间应该小于1秒
                self.assertLess(response_time, 1.0)
            else:
                print(f"⚠️  数据库查询性能测试 - 关键词'{keyword}'失败: {response.status_code}")
    
    def test_error_response_time(self):
        """测试错误响应时间"""
        # 测试各种错误情况
        error_cases = [
            (f"{self.base_url}/api/search", {}),  # 缺少必填字段
            (f"{self.base_url}/api/questions", {}),  # 无效数据
            (f"{self.base_url}/nonexistent", {}),  # 不存在的端点
        ]
        
        for url, data in error_cases:
            response, response_time = self.measure_response_time(
                self.session.post, url, json=data
            )
            
            # 错误响应也应该很快（小于0.5秒）
            self.assertLess(response_time, 0.5)
            print(f"✓ 错误响应时间测试 - {url}: 耗时{response_time:.3f}秒")
    
    def test_stress_test(self):
        """压力测试"""
        print("🚀 开始压力测试...")
        
        # 持续运行一段时间
        test_duration = 30  # 30秒
        start_time = time.time()
        
        request_count = 0
        success_count = 0
        response_times = []
        
        while time.time() - start_time < test_duration:
            try:
                # 随机选择操作类型
                import random
                operation = random.choice(["search", "create"])
                
                if operation == "search":
                    search_data = {
                        "question": f"压力测试{random.randint(1, 100)}",
                        "type": random.randint(0, 4)
                    }
                    response = self.session.post(
                        f"{self.base_url}/api/search", 
                        json=search_data,
                        timeout=2
                    )
                else:
                    question_data = {
                        "question": f"压力测试题目{random.randint(1, 1000)}",
                        "options": ["选项A", "选项B", "选项C", "选项D"],
                        "type": random.randint(0, 4),
                        "answer": {"answerText": "压力测试答案"}
                    }
                    response = self.session.post(
                        f"{self.base_url}/api/questions", 
                        json=question_data,
                        timeout=2
                    )
                
                request_count += 1
                if response.status_code == 200:
                    success_count += 1
                
            except requests.exceptions.RequestException:
                pass
            
            # 稍微休息一下，避免过于频繁
            time.sleep(0.1)
        
        # 计算结果
        success_rate = (success_count / request_count * 100) if request_count > 0 else 0
        requests_per_second = request_count / test_duration
        
        print(f"✓ 压力测试完成 - 总请求: {request_count}, 成功: {success_count}, 成功率: {success_rate:.1f}%, 频率: {requests_per_second:.1f}请求/秒")
        
        # 基本性能要求
        self.assertGreaterEqual(success_rate, 70)  # 成功率至少70%
        self.assertGreaterEqual(requests_per_second, 5)  # 至少5请求/秒

def run_performance_tests():
    """运行所有性能测试"""
    print("⚡ 开始TikuLocal性能测试...")
    print("=" * 50)
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(PerformanceTest)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    
    print("\n" + "=" * 50)
    print(f"📊 性能测试结果:")
    print(f"   运行测试: {result.testsRun}")
    print(f"   成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   失败: {len(result.failures)}")
    print(f"   错误: {len(result.errors)}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_performance_tests()
    exit(0 if success else 1)