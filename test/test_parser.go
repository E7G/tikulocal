package main

import (
	"fmt"
	"log"
)

func testParser() {
	// 测试样例文本
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

	fmt.Println("=== 测试解析器 ===")
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
}

func main() {
	testParser()
}
