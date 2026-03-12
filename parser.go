package main

import (
	"fmt"
	"strings"
	"unicode/utf8"
)

type TokenType int

const (
	TokenTypeQuestionNumber TokenType = iota
	TokenTypeQuestionType
	TokenTypeQuestionStem
	TokenTypeOptionMarker
	TokenTypeOptionText
	TokenTypeCorrectAnswerMarker
	TokenTypeCorrectAnswerText
	TokenTypeMyAnswerMarker
	TokenTypeMyAnswerText
	TokenTypeStatusMarker
	TokenTypeStatusText
	TokenTypeScoreMarker
	TokenTypeScoreText
	TokenTypeUnknown
)

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
func (p *Parser) tokenize(text string) {
	lines := strings.Split(text, "\n")
	inOptionsSection := false
	currentStem := ""

	for lineNum, line := range lines {
		trimmed := strings.TrimSpace(line)
		if trimmed == "" {
			continue
		}

		if strings.Contains(trimmed, "【") && strings.Contains(trimmed, "】") {
			if currentStem != "" {
				p.tokens = append(p.tokens, Token{
					Type:  TokenTypeQuestionStem,
					Value: strings.TrimSpace(currentStem),
					Line:  lineNum,
				})
				currentStem = ""
			}

			parts := strings.Fields(trimmed)
			if len(parts) >= 1 {
				var questionNum string
				var qType string

				for _, part := range parts {
					if strings.Contains(part, "【") && strings.Contains(part, "】") {
						typeStart := strings.Index(part, "【")
						typeEnd := strings.Index(part, "】")
						if typeStart != -1 && typeEnd != -1 && typeEnd > typeStart {
							qType = strings.TrimSpace(part[typeStart+1 : typeEnd])
							if !utf8.ValidString(qType) {
								qType = strings.Map(func(r rune) rune {
									if r == utf8.RuneError {
										return -1
									}
									return r
								}, qType)
							}
						}
					} else if questionNum == "" {
						questionNum = strings.TrimRight(part, ".．")
					}
				}

				if questionNum != "" {
					p.tokens = append(p.tokens, Token{
						Type:  TokenTypeQuestionNumber,
						Value: questionNum,
						Line:  lineNum + 1,
					})
				}

				if qType != "" {
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

		if strings.HasPrefix(trimmed, "正确答案") {
			if currentStem != "" {
				p.tokens = append(p.tokens, Token{
					Type:  TokenTypeQuestionStem,
					Value: strings.TrimSpace(currentStem),
					Line:  lineNum,
				})
				currentStem = ""
			}

			var answerText string
			if strings.Contains(trimmed, "：") {
				parts := strings.SplitN(trimmed, "：", 2)
				if len(parts) >= 2 {
					answerText = strings.TrimSpace(parts[1])
				}
			} else if strings.Contains(trimmed, ":") {
				parts := strings.SplitN(trimmed, ":", 2)
				if len(parts) >= 2 {
					answerText = strings.TrimSpace(parts[1])
				}
			}

			if answerText != "" {
				p.tokens = append(p.tokens, Token{
					Type:  TokenTypeCorrectAnswerMarker,
					Value: "正确答案",
					Line:  lineNum + 1,
				})
				p.tokens = append(p.tokens, Token{
					Type:  TokenTypeCorrectAnswerText,
					Value: answerText,
					Line:  lineNum + 1,
				})
			}
			inOptionsSection = false
			continue
		}

		if strings.HasPrefix(trimmed, "我的答案") {
			if currentStem != "" {
				p.tokens = append(p.tokens, Token{
					Type:  TokenTypeQuestionStem,
					Value: strings.TrimSpace(currentStem),
					Line:  lineNum,
				})
				currentStem = ""
			}

			var answerText string
			if strings.Contains(trimmed, "：") {
				parts := strings.SplitN(trimmed, "：", 2)
				if len(parts) >= 2 {
					answerText = strings.TrimSpace(parts[1])
				}
			} else if strings.Contains(trimmed, ":") {
				parts := strings.SplitN(trimmed, ":", 2)
				if len(parts) >= 2 {
					answerText = strings.TrimSpace(parts[1])
				}
			}

			if answerText != "" {
				p.tokens = append(p.tokens, Token{
					Type:  TokenTypeMyAnswerMarker,
					Value: "我的答案",
					Line:  lineNum + 1,
				})
				p.tokens = append(p.tokens, Token{
					Type:  TokenTypeMyAnswerText,
					Value: answerText,
					Line:  lineNum + 1,
				})
			}
			inOptionsSection = false
			continue
		}

		if strings.HasPrefix(trimmed, "答案") && !strings.HasPrefix(trimmed, "答案状态") {
			if currentStem != "" {
				p.tokens = append(p.tokens, Token{
					Type:  TokenTypeQuestionStem,
					Value: strings.TrimSpace(currentStem),
					Line:  lineNum,
				})
				currentStem = ""
			}

			var answerText string
			if strings.Contains(trimmed, "：") {
				parts := strings.SplitN(trimmed, "：", 2)
				if len(parts) >= 2 {
					answerText = strings.TrimSpace(parts[1])
				}
			} else if strings.Contains(trimmed, ":") {
				parts := strings.SplitN(trimmed, ":", 2)
				if len(parts) >= 2 {
					answerText = strings.TrimSpace(parts[1])
				}
			}

			if answerText != "" {
				p.tokens = append(p.tokens, Token{
					Type:  TokenTypeCorrectAnswerMarker,
					Value: "答案",
					Line:  lineNum + 1,
				})
				p.tokens = append(p.tokens, Token{
					Type:  TokenTypeCorrectAnswerText,
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

	optionMarkers := p.findOptionMarkers(line)
	if len(optionMarkers) < 2 {
		fmt.Printf("DEBUG: No multiple options found, trying single option parsing\n")
		return p.parseSingleOptions(line, lineNum)
	}

	fmt.Printf("DEBUG: Found %d option markers\n", len(optionMarkers))

	for i := 0; i < len(optionMarkers); i++ {
		markerInfo := optionMarkers[i]
		marker := markerInfo.marker
		startPos := markerInfo.endPos
		endPos := len(markerInfo.runes)

		if i+1 < len(optionMarkers) {
			endPos = optionMarkers[i+1].pos
		}

		optionText := strings.TrimSpace(string(markerInfo.runes[startPos:endPos]))

		if !utf8.ValidString(optionText) {
			optionText = strings.Map(func(r rune) rune {
				if r == utf8.RuneError {
					return -1
				}
				return r
			}, optionText)
		}

		fmt.Printf("DEBUG: Option %s: '%s'\n", marker, optionText)

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

type optionMarkerInfo struct {
	pos    int
	endPos int
	marker string
	runes  []rune
}

func (p *Parser) findOptionMarkers(line string) []optionMarkerInfo {
	markers := []optionMarkerInfo{}
	runes := []rune(line)

	for i := 0; i < len(runes); i++ {
		if runes[i] >= 'A' && runes[i] <= 'Z' {
			marker := string(runes[i])
			var endPos int

			if i+1 < len(runes) {
				nextChar := runes[i+1]
				if nextChar == '、' {
					endPos = i + 2
					markers = append(markers, optionMarkerInfo{pos: i, endPos: endPos, marker: marker, runes: runes})
				} else if nextChar == '.' {
					endPos = i + 2
					markers = append(markers, optionMarkerInfo{pos: i, endPos: endPos, marker: marker, runes: runes})
				} else if nextChar == '．' {
					endPos = i + 2
					markers = append(markers, optionMarkerInfo{pos: i, endPos: endPos, marker: marker, runes: runes})
				}
			}
		}
	}

	return markers
}

func (p *Parser) parseSingleOptions(line string, lineNum int) bool {
	originalLen := len(p.tokens)
	i := 0
	runes := []rune(line)

	for i < len(runes) {
		if runes[i] >= 'A' && runes[i] <= 'Z' {
			markerLen := 0
			if i+1 < len(runes) {
				nextChar := runes[i+1]
				if nextChar == '、' || nextChar == '.' || nextChar == '．' {
					markerLen = 2
				}
			}

			if markerLen > 0 {
				optionMarker := string(runes[i])
				optionStart := i + markerLen
				optionEnd := len(runes)

				for j := optionStart; j < len(runes); j++ {
					if runes[j] >= 'A' && runes[j] <= 'Z' {
						if j+1 < len(runes) {
							nextChar := runes[j+1]
							if nextChar == '、' || nextChar == '.' || nextChar == '．' {
								optionEnd = j
								break
							}
						}
					}
				}

				optionText := strings.TrimSpace(string(runes[optionStart:optionEnd]))
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

	fmt.Printf("DEBUG: parseSingleOptions returning %v (added %d tokens)\n", len(p.tokens) > originalLen, len(p.tokens)-originalLen)
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
			if i+1 < len(p.tokens) && p.tokens[i+1].Type == TokenTypeOptionText {
				currentQuestion.Options = append(currentQuestion.Options, strings.TrimSpace(p.tokens[i+1].Value))
				i++
			}

		case TokenTypeCorrectAnswerMarker:
			if i+1 < len(p.tokens) && p.tokens[i+1].Type == TokenTypeCorrectAnswerText {
				answerText := strings.TrimSpace(p.tokens[i+1].Value)
				fmt.Printf("DEBUG: Processing correct answer text: '%s'\n", answerText)

				if answerText == "对" || answerText == "错" {
					currentQuestion.Answer = []string{answerText}
				} else {
					var newAnswers []string
					for _, ch := range answerText {
						if ch >= 'A' && ch <= 'Z' {
							idx := int(ch - 'A')
							if idx >= 0 && idx < len(currentQuestion.Options) {
								newAnswers = append(newAnswers, currentQuestion.Options[idx])
								fmt.Printf("DEBUG: Added correct answer text '%s' for option %c\n", currentQuestion.Options[idx], ch)
							} else {
								newAnswers = append(newAnswers, string(ch))
								fmt.Printf("DEBUG: Added correct answer letter '%c' (option index %d out of range)\n", ch, idx)
							}
						}
					}
					if len(newAnswers) > 0 {
						currentQuestion.Answer = newAnswers
					}
				}
				i++
			}

		case TokenTypeMyAnswerMarker:
			if i+1 < len(p.tokens) && p.tokens[i+1].Type == TokenTypeMyAnswerText {
				if len(currentQuestion.Answer) == 0 {
					answerText := strings.TrimSpace(p.tokens[i+1].Value)
					fmt.Printf("DEBUG: Processing my answer text (no correct answer): '%s'\n", answerText)

					if answerText == "对" || answerText == "错" {
						currentQuestion.Answer = []string{answerText}
					} else {
						var newAnswers []string
						for _, ch := range answerText {
							if ch >= 'A' && ch <= 'Z' {
								idx := int(ch - 'A')
								if idx >= 0 && idx < len(currentQuestion.Options) {
									newAnswers = append(newAnswers, currentQuestion.Options[idx])
									fmt.Printf("DEBUG: Added my answer text '%s' for option %c\n", currentQuestion.Options[idx], ch)
								} else {
									newAnswers = append(newAnswers, string(ch))
									fmt.Printf("DEBUG: Added my answer letter '%c' (option index %d out of range)\n", ch, idx)
								}
							}
						}
						if len(newAnswers) > 0 {
							currentQuestion.Answer = newAnswers
						}
					}
				} else {
					fmt.Printf("DEBUG: Skipping my answer, already have correct answer\n")
				}
				i++
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
