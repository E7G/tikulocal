use axum::{
    extract::{Path, State},
    http::StatusCode,
    response::Json,
};
use sqlx::SqlitePool;
use tracing::{error, info};

use crate::models::{
    CreateQuestionRequest, CreateQuestionResponse, CreateQuestionData,
    GetAllQuestionsResponse, GetAllQuestionsData, QuestionResponse,
    ImportQuestionsRequest, ImportQuestionsResponse, ImportQuestionsData, ImportResult,
    DeleteQuestionResponse, DeleteQuestionData,
    ClearQuestionsResponse, ClearQuestionsData,
    SearchRequest, SearchResponse,
    Question, Answer
};
use crate::db::QuestionService;

// 创建路由
pub fn create_routes() -> axum::Router<SqlitePool> {
    axum::Router::new()
        .route("/", axum::routing::get(home))
        .route("/api/search", axum::routing::post(search_questions))
        .route("/adapter-service/search", axum::routing::post(adapter_search_questions)) // 添加适配器端点
        .route("/api/questions", axum::routing::post(create_question))
        .route("/api/questions", axum::routing::get(get_all_questions))
        .route("/api/import", axum::routing::post(import_questions))
        // 添加前端需要的路由 - 修复404错误
        .route("/questions", axum::routing::get(get_all_questions))
        .route("/questions/import", axum::routing::post(import_questions))
        .route("/api/questions/:id", axum::routing::delete(delete_question))
        .route("/api/questions", axum::routing::delete(clear_questions))
}

// 首页处理函数
async fn home() -> axum::response::Html<&'static str> {
    axum::response::Html(include_str!("../static/index.html"))
}

// 统一的搜索逻辑 - 消除重复代码
async fn perform_search(service: &QuestionService, keyword: &str) -> Result<Option<Question>, StatusCode> {
    let questions = service.search_questions(keyword).await
        .map_err(|e| {
            error!("搜索题目失败: {}", e);
            StatusCode::INTERNAL_SERVER_ERROR
        })?;
    
    Ok(questions.into_iter().next())
}

// 构建响应 - 消除重复代码
fn build_search_response(question: &Question) -> serde_json::Value {
    let options_data = question.options.as_ref()
        .and_then(|s| serde_json::from_str::<Vec<String>>(s).ok());
    
    let answer: Answer = serde_json::from_str(&question.answer).unwrap_or_default();
    
    serde_json::json!({
        "question": question.question,
        "type": question.question_type,
        "options": options_data,
        "answer": {
            "bestAnswer": answer.best_answer.unwrap_or_default(),
            "answerText": answer.answer_text.unwrap_or_default(),
            "answerKey": answer.answer_key.unwrap_or_default(),
            "answerKeyText": answer.answer_key_text.unwrap_or_default(),
            "answerIndex": answer.answer_index.unwrap_or_default(),
            "allAnswer": answer.all_answer.unwrap_or_default()
        }
    })
}

// 适配器搜索 - 为前端提供兼容的搜索接口
pub async fn adapter_search_questions(
    State(pool): State<SqlitePool>,
    body: String,
) -> Result<Json<serde_json::Value>, StatusCode> {
    info!("适配器搜索题目");

    // 宽容地解析JSON
    let request: serde_json::Value = serde_json::from_str(&body).map_err(|e| {
        error!("解析JSON失败: {}", e);
        StatusCode::BAD_REQUEST
    })?;

    let question = request.get("question")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    if question.is_empty() {
        return Ok(Json(serde_json::json!({
            "error": "题目内容不能为空"
        })));
    }

    let service = QuestionService::new(pool);
    match perform_search(&service, &question).await? {
        Some(q) => Ok(Json(build_search_response(&q))),
        None => Ok(Json(serde_json::json!({
            "error": "没有找到匹配的题目"
        })))
    }
}

// 搜索题目 - 使用统一搜索逻辑
pub async fn search_questions(
    State(pool): State<SqlitePool>,
    Json(request): Json<SearchRequest>,
) -> Result<Json<SearchResponse>, StatusCode> {
    info!("搜索题目: {}", request.question);

    let service = QuestionService::new(pool);
    match perform_search(&service, &request.question).await? {
        Some(q) => {
            let options = q.options.as_ref()
                .and_then(|s| serde_json::from_str::<Vec<String>>(s).ok());
            let answer: Answer = serde_json::from_str(&q.answer).unwrap_or_default();

            let response = SearchResponse {
                plat: 1,
                question: q.question,
                options,
                question_type: q.question_type,
                answer,
            };

            Ok(Json(response))
        },
        None => Err(StatusCode::NOT_FOUND)
    }
}

// 创建题目 - 使用业务逻辑层
pub async fn create_question(
    State(pool): State<SqlitePool>,
    Json(request): Json<CreateQuestionRequest>,
) -> Result<Json<CreateQuestionResponse>, StatusCode> {
    info!("创建题目: {}", request.question);

    let service = QuestionService::new(pool);
    let id = service.create_question(&request.question, request.options, request.question_type, &request.answer)
        .await
        .map_err(|e| {
            error!("创建题目失败: {}", e);
            StatusCode::INTERNAL_SERVER_ERROR
        })?;

    let response = CreateQuestionResponse {
        code: 200,
        data: CreateQuestionData {
            msg: "题目创建成功".to_string(),
            success: true,
            data: id,
        },
    };

    Ok(Json(response))
}

// 统一的题目转换函数 - 消除重复代码
fn convert_question_to_response(question: &Question) -> QuestionResponse {
    let options = question.options.as_ref()
        .and_then(|s| serde_json::from_str::<Vec<String>>(s).ok());
    let answer: Answer = serde_json::from_str(&question.answer).unwrap_or_default();
    
    QuestionResponse {
        id: question.id,
        question: question.question.clone(),
        options,
        question_type: question.question_type,
        answer,
    }
}

// 获取所有题目 - 使用业务逻辑层
pub async fn get_all_questions(
    State(pool): State<SqlitePool>,
) -> Result<Json<GetAllQuestionsResponse>, StatusCode> {
    info!("获取所有题目");

    let service = QuestionService::new(pool);
    let questions = service.get_all_questions().await
        .map_err(|e| {
            error!("获取所有题目失败: {}", e);
            StatusCode::INTERNAL_SERVER_ERROR
        })?;

    let question_responses: Vec<QuestionResponse> = questions
        .iter()
        .map(convert_question_to_response)
        .collect();

    let response = GetAllQuestionsResponse {
        code: 200,
        data: GetAllQuestionsData {
            msg: "获取所有题目成功".to_string(),
            success: true,
            data: question_responses,
        },
    };

    Ok(Json(response))
}

// 导入题目 - 使用业务逻辑层
pub async fn import_questions(
    State(pool): State<SqlitePool>,
    Json(request): Json<ImportQuestionsRequest>,
) -> Result<Json<ImportQuestionsResponse>, StatusCode> {
    info!("导入题目: {} 道题", request.questions.len());

    let service = QuestionService::new(pool);
    let mut success_count = 0;
    let mut failed_count = 0;
    let mut errors = Vec::new();

    for (index, question_request) in request.questions.into_iter().enumerate() {
        match service.create_question(
            &question_request.question,
            question_request.options,
            question_request.question_type,
            &question_request.answer
        ).await {
            Ok(_) => success_count += 1,
            Err(e) => {
                let error_msg = format!("题目 {} 导入失败: {}", index + 1, e);
                error!("{}", error_msg);
                errors.push(error_msg);
                failed_count += 1;
            }
        }
    }

    let response = ImportQuestionsResponse {
        code: 200,
        data: ImportQuestionsData {
            msg: format!("导入完成，成功: {}, 失败: {}", success_count, failed_count),
            success: true,
            data: ImportResult {
                success_count,
                failed_count,
                errors: if errors.is_empty() { None } else { Some(errors) },
            },
        },
    };

    Ok(Json(response))
}

// 删除题目 - 使用业务逻辑层
pub async fn delete_question(
    State(pool): State<SqlitePool>,
    Path(id): Path<i64>,
) -> Result<Json<DeleteQuestionResponse>, StatusCode> {
    info!("删除题目: {}", id);

    let service = QuestionService::new(pool);
    let deleted = service.delete_question(id).await
        .map_err(|e| {
            error!("删除题目失败: {}", e);
            StatusCode::INTERNAL_SERVER_ERROR
        })?;

    if !deleted {
        return Err(StatusCode::NOT_FOUND);
    }

    let response = DeleteQuestionResponse {
        code: 200,
        data: DeleteQuestionData {
            msg: "题目删除成功".to_string(),
            success: true,
            data: (),
        },
    };

    Ok(Json(response))
}

// 清空所有题目 - 使用业务逻辑层
pub async fn clear_questions(
    State(pool): State<SqlitePool>,
) -> Result<Json<ClearQuestionsResponse>, StatusCode> {
    info!("清空所有题目");

    let service = QuestionService::new(pool);
    service.clear_questions().await
        .map_err(|e| {
            error!("清空题目失败: {}", e);
            StatusCode::INTERNAL_SERVER_ERROR
        })?;

    let response = ClearQuestionsResponse {
        code: 200,
        data: ClearQuestionsData {
            msg: "所有题目已清空".to_string(),
            success: true,
            data: (),
        },
    };

    Ok(Json(response))
}