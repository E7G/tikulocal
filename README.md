# 题库适配器 - 本地版

基于 PyQt5、qfluentwidgets 和 SQLite 构建的本地题库管理工具，适合整理、检索和向兼容平台提供题库答案。

## 功能特性

- **导入首页**：启动后直接进入题库导入页面，不必先切换导航。
- **批量导入**：支持一次选择多个 Word / JSON 文件，也支持拖拽文件到清单。
- **导入前检查**：拖入文件只会加入待导入清单，不会未经确认就立即写入题库。
- **清晰的导入反馈**：逐个显示文件导入数量、失败原因；失败或未识别的文件会保留在清单中，便于检查和重试。
- **灵活搜索**：支持按题目类型筛选、忽略常见标点和空格，并优先显示匹配程度更高的结果。
- **题库管理**：查看最近导入的题目、多选删除、清空题库前确认，并查看题目数量统计。
- **本地存储**：题库数据保存在 SQLite 数据库中。
- **兼容 API**：提供 RESTful API，兼容 tikuAdapter 格式。
- **自动发布**：支持 GitHub Actions 打包发布。

## 技术栈

- Python 3.10+
- PyQt5 + qfluentwidgets
- SQLite
- python-docx
- Flask
- PyInstaller

## 快速开始

### 使用 pixi（推荐）

~~~bash
pixi run start
~~~

### 使用 pip

~~~bash
pip install -r requirements.txt
python main.py
~~~

## 使用说明

### 1. 导入题库（首页）

支持 .docx 和 .json 文件。

1. 点击“选择文件（可多选）”，或把文件直接拖到文件清单中。
2. 检查待导入清单；不需要的文件可以移除，也可以清空整个清单。
3. 点击“导入全部文件”。
4. 在“导入结果”中查看每个文件导入的题目数量和失败原因。失败或没有识别到题目的文件会保留在清单中，方便检查后重试。

重复添加同一路径的文件不会在待导入清单中重复显示。导入操作会根据扩展名自动识别文件格式。

### 只保存正确答案（兼容超星 / 优学院 / 长江雨课堂导出器）

本项目的 Word 解析器针对
[E7G/chaoxing_ulearning_Answer_to_Word](https://github.com/E7G/chaoxing_ulearning_Answer_to_Word)
实际导出结构进行了适配，支持题号与题型标识、常见选项标号、手动换行、正确答案位于单独段落、题目解析和图片所在段落等情况。

**导入判定原则：**

- 只接受导出文档中明确标注的「正确答案」、「标准答案」或「参考答案」。
- 「我的答案」、「答案状态：正确」、「得分」不能作为正确答案来源；即使我的答案碰巧是正确的，没有明确公布标准答案也会跳过。
- 有明确正确答案的题目，即使个人答错，也会保留**标准正确答案**，而非作答记录。
- 选择题将答案 B、B. 选项内容、A、C 等统一为选项字母；遇到仅有选项正文的情况，只有能准确对应到已解析选项时才转换。
- 无答案、暂无、答案不完整或无法对应选项的选择题会被跳过，不猜测正确答案。
- 导入结果展示每个 Word 文件成功导入及跳过的数量。

**导出器自身的数据限制：**当前版本的优学院导出流程有些页面只记录「我的答案」，没有提供正确答案。这样的文档不能凭作答记录推断正确答案，会安全地跳过这些题目。文档内纯图片题干或纯图片答案也不能作为可搜索文本完整保存；有正文文本的题目仍可按文本导入。

### 2. JSON 格式

可以直接使用题目数组：

~~~json
[
  {
    "question": "题目内容",
    "options": ["选项 A", "选项 B"],
    "type": 0,
    "answer": "A"
  }
]
~~~

也可以使用包含 questions 数组的对象：

~~~json
{
  "questions": [
    {
      "question": "题目内容",
      "options": ["选项 A", "选项 B"],
      "type": 0,
      "answer": "A"
    }
  ]
}
~~~

字段说明：

| 字段 | 说明 |
| --- | --- |
| question | 题目内容，也可使用 content |
| options | 选项数组；没有选项时可为空数组 |
| type | 题型编号：0 单选、1 多选、2 填空、3 判断、4 问答 |
| answer | 正确答案，必填 |

缺少题目内容或正确答案的记录会被跳过。导入时会同时生成搜索字段，确保 JSON 导入的题目也能被桌面端搜索。

### 3. 搜索题目

- 输入题目中的几个关键词即可搜索，也可以按 Enter 开始。
- 可按单选、多选、填空、判断或问答题筛选。
- 搜索会忽略常见标点和空白，并优先显示匹配度较高的题目。
- 没有结果时，页面会给出缩短关键词、检查题型和确认导入状态等建议。

### 4. 题库管理

- 统计卡片显示题目总数及单选、多选和判断题数量。
- 列表默认显示最近 100 道题目，可按题目、题型、选项或答案关键词即时筛选。
- 点击一行选择题目；按住 Ctrl 或 Shift 可多选，然后点击“删除选中”。
- 删除和清空前会显示确认提示，避免误操作。

## API 接口

HTTP 服务器默认监听 localhost:8060。

### POST /adapter-service/search

搜索题目：

~~~bash
curl -X POST http://localhost:8060/adapter-service/search \
  -H "Content-Type: application/json" \
  -d '{"question":"毛泽东思想","options":[],"type":0}'
~~~

响应示例：

~~~json
{
  "plat": 0,
  "question": "题目内容",
  "options": ["选项 A", "选项 B"],
  "type": 0,
  "answer": {
    "answerKey": ["A"],
    "answerKeyText": "A",
    "answerIndex": [0],
    "answerText": "选项 A",
    "bestAnswer": ["选项 A"],
    "allAnswer": [["选项 A"]]
  }
}
~~~

其他接口：

- GET /：健康检查页面。
- GET /adapter-service：适配器状态。
- HEAD /adapter-service/search：心跳检测。

## 开发与测试

运行题目解析器回归测试：

~~~bash
python -m unittest discover -s tests -v
~~~

使用 PyInstaller 打包：

~~~bash
pip install pyinstaller
pyinstaller tikulocal.spec
~~~

推送 v* 标签可触发自动发布：

~~~bash
git tag v1.0.0
git push origin v1.0.0
~~~

## 项目结构

~~~text
tikulocal/
├── main.py
├── parser.py
├── tests/
│   └── test_parser.py
├── requirements.txt
├── pixi.toml
├── tikulocal.spec
├── icon.png
└── README.md
~~~

## License

MIT License
