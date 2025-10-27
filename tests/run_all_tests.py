#!/usr/bin/env python3
"""
TikuLocal完整测试套件运行器
运行所有测试并生成综合报告
"""

import sys
import os
import time
import subprocess
import json
from datetime import datetime
from typing import Dict, List, Tuple

class TestRunner:
    """测试运行器"""
    
    def __init__(self):
        self.test_files = [
            "test_api_integration.py",
            "test_database_operations.py", 
            "test_file_parsing.py",
            "test_performance.py"
        ]
        self.results = {}
        self.start_time = None
        self.end_time = None
    
    def check_dependencies(self) -> bool:
        """检查依赖"""
        print("🔍 检查测试依赖...")
        
        dependencies = {
            "requests": "requests",
            "psutil": "psutil",
            "unittest": "unittest"
        }
        
        missing_deps = []
        
        for module, package in dependencies.items():
            try:
                __import__(module)
            except ImportError:
                missing_deps.append(package)
        
        if missing_deps:
            print(f"❌ 缺少依赖包: {', '.join(missing_deps)}")
            print("请安装: pip install " + " ".join(missing_deps))
            return False
        
        print("✅ 所有依赖已安装")
        return True
    
    def check_service_status(self) -> bool:
        """检查服务状态"""
        print("🔍 检查TikuLocal服务状态...")
        
        try:
            import requests
            response = requests.get("http://localhost:8060/", timeout=5)
            if response.status_code == 200:
                print("✅ TikuLocal服务正在运行")
                return True
            else:
                print(f"❌ TikuLocal服务返回错误状态码: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print("❌ TikuLocal服务未启动")
            print("请先启动服务: cargo run")
            return False
        except Exception as e:
            print(f"❌ 检查服务状态时出错: {e}")
            return False
    
    def run_single_test(self, test_file: str) -> Tuple[bool, str, float]:
        """运行单个测试文件"""
        print(f"\n📋 运行测试: {test_file}")
        print("-" * 50)
        
        start_time = time.time()
        
        try:
            # 运行测试文件
            result = subprocess.run(
                [sys.executable, test_file],
                cwd="tests",
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            execution_time = time.time() - start_time
            success = result.returncode == 0
            
            # 输出结果
            if success:
                print(f"✅ {test_file} - 通过 (耗时: {execution_time:.2f}秒)")
            else:
                print(f"❌ {test_file} - 失败 (耗时: {execution_time:.2f}秒)")
                if result.stdout:
                    print("STDOUT:", result.stdout)
                if result.stderr:
                    print("STDERR:", result.stderr)
            
            return success, result.stdout + result.stderr, execution_time
            
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            print(f"⏰ {test_file} - 超时 (耗时: {execution_time:.2f}秒)")
            return False, "测试超时", execution_time
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"💥 {test_file} - 异常 (耗时: {execution_time:.2f}秒)")
            print(f"错误: {e}")
            return False, str(e), execution_time
    
    def run_all_tests(self) -> bool:
        """运行所有测试"""
        print("🚀 开始运行TikuLocal完整测试套件...")
        print("=" * 60)
        
        self.start_time = time.time()
        
        # 检查依赖和服务状态
        if not self.check_dependencies():
            return False
        
        if not self.check_service_status():
            return False
        
        print("\n" + "=" * 60)
        
        # 运行每个测试文件
        total_tests = len(self.test_files)
        passed_tests = 0
        
        for i, test_file in enumerate(self.test_files, 1):
            print(f"\n[{i}/{total_tests}] ", end="")
            
            success, output, execution_time = self.run_single_test(test_file)
            
            self.results[test_file] = {
                "success": success,
                "output": output,
                "execution_time": execution_time
            }
            
            if success:
                passed_tests += 1
        
        self.end_time = time.time()
        
        # 生成报告
        self.generate_report(passed_tests, total_tests)
        
        return passed_tests == total_tests
    
    def generate_report(self, passed_tests: int, total_tests: int):
        """生成测试报告"""
        total_time = self.end_time - self.start_time
        
        print("\n" + "=" * 60)
        print("📊 TIKULOCAL测试报告")
        print("=" * 60)
        
        print(f"\n🕐 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  总耗时: {total_time:.2f}秒")
        print(f"📋 测试文件: {total_tests}个")
        print(f"✅ 通过: {passed_tests}个")
        print(f"❌ 失败: {total_tests - passed_tests}个")
        print(f"📈 成功率: {(passed_tests/total_tests*100):.1f}%")
        
        print("\n📋 详细结果:")
        print("-" * 60)
        
        for test_file, result in self.results.items():
            status = "✅ 通过" if result["success"] else "❌ 失败"
            print(f"{status} {test_file:<30} 耗时: {result['execution_time']:.2f}秒")
        
        print("\n🎯 测试覆盖范围:")
        print("-" * 60)
        print("• API集成测试: 测试所有API端点的功能和正确性")
        print("• 数据库操作测试: 测试数据库连接、数据完整性和性能")
        print("• 文件解析测试: 测试文件读取、格式检测和数据验证")
        print("• 性能测试: 测试系统响应时间、并发处理能力和稳定性")
        
        print("\n🔧 测试环境要求:")
        print("-" * 60)
        print("• TikuLocal服务必须在 http://localhost:8060 运行")
        print("• Python 3.6+ 环境")
        print("• 依赖包: requests, psutil")
        print("• 足够的系统资源（内存、CPU）")
        
        if passed_tests == total_tests:
            print("\n🎉 所有测试通过！系统运行良好。")
        else:
            print(f"\n⚠️  {total_tests - passed_tests}个测试失败，请检查错误信息并修复问题。")
            print("\n🔍 故障排除建议:")
            print("• 确保TikuLocal服务正常运行")
            print("• 检查网络连接和端口配置")
            print("• 查看具体的错误输出信息")
            print("• 确保测试数据文件存在且格式正确")
        
        # 保存详细报告到文件
        self.save_detailed_report()
    
    def save_detailed_report(self):
        """保存详细报告到文件"""
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(self.test_files),
            "passed_tests": sum(1 for r in self.results.values() if r["success"]),
            "total_time": self.end_time - self.start_time,
            "results": self.results
        }
        
        report_file = "tests/test_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 详细测试报告已保存到: {report_file}")

def main():
    """主函数"""
    # 确保在正确的目录
    if not os.path.exists("tests"):
        print("❌ 错误：必须在项目根目录运行此脚本")
        print("当前目录:", os.getcwd())
        return False
    
    # 运行测试
    runner = TestRunner()
    success = runner.run_all_tests()
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)