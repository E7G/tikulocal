# tikulocal
 一个简易的本地题库程序，为一些脚本提供本地的题库api替代。

# 别名-题库管理系统 (TikuLocal)

这是一个功能强大的题库管理系统，能够解析DOCX文档中的题目、存储到SQLite数据库、提供图形化管理界面（GUI）以及Web搜索API服务。系统内置高效的题目匹配算法，支持多种题型识别和智能搜索。

## 功能特点

- **智能文档解析**：自动识别Word文档中的题目、选项和答案
- **题库管理**：图形化界面管理所有题目（增删查改）
- **高效搜索**：模糊匹配题目内容，支持中文检索
- **Web服务API**：提供HTTP接口供外部应用查询题库
- **跨平台支持**：可在Windows、macOS和Linux上运行
- **数据持久化**：使用SQLite数据库存储题库内容
- **拖放支持**：轻松导入DOCX文档（bug）

## 安装与运行

### 前提条件
- Go 1.20+ 环境
- SQLite 3

### 安装步骤
```bash
# 克隆仓库
git clone https://github.com/E7G/tikulocal.git
cd tikulocal

# 安装依赖
go mod tidy

# 构建项目
go build .

# 生成可执行文件
go install fyne.io/tools/cmd/fyne@latest
fyne package -os windows -icon icon.png

```

### 运行程序
windows下直接运行可执行文件即可，或者
```bash
# 运行图形化管理界面
./tikulocal
```

## 使用说明

### GUI界面操作
1. **导入题目**：点击"选择文件"按钮或拖放DOCX文件到输入框
2. **解析文档**：点击"解析文件"按钮导入题目到数据库
3. **搜索题目**：在搜索框输入题目内容，点击"搜索题目"
4. **题库浏览**：默认显示数据库中所有题目

### Web服务API
程序启动后会在`8060`端口提供Web服务：

```bash
# 启动服务后访问
http://localhost:8060
```

#### 搜索端点
`POST /adapter-service/search`

**请求示例**：
```json
{
  "question": "计算机的核心部件是什么？",
  "options": ["CPU", "GPU", "内存", "硬盘"],
  "type": 0
}
```

**响应示例**：
```json
{
  "plat": 0,
  "question": "计算机的核心部件是什么",
  "options": ["CPU", "GPU", "内存", "硬盘"],
  "type": 0,
  "answer": {
    "answerKey": ["A"],
    "answerKeyText": "A",
    "answerIndex": [0],
    "answerText": "CPU",
    "bestAnswer": ["CPU"],
    "allAnswer": [
      ["CPU"],
      ["A、CPU"]
    ]
  }
}
```

## 技术支持

### 支持的DOCX格式
```
【单选题】计算机的核心部件是什么？
A、CPU
B、GPU
C、内存
D、硬盘
正确答案：A

【判断题】Go语言是Google开发的？
正确答案：对
```

### 常见问题
1. **中文支持问题**：确保系统使用UTF-8编码
2. **DOCX解析失败**：检查文档格式是否符合标准模板
3. **数据库位置**：程序会在当前目录创建`tiku.db`文件
4. **端口冲突**：修改代码中的`port := ":8060"`更换端口

## 贡献

欢迎提交Issue和Pull Request：
1. Fork项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开Pull Request

## 许可证

本项目采用 MIT 许可证 - 详情请参阅 [LICENSE](LICENSE) 文件。

---
**提示**：首次运行时，程序会自动创建SQLite数据库文件。导入题目后，可以通过Web API接口查询题库内容。