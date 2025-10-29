#!/usr/bin/env python3
"""
解析answer2.txt文件 - 适配新版格式
Linus式思考：消除特殊情况，统一处理逻辑
"""

import json
import re
import sys


def parse_answer2_file(file_path):
    """解析answer2.txt文件"""
    questions = []
    current_chapter = ""
    question_counter = 0
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # 跳过空行
        if not line:
            i += 1
            continue
        
        # 匹配章节标题（如"二.判断题（共2题,66.7分）"）
        chapter_match = re.match(r'^(.+?)\([共共].*?题.*\)$', line)
        if chapter_match:
            current_chapter = chapter_match.group(1).rstrip('.')
            i += 1
            continue
        
        # 匹配题目（如"1【单选题】题目内容"）
        question_match = re.match(r'^\d+[【\[](单选题|多选题|判断题)[】\]](.*)', line)
        if question_match:
            q_type = question_match.group(1)
            question_text = question_match.group(2).strip()
            
            question_data = {
                "type": q_type,
                "question": question_text,
                "options": [],
                "answer": "",
                "chapter": current_chapter
            }
            
            # 解析选项（A、B、C、D格式）
            i += 1
            while i < len(lines):
                line = lines[i].strip()
                
                # 跳过空行
                if line == '':
                    i += 1
                    continue
                    
                # 匹配各种格式的选项：A、xxx, · A、xxx, A.xxx 等
                option_match = re.match(r'^[·\s]*([A-Z])[、\.](.+)', line)
                if option_match:
                    option_text = option_match.group(2).strip()
                    question_data["options"].append({"value": option_text})
                    i += 1
                else:
                    # 不是选项格式，结束选项解析
                    break
            
            # 解析答案和得分
            while i < len(lines):
                answer_line = lines[i].strip()
                
                # 匹配答案（如"我的答案：B得分：33.3分"）
                answer_match = re.match(r'我的答案：(.+?)得分：\s*([\d.]+)分', answer_line)
                if answer_match:
                    question_data["answer"] = answer_match.group(1).strip()
                    question_data["score"] = float(answer_match.group(2))
                    i += 1
                    break
                
                # 匹配只有答案的行（如"我的答案：B"）
                simple_answer_match = re.match(r'我的答案：(.+)', answer_line)
                if simple_answer_match and not answer_line.endswith('分'):
                    question_data["answer"] = simple_answer_match.group(1).strip()
                    i += 1
                    break
                
                i += 1
            
            # 清理答案格式（判断题）
            if q_type == "判断题":
                if question_data["answer"] in ["√", "对", "正确"]:
                    question_data["answer"] = "√"
                elif question_data["answer"] in ["×", "错", "错误"]:
                    question_data["answer"] = "×"
            
            questions.append(question_data)
            question_counter += 1
            continue
        
        i += 1
    
    return {"questions": questions, "total": len(questions)}


def main():
    """命令行入口"""
    if len(sys.argv) != 3:
        print("用法: python parse_answer2_to_json.py <输入文件> <输出文件>")
        print("示例: python parse_answer2_to_json.py reference/answer2.txt reference/answer2_parsed.json")
        return
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    try:
        data = parse_answer2_file(input_file)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 解析完成！")
        print(f"📊 共解析 {data['total']} 道题目")
        
        # 显示统计信息
        type_count = {}
        for q in data['questions']:
            q_type = q['type']
            type_count[q_type] = type_count.get(q_type, 0) + 1
        
        print(f"📈 题型分布:")
        for q_type, count in type_count.items():
            print(f"  {q_type}: {count} 题")
        
        # 显示前3道题作为示例
        print(f"\n🔍 前3道题示例:")
        for i, q in enumerate(data['questions'][:3]):
            print(f"题目 {i+1}: {q['question'][:50]}...")
            print(f"  类型: {q['type']}")
            print(f"  答案: {q['answer']}")
            if q['options']:
                print(f"  选项数: {len(q['options'])}")
        
    except Exception as e:
        print(f"❌ 解析失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()