# API 文档

题库管理系统 (TikuLocal) 提供RESTful API接口，支持外部系统调用。

## 🌐 基础信息

- **服务地址**: `http://localhost:8060`
- **协议**: HTTP/HTTPS
- **数据格式**: JSON
- **字符编码**: UTF-8

## 📋 接口列表

### 1. 健康检查

#### GET /
检查服务状态

**请求示例**:
```bash
curl -X GET http://localhost:8060/
```

**响应示例**:
```json
{
  "status": "running",
  "version": "1.2.5",
  "docs": "/adapter-service/search"
}
```

#### HEAD /
检查服务状态（轻量级）

**请求示例**:
```bash
curl -I http://localhost:8060/
```

**响应示例**:
```http
HTTP/1.1 200 OK
Content-Type: application/json
```

### 2. 题目搜索

#### POST /adapter-service/search
搜索题目并返回答案

**请求参数**:
```json
{
  "question": "题目内容",
  "options": ["选项A", "选项B", "选项C", "选项D"],
  "type": 0
}
```

**参数说明**:
- `question` (string, 必需): 题目内容
- `options` (array, 可选): 选项列表
- `type` (integer, 必需): 题目类型
  - `0`: 单选题
  - `1`: 多选题
  - `2`: 判断题
  - `3`: 填空题
  - `4`: 简答题

**请求示例**:
```bash
curl -X POST http://localhost:8060/adapter-service/search \
  -H "Content-Type: application/json" \
  -d '{
    "question": "下列哪个是Go语言的特点？",
    "options": ["编译型语言", "解释型语言", "脚本语言", "标记语言"],
    "type": 0
  }'
```

**成功响应** (200):
```json
{
  "plat": 0,
  "question": "下列哪个是Go语言的特点？",
  "options": ["编译型语言", "解释型语言", "脚本语言", "标记语言"],
  "type": 0,
  "answer": {
    "answerKey": ["A"],
    "answerKeyText": "A",
    "answerIndex": [0],
    "answerText": "编译型语言",
    "bestAnswer": ["编译型语言"],
    "allAnswer": [
      ["编译型语言"],
      ["A、编译型语言"]
    ]
  }
}
```

**错误响应** (400):
```json
{
  "error": "题目内容不能为空"
}
```

**错误响应** (404):
```json
{
  "error": "未找到相关问题"
}
```

**错误响应** (500):
```json
{
  "error": "数据库查询失败"
}
```

### 3. CORS 支持

所有接口都支持CORS，允许跨域请求：

**预检请求** (OPTIONS):
```bash
curl -X OPTIONS http://localhost:8060/adapter-service/search \
  -H "Origin: http://example.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type"
```

**CORS 头信息**:
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Origin, Content-Type, Authorization, Accept
Access-Control-Allow-Credentials: true
Access-Control-Max-Age: 43200
```

## 🔧 错误处理

### HTTP 状态码

- `200`: 请求成功
- `400`: 请求参数错误
- `404`: 资源未找到
- `500`: 服务器内部错误

### 错误响应格式

所有错误响应都使用统一的JSON格式：

```json
{
  "error": "错误描述信息"
}
```

## 📊 响应字段说明

### 搜索接口响应字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `plat` | integer | 平台标识，固定为0 |
| `question` | string | 题目内容 |
| `options` | array | 选项列表 |
| `type` | integer | 题目类型 |
| `answer.answerKey` | array | 答案键值（A、B、C、D等） |
| `answer.answerKeyText` | string | 答案键值文本 |
| `answer.answerIndex` | array | 答案索引（0、1、2、3等） |
| `answer.answerText` | string | 答案文本 |
| `answer.bestAnswer` | array | 最佳答案 |
| `answer.allAnswer` | array | 所有答案格式 |

## 🚀 使用示例

### JavaScript 示例

```javascript
// 搜索题目
async function searchQuestion(question, options, type) {
  try {
    const response = await fetch('http://localhost:8060/adapter-service/search', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question: question,
        options: options,
        type: type
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('搜索失败:', error);
    throw error;
  }
}

// 使用示例
searchQuestion(
  "下列哪个是Go语言的特点？",
  ["编译型语言", "解释型语言", "脚本语言", "标记语言"],
  0
).then(result => {
  console.log('答案:', result.answer.bestAnswer);
}).catch(error => {
  console.error('错误:', error);
});
```

### Python 示例

```python
import requests
import json

def search_question(question, options, question_type):
    url = "http://localhost:8060/adapter-service/search"
    data = {
        "question": question,
        "options": options,
        "type": question_type
    }
    
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None

# 使用示例
result = search_question(
    "下列哪个是Go语言的特点？",
    ["编译型语言", "解释型语言", "脚本语言", "标记语言"],
    0
)

if result:
    print("答案:", result["answer"]["bestAnswer"])
```

## 🔒 安全说明

### 输入验证
- 所有输入参数都会进行验证
- 题目内容长度限制为100个字符
- 选项数量建议不超过26个（A-Z）

### 错误信息
- 错误信息不会泄露敏感信息
- 详细的错误日志仅记录在服务器端

## 📝 注意事项

1. **服务启动**: 确保题库管理系统已启动并监听8060端口
2. **数据准备**: 确保题库中已导入相关题目
3. **网络连接**: 确保客户端能够访问服务地址
4. **字符编码**: 所有请求和响应都使用UTF-8编码

## 🔗 相关链接

- [主项目README](../README.md)
- [使用指南](../README.md#使用指南)
- [更新日志](../CHANGELOG.md) 