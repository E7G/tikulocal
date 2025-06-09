package main

import (
	"archive/zip"
	"bytes"
	"encoding/xml"
	"fmt"
	"log"
	"net/http"
	"regexp"
	"strings"

	"fyne.io/fyne/v2"
	"fyne.io/fyne/v2/app"
	"fyne.io/fyne/v2/container"
	"fyne.io/fyne/v2/dialog"
	"fyne.io/fyne/v2/widget"
	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

var (
	db          *gorm.DB
	guiApp      fyne.App
	guiWindow   fyne.Window
	statusLabel *widget.Label
	progressBar *widget.ProgressBar
	// 替换为 widget.RichText
	resultRichText *widget.RichText

	// 预编译所有正则表达式，避免重复编译
	cleanTextRegex = regexp.MustCompile(`[\pP\s]`)
	typeReg        = regexp.MustCompile(`【(.*?)】\s*`)
	questionReg    = regexp.MustCompile(`【(.*?)】\s*(.*?)\s*正确答案：\s*([A-Z对错]+)`)
	// 匹配不包含 abcd 选项的题目文本，直到遇到第一个 A-Z 选项前缀或字符串结束
	questionTextReg = regexp.MustCompile(`^([^A-Z]*?)(\s*[A-Z]、|$)`)
	// 修改正则表达式，提取选项内容，忽略 A-Z 及顿号
	optionReg = regexp.MustCompile(`[A-Z]、([^A-Z]*)`)
	answerReg = regexp.MustCompile(`正确答案：\s*([A-Z对错]+)`)
)

// 定义题目结构体
type Question struct {
	gorm.Model
	Type    string   `gorm:"index"`
	Text    string   `gorm:"index;unique"`
	Options []string `gorm:"type:text;serializer:json"`
	Answer  []string `gorm:"type:text;serializer:json"`
}

// 清洗题目文本，去除标点和空格
func cleanText(text string) string {
	return cleanTextRegex.ReplaceAllString(text, "")
}

// 初始化数据库
func initDB() error {
	var err error
	db, err = gorm.Open(sqlite.Open("tiku.db"), &gorm.Config{})
	if err != nil {
		return err
	}
	return db.AutoMigrate(&Question{})
}

// 显示所有题目
func showAllQuestions() {
	results, err := searchQuestions("")
	if err != nil {
		statusLabel.SetText(fmt.Sprintf("查询所有题目失败: %v", err))
		dialog.ShowError(err, guiWindow)
		return
	}

	// 使用更规范的Markdown格式
	var result strings.Builder
	result.WriteString(fmt.Sprintf("### 共找到 %d 道题目\n\n", len(results)))

	for i, q := range results {
		if i >= 5 { // 只显示前5题
			break
		}
		result.WriteString(fmt.Sprintf("#### 题目 %d\n", i+1))
		result.WriteString(fmt.Sprintf("**题型**: %s\n\n", q.Type))
		result.WriteString(fmt.Sprintf("**题目内容**: %s\n\n", q.Text))
		result.WriteString("**选项**:\n")
		for _, opt := range q.Options {
			result.WriteString(fmt.Sprintf("- %s\n", opt))
		}
		result.WriteString(fmt.Sprintf("\n**答案**: %s\n\n", strings.Join(q.Answer, ", ")))
	}

	// 更新 widget.RichText 的内容
	resultRichText.ParseMarkdown(result.String())
	statusLabel.SetText(fmt.Sprintf("查询完成! 共找到 %d 道题目", len(results)))
}

func setupGUI() {
	guiApp = app.NewWithID("com.tikulocal.app")
	guiWindow = guiApp.NewWindow("题库管理系统")
	guiWindow.Resize(fyne.NewSize(800, 600))

	// 创建控件
	title := widget.NewLabelWithStyle("题库管理系统", fyne.TextAlignCenter, fyne.TextStyle{Bold: true})
	statusLabel = widget.NewLabel("就绪")
	progressBar = widget.NewProgressBar()
	progressBar.Hide()

	// 创建 widget.RichText 替代 canvas.Text
	resultRichText = widget.NewRichTextWithText("")
	resultScroll := container.NewScroll(resultRichText)
	resultScroll.SetMinSize(fyne.NewSize(400, 300))

	filePathEntry := widget.NewEntry()
	filePathEntry.SetPlaceHolder("选择或拖放DOCX文件到这里...")

	parseBtn := widget.NewButton("解析文件", func() {
		path := filePathEntry.Text
		if path == "" {
			dialog.ShowError(fmt.Errorf("请先选择文件"), guiWindow)
			return
		}

		statusLabel.SetText("正在解析文档...")
		progressBar.Show()
		progressBar.SetValue(0)

		fyne.Do(func() {
			defer func() {
				progressBar.Hide()
				progressBar.SetValue(0)
			}()

			questions, err := loadDocx(path)
			if err != nil {
				statusLabel.SetText(fmt.Sprintf("解析失败: %v", err))
				dialog.ShowError(err, guiWindow)
				return
			}

			// 清洗题目文本，去除标点和空格
			for i := range questions {
				questions[i].Text = cleanText(questions[i].Text)
			}

			// 更新结果，使用更规范的Markdown格式
			var result strings.Builder
			result.WriteString(fmt.Sprintf("### 成功解析 %d 道题目\n\n", len(questions)))

			for i, q := range questions {
				if i >= 5 { // 只显示前5题
					break
				}
				result.WriteString(fmt.Sprintf("#### 题目 %d\n", i+1))
				result.WriteString(fmt.Sprintf("**题型**: %s\n\n", q.Type))
				result.WriteString(fmt.Sprintf("**题目内容**: %s\n\n", q.Text))
				result.WriteString("**选项**:\n")
				for _, opt := range q.Options {
					result.WriteString(fmt.Sprintf("- %s\n", opt))
				}
				result.WriteString(fmt.Sprintf("\n**答案**: %s\n\n", strings.Join(q.Answer, ", ")))
			}

			// 更新 widget.RichText 的内容
			resultRichText.ParseMarkdown(result.String())
			statusLabel.SetText(fmt.Sprintf("解析完成! 共添加 %d 道题目", len(questions)))

			// 保存到数据库
			if err := saveQuestionsToDB(questions); err != nil {
				statusLabel.SetText(fmt.Sprintf("保存失败: %v", err))
				dialog.ShowError(err, guiWindow)
			}

			// 解析完成后显示所有题目
			showAllQuestions()
		})
	})

	searchEntry := widget.NewEntry()
	searchEntry.SetPlaceHolder("输入题目内容...")
	searchBtn := widget.NewButton("搜索题目", func() {
		query := searchEntry.Text

		// 清洗搜索查询，去除标点和空格
		cleanedQuery := cleanText(query)

		fyne.Do(func() {
			results, err := searchQuestions(cleanedQuery)
			if err != nil {
				statusLabel.SetText(fmt.Sprintf("搜索失败: %v", err))
				dialog.ShowError(err, guiWindow)
				return
			}

			if len(results) == 0 {
				resultRichText.ParseMarkdown("### 未找到相关题目")
				statusLabel.SetText("未找到匹配的题目")
				return
			}

			// 使用更规范的Markdown格式
			var result strings.Builder
			result.WriteString(fmt.Sprintf("### 找到 %d 条匹配结果\n\n", len(results)))

			for i, q := range results {
				if i >= 5 { // 只显示前5题
					break
				}
				result.WriteString(fmt.Sprintf("#### 题目 %d\n", i+1))
				result.WriteString(fmt.Sprintf("**题型**: %s\n\n", q.Type))
				result.WriteString(fmt.Sprintf("**题目内容**: %s\n\n", q.Text))
				result.WriteString("**选项**:\n")
				for _, opt := range q.Options {
					result.WriteString(fmt.Sprintf("- %s\n", opt))
				}
				result.WriteString(fmt.Sprintf("\n**答案**: %s\n\n", strings.Join(q.Answer, ", ")))
			}

			// 更新 widget.RichText 的内容
			resultRichText.ParseMarkdown(result.String())
			statusLabel.SetText(fmt.Sprintf("搜索完成! 共找到 %d 条结果", len(results)))
		})
	})

	// 文件选择按钮
	fileBtn := widget.NewButton("选择文件", func() {
		dialog.ShowFileOpen(func(reader fyne.URIReadCloser, err error) {
			if err == nil && reader != nil {
				filePathEntry.SetText(reader.URI().Path())
			}
		}, guiWindow)
	})

	// 拖放支持
	filePathEntry.OnSubmitted = func(s string) {
		parseBtn.OnTapped()
	}

	// 布局
	fileRow := container.NewBorder(nil, nil, fileBtn, parseBtn, filePathEntry)
	searchRow := container.NewBorder(nil, nil, nil, searchBtn, searchEntry)
	topSection := container.NewVBox(title, fileRow, searchRow, widget.NewSeparator())

	resultScroll = container.NewScroll(resultRichText)
	resultScroll.SetMinSize(fyne.NewSize(780, 400))

	// 在布局中替换原有组件
	content := container.NewBorder(
		topSection,
		container.NewVBox(progressBar, statusLabel),
		nil,
		nil,
		resultScroll,
	)

	guiWindow.SetContent(content)

	// 启动时显示所有题目
	showAllQuestions()

	// 启动时显示窗口
	guiWindow.Show()
}

func saveQuestionsToDB(questions []Question) error {
	tx := db.Begin()
	defer func() {
		if r := recover(); r != nil {
			tx.Rollback()
		}
	}()

	for _, q := range questions {
		// 清洗题目文本，去除标点和空格
		cleanedText := cleanText(q.Text)
		// 检查题目是否已存在
		var existing Question
		if err := db.Where("text = ?", cleanedText).First(&existing).Error; err == nil {
			continue // 跳过已存在的题目
		}

		q.Text = cleanedText
		if err := tx.Create(&q).Error; err != nil {
			tx.Rollback()
			return fmt.Errorf("保存题目失败: %v", err)
		}
	}

	return tx.Commit().Error
}

func searchQuestions(query string) ([]Question, error) {
	var results []Question

	// 清理并缩短查询文本
	cleanedQuery := cleanText(query)
	// 由于直接按字节切片可能会截断中文，使用 rune 来处理字符串，确保中文不会被截断
	if len([]rune(cleanedQuery)) > 100 {
		cleanedQuery = string([]rune(cleanedQuery)[:100])
	}

	var queryDB *gorm.DB
	if query == "" {
		queryDB = db
	} else {
		queryDB = db.Where("text LIKE ?", "%"+cleanedQuery+"%")
	}

	if err := queryDB.Find(&results).Error; err != nil {
		return nil, err
	}

	return results, nil
}

// 初始化必要的目录和文件
func initResources() error {
	return nil
}

func main() {
	// 初始化数据库
	if err := initDB(); err != nil {
		fmt.Printf("初始化数据库失败: %v\n", err)
		return
	}

	// 初始化必要的资源
	if err := initResources(); err != nil {
		fmt.Printf("初始化资源失败: %v\n", err)
		return
	}

	// 设置GUI
	setupGUI()

	// 启动Web服务
	go startWebService()

	// 运行GUI主循环
	guiApp.Run()
}

func startWebService() {
	// 初始化WEB服务
	r := gin.Default()

	// 配置404处理
	r.NoRoute(func(c *gin.Context) {
		c.JSON(404, gin.H{
			"error": "endpoint not found",
			"path":  c.Request.URL.Path,
		})
	})

	// 配置CORS中间件
	setupCORS(r)

	// 注册带参数路由
	r.POST("/adapter-service/search", handleSearch)

	// 添加默认路由
	r.GET("/", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"status":  "running",
			"version": "1.0.0",
			"docs":    "/adapter-service/search",
		})
	})
	r.HEAD("/", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"status":  "running",
			"version": "1.0.0",
			"docs":    "/adapter-service/search",
		})
	})

	// 处理OPTIONS请求
	r.OPTIONS("/*any", func(c *gin.Context) {
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
		c.Header("Access-Control-Allow-Headers", "*")
		c.Status(204)
	})

	// 启动服务并处理错误
	port := ":8060"
	fmt.Printf("Web服务将在端口 %s 启动\n", port)
	if err := r.Run(port); err != nil {
		fmt.Printf("启动Web服务失败: %v\n", err)
	}
}

func setupCORS(r *gin.Engine) {
	config := cors.DefaultConfig()
	config.AllowOrigins = []string{"*"}
	config.AllowMethods = []string{"GET", "POST", "PUT", "DELETE"}
	config.AllowHeaders = []string{"Origin", "Content-Type", "Authorization"}
	r.Use(cors.New(config))
}

// 加载DOCX文件并解析题目
func loadDocx(path string) ([]Question, error) {
	fmt.Printf("开始加载DOCX文件，文件路径: %s\n", path)
	// 读取DOCX文件(ZIP格式)
	r, err := zip.OpenReader(path)
	if err != nil {
		fmt.Printf("无法打开DOCX文件，错误信息: %v\n", err)
		return nil, fmt.Errorf("无法打开DOCX文件: %v", err)
	}
	defer r.Close()
	fmt.Printf("成功打开DOCX文件: %s\n", path)

	// 查找document.xml
	fmt.Println("开始查找document.xml文件")
	xmlFile, err := findXMLFile(r)
	if err != nil {
		fmt.Printf("找不到document.xml文件，错误信息: %v\n", err)
		return nil, err
	}
	fmt.Println("成功找到document.xml文件")

	// 读取XML内容
	fmt.Println("开始读取XML文件内容")
	content, err := readXMLContent(xmlFile)
	if err != nil {
		fmt.Printf("读取XML文件内容失败，错误信息: %v\n", err)
		return nil, err
	}
	fmt.Println("成功读取XML文件内容")

	// 提取所有文本内容（保留换行）
	fmt.Println("开始从XML中提取文本内容")
	text := extractTextFromXML(content)
	fmt.Println("成功从XML中提取文本内容")
	fmt.Printf("提取的文本内容长度: %d\n", len(text))
	fmt.Println("提取的文本内容:")
	fmt.Println(text)

	// 解析题目
	fmt.Println("开始解析题目")
	questions, err := parseQuestions(text)
	if err != nil {
		fmt.Printf("解析题目失败，错误信息: %v\n", err)
		return nil, err
	}
	fmt.Printf("成功解析 %d 道题目\n", len(questions))

	return questions, nil
}

// 查找document.xml文件
func findXMLFile(r *zip.ReadCloser) (*zip.File, error) {
	for _, f := range r.File {
		if f.Name == "word/document.xml" {
			return f, nil
		}
	}
	return nil, fmt.Errorf("找不到document.xml")
}

// 读取XML文件内容
func readXMLContent(xmlFile *zip.File) (string, error) {
	rc, err := xmlFile.Open()
	if err != nil {
		return "", err
	}
	defer rc.Close()

	buf := new(bytes.Buffer)
	if _, err := buf.ReadFrom(rc); err != nil {
		return "", err
	}
	return buf.String(), nil
}

// 解析题目 - 优化的解析逻辑
func parseQuestions(text string) ([]Question, error) {
	var questions []Question
	matches := questionReg.FindAllStringSubmatch(text, -1)
	// fmt.Printf("找到 %d 个匹配的题目\n", len(matches))
	if len(matches) == 0 {
		return nil, fmt.Errorf("未找到有效的题目")
	}

	for _, match := range matches {
		// 清晰地输出match的内容，按索引和对应值展示
		fmt.Println("匹配到的内容:")
		for i, item := range match {
			fmt.Printf("索引 %d: %s\n", i, item)
		}
		if len(match) < 4 {
			continue
		}

		// 初始化 q 变量
		var q Question
		// 查找题目文本
		if questionTextMatches := questionTextReg.FindStringSubmatch(match[2]); len(questionTextMatches) > 2 {
			// 清晰输出questionTextMatches所有内容
			// for i, item := range questionTextMatches {
			// 	fmt.Printf("questionTextMatches 索引 %d: %s\n", i, item)
			// }
			// 若匹配成功，获取题目文本并去除首尾空格
			questionText := strings.TrimSpace(questionTextMatches[1])
			// 清洗题目文本，去除标点和空格
			cleanedQuestionText := cleanText(questionText)
			fmt.Printf("找到的清洗后题目文本: %s\n", cleanedQuestionText)
			q = Question{
				Type: strings.TrimSpace(match[1]), // 题型，去除首尾空格
				Text: cleanedQuestionText,         // 清洗后的题目文本
			}
		} else {
			// 若未匹配到题目文本，使用原始内容并去除首尾空格
			originalText := strings.TrimSpace(match[2])
			// 清洗题目文本，去除标点和空格
			cleanedOriginalText := cleanText(originalText)
			q = Question{
				Type: strings.TrimSpace(match[1]), // 题型，去除首尾空格
				Text: cleanedOriginalText,         // 清洗后的题目文本
			}
		}

		// 解析选项
		optionsSection := strings.TrimSpace(match[2])
		optionMatches := optionReg.FindAllStringSubmatch(optionsSection, -1)
		for _, opt := range optionMatches {
			// 清晰输出opt内容，按索引和对应值展示
			fmt.Println("当前解析的选项内容:")
			for i, item := range opt {
				fmt.Printf("索引 %d: %s\n", i, item)
			}
			if len(opt) > 1 {
				// 保存选项时去掉最前面的 abcd 及顿号
				q.Options = append(q.Options, strings.TrimSpace(opt[1]))
			}
		}

		// 解析答案
		answerStr := match[3]
		if answerStr == "对" || answerStr == "错" {
			q.Answer = []string{answerStr}
		} else {
			// 清空原答案
			q.Answer = []string{}
			for _, char := range answerStr {
				index := int(char - 'A')
				if index >= 0 && index < len(q.Options) {
					// 提取选项文本作为答案
					q.Answer = append(q.Answer, q.Options[index])
				}
			}
		}

		questions = append(questions, q)
	}

	return questions, nil
}

// 从XML中提取文本内容
func extractTextFromXML(xmlContent string) string {
	var textBuilder strings.Builder
	d := xml.NewDecoder(bytes.NewReader([]byte(xmlContent)))

	for {
		t, err := d.Token()
		if err != nil || t == nil {
			break
		}

		if se, ok := t.(xml.StartElement); ok && se.Name.Local == "t" {
			var tText string
			if err := d.DecodeElement(&tText, &se); err == nil {
				textBuilder.WriteString(tText)
				textBuilder.WriteRune(' ')
			}
		}
	}
	return textBuilder.String()
}

// 处理搜索请求 - 兼容新API格式
// 生成带选项前缀的格式化答案
func generateFormattedAnswers(answers []string, options []string) []string {
	if len(options) == 0 {
		return answers
	}
	var formatted []string
	for _, ans := range answers {
		for i, opt := range options {
			if strings.Contains(opt, ans) || strings.Contains(ans, opt) {
				formatted = append(formatted, fmt.Sprintf("%c、%s", 'A'+i, ans))
				break
			}
		}
	}
	return formatted
}

func handleSearch(c *gin.Context) {
	// 处理查询参数
	_ = c.Query("use")

	var request struct {
		Question string   `json:"question"`
		Options  []string `json:"options"`
		Type     int      `json:"type"`
	}

	if err := c.BindJSON(&request); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "无效的请求格式"})
		return
	}

	// 验证题型参数
	if request.Type < 0 || request.Type > 4 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "无效的题型参数"})
		return
	}

	// 清理并缩短查询文本
	cleanedQuery := cleanText(request.Question)
	// log.Printf("原始查询: %s", cleanedQuery)
	// 由于直接按字节切片可能会截断中文，使用 rune 来处理字符串，确保中文不会被截断
	if len([]rune(cleanedQuery)) > 100 {
		cleanedQuery = string([]rune(cleanedQuery)[:100])
	}
	log.Printf("API请求: 题型:%d 题目:%s", request.Type, cleanedQuery)

	var results []Question
	query := db
	if request.Question != "" {
		query = query.Where("text LIKE ?", "%"+cleanedQuery+"%")
	}

	if err := query.Find(&results).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "数据库查询失败"})
		return
	}

	// 如果没有找到结果
	if len(results) == 0 {
		c.JSON(http.StatusNotFound, gin.H{"error": "未找到相关问题"})
		return
	}

	// 返回第一个匹配结果（按相似度排序）
	bestMatch := results[0]

	// 构建符合API规范的响应
	answerKey := []string{}
	answerIndex := []int{}
	answerText := []string{}

	for i, option := range request.Options {
		for _, ans := range bestMatch.Answer {
			if strings.Contains(option, ans) || strings.Contains(ans, option) {
				answerKey = append(answerKey, string(rune('A'+i)))
				answerIndex = append(answerIndex, i)
				answerText = append(answerText, option)
			}
		}
	}

	// 如果没匹配到选项，使用原始答案
	if len(answerKey) == 0 {
		answerKey = bestMatch.Answer
		answerIndex = []int{0} // 简化处理
		for _, ans := range bestMatch.Answer {
			answerText = append(answerText, ans)
		}
	}

	// 构建标准API响应
	response := gin.H{
		"plat":     0, // 本地题库标识
		"question": bestMatch.Text,
		"options":  request.Options,
		"type":     request.Type,
		"answer": gin.H{
			"answerKey":     answerKey,
			"answerKeyText": strings.Join(answerKey, ""),
			"answerIndex":   answerIndex,
			"answerText":    strings.Join(answerText, "#"),
			"bestAnswer":    bestMatch.Answer,
			"allAnswer": [][]string{
				bestMatch.Answer,
				generateFormattedAnswers(bestMatch.Answer, request.Options), // 根据请求选项生成前缀
			},
		},
	}

	// 记录API调用日志
	log.Printf("API请求处理完成 题型:%d 匹配答案:%v", request.Type, bestMatch.Answer)

	c.JSON(http.StatusOK, response)
}
