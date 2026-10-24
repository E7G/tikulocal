use anyhow::{Context, Result};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::path::Path;

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Question {
    #[serde(default, alias = "content")]
    pub question: String,
    #[serde(default)]
    pub options: Vec<String>,
    #[serde(default, rename = "type")]
    pub kind: i32,
    #[serde(default)]
    pub answer: String,
}

#[derive(Clone, Debug)]
pub struct Record {
    pub id: i64,
    pub question: Question,
    pub created_at: String,
}

pub fn normalized(s: &str) -> String {
    s.chars()
        .filter(|c| c.is_alphanumeric() || ('一'..='龥').contains(c))
        .flat_map(char::to_lowercase)
        .collect()
}
pub fn open(path: &Path) -> Result<Connection> {
    let db = Connection::open(path).context("Open SQLite question database")?;
    db.execute_batch(
        "CREATE TABLE IF NOT EXISTS questions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL, options TEXT, type INTEGER NOT NULL, answer TEXT NOT NULL,
        search_question TEXT, search_options TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE INDEX IF NOT EXISTS idx_questions_type ON questions(type);
        CREATE INDEX IF NOT EXISTS idx_questions_search ON questions(search_question);",
    )?;
    let mut columns = Vec::new();
    {
        let mut stmt = db.prepare("PRAGMA table_info(questions)")?;
        let rows = stmt.query_map([], |r| r.get::<_, String>(1))?;
        for row in rows {
            columns.push(row?);
        }
    }
    for name in ["search_question", "search_options"] {
        if !columns.iter().any(|v| v == name) {
            db.execute(&format!("ALTER TABLE questions ADD COLUMN {name} TEXT"), [])?;
        }
    }
    Ok(db)
}
pub fn add_many(db: &mut Connection, questions: &[Question]) -> Result<usize> {
    let tx = db.transaction()?;
    let mut added = 0;
    {
        let mut stmt=tx.prepare("INSERT INTO questions(question,options,type,answer,search_question,search_options) VALUES (?1,?2,?3,?4,?5,?6)")?;
        for q in questions {
            if q.question.trim().is_empty() || q.answer.trim().is_empty() {
                continue;
            }
            let opt = serde_json::to_string(&q.options)?;
            stmt.execute(params![
                q.question,
                opt,
                q.kind,
                q.answer,
                normalized(&q.question),
                normalized(&opt)
            ])?;
            added += 1;
        }
    }
    tx.commit()?;
    Ok(added)
}
pub fn list(db: &Connection, limit: usize) -> Result<Vec<Record>> {
    let mut stmt=db.prepare("SELECT id,question,options,type,answer,created_at FROM questions ORDER BY id DESC LIMIT ?1")?;
    let rows = stmt.query_map([limit as i64], |r| {
        let options: String = r.get(2)?;
        Ok(Record {
            id: r.get(0)?,
            question: Question {
                question: r.get(1)?,
                options: serde_json::from_str(&options).unwrap_or_default(),
                kind: r.get(3)?,
                answer: r.get(4)?,
            },
            created_at: r.get(5)?,
        })
    })?;
    rows.collect::<rusqlite::Result<Vec<_>>>()
        .map_err(Into::into)
}
pub fn stats(db: &Connection) -> Result<[i64; 6]> {
    let mut values = [0; 6];
    values[0] = db.query_row("SELECT COUNT(*) FROM questions", [], |r| r.get(0))?;
    for i in 0..5 {
        values[i + 1] = db.query_row(
            "SELECT COUNT(*) FROM questions WHERE type=?1",
            [i as i32],
            |r| r.get(0),
        )?;
    }
    Ok(values)
}
pub fn delete(db: &Connection, ids: &[i64]) -> Result<usize> {
    let mut total = 0;
    for id in ids {
        total += db.execute("DELETE FROM questions WHERE id=?1", [id])?;
    }
    Ok(total)
}
pub fn clear(db: &Connection) -> Result<usize> {
    Ok(db.execute("DELETE FROM questions", [])?)
}
pub fn search(
    db: &Connection,
    query: &str,
    options: &[String],
    kind: Option<i32>,
    limit: usize,
) -> Result<Vec<(i32, Question)>> {
    let query_norm = normalized(query);
    if query_norm.is_empty() {
        return Ok(Vec::new());
    }
    let mut stmt = db.prepare(
        "SELECT question,options,type,answer,search_question,search_options FROM questions",
    )?;
    let records = stmt.query_map([], |r| {
        let opt: String = r.get(1)?;
        Ok((
            Question {
                question: r.get(0)?,
                options: serde_json::from_str(&opt).unwrap_or_default(),
                kind: r.get(2)?,
                answer: r.get(3)?,
            },
            r.get::<_, Option<String>>(4)?,
            r.get::<_, Option<String>>(5)?,
        ))
    })?;
    let mut scored = Vec::new();
    for item in records {
        let (q, search_q, search_o) = item?;
        if let Some(t) = kind {
            if t != q.kind {
                continue;
            }
        }
        let sq = search_q
            .filter(|s| !s.is_empty())
            .unwrap_or_else(|| normalized(&q.question));
        let so = search_o
            .filter(|s| !s.is_empty())
            .unwrap_or_else(|| normalized(&q.options.join(" ")));
        let mut score = if sq == query_norm {
            100
        } else if sq.contains(&query_norm) || query_norm.contains(&sq) {
            50
        } else {
            0
        };
        let matched = options
            .iter()
            .map(|o| normalized(o))
            .filter(|o| !o.is_empty() && so.contains(o))
            .count();
        if !options.is_empty() && matched == options.len() {
            score += 50;
        } else {
            score += 10 * matched as i32;
        }
        if score > 0 {
            scored.push((score, q));
        }
    }
    scored.sort_unstable_by(|a, b| b.0.cmp(&a.0));
    scored.truncate(limit);
    Ok(scored)
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn search_and_persistence() {
        let mut db = Connection::open_in_memory().unwrap();
        db.execute_batch("CREATE TABLE questions(id INTEGER PRIMARY KEY, question TEXT, options TEXT,type INTEGER,answer TEXT,search_question TEXT,search_options TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP)").unwrap();
        add_many(
            &mut db,
            &[Question {
                question: "中 国 ，历史".into(),
                options: vec!["甲".into(), "乙".into()],
                kind: 0,
                answer: "A".into(),
            }],
        )
        .unwrap();
        assert_eq!(search(&db, "中国历史", &[], None, 10).unwrap().len(), 1);
        assert_eq!(stats(&db).unwrap()[0], 1);
    }
}
