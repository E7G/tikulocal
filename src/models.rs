use serde::{Deserialize, Serialize};

// 题目类型枚举
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum QuestionType {
    #[serde(rename = "0")]
    SingleChoice,    // 单选题
    #[serde(rename = "1")]
    MultipleChoice,  // 多选题
    #[serde(rename = "2")]
    FillBlank,       // 填空题
    #[serde(rename = "3")]
    TrueFalse,       // 判断题
    #[serde(rename = "4")]
    Essay,           // 问答题
}

impl From<i32> for QuestionType {
    fn from(value: i32) -> Self {
        match value {
            0 => QuestionType::SingleChoice,
            1 => QuestionType::MultipleChoice,
            2 => QuestionType::FillBlank,
            3 => QuestionType::TrueFalse,
            4 => QuestionType::Essay,
            _ => QuestionType::SingleChoice, // 默认为单选题
        }
    }
}

impl From<QuestionType> for i32 {
    fn from(question_type: QuestionType) -> Self {
        match question_type {
            QuestionType::SingleChoice => 0,
            QuestionType::MultipleChoice => 1,
            QuestionType::FillBlank => 2,
            QuestionType::TrueFalse => 3,
            QuestionType::Essay => 4,
        }
    }
}

// 题目模型
#[derive(Debug, Clone, Serialize, Deserialize, sqlx::FromRow)]
pub struct Question {
    pub id: Option<i64>,
    pub question: String,
    pub options: Option<String>,
    #[serde(rename = "type")]
    pub question_type: i32,
    pub answer: String,
}

// 搜索请求
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchRequest {
    pub question: String,
    pub options: Option<Vec<String>>,
    #[serde(rename = "type")]
    pub question_type: i32,
}

// 搜索响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResponse {
    pub plat: i32,
    pub question: String,
    pub options: Option<Vec<String>>,
    #[serde(rename = "type")]
    pub question_type: i32,
    pub answer: Answer,
}

// 创建题目请求
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateQuestionRequest {
    pub question: String,
    pub options: Option<Vec<String>>,
    #[serde(rename = "type")]
    pub question_type: i32,
    pub answer: Answer,
}

// 创建题目响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateQuestionResponse {
    pub code: i32,
    pub data: CreateQuestionData,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateQuestionData {
    pub msg: String,
    pub success: bool,
    pub data: i64,
}

// 获取所有题目响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GetAllQuestionsResponse {
    pub code: i32,
    pub data: GetAllQuestionsData,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GetAllQuestionsData {
    pub msg: String,
    pub success: bool,
    pub data: Vec<QuestionResponse>,
}

// 题目响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QuestionResponse {
    pub id: Option<i64>,
    pub question: String,
    pub options: Option<Vec<String>>,
    #[serde(rename = "type")]
    pub question_type: i32,
    pub answer: Answer,
}

// 导入题目请求
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ImportQuestionsRequest {
    pub questions: Vec<CreateQuestionRequest>,
}

// 导入题目响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ImportQuestionsResponse {
    pub code: i32,
    pub data: ImportQuestionsData,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ImportQuestionsData {
    pub msg: String,
    pub success: bool,
    pub data: ImportResult,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ImportResult {
    pub success_count: i32,
    pub failed_count: i32,
    pub errors: Option<Vec<String>>,
}

// 删除题目响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeleteQuestionResponse {
    pub code: i32,
    pub data: DeleteQuestionData,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeleteQuestionData {
    pub msg: String,
    pub success: bool,
    pub data: (),
}

// 清空题目响应
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClearQuestionsResponse {
    pub code: i32,
    pub data: ClearQuestionsData,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClearQuestionsData {
    pub msg: String,
    pub success: bool,
    pub data: (),
}

// 答案模型
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct Answer {
    #[serde(rename = "answerKey")]
    pub answer_key: Option<Vec<String>>,
    #[serde(rename = "answerKeyText")]
    pub answer_key_text: Option<String>,
    #[serde(rename = "answerIndex")]
    pub answer_index: Option<Vec<i32>>,
    #[serde(rename = "answerText")]
    pub answer_text: Option<String>,
    #[serde(rename = "bestAnswer")]
    pub best_answer: Option<Vec<String>>,
    #[serde(rename = "allAnswer")]
    pub all_answer: Option<Vec<Vec<String>>>,
}