use sqlx::{sqlite::SqlitePoolOptions, SqlitePool};
use std::path::Path;
use tokio::fs;
use tracing::info;

use crate::models::{Question, Answer};

pub async fn create_pool() -> Result<SqlitePool, sqlx::Error> {
    // 使用create_if_missing=true参数，SQLite会在文件不存在时自动创建
    let database_url = "sqlite:./questions.db?mode=rwc";
    
    // 检查数据库文件是否存在，如果不存在则创建
    if !Path::new("./questions.db").exists() {
        // 创建一个空文件
        fs::File::create("./questions.db").await
            .map_err(|e| sqlx::Error::Io(e))?;
        println!("数据库文件已创建: questions.db");
    }

    // 创建连接池
    let pool = SqlitePoolOptions::new()
        .max_connections(10)
        .acquire_timeout(std::time::Duration::from_secs(30))
        .connect(database_url)
        .await?;

    // 运行迁移
    init_db(&pool).await?;

    Ok(pool)
}

// 初始化数据库
async fn init_db(pool: &SqlitePool) -> Result<(), sqlx::Error> {
    // 创建题目表
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL UNIQUE,
            options TEXT,
            type INTEGER NOT NULL,
            answer TEXT NOT NULL
        )
        "#,
    )
    .execute(pool)
    .await?;
    
    // 创建索引以提高搜索性能
    sqlx::query("CREATE INDEX IF NOT EXISTS idx_questions_question ON questions(question)")
        .execute(pool)
        .await?;

    sqlx::query("CREATE INDEX IF NOT EXISTS idx_questions_type ON questions(type)")
        .execute(pool)
        .await?;
    
    info!("数据库表创建完成");
    Ok(())
}

// 业务逻辑层 - 消除重复代码
pub struct QuestionService {
    pool: SqlitePool,
}

impl QuestionService {
    pub fn new(pool: SqlitePool) -> Self {
        Self { pool }
    }

    // 统一的题目查询逻辑
    async fn query_questions(&self, sql: &str, binds: Vec<String>) -> Result<Vec<Question>, sqlx::Error> {
        let mut query = sqlx::query_as::<_, Question>(sql);
        
        for bind in binds {
            query = query.bind(bind);
        }
        
        query.fetch_all(&self.pool).await
    }

    // 搜索题目 - 消除handlers.rs中的重复代码
    pub async fn search_questions(&self, keyword: &str) -> Result<Vec<Question>, sqlx::Error> {
        self.query_questions(
            "SELECT id, question, options, type as question_type, answer FROM questions WHERE question LIKE ?",
            vec![format!("%{}%", keyword)]
        ).await
    }

    // 获取所有题目
    pub async fn get_all_questions(&self) -> Result<Vec<Question>, sqlx::Error> {
        self.query_questions(
            "SELECT id, question, options, type as question_type, answer FROM questions ORDER BY id",
            vec![]
        ).await
    }

    // 检查题目是否已存在
    pub async fn question_exists(&self, question: &str) -> Result<bool, sqlx::Error> {
        let count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM questions WHERE question = ?"
        )
        .bind(question)
        .fetch_one(&self.pool)
        .await?;
        
        Ok(count > 0)
    }

    // 创建题目 - 统一JSON序列化，支持去重
    pub async fn create_question(&self, question: &str, options: Option<Vec<String>>, question_type: i32, answer: &Answer) -> Result<i64, sqlx::Error> {
        let options_json = options.as_ref().map(|o| serde_json::to_string(o).ok()).flatten();
        let answer_json = serde_json::to_string(answer).map_err(|e| sqlx::Error::ColumnDecode {
            index: "answer".into(),
            source: Box::new(e),
        })?;

        let result = sqlx::query(
            "INSERT INTO questions (question, options, type, answer) VALUES (?, ?, ?, ?)"
        )
        .bind(question)
        .bind(options_json)
        .bind(question_type)
        .bind(answer_json)
        .execute(&self.pool)
        .await?;

        Ok(result.last_insert_rowid())
    }

    // 删除题目
    pub async fn delete_question(&self, id: i64) -> Result<bool, sqlx::Error> {
        let result = sqlx::query("DELETE FROM questions WHERE id = ?")
            .bind(id)
            .execute(&self.pool)
            .await?;

        Ok(result.rows_affected() > 0)
    }

    // 清空所有题目
    pub async fn clear_questions(&self) -> Result<(), sqlx::Error> {
        sqlx::query("DELETE FROM questions")
            .execute(&self.pool)
            .await?;
        
        Ok(())
    }
}