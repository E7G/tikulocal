# 项目结构说明

本文档详细说明了题库管理系统 (TikuLocal) 的项目结构和文件组织。

## 📁 目录结构

```
tikulocal/
├── 📄 README.md                 # 项目主文档
├── 📄 CHANGELOG.md              # 详细变更日志
├── 📄 main.go                   # 主程序源码
├── 📄 go.mod                    # Go模块定义
├── 📄 go.sum                    # Go依赖校验
├── 📄 LICENSE                   # 开源许可证
├── 📄 .gitignore                # Git忽略文件
├── 📄 .gitattributes            # Git属性配置
├── 🖼️ icon.png                  # 应用图标
├── 💾 tiku.db                   # SQLite数据库文件
├── 🚀 tikulocal.exe             # 编译后的可执行文件
├── 📁 fonts/                    # 字体文件目录
│   ├── 📄 NotoSansCJKsc-Regular.otf  # 中文字体文件
│   └── 📄 README.md             # 字体说明
├── 📁 docs/                     # 开发文档目录
│   ├── 📄 README.md             # 文档索引
│   ├── 📄 API.md                # API接口文档
│   ├── 📄 FONT_CONFIG.md        # 字体配置说明
│   ├── 📄 DISPLAY_IMPROVEMENT.md # 界面优化说明
│   ├── 📄 DRAG_DROP_FIX.md      # 拖放功能说明
│   ├── 📄 OPTIMIZATION.md       # 代码优化总结
│   ├── 📄 PROJECT_STRUCTURE.md  # 项目结构说明（本文档）
│   ├── 📄 test_cards.md         # 卡片显示测试
│   ├── 📄 test_drag_drop.md     # 拖放功能测试
│   └── 📄 test_font.md          # 字体功能测试
├── 📁 test/                     # 测试文件目录
│   ├── 📄 run_tests.bat         # Windows测试运行脚本
│   ├── 📄 test_parser.go        # 解析器功能测试
│   └── 📄 verify_fix.go         # 解析器修复验证测试
├── 📁 test_embedded_font/       # 字体测试目录
```

## 📋 文件说明

### 🚀 核心文件

| 文件 | 说明 | 重要性 |
|------|------|--------|
| `main.go` | 主程序源码，包含所有功能实现 | ⭐⭐⭐⭐⭐ |
| `README.md` | 项目主文档，包含功能介绍和使用指南 | ⭐⭐⭐⭐⭐ |
| `CHANGELOG.md` | 详细变更日志，记录所有版本更新 | ⭐⭐⭐⭐ |
| `go.mod` | Go模块定义，管理依赖关系 | ⭐⭐⭐⭐ |
| `go.sum` | Go依赖校验文件 | ⭐⭐⭐ |

### 📚 文档文件

| 文件 | 说明 | 用途 |
|------|------|------|
| `docs/README.md` | 文档索引和导航 | 快速找到相关文档 |
| `docs/API.md` | API接口详细说明 | 开发者集成参考 |
| `docs/FONT_CONFIG.md` | 字体配置说明 | 中文字体支持配置 |
| `docs/DISPLAY_IMPROVEMENT.md` | 界面优化说明 | UI改进记录 |
| `docs/DRAG_DROP_FIX.md` | 拖放功能说明 | 文件拖放实现 |
| `docs/OPTIMIZATION.md` | 代码优化总结 | 性能优化记录 |
| `docs/PROJECT_STRUCTURE.md` | 项目结构说明 | 本文档 |

### 🧪 测试文件

| 文件 | 说明 | 测试内容 |
|------|------|----------|
| `test/verify_fix.go` | 解析器修复验证测试 | 验证选项解析和答案显示修复效果 |
| `test/test_parser.go` | 解析器功能测试 | 测试解析器核心功能 |
| `test/run_tests.bat` | Windows测试运行脚本 | 一键运行所有测试 |
| `docs/test_cards.md` | 卡片显示测试 | 界面显示功能 |
| `docs/test_drag_drop.md` | 拖放功能测试 | 文件拖放功能 |
| `docs/test_font.md` | 字体功能测试 | 中文字体显示 |

### 🔧 配置文件

| 文件 | 说明 | 配置内容 |
|------|------|----------|
| `.gitignore` | Git忽略文件 | 排除不需要版本控制的文件 |
| `.gitattributes` | Git属性配置 | 文件处理规则 |
| `LICENSE` | 开源许可证 | MIT许可证 |

### 📦 资源文件

| 文件 | 说明 | 用途 |
|------|------|------|
| `icon.png` | 应用图标 | GUI界面图标 |
| `fonts/NotoSansCJKsc-Regular.otf` | 中文字体 | 界面中文显示 |
| `tiku.db` | SQLite数据库 | 题目数据存储 |

## 🏗️ 代码结构

### 主要模块

```go
// 核心模块
├── 数据库操作 (GORM + SQLite)
├── GUI界面 (Fyne)
├── 文档解析 (DOCX)
├── Web API (Gin)
└── 字体支持 (自定义主题)

// 功能模块
├── 题目管理 (CRUD)
├── 搜索功能 (模糊搜索)
├── 文件拖放 (跨平台)
├── 分页显示 (高效浏览)
└── 错误处理 (统一处理)
```

### 关键函数

| 函数 | 模块 | 功能 |
|------|------|------|
| `main()` | 主程序 | 程序入口和初始化 |
| `setupGUI()` | GUI | 界面设置和布局 |
| `loadDocx()` | 文档解析 | DOCX文件解析 |
| `parseQuestions()` | 题目解析 | 题目内容提取 |
| `searchQuestionsPaginated()` | 搜索 | 分页搜索功能 |
| `saveQuestionsToDB()` | 数据库 | 题目保存 |
| `handleSearch()` | API | Web接口处理 |

## 📊 数据流

```
DOCX文件 → 解析提取 → 清洗处理 → 数据库存储
                                    ↓
用户搜索 ← 分页查询 ← 模糊匹配 ← 数据库查询
    ↓
Web API → 外部系统调用
```

## 🔄 开发流程

### 1. 功能开发
1. 在 `main.go` 中实现新功能
2. 更新相关文档
3. 添加测试用例
4. 更新 `CHANGELOG.md`

### 2. 测试验证
1. 在 `test/` 目录添加测试用例
2. 运行测试验证功能正确性
3. 检查测试结果和输出
4. 更新测试文档

### 3. 文档维护
1. 更新 `README.md` 主文档
2. 在 `docs/` 目录添加详细说明
3. 更新 `docs/README.md` 索引
4. 检查文档链接有效性

### 3. 版本发布
1. 更新版本号
2. 编译可执行文件
3. 更新 `CHANGELOG.md`
4. 创建Git标签

## 🛠️ 开发环境

### 必需工具
- Go 1.16+
- Git
- 文本编辑器 (VS Code推荐)

### 可选工具
- SQLite浏览器 (查看数据库)
- Postman (测试API)
- 字体编辑器 (修改字体)

## 📝 注意事项

### 文件命名
- 使用小写字母和下划线
- 避免中文文件名
- 保持命名一致性

### 文档规范
- 使用Markdown格式
- 添加适当的emoji图标
- 保持文档结构清晰

### 代码规范
- 遵循Go语言规范
- 添加详细注释
- 使用有意义的变量名

## 🔗 相关链接

- [主项目README](../README.md)
- [开发文档索引](README.md)
- [API接口文档](API.md)
- [变更日志](../CHANGELOG.md)