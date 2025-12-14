package main

import (
	"fmt"
	"sort"
	"strings"
	"unicode/utf8"
)

// TokenType 表示词法单元的类型
type TokenType int

const (
	TokenTypeQuestionNumber TokenType = iota
	TokenTypeQuestionType
	TokenTypeQuestionStem
	TokenTypeOptionMarker
	TokenTypeOptionText
	TokenTypeAnswerMarker
	TokenTypeAnswerText
	TokenTypeStatusMarker
	TokenTypeStatusText
	TokenTypeScoreMarker
	TokenTypeScoreText
	TokenTypeUnknown
)

// Token 表示一个词法单元
type Token struct {
	Type  TokenType
	Value string
	Line  int
}

// Parser 表示文档解析器
type Parser struct {
	tokens []Token
	pos    int
}

// NewParser 创建一个新的解析器
func NewParser() *Parser {
	return &Parser{
		tokens: make([]Token, 0),
		pos:    0,
	}
}

// tokenize 执行词法分析，将文本转换为词法单元
// tokenize 执行词法分析，将文本转换为词法单元
func (p *Parser) tokenize(text string) {
	lines := strings.Split(text, "\n")
	inOptionsSection := false
	currentStem := "" // 累积当前题干

	for lineNum, line := range lines {
		trimmed := strings.TrimSpace(line)
		if trimmed == "" {
			continue
		}

		// 检查是否是题目编号（例如 "50 【判断题】"）
		if strings.Contains(trimmed, "【") && strings.Contains(trimmed, "】") {
			// 保存之前的题干（如果有）
			if currentStem != "" {
				p.tokens = append(p.tokens, Token{
					Type:  TokenTypeQuestionStem,
					Value: strings.TrimSpace(currentStem),
					Line:  lineNum,
				})
				currentStem = ""
			}

			parts := strings.SplitN(trimmed, " ", 2)
			if len(parts) >= 2 {
				// 添加题目编号
				p.tokens = append(p.tokens, Token{
					Type:  TokenTypeQuestionNumber,
					Value: strings.TrimSpace(parts[0]),
					Line:  lineNum + 1,
				})

				// 提取题型
				typeStart := strings.Index(parts[1], "【")
				typeEnd := strings.Index(parts[1], "】")
				if typeStart != -1 && typeEnd != -1 && typeEnd > typeStart {
					qType := strings.TrimSpace(parts[1][typeStart+1 : typeEnd])
					// 确保题型编码正确
					if !utf8.ValidString(qType) {
						qType = strings.Map(func(r rune) rune {
							if r == utf8.RuneError {
								return -1
							}
							return r
						}, qType)
					}
					p.tokens = append(p.tokens, Token{
						Type:  TokenTypeQuestionType,
						Value: qType,
						Line:  lineNum + 1,
					})
				}
			}
			inOptionsSection = false
			continue
		}

		// 检查是否是"选项："标记
		if strings.HasPrefix(trimmed, "选项：") {
			// 保存之前的题干（如果有）
			if currentStem != "" {
				p.tokens = append(p.tokens, Token{
					Type:  TokenTypeQuestionStem,
					Value: strings.TrimSpace(currentStem),
					Line:  lineNum,
				})
				currentStem = ""
			}

			inOptionsSection = true
			// 提取选项内容
			optionsPart := strings.TrimPrefix(trimmed, "选项：")
			optionsPart = strings.TrimSpace(optionsPart)

			if optionsPart != "" {
				// 立即解析这一行的选项
				p.parseOptionsInLine(optionsPart, lineNum+1)
			}
			continue
		}

		// 如果在选项区域，解析选项
		if inOptionsSection {
			if p.parseOptionsInLine(trimmed, lineNum+1) {
				continue
			}
			// 如果没能解析为选项，说明选项区域结束
			inOptionsSection = false
		}

		// 检查是否是答案标记
		if strings.HasPrefix(trimmed, "我的答案") || strings.HasPrefix(trimmed, "正确答案") || strings.HasPrefix(trimmed, "答案") {
			// 保存之前的题干（如果有）
			if currentStem != "" {
				p.tokens = append(p.tokens, Token{
					Type:  TokenTypeQuestionStem,
					Value: strings.TrimSpace(currentStem),
					Line:  lineNum,
				})
				currentStem = ""
			}

			var marker, answerText string

			// 尝试不同的分割方式
			if strings.Contains(trimmed, "：") {
				parts := strings.SplitN(trimmed, "：", 2)
				if len(parts) >= 2 {
					marker = strings.TrimSpace(parts[0])
					answerText = strings.TrimSpace(parts[1])
				}
			} else if strings.Contains(trimmed, ":") {
				parts := strings.SplitN(trimmed, ":", 2)
				if len(parts) >= 2 {
					marker = strings.TrimSpace(parts[0])
					answerText = strings.TrimSpace(parts[1])
				}
			}

			if marker != "" && answerText != "" {
				p.tokens = append(p.tokens, Token{
					Type:  TokenTypeAnswerMarker,
					Value: marker,
					Line:  lineNum + 1,
				})
				p.tokens = append(p.tokens, Token{
					Type:  TokenTypeAnswerText,
					Value: answerText,
					Line:  lineNum + 1,
				})
			}
			inOptionsSection = false
			continue
		}

		// 检查是否是状态或分数标记
		if strings.HasPrefix(trimmed, "答案状态") || strings.HasPrefix(trimmed, "得分") {
			continue // 忽略这些行
		}

		// 其他内容作为题干的一部分累积
		if currentStem == "" {
			currentStem = trimmed
		} else {
			currentStem += " " + trimmed
		}

		// 检查累积的题干是否包含选项格式，如果是则立即解析
		// 但只有在累积了足够多的内容后才解析，避免过早解析
		if strings.Contains(currentStem, "A、") && strings.Contains(currentStem, "B、") {
			fmt.Printf("DEBUG: Found options in accumulated stem: '%s'\n", currentStem)
			// 检查是否包含所有四个选项，如果是则进行完整解析
			if strings.Contains(currentStem, "C、") && strings.Contains(currentStem, "D、") {
				fmt.Printf("DEBUG: Found all 4 options, parsing complete set\n")
				if p.parseOptionsInLine(currentStem, lineNum) {
					// 如果成功解析为选项，清空累积的题干
					currentStem = ""
				}
			}
		}
	}

	// 保存最后的题干（如果有）
	if currentStem != "" {
		// 尝试解析题干中的选项（如果包含选项格式）
		if p.parseOptionsInLine(currentStem, len(lines)) {
			// 如果成功解析为选项，不将其作为题干
		} else {
			p.tokens = append(p.tokens, Token{
				Type:  TokenTypeQuestionStem,
				Value: strings.TrimSpace(currentStem),
				Line:  len(lines),
			})
		}
	}
}

// parseOptionsInLine 解析一行中的选项，返回是否成功解析
func (p *Parser) parseOptionsInLine(line string, lineNum int) bool {
	originalLen := len(p.tokens)

	fmt.Printf("DEBUG: parseOptionsInLine called with line: '%s'\n", line)

	// 首先检查这一行是否包含多个选项格式
	if strings.Contains(line, "A、") && strings.Contains(line, "B、") {
		fmt.Printf("DEBUG: Found multiple options in line\n")

		// 改进的解析方法：使用字符串包含来查找选项标记
		markers := []string{}
		for ch := 'A'; ch <= 'Z'; ch++ {
			markers = append(markers, string(ch)+"、")
		}
		markerPositions := []int{}

		for _, marker := range markers {
			if pos := strings.Index(line, marker); pos != -1 {
				markerPositions = append(markerPositions, pos)
				fmt.Printf("DEBUG: Found marker '%s' at position %d\n", marker, pos)
			}
		}

		// 排序位置
		sort.Ints(markerPositions)
		fmt.Printf("DEBUG: Found %d option markers at positions: %v\n", len(markerPositions), markerPositions)

		// 解析每个选项
		for i := 0; i < len(markerPositions); i++ {
			markerPos := markerPositions[i]

			// 确定标记字符（A、B、C、D）
			marker := string(line[markerPos])

			// 确定选项文本的开始位置（跳过标记）
			startPos := markerPos + 2 // "A、"是2个字符
			endPos := len(line)

			// 如果还有下一个选项，则结束位置为下一个选项的开始
			if i+1 < len(markerPositions) {
				endPos = markerPositions[i+1]
			}

			optionText := strings.TrimSpace(line[startPos:endPos])

			// 清理编码问题
			if !utf8.ValidString(optionText) {
				optionText = strings.Map(func(r rune) rune {
					if r == utf8.RuneError {
						return -1
					}
					return r
				}, optionText)
			}

			fmt.Printf("DEBUG: Option %s: '%s' (start:%d, end:%d)\n", marker, optionText, startPos, endPos)

			if optionText != "" {
				p.tokens = append(p.tokens, Token{
					Type:  TokenTypeOptionMarker,
					Value: marker,
					Line:  lineNum,
				})
				p.tokens = append(p.tokens, Token{
					Type:  TokenTypeOptionText,
					Value: optionText,
					Line:  lineNum,
				})
			}
		}

		fmt.Printf("DEBUG: parseOptionsInLine returning %v (added %d tokens)\n", len(p.tokens) > originalLen, len(p.tokens)-originalLen)
		return len(p.tokens) > originalLen
	}

	fmt.Printf("DEBUG: No multiple options found, trying single option parsing\n")

	// 原有的单选项解析逻辑
	i := 0
	for i < len(line) {
		// 查找选项标记（A、B、C等）
		if i+1 < len(line) && line[i] >= 'A' && line[i] <= 'Z' {
			markerLen := 0
			if line[i+1:i+2] == "、" {
				markerLen = 2
			} else if i+2 < len(line) && line[i+1:i+3] == "．" {
				markerLen = 3 // 全角点号
			}

			if markerLen > 0 {
				optionMarker := string(line[i])
				optionStart := i + markerLen
				optionEnd := len(line)

				// 查找下一个选项标记
				for j := optionStart; j < len(line); j++ {
					if j+1 < len(line) && line[j] >= 'A' && line[j] <= 'Z' {
						if line[j+1:j+2] == "、" || (j+2 < len(line) && line[j+1:j+3] == "．") {
							optionEnd = j
							break
						}
					}
				}

				optionText := strings.TrimSpace(line[optionStart:optionEnd])
				if optionText != "" {
					p.tokens = append(p.tokens, Token{
						Type:  TokenTypeOptionMarker,
						Value: optionMarker,
						Line:  lineNum,
					})
					p.tokens = append(p.tokens, Token{
						Type:  TokenTypeOptionText,
						Value: optionText,
						Line:  lineNum,
					})
				}

				i = optionEnd
				continue
			}
		}
		i++
	}

	fmt.Printf("DEBUG: parseOptionsInLine returning %v (added %d tokens)\n", len(p.tokens) > originalLen, len(p.tokens)-originalLen)
	return len(p.tokens) > originalLen
}

// parse 执行语法分析，将词法单元转换为题目结构
func (p *Parser) parse(text string) ([]Question, error) {
	// 执行词法分析
	p.tokenize(text)

	// 按题目分组
	questions := []Question{}
	currentQuestion := Question{}

	for i := 0; i < len(p.tokens); i++ {
		token := p.tokens[i]

		switch token.Type {
		case TokenTypeQuestionNumber:
			// 保存前一个题目
			if currentQuestion.Type != "" {
				questions = append(questions, currentQuestion)
			}
			// 开始新题目
			currentQuestion = Question{}

		case TokenTypeQuestionType:
			currentQuestion.Type = strings.TrimSpace(token.Value)

		case TokenTypeQuestionStem:
			// 合并多行题干，但避免重复
			stemText := strings.TrimSpace(token.Value)
			if currentQuestion.Text == "" {
				currentQuestion.Text = stemText
			} else if !strings.Contains(currentQuestion.Text, stemText) {
				// 只有当新内容不包含在现有文本中时才添加
				currentQuestion.Text += " " + stemText
			}

			// 清理题干中的多余内容
			currentQuestion.Text = strings.ReplaceAll(currentQuestion.Text, "选项：", "")
			currentQuestion.Text = strings.ReplaceAll(currentQuestion.Text, "( )", "")
			currentQuestion.Text = strings.ReplaceAll(currentQuestion.Text, "（ ）", "")
			currentQuestion.Text = strings.TrimSpace(currentQuestion.Text)

		case TokenTypeOptionMarker:
			// 选项标记，下一个token应该是选项文本
			if i+1 < len(p.tokens) && p.tokens[i+1].Type == TokenTypeOptionText {
				currentQuestion.Options = append(currentQuestion.Options, strings.TrimSpace(p.tokens[i+1].Value))
				i++ // 跳过下一个token，因为已经处理了
			}

		case TokenTypeAnswerMarker:
			// 答案标记，下一个token应该是答案文本
			if i+1 < len(p.tokens) && p.tokens[i+1].Type == TokenTypeAnswerText {
				answerText := strings.TrimSpace(p.tokens[i+1].Value)

				fmt.Printf("DEBUG: Processing answer text: '%s'\n", answerText)

				// 处理答案
				if answerText == "对" || answerText == "错" {
					currentQuestion.Answer = []string{answerText}
				} else {
					// 处理字母答案（A、B、C等）
					for _, ch := range answerText {
						if ch >= 'A' && ch <= 'Z' {
							idx := int(ch - 'A')
							if idx >= 0 && idx < len(currentQuestion.Options) {
								// 存储选项文本而不是选项字母
								currentQuestion.Answer = append(currentQuestion.Answer, currentQuestion.Options[idx])
								fmt.Printf("DEBUG: Added answer text '%s' for option %c\n", currentQuestion.Options[idx], ch)
							} else {
								// 如果选项索引超出范围，直接存储字母
								currentQuestion.Answer = append(currentQuestion.Answer, string(ch))
								fmt.Printf("DEBUG: Added answer letter '%c' (option index %d out of range)\n", ch, idx)
							}
						}
					}
				}
				i++ // 跳过下一个token，因为已经处理了
			}

		case TokenTypeStatusMarker, TokenTypeStatusText, TokenTypeScoreMarker, TokenTypeScoreText:
			// 忽略状态和分数信息
			continue
		}
	}

	// 添加最后一个题目
	if currentQuestion.Type != "" {
		questions = append(questions, currentQuestion)
	}

	if len(questions) == 0 {
		return nil, fmt.Errorf("没有成功解析任何题目")
	}

	return questions, nil
}

// ParseQuestions 使用新的解析器解析题目
func ParseQuestions(text string) ([]Question, error) {
	if text == "" {
		return nil, fmt.Errorf("输入文本为空")
	}

	parser := NewParser()
	return parser.parse(text)
}
