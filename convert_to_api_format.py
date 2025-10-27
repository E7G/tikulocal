#!/usr/bin/env python3
"""
将Linus格式的JSON转换为API导入格式
保持简单，拒绝过度设计
"""

import json
import sys


def convert_answer_to_api_format(question):
    """
    将简单答案转换为过度设计的API格式
    这是为了满足API要求，不是好设计
    """
    answer_text = question["answer"]
    q_type = question["type"]
    options = question.get("options", [])
    
    # 基础答案键 - 拒绝None，用空列表
    answer_key = []
    answer_index = []
    answer_text_list = []
    
    if q_type == "单选题":
        # 单选题：A -> 0，简单直接
        if answer_text and answer_text in "ABCD":
            answer_key = [answer_text]
            answer_index = [ord(answer_text) - ord('A')]
            if answer_index[0] < len(options):
                answer_text_list = [options[answer_index[0]]["value"]]
    
    elif q_type == "多选题":
        # 多选题：AC -> [0, 2]，逐个处理
        for char in answer_text:
            if char in "ABCD":
                answer_key.append(char)
                idx = ord(char) - ord('A')
                answer_index.append(idx)
                if idx < len(options):
                    answer_text_list.append(options[idx]["value"])
    
    elif q_type == "判断题":
        # 判断题：√/X/对/错 -> 布尔值映射
        if answer_text == "√" or answer_text == "对":
            answer_key = ["√"]
            answer_text_list = ["正确"]
        elif answer_text == "X" or answer_text == "错":
            answer_key = ["X"]
            answer_text_list = ["错误"]
    
    # API要求6个字段，尽管冗余但照做
    return {
        "answerKey": answer_key,
        "answerKeyText": "".join(answer_key),
        "answerIndex": answer_index,
        "answerText": answer_text_list[0] if answer_text_list else "",
        "bestAnswer": answer_text_list,
        "allAnswer": [answer_text_list]  # 最冗余的部分，但API要
    }


def convert_to_api_format(input_file, output_file):
    """转换整个JSON文件到API格式"""
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 保持原有结构，只转换questions数组
        api_questions = []
        
        for q in data["questions"]:
            api_question = {
                "question": q["question"],
                "options": [opt["value"] for opt in q.get("options", [])],
                "type": 0 if q["type"] == "单选题" else (1 if q["type"] == "多选题" else 2),
                "answer": convert_answer_to_api_format(q)
            }
            api_questions.append(api_question)
        
        # 构建API格式输出
        api_data = {
            "questions": api_questions
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(api_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 转换完成：{input_file} -> {output_file}")
        print(f"📊 共转换 {len(api_questions)} 道题目")
        
        # 显示几个示例
        print("\n🔍 转换示例：")
        for i, q in enumerate(api_questions[:3]):
            print(f"题目 {i+1}: {q['question'][:50]}...")
            print(f"  类型: {q['type']} (0=单选,1=多选,2=判断)")
            print(f"  答案: {q['answer']['answerKeyText']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 转换失败: {e}")
        return False


def main():
    """命令行入口"""
    if len(sys.argv) != 3:
        print("用法: python convert_to_api_format.py <输入文件> <输出文件>")
        print("示例: python convert_to_api_format.py reference/answers_linus.json reference/api_format.json")
        return
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    convert_to_api_format(input_file, output_file)


if __name__ == "__main__":
    main()