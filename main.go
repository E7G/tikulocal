package main

import (
	"archive/zip"
	"bytes"
	"embed"
	"encoding/xml"
	"fmt"
	"log"
	"net/http"
	"os"
	"regexp"
	"strconv"
	"strings"

	"fyne.io/fyne/v2"
	"fyne.io/fyne/v2/app"
	"fyne.io/fyne/v2/canvas"
	"fyne.io/fyne/v2/container"
	"fyne.io/fyne/v2/dialog"
	"fyne.io/fyne/v2/theme"
	"fyne.io/fyne/v2/widget"
	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

//go:embed fonts/NotoSansCJKsc-Regular.otf
var embeddedFonts embed.FS

// 常量定义
const (
	// 应用配置
	AppName      = "com.tikulocal.app"
	WindowTitle  = "题库管理系统"
	WindowWidth  = 1000
	WindowHeight = 700

	// 分页配置
	DefaultItemsPerPage = 5
	MaxQueryLength      = 100

	// Web服务配置
	WebPort = ":8060"

	// 数据库配置
	DBName = "tiku.db"
)

// 全局变量
var (
	// 数据库连接
	db *gorm.DB

	// GUI组件
	guiApp          fyne.App
	guiWindow       fyne.Window
	statusLabel     *widget.Label
	progressBar     *widget.ProgressBar
	resultContainer *fyne.Container
	resultScroll    *container.Scroll
	statsLabel      *widget.Label

	// 分页相关
	currentPage    = 1
	itemsPerPage   = DefaultItemsPerPage
	totalQuestions = 0
	prevPageBtn    *widget.Button
	nextPageBtn    *widget.Button
	jumpPageEntry  *widget.Entry
	jumpPageBtn    *widget.Button

	// 题目分块正则（支持题号和题型）- 兼容Go语法
	questionBlockPattern = regexp.MustCompile(`(?m)^\d+．\s*\n?【[^】]+】`)
	// 选项正则 - 兼容Go语法
	optionPattern = regexp.MustCompile(`(?m)^([A-Z])、([\s\S]*?)(?:\n[A-Z]、|\n正确答案|\n$)`)
	// 答案正则 - 兼容Go语法
	answerPattern = regexp.MustCompile(`(?m)^正确答案[：:]*\s*([A-Z对错]+)`)
)

// 自定义主题结构体
type customTheme struct {
	fyne.Theme
}

// 创建自定义主题
func newCustomTheme() fyne.Theme {
	return &customTheme{Theme: theme.DefaultTheme()}
}

// 重写Font方法以支持中文字体
func (t *customTheme) Font(style fyne.TextStyle) fyne.Resource {
	// 优先使用嵌入的字体文件
	fontData, err := embeddedFonts.ReadFile("fonts/NotoSansCJKsc-Regular.otf")
	if err == nil {
		font := fyne.NewStaticResource("NotoSansCJKsc-Regular", fontData)
		log.Printf("成功加载嵌入字体: NotoSansCJKsc-Regular.otf")
		return font
	} else {
		log.Printf("读取嵌入字体失败: %v", err)
	}

	// 如果嵌入字体失败，尝试加载本地字体文件
	fontPath := "fonts/NotoSansCJKsc-Regular.otf"
	if _, err := os.Stat(fontPath); err == nil {
		if font, err := fyne.LoadResourceFromPath(fontPath); err == nil {
			log.Printf("成功加载本地字体: %s", fontPath)
			return font
		} else {
			log.Printf("加载本地字体失败: %s - %v", fontPath, err)
		}
	} else {
		log.Printf("本地字体文件不存在: %s", fontPath)
	}

	// 如果本地字体不存在，尝试使用系统字体
	systemFonts := []string{
		"C:/Windows/Fonts/msyh.ttc",   // 微软雅黑
		"C:/Windows/Fonts/simsun.ttc", // 宋体
		"C:/Windows/Fonts/simhei.ttf", // 黑体
		"C:/Windows/Fonts/simkai.ttf", // 楷体
	}

	for _, fontPath := range systemFonts {
		if _, err := os.Stat(fontPath); err == nil {
			if font, err := fyne.LoadResourceFromPath(fontPath); err == nil {
				log.Printf("成功加载系统字体: %s", fontPath)
				return font
			} else {
				log.Printf("加载系统字体失败: %s - %v", fontPath, err)
			}
		}
	}

	// 如果都失败，返回默认字体
	log.Printf("使用Fyne默认字体")
	return t.Theme.Font(style)
}

// 状态管理函数
func showError(message string, err error) {
	errorMsg := fmt.Sprintf("❌ %s: %v", message, err)
	if statusLabel != nil {
		statusLabel.SetText(errorMsg)
	}
	if guiWindow != nil && err != nil {
		dialog.ShowError(err, guiWindow)
	}
	log.Printf("错误: %s - %v", message, err)
}

func showSuccess(message string) {
	successMsg := fmt.Sprintf("✅ %s", message)
	if statusLabel != nil {
		statusLabel.SetText(successMsg)
	}
	log.Printf("成功: %s", message)
}

func showProcessing(message string) {
	processingMsg := fmt.Sprintf("⏳ %s", message)
	if statusLabel != nil {
		statusLabel.SetText(processingMsg)
	}
	log.Printf("处理中: %s", message)
}

// 更新统计信息
func updateStats() {
	if db == nil || statsLabel == nil {
		return
	}

	var count int64
	if err := db.Model(&Question{}).Count(&count).Error; err != nil {
		log.Printf("获取题目总数失败: %v", err)
		return
	}

	typeCount := getQuestionCountByType()
	var stats strings.Builder
	stats.WriteString(fmt.Sprintf("📊 总题目数: %d", count))

	if len(typeCount) > 0 {
		stats.WriteString(" | 题型分布: ")
		for t, c := range typeCount {
			stats.WriteString(fmt.Sprintf("%s:%d ", t, c))
		}
	}

	statsLabel.SetText(stats.String())
}

// 清洗题目文本，去除标点和空格
func cleanText(text string) string {
	// 去除标点符号和空格的正则表达式，兼容Go语法
	cleanRegex := regexp.MustCompile(`[^\p{Han}\p{Latin}0-9]`)
	return cleanRegex.ReplaceAllString(text, "")
}

// 初始化数据库
func initDB() error {
	var err error
	db, err = gorm.Open(sqlite.Open(DBName), &gorm.Config{})
	if err != nil {
		return err
	}
	return db.AutoMigrate(&Question{})
}

// 分页查询题目 - 优化版本
func searchQuestionsPaginated(query string, page, limit int) ([]Question, error) {
	if page < 1 || limit < 1 {
		return nil, fmt.Errorf("无效的分页参数: page=%d, limit=%d", page, limit)
	}

	var results []Question
	queryDB := db

	// 如果有查询条件，添加WHERE子句
	if query != "" {
		cleanedQuery := cleanText(query)
		if len([]rune(cleanedQuery)) > MaxQueryLength {
			cleanedQuery = string([]rune(cleanedQuery)[:MaxQueryLength])
		}
		queryDB = db.Where("text LIKE ?", "%"+cleanedQuery+"%")
	}

	offset := (page - 1) * limit
	if err := queryDB.Offset(offset).Limit(limit).Find(&results).Error; err != nil {
		return nil, fmt.Errorf("查询题目失败: %w", err)
	}

	return results, nil
}

// 获取每个题型的题目数量 - 优化版本
func getQuestionCountByType() map[string]int {
	if db == nil {
		return nil
	}

	// 使用原生SQL查询提高性能
	var results []struct {
		Type  string `gorm:"column:type"`
		Count int    `gorm:"column:count"`
	}

	if err := db.Raw(`
		SELECT type, COUNT(*) as count 
		FROM questions 
		WHERE deleted_at IS NULL 
		GROUP BY type
	`).Scan(&results).Error; err != nil {
		log.Printf("获取题型统计失败: %v", err)
		return nil
	}

	countMap := make(map[string]int)
	for _, result := range results {
		countMap[result.Type] = result.Count
	}

	return countMap
}

// 自动换行函数，将长文本按指定长度换行
func autoWrapText(text string, maxLen int) string {
	words := strings.Fields(text)
	var result strings.Builder
	currentLen := 0
	for i, word := range words {
		if i > 0 {
			if currentLen+len(word)+1 > maxLen {
				result.WriteString("\n")
				currentLen = 0
			} else {
				result.WriteString(" ")
				currentLen++
			}
		}
		result.WriteString(word)
		currentLen += len(word)
	}
	return result.String()
}

// 显示所有题目 - 优化版本
func showAllQuestions() {
	if db == nil {
		showError("数据库未初始化", fmt.Errorf("数据库连接为空"))
		return
	}

	// 获取题目数据
	results, err := searchQuestionsPaginated("", currentPage, itemsPerPage)
	if err != nil {
		showError("查询所有题目失败", err)
		return
	}

	// 获取总题目数
	var count int64
	if err := db.Model(&Question{}).Count(&count).Error; err != nil {
		showError("获取题目总数失败", err)
		return
	}
	totalQuestions = int(count)

	// 计算总页数并验证当前页
	totalPages := (totalQuestions + itemsPerPage - 1) / itemsPerPage
	if totalPages == 0 {
		totalPages = 1
	}

	// 确保当前页在有效范围内
	if currentPage < 1 {
		currentPage = 1
	} else if currentPage > totalPages {
		currentPage = totalPages
	}

	// 生成卡片式显示内容
	if resultContainer != nil {
		cards := generateQuestionsCards(results, totalQuestions, currentPage, totalPages, "📚 题库总览")
		resultContainer.Objects = cards
		resultContainer.Refresh()

		// 自动回顶到顶部
		scrollToTop()
	}

	showSuccess(fmt.Sprintf("查询完成! 共找到 %d 道题目，当前第 %d 页，总页数 %d",
		totalQuestions, currentPage, totalPages))

	// 更新分页按钮状态
	updatePaginationButtons()
}

// 滚动到顶部
func scrollToTop() {
	// 通过刷新容器来触发滚动重置
	if resultScroll != nil {
		resultScroll.ScrollToTop()
	}
}

// 创建单个题目卡片（美化版）
func createQuestionCard(q Question, questionNum int, typeIcon string) *fyne.Container {
	// 题目编号 - 使用更醒目的样式
	numLabel := widget.NewLabelWithStyle(fmt.Sprintf("🎯 题目 %d", questionNum), fyne.TextAlignLeading, fyne.TextStyle{Bold: true})
	numLabel.TextStyle = fyne.TextStyle{Bold: true}
	// 题型标识
	qType := widget.NewLabel(fmt.Sprintf("%s %s", typeIcon, q.Type))
	qType.TextStyle = fyne.TextStyle{Bold: true}
	// 题目内容 - 添加标签
	contentLabel := widget.NewLabel("题目内容：")
	contentLabel.TextStyle = fyne.TextStyle{Bold: true}
	qText := widget.NewLabel(formatQuestionText(q.Text))
	qText.Wrapping = fyne.TextWrapWord
	// 选项区域
	var optionObjs []fyne.CanvasObject
	if len(q.Options) > 0 {
		optionLabel := widget.NewLabel("选项：")
		optionLabel.TextStyle = fyne.TextStyle{Bold: true}
		optionObjs = append(optionObjs, optionLabel)
		for j, opt := range q.Options {
			optionLetter := string(rune('A' + j))
			optionText := widget.NewLabel(fmt.Sprintf("%s. %s", optionLetter, opt))
			optionText.Wrapping = fyne.TextWrapWord
			optionObjs = append(optionObjs, optionText)
		}
	}
	// 答案 - 使用高亮样式
	ansLabel := widget.NewLabel("✅ 答案：")
	ansLabel.TextStyle = fyne.TextStyle{Bold: true}
	ans := widget.NewLabel(strings.Join(q.Answer, ", "))
	ans.TextStyle = fyne.TextStyle{Bold: true}
	// 组合题目内容
	questionContent := container.NewVBox(
		numLabel,
		qType,
		contentLabel,
		qText,
	)
	if len(optionObjs) > 0 {
		questionContent.Add(container.NewVBox(optionObjs...))
	}
	questionContent.Add(container.NewHBox(ansLabel, ans))

	// 美化：卡片背景（背景色+内边距，兼容暗色主题）
	bg := canvas.NewRectangle(theme.InputBackgroundColor())
	card := container.NewMax(
		bg,
		container.NewPadded(questionContent),
	)
	return container.NewVBox(card)
}

// 生成题目卡片内容
func generateQuestionsCards(questions []Question, total, currentPage, totalPages int, title string) []fyne.CanvasObject {
	var cards []fyne.CanvasObject

	// 标题和统计信息 - 使用更醒目的样式
	// titleLabel := widget.NewLabelWithStyle(title, fyne.TextAlignLeading, fyne.TextStyle{Bold: true})
	// titleLabel.TextStyle = fyne.TextStyle{Bold: true}

	// stats := widget.NewLabel(fmt.Sprintf("📊 统计: 共 %d 道题目 | 📄 第 %d/%d 页", total, currentPage, totalPages))
	// stats.TextStyle = fyne.TextStyle{Italic: true}

	// // 添加标题区域
	// headerCard := container.NewVBox(
	// 	titleLabel,
	// 	stats,
	// 	widget.NewSeparator(),
	// )
	// cards = append(cards, headerCard)

	for i, q := range questions {
		questionNum := (currentPage-1)*itemsPerPage + i + 1
		typeIcon := getTypeIcon(q.Type)

		// 创建题目卡片容器
		questionCard := createQuestionCard(q, questionNum, typeIcon)
		cards = append(cards, questionCard)

		// 在题目之间添加分隔线（除了最后一个）
		if i < len(questions)-1 {
			// 使用更明显的分隔线
			separator := widget.NewSeparator()
			cards = append(cards, separator)
		}
	}

	return cards
}

// 生成文件解析预览卡片
func generatePreviewCards(questions []Question) []fyne.CanvasObject {
	var cards []fyne.CanvasObject

	// 标题和统计信息 - 使用更醒目的样式
	titleLabel := widget.NewLabelWithStyle("🎉 成功解析题目预览", fyne.TextAlignLeading, fyne.TextStyle{Bold: true})
	titleLabel.TextStyle = fyne.TextStyle{Bold: true}

	stats := widget.NewLabel(fmt.Sprintf("📊 共解析 %d 道题目（显示前5题预览）", len(questions)))
	stats.TextStyle = fyne.TextStyle{Italic: true}

	// 添加标题区域
	headerCard := container.NewVBox(
		titleLabel,
		stats,
		widget.NewSeparator(),
	)
	cards = append(cards, headerCard)

	// 只显示前5题作为预览
	previewCount := 5
	if len(questions) < previewCount {
		previewCount = len(questions)
	}

	for i := 0; i < previewCount; i++ {
		q := questions[i]
		typeIcon := getTypeIcon(q.Type)

		// 创建题目卡片
		questionCard := createQuestionCard(q, i+1, typeIcon)
		cards = append(cards, questionCard)

		// 在题目之间添加分隔线（除了最后一个）
		if i < previewCount-1 {
			separator := widget.NewSeparator()
			cards = append(cards, separator)
		}
	}

	// 如果有更多题目，显示提示
	if len(questions) > previewCount {
		moreSeparator := widget.NewSeparator()
		moreLabel := widget.NewLabel(fmt.Sprintf("... 还有 %d 道题目已保存到数据库", len(questions)-previewCount))
		moreLabel.TextStyle = fyne.TextStyle{Italic: true}
		cards = append(cards, moreSeparator, moreLabel)
	}

	return cards
}

// 获取题型图标
func getTypeIcon(questionType string) string {
	switch questionType {
	case "单选题":
		return "🔘"
	case "多选题":
		return "☑️"
	case "判断题":
		return "✅"
	case "填空题":
		return "📝"
	case "简答题":
		return "💬"
	default:
		return "❓"
	}
}

// 格式化题目文本 - 自动换行和清理
func formatQuestionText(text string) string {
	// 清理多余的空白字符
	text = strings.TrimSpace(text)

	// 如果文本太长，进行换行处理
	if len([]rune(text)) > 80 {
		return autoWrapText(text, 80)
	}

	return text
}

// 更新分页按钮状态
func updatePaginationButtons() {
	if prevPageBtn != nil {
		prevPageBtn.Disable()
		if currentPage > 1 {
			prevPageBtn.Enable()
		}
	}

	if nextPageBtn != nil {
		nextPageBtn.Disable()
		if currentPage*itemsPerPage < totalQuestions {
			nextPageBtn.Enable()
		}
	}
}

// 上一页
func prevPage() {
	if currentPage > 1 {
		currentPage--
		showAllQuestions()
	}
}

// 下一页
func nextPage() {
	totalPages := (totalQuestions + itemsPerPage - 1) / itemsPerPage
	if currentPage < totalPages {
		currentPage++
		showAllQuestions()
	}
}

// 跳转到指定页数
func jumpToPage() {
	if jumpPageEntry == nil {
		return
	}

	pageStr := jumpPageEntry.Text
	if pageStr == "" {
		dialog.ShowError(fmt.Errorf("请输入页码"), guiWindow)
		return
	}

	page, err := strconv.Atoi(pageStr)
	if err != nil {
		dialog.ShowError(fmt.Errorf("请输入有效的页码"), guiWindow)
		return
	}

	totalPages := (totalQuestions + itemsPerPage - 1) / itemsPerPage
	if totalPages == 0 {
		totalPages = 1
	}

	if page < 1 || page > totalPages {
		dialog.ShowError(fmt.Errorf("页码超出范围，总页数为 %d", totalPages), guiWindow)
		return
	}

	currentPage = page
	showAllQuestions()
}

func setupGUI() {
	guiApp = app.NewWithID(AppName)

	// 应用自定义主题以支持中文字体
	guiApp.Settings().SetTheme(newCustomTheme())

	guiWindow = guiApp.NewWindow(WindowTitle)
	guiWindow.Resize(fyne.NewSize(WindowWidth, WindowHeight))

	// 创建主标题（太占位置了不需要）
	// title := widget.NewLabelWithStyle("📚 题库管理系统", fyne.TextAlignCenter, fyne.TextStyle{Bold: true})

	// 创建状态标签，使用更好的样式
	statusLabel = widget.NewLabel("✅ 系统就绪")
	statusLabel.TextStyle = fyne.TextStyle{Italic: true}

	// 创建进度条
	progressBar = widget.NewProgressBar()
	progressBar.Hide()

	// 创建结果显示区域（卡片式）
	resultContainer = container.NewVBox()
	resultScroll = container.NewScroll(resultContainer)
	resultScroll.SetMinSize(fyne.NewSize(800, 400))

	// 文件选择区域
	filePathEntry := widget.NewEntry()
	filePathEntry.SetPlaceHolder("📄 选择或拖放DOCX文件到这里...")
	filePathEntry.TextStyle = fyne.TextStyle{Italic: true}

	// 文件选择按钮
	fileBtn := widget.NewButton("📁 选择文件", func() {
		dialog.ShowFileOpen(func(reader fyne.URIReadCloser, err error) {
			if err == nil && reader != nil {
				filePath := reader.URI().Path()
				if isValidDocxFile(filePath) {
					filePathEntry.SetText(filePath)
					showSuccess("文件已选择: " + getFileName(filePath))
				} else {
					showError("文件格式错误", fmt.Errorf("请选择有效的DOCX文件"))
				}
			}
		}, guiWindow)
	})

	// 解析按钮
	parseBtn := widget.NewButton("🔍 解析文件", func() {
		path := filePathEntry.Text
		if path == "" {
			dialog.ShowError(fmt.Errorf("请先选择文件"), guiWindow)
			return
		}

		if !isValidDocxFile(path) {
			showError("文件格式错误", fmt.Errorf("请选择有效的DOCX文件"))
			return
		}

		showProcessing("正在解析文档...")
		progressBar.Show()
		progressBar.SetValue(0)

		fyne.Do(func() {
			defer func() {
				progressBar.Hide()
				progressBar.SetValue(0)
			}()

			questions, err := loadDocx(path)
			if err != nil {
				showError("解析失败", err)
				return
			}

			// 清洗题目文本，去除标点和空格
			for i := range questions {
				questions[i].Text = cleanText(questions[i].Text)
			}

			// 更新结果，使用卡片式显示
			if resultContainer != nil {
				previewCards := generatePreviewCards(questions)
				resultContainer.Objects = previewCards
				resultContainer.Refresh()
			}

			showSuccess(fmt.Sprintf("解析完成! 共添加 %d 道题目", len(questions)))

			// 保存到数据库
			if err := saveQuestionsToDB(questions); err != nil {
				showError("保存失败", err)
			}

			// 解析完成后显示所有题目
			currentPage = 1
			showAllQuestions()
		})
	})

	// 搜索区域
	searchEntry := widget.NewEntry()
	searchEntry.SetPlaceHolder("🔍 输入题目内容进行搜索...")
	searchEntry.TextStyle = fyne.TextStyle{Italic: true}

	searchBtn := widget.NewButton("🔍 搜索题目", func() {
		query := searchEntry.Text

		// 清洗搜索查询，去除标点和空格
		cleanedQuery := cleanText(query)
		currentPage = 1

		fyne.Do(func() {
			results, err := searchQuestionsPaginated(cleanedQuery, currentPage, itemsPerPage)
			if err != nil {
				showError("搜索失败", err)
				return
			}

			// 获取总题目数
			var count int64
			cleanedQuery = cleanText(query)
			if len([]rune(cleanedQuery)) > MaxQueryLength {
				cleanedQuery = string([]rune(cleanedQuery)[:MaxQueryLength])
			}
			var queryDB *gorm.DB
			if query == "" {
				queryDB = db
			} else {
				queryDB = db.Where("text LIKE ?", "%"+cleanedQuery+"%")
			}
			if err := queryDB.Model(&Question{}).Count(&count).Error; err != nil {
				showError("获取搜索结果总数失败", err)
				return
			}
			totalQuestions = int(count)

			// 计算总页数
			totalPages := (totalQuestions + itemsPerPage - 1) / itemsPerPage

			if len(results) == 0 {
				// 显示无结果卡片
				noResultCard := container.NewVBox(
					widget.NewLabelWithStyle("🔍 未找到相关题目", fyne.TextAlignCenter, fyne.TextStyle{Bold: true}),
					widget.NewLabel("请尝试其他关键词或检查拼写"),
				)
				resultContainer.Objects = []fyne.CanvasObject{noResultCard}
				resultContainer.Refresh()
				statusLabel.SetText("❌ 未找到匹配的题目")
				return
			}

			// 使用卡片式显示搜索结果
			if resultContainer != nil {
				searchCards := generateQuestionsCards(results, totalQuestions, currentPage, totalPages, "🔍 搜索结果")
				resultContainer.Objects = searchCards
				resultContainer.Refresh()

				// 自动回顶到顶部
				scrollToTop()
			}

			showSuccess(fmt.Sprintf("搜索完成! 共找到 %d 条结果，当前第 %d 页，总页数 %d", totalQuestions, currentPage, totalPages))

			// 更新分页按钮状态
			prevPageBtn.Disable()
			nextPageBtn.Disable()
			if currentPage > 1 {
				prevPageBtn.Enable()
			}
			if currentPage*itemsPerPage < totalQuestions {
				nextPageBtn.Enable()
			}
		})
	})

	// 拖放支持 - 修复版本
	// 拖放功能在setupDropZone函数中处理

	// 添加拖放区域支持
	setupDropZone(filePathEntry, guiWindow)

	// 分页按钮
	prevPageBtn = widget.NewButton("⬅️ 上一页", prevPage)
	prevPageBtn.Disable()
	nextPageBtn = widget.NewButton("下一页 ➡️", nextPage)
	nextPageBtn.Disable()

	// 跳转到指定页数的输入框和按钮
	jumpPageEntry = widget.NewEntry()
	jumpPageEntry.SetPlaceHolder("页码")
	jumpPageEntry.TextStyle = fyne.TextStyle{Italic: true}
	jumpPageBtn = widget.NewButton("跳转", jumpToPage)

	// 统计信息显示
	statsLabel = widget.NewLabel("📊 统计信息加载中...")
	statsLabel.TextStyle = fyne.TextStyle{Italic: true}

	// 数据管理按钮区域
	addBtn := widget.NewButton("➕ 添加题目", func() {
		showAddQuestionDialog()
	})

	editBtn := widget.NewButton("✏️ 编辑题目", func() {
		showEditQuestionDialog()
	})

	deleteBtn := widget.NewButton("🗑️ 删除题目", func() {
		showDeleteQuestionDialog()
	})

	clearAllBtn := widget.NewButton("💥 清空题库", func() {
		showClearAllDialog()
	})

	refreshBtn := widget.NewButton("🔄 刷新", func() {
		showAllQuestions()
		updateStats()
	})

	// 数据管理区域
	dataManagementRow := container.NewHBox(
		addBtn,
		editBtn,
		deleteBtn,
		clearAllBtn,
		refreshBtn,
	)

	// 分页控件布局
	pagination := container.NewHBox(
		prevPageBtn,
		nextPageBtn,
		widget.NewLabel("跳转到:"),
		jumpPageEntry,
		jumpPageBtn,
	)

	// 文件操作区域
	fileRow := container.NewBorder(nil, nil, fileBtn, parseBtn, filePathEntry)

	// 搜索区域
	searchRow := container.NewBorder(nil, nil, nil, searchBtn, searchEntry)

	// 顶部区域
	topSection := container.NewVBox(
		// title,
		container.NewHBox(widget.NewLabel(""), statsLabel), // 添加一些间距
		fileRow,
		searchRow,
		widget.NewSeparator(),
		dataManagementRow, // 添加数据管理按钮
		widget.NewSeparator(),
	)

	// 底部状态区域
	bottomSection := container.NewVBox(
		progressBar,
		pagination,
		statusLabel,
	)

	// 主布局
	content := container.NewBorder(
		topSection,
		bottomSection,
		nil,
		nil,
		resultScroll,
	)

	// 设置内容并刷新
	guiWindow.SetContent(content)
	content.Refresh()

	// 启动时显示所有题目
	showAllQuestions()

	// 更新统计信息
	updateStats()

	// 显示窗口
	guiWindow.Show()
}

// 保存题目到数据库 - 优化版本
func saveQuestionsToDB(questions []Question) error {
	if len(questions) == 0 {
		return fmt.Errorf("没有题目需要保存")
	}

	tx := db.Begin()
	if tx.Error != nil {
		return fmt.Errorf("开始事务失败: %w", tx.Error)
	}

	defer func() {
		if r := recover(); r != nil {
			tx.Rollback()
			log.Printf("事务回滚: %v", r)
		}
	}()

	savedCount := 0
	skippedCount := 0

	for _, q := range questions {
		// 清洗题目文本
		cleanedText := cleanText(q.Text)
		if cleanedText == "" {
			skippedCount++
			continue
		}

		// 检查题目是否已存在（排除已软删除的记录）
		var existing Question
		if err := db.Unscoped().Where("text = ?", cleanedText).First(&existing).Error; err == nil {
			// 如果找到记录，检查是否已被软删除
			if existing.DeletedAt.Valid {
				// 如果已被软删除，则恢复该记录并更新内容
				log.Printf("发现已删除的重复题目，正在恢复: %s", cleanedText)
				existing.Type = q.Type
				existing.Options = q.Options
				existing.Answer = q.Answer
				existing.DeletedAt = gorm.DeletedAt{} // 清除软删除标记

				if err := tx.Unscoped().Save(&existing).Error; err != nil {
					tx.Rollback()
					return fmt.Errorf("恢复题目失败: %w", err)
				}
				savedCount++
			} else {
				// 如果记录存在且未被删除，则跳过
				skippedCount++
			}
			continue
		}

		// 保存新题目
		q.Text = cleanedText
		if err := tx.Create(&q).Error; err != nil {
			tx.Rollback()
			return fmt.Errorf("保存题目失败: %w", err)
		}
		savedCount++
	}

	if err := tx.Commit().Error; err != nil {
		return fmt.Errorf("提交事务失败: %w", err)
	}

	log.Printf("保存完成: 新增 %d 道题目, 跳过 %d 道重复题目", savedCount, skippedCount)
	return nil
}

// 搜索题目 - 优化版本
func searchQuestions(query string) ([]Question, error) {
	if db == nil {
		return nil, fmt.Errorf("数据库未初始化")
	}

	var results []Question
	queryDB := db

	// 如果有查询条件，添加WHERE子句
	if query != "" {
		cleanedQuery := cleanText(query)
		if len([]rune(cleanedQuery)) > MaxQueryLength {
			cleanedQuery = string([]rune(cleanedQuery)[:MaxQueryLength])
		}
		queryDB = db.Where("text LIKE ?", "%"+cleanedQuery+"%")
	}

	if err := queryDB.Find(&results).Error; err != nil {
		return nil, fmt.Errorf("搜索题目失败: %w", err)
	}

	return results, nil
}

// 初始化必要的资源
func initResources() error {
	// 这里可以添加其他初始化逻辑，比如创建目录等
	return nil
}

// 主函数 - 优化版本
func main() {
	// 设置日志格式
	log.SetFlags(log.LstdFlags | log.Lshortfile)
	log.Println("启动题库管理系统...")

	// 初始化数据库
	if err := initDB(); err != nil {
		log.Fatalf("初始化数据库失败: %v", err)
	}
	log.Println("数据库初始化成功")

	// 初始化必要的资源
	if err := initResources(); err != nil {
		log.Fatalf("初始化资源失败: %v", err)
	}

	// 设置GUI
	setupGUI()
	log.Println("GUI初始化成功")

	// 启动Web服务
	go func() {
		if err := startWebService(); err != nil {
			log.Printf("Web服务启动失败: %v", err)
		}
	}()

	// 运行GUI主循环
	log.Println("启动GUI主循环...")
	guiApp.Run()
	log.Println("程序正常退出")
}

// 启动Web服务 - 优化版本
func startWebService() error {
	// 初始化WEB服务
	r := gin.Default()

	// 配置404处理
	r.NoRoute(func(c *gin.Context) {
		c.JSON(http.StatusNotFound, gin.H{
			"error": "endpoint not found",
			"path":  c.Request.URL.Path,
		})
	})

	// 配置CORS中间件
	setupCORS(r)

	// 注册路由
	setupRoutes(r)

	// 启动服务
	log.Printf("Web服务将在端口 %s 启动", WebPort)
	if err := r.Run(WebPort); err != nil {
		return fmt.Errorf("启动Web服务失败: %w", err)
	}

	return nil
}

// 设置路由
func setupRoutes(r *gin.Engine) {
	// 搜索接口
	r.POST("/adapter-service/search", handleSearch)

	// 健康检查接口
	r.GET("/", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":  "running",
			"version": "1.0.0",
			"docs":    "/adapter-service/search",
		})
	})

	r.HEAD("/", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
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
		c.Status(http.StatusNoContent)
	})
}

// 设置CORS - 优化版本
func setupCORS(r *gin.Engine) {
	config := cors.DefaultConfig()
	config.AllowOrigins = []string{"*"}
	config.AllowMethods = []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"}
	config.AllowHeaders = []string{"Origin", "Content-Type", "Authorization", "Accept"}
	config.AllowCredentials = true
	config.MaxAge = 12 * 60 * 60 // 12小时

	r.Use(cors.New(config))
}

// 加载DOCX文件并解析题目 - 优化版本
func loadDocx(path string) ([]Question, error) {
	log.Printf("开始加载DOCX文件: %s", path)

	// 读取DOCX文件(ZIP格式)
	r, err := zip.OpenReader(path)
	if err != nil {
		return nil, fmt.Errorf("无法打开DOCX文件: %w", err)
	}
	defer r.Close()

	// 查找document.xml
	xmlFile, err := findXMLFile(r)
	if err != nil {
		return nil, fmt.Errorf("找不到document.xml文件: %w", err)
	}

	// 读取XML内容
	content, err := readXMLContent(xmlFile)
	if err != nil {
		return nil, fmt.Errorf("读取XML文件内容失败: %w", err)
	}

	// 提取所有文本内容
	text := extractTextFromXML(content)
	log.Printf("提取的文本内容长度: %d", len(text))

	// 解析题目
	questions, err := ParseQuestions(text)
	if err != nil {
		return nil, fmt.Errorf("解析题目失败: %w", err)
	}

	log.Printf("成功解析 %d 道题目", len(questions))
	return questions, nil
}

// 查找document.xml文件 - 优化版本
func findXMLFile(r *zip.ReadCloser) (*zip.File, error) {
	for _, f := range r.File {
		if f.Name == "word/document.xml" {
			return f, nil
		}
	}
	return nil, fmt.Errorf("在ZIP文件中找不到word/document.xml")
}

// 读取XML文件内容 - 优化版本
func readXMLContent(xmlFile *zip.File) (string, error) {
	rc, err := xmlFile.Open()
	if err != nil {
		return "", fmt.Errorf("打开XML文件失败: %w", err)
	}
	defer rc.Close()

	buf := new(bytes.Buffer)
	if _, err := buf.ReadFrom(rc); err != nil {
		return "", fmt.Errorf("读取XML内容失败: %w", err)
	}

	return buf.String(), nil
}

// 解析所有题目
func parseQuestions(text string) ([]Question, error) {
	if text == "" {
		return nil, fmt.Errorf("输入文本为空")
	}

	lines := strings.Split(text, "\n")
	var questions []Question
	var currentBlock []string
	blockStart := false

	for idx, line := range lines {
		log.Printf("[行调试] 行号:%d 内容:[%s]", idx+1, line)
		trimmed := strings.TrimSpace(line)
		if trimmed == "" {
			continue
		}
		// 检查是否是新的题目开始（数字+全角点+【题型】）
		if matched, _ := regexp.MatchString(`^\s*\d+．\s*【[^】]+】`, line); matched {
			// 处理前一个题目块
			if blockStart && len(currentBlock) > 0 {
				blockStr := strings.Join(currentBlock, "\n")
				log.Println("[题目分块] 原始内容:\n" + blockStr)
				if q, err := parseSingleQuestionBlock(blockStr); err == nil {
					questions = append(questions, q)
				} else {
					log.Printf("跳过题目块: %v", err)
				}
			}
			// 开始新的题目块
			currentBlock = []string{trimmed}
			blockStart = true
		} else if blockStart {
			currentBlock = append(currentBlock, line)
		}
	}
	// 处理最后一个题目块
	if blockStart && len(currentBlock) > 0 {
		blockStr := strings.Join(currentBlock, "\n")
		log.Println("[题目分块] 原始内容:\n" + blockStr)
		if q, err := parseSingleQuestionBlock(blockStr); err == nil {
			questions = append(questions, q)
		} else {
			log.Printf("跳过题目块: %v", err)
		}
	}
	if len(questions) == 0 {
		return nil, fmt.Errorf("没有成功解析任何题目")
	}
	return questions, nil
}

// 解析单个题目块
func parseSingleQuestionBlock(block string) (Question, error) {
	// 题型
	typeRe := regexp.MustCompile(`【([^】]+)】`)
	typeMatch := typeRe.FindStringSubmatch(block)
	var qType string
	if len(typeMatch) >= 2 {
		qType = strings.TrimSpace(typeMatch[1])
	}

	// 提取题干（题型后到"选项："前的内容）
	stemRe := regexp.MustCompile(`【[^】]+】([\s\S]*?)选项：`)
	stemMatch := stemRe.FindStringSubmatch(block)
	stem := ""
	if len(stemMatch) > 1 {
		stem = strings.TrimSpace(stemMatch[1])
		stem = strings.ReplaceAll(stem, "( )", "") // 去除括号
		stem = strings.ReplaceAll(stem, "（ ）", "")
	}

	// 如果没有找到"选项："，尝试使用A、作为分隔符
	if stem == "" {
		stemRe := regexp.MustCompile(`【[^】]+】([\s\S]*?)A、`)
		stemMatch := stemRe.FindStringSubmatch(block)
		if len(stemMatch) > 1 {
			stem = strings.TrimSpace(stemMatch[1])
			stem = strings.ReplaceAll(stem, "( )", "")
			stem = strings.ReplaceAll(stem, "（ ）", "")
		}
	}

	// 对于判断题，题干可能在"我的答案"之前
	if stem == "" && strings.Contains(block, "我的答案") {
		// 尝试从题型后到"我的答案"前提取题干
		judgeRe := regexp.MustCompile(`【[^】]+】([\s\S]*?)我的答案`)
		judgeMatch := judgeRe.FindStringSubmatch(block)
		if len(judgeMatch) > 1 {
			stem = strings.TrimSpace(judgeMatch[1])
			stem = strings.ReplaceAll(stem, "( )", "")
			stem = strings.ReplaceAll(stem, "（ ）", "")
		}
	}

	// 对于判断题，如果还是没有找到题干，尝试在"正确答案"之前
	if stem == "" && strings.Contains(block, "正确答案") {
		// 尝试从题型后到"正确答案"前提取题干
		judgeRe := regexp.MustCompile(`【[^】]+】([\s\S]*?)正确答案`)
		judgeMatch := judgeRe.FindStringSubmatch(block)
		if len(judgeMatch) > 1 {
			stem = strings.TrimSpace(judgeMatch[1])
			stem = strings.ReplaceAll(stem, "( )", "")
			stem = strings.ReplaceAll(stem, "（ ）", "")
		}
	}

	// 提取选项（A-Z）- 改进版本
	options := []string{}

	// 方法1：使用正则表达式精确提取选项
	optionRe := regexp.MustCompile(`([A-Z])、([^A-Z]*?)(?:\n[A-Z]、|\n正确答案|\n我的答案|\n答案状态|\n得分|\n$|$)`)
	optionMatches := optionRe.FindAllStringSubmatch(block, -1)

	for _, match := range optionMatches {
		if len(match) > 2 {
			opt := strings.TrimSpace(match[2])
			if opt != "" {
				options = append(options, opt)
			}
		}
	}

	// 方法2：如果正则表达式方法失败，使用字符串分割方法
	if len(options) == 0 {
		// 先找到"正确答案"的位置，用于确定选项的结束边界
		ansIndex := strings.Index(block, "正确答案")
		if ansIndex == -1 {
			ansIndex = strings.Index(block, "我的答案")
		}
		if ansIndex == -1 {
			ansIndex = len(block)
		}

		// 提取选项部分（从A、开始到"正确答案"或"我的答案"之前）
		optionSection := block
		if ansIndex > 0 {
			optionSection = block[:ansIndex]
		}

		// 按选项标记分割
		for _, letter := range "ABCDEFGHIJKLMNOPQRSTUVWXYZ" {
			marker := string(letter) + "、"
			if strings.Contains(optionSection, marker) {
				parts := strings.Split(optionSection, marker)
				if len(parts) > 1 {
					optionPart := parts[1]

					// 找到下一个选项的位置
					nextPos := len(optionPart)
					for _, nextLetter := range "ABCDEFGHIJKLMNOPQRSTUVWXYZ" {
						if nextLetter > letter {
							nextMarker := string(nextLetter) + "、"
							if idx := strings.Index(optionPart, nextMarker); idx > 0 && idx < nextPos {
								nextPos = idx
							}
						}
					}

					// 提取选项内容
					if nextPos > 0 && nextPos <= len(optionPart) {
						opt := strings.TrimSpace(optionPart[:nextPos])
						if opt != "" {
							options = append(options, opt)
						}
					}
				}
			}
		}
	}

	// 方法3：如果还是失败，使用字符遍历方法
	if len(options) == 0 {
		runes := []rune(block)
		optionPositions := []int{}

		// 找到所有选项的位置
		for i := 0; i < len(runes)-1; i++ {
			if runes[i] >= 'A' && runes[i] <= 'Z' && runes[i+1] == '、' {
				optionPositions = append(optionPositions, i)
			}
		}

		// 提取每个选项的内容
		for i, pos := range optionPositions {
			start := pos + 2 // 跳过"X、"部分
			if start >= len(runes) {
				continue
			}

			end := len(runes)

			// 找到下一个选项的位置
			if i+1 < len(optionPositions) {
				nextPos := optionPositions[i+1]
				if nextPos > start {
					end = nextPos
				}
			} else {
				// 最后一个选项，找到"正确答案"或"我的答案"的位置
				ansIndex := strings.Index(block, "正确答案")
				if ansIndex == -1 {
					ansIndex = strings.Index(block, "我的答案")
				}
				if ansIndex > start && ansIndex < len(block) {
					end = ansIndex
				}
			}

			// 确保边界安全
			if end > start && end <= len(runes) {
				opt := strings.TrimSpace(string(runes[start:end]))
				if opt != "" {
					options = append(options, opt)
				}
			}
		}
	}

	// 最终清理：确保选项不包含"正确答案"部分和其他选项
	for i, opt := range options {
		// 移除"正确答案"部分
		if ansIdx := strings.Index(opt, "正确答案"); ansIdx > 0 {
			options[i] = strings.TrimSpace(opt[:ansIdx])
		}

		// 移除其他选项标记
		for _, letter := range "ABCDEFGHIJKLMNOPQRSTUVWXYZ" {
			marker := string(letter) + "、"
			if idx := strings.Index(options[i], marker); idx > 0 {
				options[i] = strings.TrimSpace(options[i][:idx])
			}
		}

		// 清理换行符和多余空格
		options[i] = strings.ReplaceAll(options[i], "\n", " ")
		options[i] = strings.TrimSpace(options[i])
	}

	// 提取答案 - 改进版本，优先使用"正确答案："，没有的话再使用"我的答案："
	answers := []string{}

	// 首先尝试提取"正确答案："
	ansRe := regexp.MustCompile(`正确答案[：:]*\s*([A-Z对错]+)`)
	ansMatch := ansRe.FindStringSubmatch(block)
	if len(ansMatch) > 1 {
		for _, ch := range ansMatch[1] {
			if ch >= 'A' && ch <= 'Z' {
				idx := int(ch - 'A')
				if idx >= 0 && idx < len(options) {
					answers = append(answers, options[idx])
				}
			} else if ch == '对' || ch == '错' {
				answers = append(answers, string(ch))
			}
		}
	}

	// 如果没有找到"正确答案："，尝试提取"我的答案："
	if len(answers) == 0 {
		myAnsRe := regexp.MustCompile(`我的答案[：:]*\s*([A-Z对错]+)`)
		myAnsMatch := myAnsRe.FindStringSubmatch(block)
		if len(myAnsMatch) > 1 {
			for _, ch := range myAnsMatch[1] {
				if ch >= 'A' && ch <= 'Z' {
					idx := int(ch - 'A')
					if idx >= 0 && idx < len(options) {
						answers = append(answers, options[idx])
					}
				} else if ch == '对' || ch == '错' {
					answers = append(answers, string(ch))
				}
			}
		}
	}

	log.Printf("[单题解析] 题型: %s", qType)
	log.Printf("[单题解析] 题干: %s", stem)
	log.Printf("[单题解析] 选项: %+v", options)
	log.Printf("[单题解析] 答案: %+v", answers)

	return Question{
		Type:    qType,
		Text:    stem,
		Options: options,
		Answer:  answers,
	}, nil
}

// 从XML内容中提取文本 - 优化版本，支持分行还原
func extractTextFromXML(xmlContent string) string {
	var textBuilder strings.Builder
	var lastWasText bool

	// 使用XML解析器来更好地处理文档结构
	d := xml.NewDecoder(bytes.NewReader([]byte(xmlContent)))
	for {
		t, err := d.Token()
		if err != nil || t == nil {
			break
		}

		switch se := t.(type) {
		case xml.StartElement:
			switch se.Name.Local {
			case "p": // 段落开始
				// 如果不是第一个段落，添加换行符
				if textBuilder.Len() > 0 {
					textBuilder.WriteString("\n")
				}
			case "br": // 换行标签
				textBuilder.WriteString("\n")
			case "t": // 文本标签
				var tText string
				if err := d.DecodeElement(&tText, &se); err == nil {
					// 解码XML实体
					tText = strings.ReplaceAll(tText, "&amp;", "&")
					tText = strings.ReplaceAll(tText, "&lt;", "<")
					tText = strings.ReplaceAll(tText, "&gt;", ">")
					tText = strings.ReplaceAll(tText, "&quot;", "\"")
					tText = strings.ReplaceAll(tText, "&#39;", "'")

					textBuilder.WriteString(tText)
					lastWasText = true
				}
			}
		case xml.EndElement:
			if se.Name.Local == "p" {
				// 段落结束后添加换行符
				if textBuilder.Len() > 0 && lastWasText {
					textBuilder.WriteString("\n")
				}
			}
		}
	}

	// 如果XML解析器没有提取到内容，尝试使用正则表达式方法
	if textBuilder.Len() == 0 {
		textRe := regexp.MustCompile(`<w:t[^>]*>([^<]*)</w:t>`)
		matches := textRe.FindAllStringSubmatch(xmlContent, -1)

		// 同时查找段落标签以确定换行位置
		paragraphRe := regexp.MustCompile(`</w:p>`)
		paragraphMatches := paragraphRe.FindAllStringIndex(xmlContent, -1)
		paragraphIndex := 0

		for _, match := range matches {
			if len(match) > 1 {
				text := match[1]
				// 解码XML实体
				text = strings.ReplaceAll(text, "&amp;", "&")
				text = strings.ReplaceAll(text, "&lt;", "<")
				text = strings.ReplaceAll(text, "&gt;", ">")
				text = strings.ReplaceAll(text, "&quot;", "\"")
				text = strings.ReplaceAll(text, "&#39;", "'")

				textBuilder.WriteString(text)

				// 检查是否应该在当前位置添加换行符
				for paragraphIndex < len(paragraphMatches) &&
					paragraphMatches[paragraphIndex][0] < strings.Index(xmlContent, match[0]) {
					textBuilder.WriteString("\n")
					paragraphIndex++
				}
			}
		}
	}

	result := textBuilder.String()

	// 清理和规范化文本，但保留有意义的换行
	result = strings.ReplaceAll(result, "\r\n", "\n")
	result = strings.ReplaceAll(result, "\r", "\n")

	// 移除多余的连续空行，但保留单个换行符
	lines := strings.Split(result, "\n")
	var cleanedLines []string
	for _, line := range lines {
		// 保留空行，但只保留一个
		if line == "" {
			if len(cleanedLines) == 0 || cleanedLines[len(cleanedLines)-1] != "" {
				cleanedLines = append(cleanedLines, line)
			}
		} else {
			cleanedLines = append(cleanedLines, strings.TrimSpace(line))
		}
	}

	return strings.Join(cleanedLines, "\n")
}

// 处理搜索请求 - 优化版本
func handleSearch(c *gin.Context) {
	// 解析请求参数
	var request struct {
		Question string   `json:"question" binding:"required"`
		Options  []string `json:"options"`
		Type     int      `json:"type" binding:"min=0,max=4"`
	}

	if err := c.ShouldBindJSON(&request); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": fmt.Sprintf("无效的请求格式: %v", err),
		})
		return
	}

	// 验证请求参数
	if request.Question == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "题目内容不能为空"})
		return
	}

	// 清理查询文本
	cleanedQuery := cleanText(request.Question)
	if len([]rune(cleanedQuery)) > MaxQueryLength {
		cleanedQuery = string([]rune(cleanedQuery)[:MaxQueryLength])
	}

	log.Printf("API请求: 题型:%d 题目:%s", request.Type, cleanedQuery)

	// 查询数据库
	results, err := searchQuestions(cleanedQuery)
	if err != nil {
		log.Printf("数据库查询失败: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "数据库查询失败"})
		return
	}

	// 处理查询结果
	if len(results) == 0 {
		c.JSON(http.StatusNotFound, gin.H{"error": "未找到相关问题"})
		return
	}

	// 构建响应
	response := buildSearchResponse(results[0], request.Options, request.Type)

	log.Printf("API请求处理完成 题型:%d 匹配答案:%v", request.Type, results[0].Answer)
	c.JSON(http.StatusOK, response)
}

// 构建搜索响应
func buildSearchResponse(question Question, options []string, questionType int) gin.H {
	answerKey := []string{}
	answerIndex := []int{}
	answerText := []string{}

	// 匹配选项和答案
	for i, option := range options {
		for _, ans := range question.Answer {
			if strings.Contains(option, ans) || strings.Contains(ans, option) {
				answerKey = append(answerKey, string(rune('A'+i)))
				answerIndex = append(answerIndex, i)
				answerText = append(answerText, option)
			}
		}
	}

	// 如果没有匹配到选项，使用原始答案
	if len(answerKey) == 0 {
		answerKey = question.Answer
		answerIndex = make([]int, len(question.Answer))
		for i := range answerIndex {
			answerIndex[i] = 0
		}
		answerText = question.Answer
	}

	// 生成格式化答案
	formattedAnswers := generateFormattedAnswers(question.Answer, options)
	if len(formattedAnswers) == 0 {
		formattedAnswers = question.Answer
	}

	return gin.H{
		"plat":     0,
		"question": question.Text,
		"options":  options,
		"type":     questionType,
		"answer": gin.H{
			"answerKey":     answerKey,
			"answerKeyText": strings.Join(answerKey, ""),
			"answerIndex":   answerIndex,
			"answerText":    strings.Join(answerText, "#"),
			"bestAnswer":    question.Answer,
			"allAnswer": [][]string{
				question.Answer,
				formattedAnswers,
			},
		},
	}
}

// 生成带选项前缀的格式化答案 - 优化版本
func generateFormattedAnswers(answers []string, options []string) []string {
	if len(answers) == 0 || len(options) == 0 {
		return answers
	}

	formatted := make([]string, 0, len(answers))
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

// 文件验证和拖放支持函数
func isValidDocxFile(filePath string) bool {
	if filePath == "" {
		return false
	}

	// 检查文件扩展名
	ext := strings.ToLower(getFileExtension(filePath))
	if ext != ".docx" {
		return false
	}

	// 检查文件是否存在
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		return false
	}

	return true
}

func getFileExtension(filePath string) string {
	lastDot := strings.LastIndex(filePath, ".")
	if lastDot == -1 {
		return ""
	}
	return filePath[lastDot:]
}

func getFileName(filePath string) string {
	parts := strings.Split(filePath, string(os.PathSeparator))
	if len(parts) > 0 {
		return parts[len(parts)-1]
	}
	return filePath
}

// 设置拖放区域
func setupDropZone(entry *widget.Entry, window fyne.Window) {
	// 使用Fyne的正确拖放API
	window.SetOnDropped(func(pos fyne.Position, uris []fyne.URI) {
		if len(uris) > 0 {
			// 获取第一个拖放的文件URI
			uri := uris[0]
			filePath := uri.Path()

			// 处理文件路径
			filePath = cleanDropPath(filePath)

			if isValidDocxFile(filePath) {
				entry.SetText(filePath)
				showSuccess("文件已拖放: " + getFileName(filePath))
			} else {
				showError("文件格式错误", fmt.Errorf("请拖放有效的DOCX文件"))
			}
		}
	})

	// 保留OnSubmitted事件作为备用
	entry.OnSubmitted = func(path string) {
		if path != "" {
			// 处理Windows拖放的文件路径格式
			path = cleanDropPath(path)

			if isValidDocxFile(path) {
				entry.SetText(path)
				showSuccess("文件已拖放: " + getFileName(path))
			} else {
				showError("文件格式错误", fmt.Errorf("请拖放有效的DOCX文件"))
			}
		}
	}
}

// 清理拖放的文件路径
func cleanDropPath(path string) string {
	// 移除可能的引号
	path = strings.Trim(path, `"'`)

	// 处理Windows路径分隔符
	path = strings.ReplaceAll(path, "\\", string(os.PathSeparator))

	return path
}

// ==================== 数据管理功能 ====================

// 显示添加题目对话框
func showAddQuestionDialog() {
	// 题型选择
	typeSelect := widget.NewSelect([]string{"单选题", "多选题", "判断题", "填空题", "简答题"}, nil)
	typeSelect.SetSelected("单选题")

	// 题干输入
	questionEntry := widget.NewMultiLineEntry()
	questionEntry.SetPlaceHolder("请输入题目内容...")
	questionEntry.Wrapping = fyne.TextWrapWord

	// 选项输入区域
	optionsContainer := container.NewVBox()
	var optionEntries []*widget.Entry

	// 添加选项的函数
	addOption := func() {
		optionEntry := widget.NewEntry()
		optionEntry.SetPlaceHolder(fmt.Sprintf("选项 %c", 'A'+len(optionEntries)))
		optionEntries = append(optionEntries, optionEntry)
		optionsContainer.Add(container.NewHBox(
			widget.NewLabel(fmt.Sprintf("%c.", 'A'+len(optionEntries)-1)),
			optionEntry,
		))
		optionsContainer.Refresh()
	}

	// 移除选项的函数
	removeOption := func() {
		if len(optionEntries) > 0 {
			optionsContainer.Remove(optionsContainer.Objects[len(optionsContainer.Objects)-1])
			optionEntries = optionEntries[:len(optionEntries)-1]
			optionsContainer.Refresh()
		}
	}

	// 选项管理按钮
	optionButtons := container.NewHBox(
		widget.NewButton("➕ 添加选项", addOption),
		widget.NewButton("➖ 移除选项", removeOption),
	)

	// 答案输入
	answerEntry := widget.NewEntry()
	answerEntry.SetPlaceHolder("请输入答案（如：A 或 A,B 或 对/错）")

	// 初始添加4个选项
	for i := 0; i < 4; i++ {
		addOption()
	}

	// 创建表单
	form := &widget.Form{
		Items: []*widget.FormItem{
			{Text: "题型", Widget: typeSelect, HintText: "选择题目类型"},
			{Text: "题干", Widget: questionEntry, HintText: "输入题目内容"},
			{Text: "选项", Widget: container.NewVBox(optionButtons, optionsContainer), HintText: "添加题目选项"},
			{Text: "答案", Widget: answerEntry, HintText: "输入正确答案"},
		},
	}

	// 显示对话框
	dialog.ShowForm("添加题目", "确定", "取消", form.Items, func(confirm bool) {
		if confirm {
			// 验证输入
			if questionEntry.Text == "" {
				dialog.ShowError(fmt.Errorf("题干不能为空"), guiWindow)
				return
			}

			if answerEntry.Text == "" {
				dialog.ShowError(fmt.Errorf("答案不能为空"), guiWindow)
				return
			}

			// 收集选项
			var options []string
			for _, entry := range optionEntries {
				if entry.Text != "" {
					options = append(options, strings.TrimSpace(entry.Text))
				}
			}

			// 处理答案
			var answers []string
			answerText := strings.TrimSpace(answerEntry.Text)

			// 如果是字母答案（A、B、C、D等）
			if matched, _ := regexp.MatchString(`^[A-Z,]+$`, answerText); matched {
				for _, ch := range answerText {
					if ch >= 'A' && ch <= 'Z' && ch != ',' {
						idx := int(ch - 'A')
						if idx < len(options) {
							answers = append(answers, options[idx])
						}
					}
				}
			} else {
				// 直接使用答案文本
				answers = []string{answerText}
			}

			// 创建题目
			question := Question{
				Type:    typeSelect.Selected,
				Text:    cleanText(questionEntry.Text),
				Options: options,
				Answer:  answers,
			}

			// 保存到数据库
			if err := db.Create(&question).Error; err != nil {
				dialog.ShowError(fmt.Errorf("保存失败: %v", err), guiWindow)
				return
			}

			dialog.ShowInformation("成功", "题目添加成功！", guiWindow)

			// 刷新显示
			showAllQuestions()
			updateStats()
		}
	}, guiWindow)
}

// 显示编辑题目对话框
func showEditQuestionDialog() {
	// 获取当前页面的题目
	results, err := searchQuestionsPaginated("", currentPage, itemsPerPage)
	if err != nil {
		dialog.ShowError(fmt.Errorf("获取题目失败: %v", err), guiWindow)
		return
	}

	if len(results) == 0 {
		dialog.ShowError(fmt.Errorf("当前页面没有题目"), guiWindow)
		return
	}

	// 创建题目选择列表
	var questionItems []string
	for i, q := range results {
		questionNum := (currentPage-1)*itemsPerPage + i + 1
		preview := q.Text
		if len([]rune(preview)) > 30 {
			preview = string([]rune(preview)[:30]) + "..."
		}
		questionItems = append(questionItems, fmt.Sprintf("%d. %s", questionNum, preview))
	}

	questionSelect := widget.NewSelect(questionItems, nil)
	if len(questionItems) > 0 {
		questionSelect.SetSelected(questionItems[0])
	}

	// 选择题目后显示编辑表单
	questionSelect.OnChanged = func(selected string) {
		if selected == "" {
			return
		}

		// 解析选中的题目索引
		parts := strings.Split(selected, ". ")
		if len(parts) < 2 {
			return
		}

		index, err := strconv.Atoi(parts[0])
		if err != nil {
			return
		}

		// 获取对应的题目
		questionIndex := index - 1 - (currentPage-1)*itemsPerPage
		if questionIndex < 0 || questionIndex >= len(results) {
			return
		}

		question := results[questionIndex]
		showEditQuestionForm(question)
	}

	// 显示选择对话框
	content := container.NewVBox(
		widget.NewLabel("请选择要编辑的题目："),
		questionSelect,
	)

	dialog.ShowCustom("选择题目", "关闭", content, guiWindow)
}

// 显示编辑题目表单
func showEditQuestionForm(question Question) {
	// 题型选择
	typeSelect := widget.NewSelect([]string{"单选题", "多选题", "判断题", "填空题", "简答题"}, nil)
	typeSelect.SetSelected(question.Type)

	// 题干输入
	questionEntry := widget.NewMultiLineEntry()
	questionEntry.SetText(question.Text)
	questionEntry.Wrapping = fyne.TextWrapWord

	// 选项输入区域
	optionsContainer := container.NewVBox()
	var optionEntries []*widget.Entry

	// 添加选项的函数
	addOption := func() {
		optionEntry := widget.NewEntry()
		optionEntry.SetPlaceHolder(fmt.Sprintf("选项 %c", 'A'+len(optionEntries)))
		optionEntries = append(optionEntries, optionEntry)
		optionsContainer.Add(container.NewHBox(
			widget.NewLabel(fmt.Sprintf("%c.", 'A'+len(optionEntries)-1)),
			optionEntry,
		))
		optionsContainer.Refresh()
	}

	// 移除选项的函数
	removeOption := func() {
		if len(optionEntries) > 0 {
			optionsContainer.Remove(optionsContainer.Objects[len(optionsContainer.Objects)-1])
			optionEntries = optionEntries[:len(optionEntries)-1]
			optionsContainer.Refresh()
		}
	}

	// 选项管理按钮
	optionButtons := container.NewHBox(
		widget.NewButton("➕ 添加选项", addOption),
		widget.NewButton("➖ 移除选项", removeOption),
	)

	// 加载现有选项
	for i, opt := range question.Options {
		addOption()
		if i < len(optionEntries) {
			optionEntries[i].SetText(opt)
		}
	}

	// 答案输入
	answerEntry := widget.NewEntry()
	answerEntry.SetText(strings.Join(question.Answer, ", "))

	// 创建表单
	form := &widget.Form{
		Items: []*widget.FormItem{
			{Text: "题型", Widget: typeSelect, HintText: "选择题目类型"},
			{Text: "题干", Widget: questionEntry, HintText: "输入题目内容"},
			{Text: "选项", Widget: container.NewVBox(optionButtons, optionsContainer), HintText: "编辑题目选项"},
			{Text: "答案", Widget: answerEntry, HintText: "输入正确答案"},
		},
	}

	// 显示对话框
	dialog.ShowForm("编辑题目", "确定", "取消", form.Items, func(confirm bool) {
		if confirm {
			// 验证输入
			if questionEntry.Text == "" {
				dialog.ShowError(fmt.Errorf("题干不能为空"), guiWindow)
				return
			}

			if answerEntry.Text == "" {
				dialog.ShowError(fmt.Errorf("答案不能为空"), guiWindow)
				return
			}

			// 收集选项
			var options []string
			for _, entry := range optionEntries {
				if entry.Text != "" {
					options = append(options, strings.TrimSpace(entry.Text))
				}
			}

			// 处理答案
			var answers []string
			answerText := strings.TrimSpace(answerEntry.Text)

			// 如果是字母答案（A、B、C、D等）
			if matched, _ := regexp.MatchString(`^[A-Z,]+$`, answerText); matched {
				for _, ch := range answerText {
					if ch >= 'A' && ch <= 'Z' && ch != ',' {
						idx := int(ch - 'A')
						if idx < len(options) {
							answers = append(answers, options[idx])
						}
					}
				}
			} else {
				// 直接使用答案文本
				answers = []string{answerText}
			}

			// 更新题目
			question.Type = typeSelect.Selected
			question.Text = cleanText(questionEntry.Text)
			question.Options = options
			question.Answer = answers

			// 保存到数据库
			if err := db.Save(&question).Error; err != nil {
				dialog.ShowError(fmt.Errorf("保存失败: %v", err), guiWindow)
				return
			}

			dialog.ShowInformation("成功", "题目更新成功！", guiWindow)

			// 刷新显示
			showAllQuestions()
			updateStats()
		}
	}, guiWindow)
}

// 显示删除题目对话框
func showDeleteQuestionDialog() {
	// 获取当前页面的题目
	results, err := searchQuestionsPaginated("", currentPage, itemsPerPage)
	if err != nil {
		dialog.ShowError(fmt.Errorf("获取题目失败: %v", err), guiWindow)
		return
	}

	if len(results) == 0 {
		dialog.ShowError(fmt.Errorf("当前页面没有题目"), guiWindow)
		return
	}

	// 创建题目选择列表
	var questionItems []string
	for i, q := range results {
		questionNum := (currentPage-1)*itemsPerPage + i + 1
		preview := q.Text
		if len([]rune(preview)) > 30 {
			preview = string([]rune(preview)[:30]) + "..."
		}
		questionItems = append(questionItems, fmt.Sprintf("%d. %s", questionNum, preview))
	}

	questionSelect := widget.NewSelect(questionItems, nil)
	if len(questionItems) > 0 {
		questionSelect.SetSelected(questionItems[0])
	}

	// 删除类型选择
	deleteTypeSelect := widget.NewSelect([]string{"软删除（可恢复）", "硬删除（不可恢复）"}, nil)
	deleteTypeSelect.SetSelected("软删除（可恢复）")

	// 删除确认函数
	confirmDelete := func() {
		if questionSelect.Selected == "" {
			return
		}

		// 解析选中的题目索引
		parts := strings.Split(questionSelect.Selected, ". ")
		if len(parts) < 2 {
			return
		}

		index, err := strconv.Atoi(parts[0])
		if err != nil {
			return
		}

		// 获取对应的题目
		questionIndex := index - 1 - (currentPage-1)*itemsPerPage
		if questionIndex < 0 || questionIndex >= len(results) {
			return
		}

		question := results[questionIndex]

		// 确认删除
		deleteType := "软删除"
		if deleteTypeSelect.Selected == "硬删除（不可恢复）" {
			deleteType = "硬删除"
		}

		dialog.ShowConfirm("确认删除",
			fmt.Sprintf("确定要%s这道题目吗？\n\n题干：%s\n\n%s",
				deleteType, question.Text,
				deleteTypeSelect.Selected),
			func(confirm bool) {
				if confirm {
					var err error

					// 根据选择执行不同类型的删除
					if deleteTypeSelect.Selected == "硬删除（不可恢复）" {
						// 硬删除
						err = db.Unscoped().Delete(&question).Error
					} else {
						// 软删除
						err = db.Delete(&question).Error
					}

					if err != nil {
						dialog.ShowError(fmt.Errorf("删除失败: %v", err), guiWindow)
						return
					}

					dialog.ShowInformation("成功", fmt.Sprintf("题目%s成功！", deleteType), guiWindow)

					// 刷新显示
					showAllQuestions()
					updateStats()
				}
			}, guiWindow)
	}

	// 显示选择对话框
	content := container.NewVBox(
		widget.NewLabel("请选择要删除的题目："),
		questionSelect,
		widget.NewLabel("删除类型："),
		deleteTypeSelect,
		widget.NewButton("删除选中题目", confirmDelete),
	)

	dialog.ShowCustom("选择题目", "关闭", content, guiWindow)
}

// 显示清空题库对话框
func showClearAllDialog() {
	// 删除类型选择
	deleteTypeSelect := widget.NewSelect([]string{"软删除（可恢复）", "硬删除（不可恢复）"}, nil)
	deleteTypeSelect.SetSelected("软删除（可恢复）")

	content := container.NewVBox(
		widget.NewLabel("⚠️ 警告：此操作将删除题库中的所有题目！"),
		widget.NewLabel("删除类型："),
		deleteTypeSelect,
		widget.NewLabel("此操作不可恢复，确定要继续吗？"),
	)

	dialog.ShowCustomConfirm("确认清空", "确定", "取消", content, func(confirm bool) {
		if confirm {
			// 再次确认
			deleteType := "软删除"
			if deleteTypeSelect.Selected == "硬删除（不可恢复）" {
				deleteType = "硬删除"
			}

			dialog.ShowConfirm("最终确认",
				fmt.Sprintf("🚨 最终警告：即将%s所有题目！\n\n请输入 'DELETE' 确认：", deleteType),
				func(finalConfirm bool) {
					if finalConfirm {
						var err error

						// 根据选择执行不同类型的删除
						if deleteTypeSelect.Selected == "硬删除（不可恢复）" {
							// 硬删除
							err = db.Session(&gorm.Session{AllowGlobalUpdate: true}).Unscoped().Delete(&Question{}).Error
						} else {
							// 软删除
							err = db.Session(&gorm.Session{AllowGlobalUpdate: true}).Delete(&Question{}).Error
						}

						if err != nil {
							dialog.ShowError(fmt.Errorf("清空失败: %v", err), guiWindow)
							return
						}

						dialog.ShowInformation("成功", fmt.Sprintf("题库已%s！", deleteType), guiWindow)

						// 刷新显示
						showAllQuestions()
						updateStats()
					}
				}, guiWindow)
		}
	}, guiWindow)
}
