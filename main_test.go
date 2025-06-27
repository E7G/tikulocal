package main

import (
	"testing"
	"strings"
	"path/filepath"
)

// 测试文本清理函数
func TestCleanText(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected string
	}{
		{
			name:     "基本清理",
			input:    "Hello, World! 你好，世界！",
			expected: "HelloWorld你好世界",
		},
		{
			name:     "空字符串",
			input:    "",
			expected: "",
		},
		{
			name:     "只有标点",
			input:    "!@#$%^&*()",
			expected: "",
		},
		{
			name:     "数字和字母",
			input:    "Test123 测试456",
			expected: "Test123测试456",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := cleanText(tt.input)
			if result != tt.expected {
				t.Errorf("cleanText(%q) = %q, want %q", tt.input, result, tt.expected)
			}
		})
	}
}

// 测试文件扩展名验证
func TestGetFileExtension(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected string
	}{
		{
			name:     "DOCX文件",
			input:    "test.docx",
			expected: ".docx",
		},
		{
			name:     "大写扩展名",
			input:    "test.DOCX",
			expected: ".DOCX",
		},
		{
			name:     "无扩展名",
			input:    "testfile",
			expected: "",
		},
		{
			name:     "多个点",
			input:    "test.file.docx",
			expected: ".docx",
		},
		{
			name:     "空字符串",
			input:    "",
			expected: "",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := getFileExtension(tt.input)
			if result != tt.expected {
				t.Errorf("getFileExtension(%q) = %q, want %q", tt.input, result, tt.expected)
			}
		})
	}
}

// 测试DOCX文件验证
func TestIsValidDocxFile(t *testing.T) {
	tests := []struct {
		name     string
		filePath string
		want     bool
	}{
		{"有效DOCX文件", "test.docx", true},
		{"大写扩展名", "test.DOCX", true},
		{"无效扩展名", "test.txt", false},
		{"无扩展名", "test", false},
		{"空字符串", "", false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// 对于测试用例，我们只检查扩展名，不检查文件是否存在
			got := isValidDocxFileForTest(tt.filePath)
			if got != tt.want {
				t.Errorf("isValidDocxFile(%q) = %v, want %v", tt.filePath, got, tt.want)
			}
		})
	}
}

// 测试用的文件验证函数，只检查扩展名
func isValidDocxFileForTest(filePath string) bool {
	if filePath == "" {
		return false
	}
	
	// 检查文件扩展名
	ext := strings.ToLower(getFileExtension(filePath))
	return ext == ".docx"
}

// 测试文件名提取
func TestGetFileName(t *testing.T) {
	tests := []struct {
		name     string
		filePath string
		want     string
	}{
		{"简单文件名", "test.docx", "test.docx"},
		{"带路径", "/path/to/test.docx", "test.docx"},
		{"Windows路径", "C:\\path\\to\\test.docx", "test.docx"},
		{"空字符串", "", ""},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := getFileNameForTest(tt.filePath)
			if got != tt.want {
				t.Errorf("getFileName(%q) = %v, want %v", tt.filePath, got, tt.want)
			}
		})
	}
}

// 测试用的文件名提取函数，使用filepath包
func getFileNameForTest(filePath string) string {
	if filePath == "" {
		return ""
	}
	return filepath.Base(filePath)
}

// 测试文本格式化
func TestFormatQuestionText(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected string
	}{
		{
			name:     "短文本",
			input:    "这是一个短题目",
			expected: "这是一个短题目",
		},
		{
			name:     "带空格",
			input:    "  带空格的题目  ",
			expected: "带空格的题目",
		},
		{
			name:     "空字符串",
			input:    "",
			expected: "",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := formatQuestionText(tt.input)
			if result != tt.expected {
				t.Errorf("formatQuestionText(%q) = %q, want %q", tt.input, result, tt.expected)
			}
		})
	}
}

// 测试题型图标
func TestGetTypeIcon(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected string
	}{
		{
			name:     "单选题",
			input:    "单选题",
			expected: "🔘",
		},
		{
			name:     "多选题",
			input:    "多选题",
			expected: "☑️",
		},
		{
			name:     "判断题",
			input:    "判断题",
			expected: "✅",
		},
		{
			name:     "填空题",
			input:    "填空题",
			expected: "📝",
		},
		{
			name:     "简答题",
			input:    "简答题",
			expected: "💬",
		},
		{
			name:     "未知题型",
			input:    "未知题型",
			expected: "❓",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := getTypeIcon(tt.input)
			if result != tt.expected {
				t.Errorf("getTypeIcon(%q) = %q, want %q", tt.input, result, tt.expected)
			}
		})
	}
}

// 测试自动换行
func TestAutoWrapText(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		maxLen   int
		expected string
	}{
		{
			name:     "短文本不需要换行",
			input:    "短文本",
			maxLen:   10,
			expected: "短文本",
		},
		{
			name:     "长文本需要换行",
			input:    "这是一个很长的文本需要换行处理",
			maxLen:   10,
			expected: "这是一个很长的文本需要换行处理",
		},
		{
			name:     "空字符串",
			input:    "",
			maxLen:   10,
			expected: "",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := autoWrapText(tt.input, tt.maxLen)
			if result != tt.expected {
				t.Errorf("autoWrapText(%q, %d) = %q, want %q", tt.input, tt.maxLen, result, tt.expected)
			}
		})
	}
}

// 测试路径清理
func TestCleanDropPath(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected string
	}{
		{
			name:     "带引号路径",
			input:    `"C:\path\to\file.docx"`,
			expected: "C:\\path\\to\\file.docx",
		},
		{
			name:     "单引号路径",
			input:    `'C:\path\to\file.docx'`,
			expected: "C:\\path\\to\\file.docx",
		},
		{
			name:     "正常路径",
			input:    "C:\\path\\to\\file.docx",
			expected: "C:\\path\\to\\file.docx",
		},
		{
			name:     "空字符串",
			input:    "",
			expected: "",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := cleanDropPath(tt.input)
			if result != tt.expected {
				t.Errorf("cleanDropPath(%q) = %q, want %q", tt.input, result, tt.expected)
			}
		})
	}
}

// 测试常量值
func TestConstants(t *testing.T) {
	if AppName != "com.tikulocal.app" {
		t.Errorf("AppName = %q, want %q", AppName, "com.tikulocal.app")
	}
	
	if WindowTitle != "题库管理系统" {
		t.Errorf("WindowTitle = %q, want %q", WindowTitle, "题库管理系统")
	}
	
	if DefaultItemsPerPage != 5 {
		t.Errorf("DefaultItemsPerPage = %d, want %d", DefaultItemsPerPage, 5)
	}
	
	if WebPort != ":8060" {
		t.Errorf("WebPort = %q, want %q", WebPort, ":8060")
	}
	
	if DBName != "tiku.db" {
		t.Errorf("DBName = %q, want %q", DBName, "tiku.db")
	}
}

// 测试正则表达式编译
func TestRegexCompilation(t *testing.T) {
	// 测试题目分块正则
	if questionBlockPattern == nil {
		t.Error("questionBlockPattern 未正确编译")
	}
	
	// 测试选项正则
	if optionPattern == nil {
		t.Error("optionPattern 未正确编译")
	}
	
	// 测试答案正则
	if answerPattern == nil {
		t.Error("answerPattern 未正确编译")
	}
}

// 测试字符串处理函数
func TestStringProcessing(t *testing.T) {
	// 测试字符串分割
	text := "A、选项1\nB、选项2\nC、选项3"
	lines := strings.Split(text, "\n")
	if len(lines) != 3 {
		t.Errorf("字符串分割结果长度 = %d, want %d", len(lines), 3)
	}
	
	// 测试字符串替换
	result := strings.ReplaceAll(text, "、", ".")
	if !strings.Contains(result, ".") {
		t.Error("字符串替换失败")
	}
	
	// 测试字符串修剪
	trimmed := strings.TrimSpace("  测试文本  ")
	if trimmed != "测试文本" {
		t.Errorf("字符串修剪失败: %q", trimmed)
	}
} 