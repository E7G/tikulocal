# 题库查询API接口文档

## 接口概述

本接口用于查询本地题库中的题目答案，支持多种题型的查询。

## 接口信息

- **接口地址**: `POST http://localhost:8060/adapter-service/search`
- **请求方法**: POST
- **内容类型**: application/json
- **数据格式**: JSON

## 请求参数

### URL参数

| 参数名 | 类型 | 是否必须 | 描述 | 示例值 |
|--------|------|----------|------|--------|
| use | string | 否 | 指定使用的题库，本接口仅支持local | local |

### 请求体参数

| 参数名 | 类型 | 是否必须 | 描述 | 示例值 |
|--------|------|----------|------|--------|
| question | string | 是 | 题目内容 | "违反安全保障义务责任属于（）" |
| options | array | 否 | 选项列表 | ["公平责任", "特殊侵权责任", "过错推定责任", "连带责任"] |
| type | integer | 是 | 题目类型：0-单选，1-多选，2-填空，3-判断，4-问答 | 1 |

## 请求示例

```bash
curl -X POST "http://localhost:8060/adapter-service/search?use=local" \
-H "Content-Type: application/json" \
-d '{
  "question": "违反安全保障义务责任属于（）",
  "options": [
    "公平责任",
    "特殊侵权责任",
    "过错推定责任",
    "连带责任"
  ],
  "type": 1
}'
```

## 响应参数

| 参数名 | 类型 | 描述 |
|--------|------|------|
| plat | integer | 平台标识 |
| question | string | 题目内容 |
| options | array | 选项列表 |
| type | integer | 题目类型 |
| answer | object | 答案信息 |
| answer.answerKey | array | 答案选项字母，如["B", "C"] |
| answer.answerKeyText | string | 答案选项字母组合，如"BC" |
| answer.answerIndex | array | 答案选项索引，如[1, 2] |
| answer.answerText | string | 答案文本，以"#"分隔，如"特殊侵权责任#过错推定责任" |
| answer.bestAnswer | array | 最佳答案列表 |
| answer.allAnswer | array | 所有可能答案组合 |

## 响应示例

```json
{
  "plat": 0,
  "question": "违反安全保障义务责任属于（）",
  "options": [
    "公平责任",
    "特殊侵权责任",
    "过错推定责任",
    "连带责任"
  ],
  "type": 1,
  "answer": {
    "answerKey": [
      "B",
      "C"
    ],
    "answerKeyText": "BC",
    "answerIndex": [
      1,
      2
    ],
    "answerText": "特殊侵权责任#过错推定责任",
    "bestAnswer": [
      "特殊侵权责任",
      "过错推定责任"
    ],
    "allAnswer": [
      [
        "特殊侵权责任",
        "过错推定责任"
      ],
      [
        "A特殊侵权责任",
        "B过错推定责任"
      ]
    ]
  }
}
```

## 题型说明

| 类型值 | 题型 | 描述 |
|--------|------|------|
| 0 | 单选题 | 只有一个正确答案 |
| 1 | 多选题 | 有多个正确答案 |
| 2 | 填空题 | 需要填写内容 |
| 3 | 判断题 | 正确或错误 |
| 4 | 问答題 | 开放性问答 |

## 错误码说明

| 错误码 | 描述 |
|--------|------|
| 400 | 请求参数错误 |
| 404 | 题目未找到 |
| 500 | 服务器内部错误 |

## 注意事项

1. 本接口仅使用本地题库，不需要提供任何Token
2. 请求参数中的question和type为必填项
3. options参数对于选择题是必需的，对于填空题和问答题可以省略
4. 答案格式会根据题型有所不同，请根据实际题型解析响应数据