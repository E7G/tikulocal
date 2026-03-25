# 题库适配器 - 本地版

基于 PyQt5 和 qfluentwidgets 构建的现代化本地题库管理系统。

## 功能特性

- **现代化 UI**：采用 Fluent Design 设计，支持浅色/深色主题跟随系统设置
- **搜索题目**：支持模糊搜索，自动去除标点和空格进行匹配
- **导入题库**：支持拖拽导入单个或批量 Word/JSON 文件
- **题库管理**：查看、删除和清空本地题库
- **HTTP API**：提供 RESTful API 接口，兼容 tikuAdapter 格式
- **自动发布**：支持 GitHub Actions 一键打包发布

## 技术栈

- Python 3.10+
- PyQt5 + qfluentwidgets（Fluent Design UI）
- SQLite（本地数据库）
- python-docx（Word 文档解析）
- PyInstaller（打包发布）

## 快速开始

### 使用 pixi（推荐）

```bash
pixi run start
```

### 使用 pip

```bash
pip install -r requirements.txt
python main.py
```

## 功能介绍

### 1. 导入题库

支持两种导入方式：

**Word 文档导入**：
- 支持拖拽文件到导入区域
- 支持批量拖入多个文件
- 自动识别文件类型（.docx 或 .json）

**JSON 文件导入**：
```json
[
  {
    "question": "题目内容",
    "options": ["A. 选项 A", "B. 选项 B"],
    "type": 0,
    "answer": "A"
  }
]
```

### 2. 搜索题目

- 支持模糊搜索
- 自动去除标点符号和空格进行匹配
- 支持按题目类型筛选
- 返回标准 JSON 格式结果

### 3. 题库管理

- 统计面板显示各类题目数量
- 支持选中删除和清空题库
- 列表显示题目详情（内容、类型、选项、答案）

## API 接口

HTTP 服务器监听端口 8060，提供以下接口：

### POST /adapter-service/search

搜索题目：

```bash
curl -X POST http://localhost:8060/adapter-service/search \
  -H "Content-Type: application/json" \
  -d '{"question": "毛泽东思想", "options": [], "type": 0}'
```

响应格式：
```json
{
  "plat": 0,
  "question": "题目内容",
  "options": ["A. 选项 A", "B. 选项 B"],
  "type": 0,
  "answer": {
    "answerKey": ["A"],
    "answerKeyText": "A",
    "answerIndex": [0],
    "answerText": "A. 选项 A",
    "bestAnswer": ["A. 选项 A"],
    "allAnswer": [["A. 选项 A"]]
  }
}
```

### GET /

健康检查接口。

### HEAD /adapter-service/search

心跳检测接口。

## Word 文档格式

```
1  【单选题】
毛泽东思想初步形成于（     ）
A. 土地革命战争时期
B. 抗日战争时期
C. 解放战争时期
D. 中华人民共和国成立后
正确答案：B
我的答案：B
答案状态：正确
得分：5

2  【多选题】
下列属于毛泽东思想组成部分的是（     ）
A. 新民主主义革命理论
B. 社会主义改造理论
C. 改革开放理论
D. 社会主义初级阶段理论
正确答案：AB
我的答案：AB
答案状态：正确
得分：10
```

## 数据库结构

SQLite 数据库 `tiku.db`，包含以下字段：

| 字段 | 说明 |
|------|------|
| id | 主键 |
| question | 原始题目 |
| options | 选项（JSON 格式） |
| type | 题目类型（0-4） |
| answer | 答案 |
| search_question | 搜索用题目（去标点） |
| search_options | 搜索用选项（去标点） |
| created_at | 创建时间 |

## 打包发布

使用 PyInstaller 打包：

```bash
pip install pyinstaller
pyinstaller tikulocal.spec
```

或使用 GitHub Actions 自动发布（推送 v* 标签触发）：

```bash
git tag v1.0.0
git push origin v1.0.0
```

## 项目结构

```
tikulocal/
├── main.py              # 主程序入口
├── parser.py            # Word 文档解析器
├── requirements.txt      # Python 依赖
├── pixi.toml            # pixi 配置
├── tikulocal.spec       # PyInstaller 配置
├── icon.png             # 应用图标
├── README.md            # 说明文档
└── .github/
    └── workflows/
        └── release.yml  # GitHub Actions 发布流程
```

## License

MIT License
