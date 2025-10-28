import re
import json
import sys

def parse_answers_to_json(input_file, output_file):
    """将answers.txt转换为JSON格式"""
    
    # 读取文件内容
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 按行分割内容
    lines = content.split('\n')
    
    questions = []
    current_question = None
    in_options = False  # 标记是否正在处理选项
    found_answer = False  # 标记是否已找到当前题目的答案
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 检查是否是题目开始
        # 统一匹配所有题目格式：
        # 1、【单选题】题目内容
        # 2、[单选题]题目内容
        # 1.[单选题]题目内容
        # 1. [单选题]题目内容（带空格）
        question_match = re.match(r'^\d+[、,\.]\s*[【\[]?(单选题|多选题|判断题)[】\]]?\s*(.*)', line)
            
        if question_match:
            # 保存上一题（如果有）
            if current_question:
                questions.append(current_question)
            
            # 开始新题目
            q_type = question_match.group(1)
            q_text = question_match.group(2).strip()
            
            current_question = {
                "type": q_type,
                "question": q_text,
                "options": [],
                "answer": ""
            }
            in_options = True  # 题目后可能跟选项
            found_answer = False  # 重置答案标记
            continue
        
        # 检查是否是章节标题 (如 1.2电影就是我们的生活)
        # 章节标题格式：数字.数字+空格+文字，且不包含题目类型和方括号
        section_match = re.match(r'^\d+\.\d+\s+(?!.*【?(单选题|多选题|判断题)】?)(?!.*\[(单选题|多选题|判断题)\]).*', line)
        if section_match:
            # 章节标题标志着新章节的开始，重置状态
            # 保存上一题（如果有）
            if current_question:
                questions.append(current_question)
                current_question = None
            in_options = False
            found_answer = False
            continue
        
        # 检查是否是章节标题 (如 5.1数字化与高科技)
        # 章节标题格式：数字.数字+文字（无空格），且不包含题目类型和方括号
        section_match2 = re.match(r'^\d+\.\d+[^0-9](?!.*【?(单选题|多选题|判断题)】?)(?!.*\[(单选题|多选题|判断题)\]).*', line)
        if section_match2:
            # 章节标题标志着新章节的开始，重置状态
            # 保存上一题（如果有）
            if current_question:
                questions.append(current_question)
                current_question = None
            in_options = False
            found_answer = False
            continue
        
        # 检查是否是选项 (A. 或 A、)
        # 只有在选项状态下且未找到答案时才处理选项
        if in_options and not found_answer and current_question:
            option_match = re.match(r'^([A-Z])[、.]\s*(.*)', line)
            if option_match:
                opt_letter = option_match.group(1)
                opt_text = option_match.group(2).strip()
                current_question["options"].append({"value": opt_text})
                continue
        
        # 检查是否是答案
        # 只有在未找到当前题目答案时才处理
        if not found_answer and current_question:
            answer_match = re.match(r'^我的答案[：:]\s*(.*)', line)
            if answer_match:
                answer = answer_match.group(1).strip()
                current_question["answer"] = answer
                found_answer = True  # 标记已找到答案
                # 不设置in_options = False，保持状态直到遇到新题目或章节标题
                continue
    
    # 保存最后一题
    if current_question:
        questions.append(current_question)
    
    # 构建结果
    result = {"questions": questions}
    
    # 写入JSON文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"成功转换 {len(questions)} 道题目")
    
    # 显示几个示例
    for i, q in enumerate(questions[:3]):
        print(f"\n题目 {i+1}:")
        print(f"  类型: {q['type']}")
        print(f"  问题: {q['question']}")
        print(f"  选项数: {len(q.get('options', []))}")
        print(f"  答案: {q.get('answer', '无')}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法: python parse_answers_to_json.py <输入文件> <输出文件>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    parse_answers_to_json(input_file, output_file)