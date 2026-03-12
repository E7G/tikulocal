package main

import (
	"fmt"
	"log"
)

func testParser() {
	fmt.Println("=== 测试原始格式 ===")
	testText := `1 【单选题】
我国第一艘国产电磁弹射航母福建舰下水，第一艘国产大型邮轮"爱达·魔都号"建成运营，加上大型( )全球领先，集齐了船舶工业皇冠上的"三颗明珠"。

选项：
A、 液化天然气运输船
B、 液化石油气运输船
C、 氢气运输船
D、 煤气运输船

我的答案：A
答案状态：正确
得分：2.0分`

	questions, err := ParseQuestions(testText)
	if err != nil {
		log.Printf("解析失败: %v", err)
		return
	}

	fmt.Printf("成功解析 %d 道题目\n", len(questions))
	for i, q := range questions {
		fmt.Printf("\n题目 %d:\n", i+1)
		fmt.Printf("题型: '%s'\n", q.Type)
		fmt.Printf("题干: '%s'\n", q.Text)
		fmt.Printf("选项: %v\n", q.Options)
		fmt.Printf("答案: %v\n", q.Answer)
	}

	fmt.Println("\n=== 测试油猴脚本格式（点号分隔）===")
	testText2 := `1 【单选题】
这是题目内容
选项：A.选项A内容 B.选项B内容 C.选项C内容 D.选项D内容
我的答案：A`

	questions2, err := ParseQuestions(testText2)
	if err != nil {
		log.Printf("解析失败: %v", err)
		return
	}

	fmt.Printf("成功解析 %d 道题目\n", len(questions2))
	for i, q := range questions2 {
		fmt.Printf("\n题目 %d:\n", i+1)
		fmt.Printf("题型: '%s'\n", q.Type)
		fmt.Printf("题干: '%s'\n", q.Text)
		fmt.Printf("选项: %v\n", q.Options)
		fmt.Printf("答案: %v\n", q.Answer)
	}

	fmt.Println("\n=== 测试油猴脚本格式（顿号分隔）===")
	testText3 := `1 【多选题】
这是多选题目
选项：A、选项A B、选项B C、选项C D、选项D
正确答案：ABC`

	questions3, err := ParseQuestions(testText3)
	if err != nil {
		log.Printf("解析失败: %v", err)
		return
	}

	fmt.Printf("成功解析 %d 道题目\n", len(questions3))
	for i, q := range questions3 {
		fmt.Printf("\n题目 %d:\n", i+1)
		fmt.Printf("题型: '%s'\n", q.Type)
		fmt.Printf("题干: '%s'\n", q.Text)
		fmt.Printf("选项: %v\n", q.Options)
		fmt.Printf("答案: %v\n", q.Answer)
	}

	fmt.Println("\n=== 测试判断题格式 ===")
	testText4 := `1 【判断题】
这是判断题内容
我的答案：对`

	questions4, err := ParseQuestions(testText4)
	if err != nil {
		log.Printf("解析失败: %v", err)
		return
	}

	fmt.Printf("成功解析 %d 道题目\n", len(questions4))
	for i, q := range questions4 {
		fmt.Printf("\n题目 %d:\n", i+1)
		fmt.Printf("题型: '%s'\n", q.Type)
		fmt.Printf("题干: '%s'\n", q.Text)
		fmt.Printf("选项: %v\n", q.Options)
		fmt.Printf("答案: %v\n", q.Answer)
	}

	fmt.Println("\n=== 测试混合格式 ===")
	testText5 := `1 【单选题】
题目1内容
选项：A.选项A B.选项B C.选项C D.选项D
我的答案：A
2 【判断题】
题目2内容
正确答案：错
3 【多选题】
题目3内容
选项：A、选项A B、选项B C、选项C D、选项D
正确答案：AC`

	questions5, err := ParseQuestions(testText5)
	if err != nil {
		log.Printf("解析失败: %v", err)
		return
	}

	fmt.Printf("成功解析 %d 道题目\n", len(questions5))
	for i, q := range questions5 {
		fmt.Printf("\n题目 %d:\n", i+1)
		fmt.Printf("题型: '%s'\n", q.Type)
		fmt.Printf("题干: '%s'\n", q.Text)
		fmt.Printf("选项: %v\n", q.Options)
		fmt.Printf("答案: %v\n", q.Answer)
	}
}

func main() {
	testParser()
}
