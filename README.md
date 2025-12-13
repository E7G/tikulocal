# 题库管理系统 (TikuLocal)

一个基于Rust和Axum开发的本地题库管理系统，支持题目查询、导入和管理功能。


## 功能特性

- 📄 **题目查询**: 支持多种题型的题目查询
- 📥 **题目导入**: 支持JSON格式的批量题目导入
- 📊 **题目管理**: 完整的题目增删改查功能
- 🌐 **Web界面**: 简洁直观的Web管理界面
- 💾 **本地存储**: 使用SQLite数据库存储题目数据

## 技术栈

- **后端**: Rust + Axum + SQLx
- **数据库**: SQLite
- **前端**: HTML + CSS + JavaScript (原生)

## 项目结构

详细的项目结构说明请参考: [docs/项目结构说明.md](docs/项目结构说明.md)

## 开发指南

开发指南请参考: [docs/开发指南.md](docs/开发指南.md)

## 快速开始

### 环境要求

- Rust 1.70+
- SQLite 3

### 安装依赖

```bash
cargo build
```

### 运行应用

```bash
cargo run
```

应用启动后，访问 http://localhost:8060 即可使用Web界面。

## API接口

### 搜索题目

```http
POST /adapter-service/search
Content-Type: application/json

{
  "question": "违反安全保障义务责任属于（）",
  "options": [
    "公平责任",
    "特殊侵权责任",
    "过错推定责任",
    "连带责任"
  ],
  "type": 1
}
```

### 创建题目

```http
POST /api/questions
Content-Type: application/json

{
  "question": "题目内容",
  "options": ["选项A", "选项B", "选项C", "选项D"],
  "type": 0,
  "answer": {
    "answerKey": ["A"],
    "answerKeyText": "A",
    "answerIndex": [0],
    "answerText": "选项A",
    "bestAnswer": ["选项A"],
    "allAnswer": [["选项A"]]
  }
}
```

### 导入题目

```http
POST /api/import
Content-Type: application/json

{
  "questions": [
    {
      "question": "题目内容",
      "options": ["选项A", "选项B", "选项C", "选项D"],
      "type": 0,
      "answer": {
        "answerKey": ["A"],
        "answerKeyText": "A",
        "answerIndex": [0],
        "answerText": "选项A",
        "bestAnswer": ["选项A"],
        "allAnswer": [["选项A"]]
      }
    }
  ]
}
```

### 获取所有题目

```http
GET /api/questions
```

### 删除题目

```http
DELETE /api/questions/{id}
```

### 清空所有题目

```http
DELETE /api/questions
```

## 题型说明

| 类型值 | 题型 | 描述 |
|--------|------|------|
| 0 | 单选题 | 只有一个正确答案 |
| 1 | 多选题 | 有多个正确答案 |
| 2 | 填空题 | 需要填写内容 |
| 3 | 判断题 | 正确或错误 |
| 4 | 问答題 | 开放性问答 |

## 使用说明

### 搜索题目

1. 在"搜索题目"标签页中输入题目内容
2. 选择题目类型
3. 可选填写选项
4. 点击"搜索题目"按钮

### 添加题目

1. 在"添加题目"标签页中输入题目内容
2. 选择题目类型
3. 根据题型添加选项（选择题需要）
4. 输入答案
5. 点击"添加题目"按钮

### 导入题目

1. 在"导入题目"标签页中拖放JSON文件或点击选择文件
2. 预览导入内容
3. 点击"导入题目"按钮

### 管理题目

1. 在"管理题目"标签页中查看所有题目
2. 查看题目统计信息
3. 可以删除单个题目或清空所有题目

## 示例文件

项目提供了一个示例JSON文件 `static/sample_questions.json`，包含了各种题型的示例题目，可以用于测试导入功能。

## 数据库

应用使用SQLite数据库存储题目数据，数据库文件为 `questions.db`，会在首次运行时自动创建。

## 许可证

MIT License