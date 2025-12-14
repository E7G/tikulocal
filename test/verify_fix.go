package main

import (
	"fmt"
	"log"
)

// 测试解析器修复效果
func testParserFix() {
	// 测试样例文本 - 模拟用户提到的复杂情况
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

	fmt.Println("=== 测试解析器修复效果 ===")

	// 创建解析器
	parser := NewParser()

	// 先进行词法分析，查看tokens
	parser.tokenize(testText)

	fmt.Printf("生成的tokens数量: %d\n", len(parser.tokens))

	// 检查是否有选项相关的tokens
	hasOptions := false
	for i, token := range parser.tokens {
		fmt.Printf("Token %d: Type=%d, Value='%s', Line=%d\n", i, token.Type, token.Value, token.Line)
		if token.Type == 4 || token.Type == 5 { // OptionMarker or OptionText
			hasOptions = true
		}
	}

	if !hasOptions {
		fmt.Println("⚠️  警告: 没有找到选项相关的tokens！")
	}
	fmt.Println()

	// 再进行完整解析
	questions, err := parser.parse(testText)
	if err != nil {
		log.Printf("解析失败: %v", err)
		return
	}

	fmt.Printf("✅ 成功解析 %d 道题目\n\n", len(questions))

	for i, q := range questions {
		fmt.Printf("📋 题目 %d:\n", i+1)
		fmt.Printf("   题型: '%s'\n", q.Type)
		fmt.Printf("   题干: '%s'\n", truncateText(q.Text, 80))
		fmt.Printf("   选项数量: %d\n", len(q.Options))
		for j, opt := range q.Options {
			fmt.Printf("     %c. %s\n", 'A'+j, truncateText(opt, 50))
		}
		fmt.Printf("   答案: %v\n", q.Answer)
		fmt.Println()
	}
}

func truncateText(text string, maxLen int) string {
	if len(text) <= maxLen {
		return text
	}
	return text[:maxLen] + "..."
}
