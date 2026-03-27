use rusqlite::{Connection, Result as SqliteResult};
use std::path::Path;

pub struct Database {
    conn: Connection,
}

impl Database {
    pub fn new(path: &Path) -> SqliteResult<Self> {
        let conn = Connection::open(path)?;
        let db = Self { conn };
        db.init_tables()?;
        Ok(db)
    }

    fn init_tables(&self) -> SqliteResult<()> {
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                options TEXT,
                type INTEGER NOT NULL,
                answer TEXT NOT NULL,
                search_question TEXT,
                search_options TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )",
            [],
        )?;

        let _ = self.conn.execute(
            "ALTER TABLE questions ADD COLUMN search_question TEXT",
            [],
        );
        let _ = self.conn.execute(
            "ALTER TABLE questions ADD COLUMN search_options TEXT",
            [],
        );

        Ok(())
    }

    fn remove_punctuation(text: &str) -> String {
        let puncts: Vec<char> = ",.!?;:\"\"''【】()《》〈〉〔〕｛｝ \t\n\r\u{3000}\u{a0}-_/@#$%^&*()+=[]{}|<>?~`"
            .chars()
            .collect();
        text.chars()
            .filter(|c| !puncts.contains(c) && !c.is_ascii_punctuation())
            .collect()
    }

    pub fn insert_questions(&mut self, questions: &[serde_json::Value]) -> SqliteResult<usize> {
        let tx = self.conn.transaction()?;
        let mut count = 0;

        for q in questions {
            let question = q["question"].as_str().unwrap_or("");
            let options = q["options"].to_string();
            let qtype = q["type"].as_i64().unwrap_or(0) as i32;
            let answer = q["answer"].as_str().unwrap_or("");

            if question.is_empty() || answer.is_empty() {
                continue;
            }

            let search_question = Self::remove_punctuation(question);
            let search_options = Self::remove_punctuation(&options);

            tx.execute(
                "INSERT INTO questions (question, options, type, answer, search_question, search_options)
                 VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
                rusqlite::params![question, options, qtype, answer, search_question, search_options],
            )?;
            count += 1;
        }

        tx.commit()?;
        Ok(count)
    }

    pub fn search_questions(
        &self,
        query: &str,
        qtype: i32,
    ) -> SqliteResult<Vec<serde_json::Value>> {
        let clean_query = Self::remove_punctuation(query);
        let pattern = format!("%{}%", clean_query);

        let sql = if qtype < 0 {
            "SELECT id, question, options, type, answer FROM questions
             WHERE search_question LIKE ?1 OR search_options LIKE ?1
             ORDER BY created_at DESC LIMIT 50"
        } else {
            "SELECT id, question, options, type, answer FROM questions
             WHERE type = ?2 AND (search_question LIKE ?1 OR search_options LIKE ?1)
             ORDER BY created_at DESC LIMIT 50"
        };

        let mut stmt = self.conn.prepare(sql)?;
        let mut results = Vec::new();

        if qtype < 0 {
            let rows = stmt.query_map([&pattern], |row| {
                Ok(serde_json::json!({
                    "id": row.get::<_, i64>(0)?,
                    "question": row.get::<_, String>(1)?,
                    "options": row.get::<_, String>(2)?,
                    "type": row.get::<_, i32>(3)?,
                    "answer": row.get::<_, String>(4)?,
                }))
            })?;
            for row in rows {
                results.push(row?);
            }
        } else {
            let rows = stmt.query_map(rusqlite::params![&pattern, qtype], |row| {
                Ok(serde_json::json!({
                    "id": row.get::<_, i64>(0)?,
                    "question": row.get::<_, String>(1)?,
                    "options": row.get::<_, String>(2)?,
                    "type": row.get::<_, i32>(3)?,
                    "answer": row.get::<_, String>(4)?,
                }))
            })?;
            for row in rows {
                results.push(row?);
            }
        }

        Ok(results)
    }

    pub fn get_stats(&self) -> SqliteResult<serde_json::Value> {
        let total: i64 = self.conn.query_row("SELECT COUNT(*) FROM questions", [], |r| r.get(0))?;
        let single: i64 = self.conn.query_row("SELECT COUNT(*) FROM questions WHERE type = 0", [], |r| r.get(0))?;
        let multi: i64 = self.conn.query_row("SELECT COUNT(*) FROM questions WHERE type = 1", [], |r| r.get(0))?;
        let judge: i64 = self.conn.query_row("SELECT COUNT(*) FROM questions WHERE type = 3", [], |r| r.get(0))?;

        Ok(serde_json::json!({
            "total": total,
            "single": single,
            "multi": multi,
            "judge": judge
        }))
    }

    pub fn get_questions(&self, limit: i32) -> SqliteResult<Vec<serde_json::Value>> {
        let mut stmt = self.conn.prepare(
            "SELECT id, question, options, type, answer, created_at FROM questions
             ORDER BY created_at DESC LIMIT ?1",
        )?;

        let rows = stmt.query_map([limit], |row| {
            Ok(serde_json::json!({
                "id": row.get::<_, i64>(0)?,
                "question": row.get::<_, String>(1)?,
                "options": row.get::<_, String>(2)?,
                "type": row.get::<_, i32>(3)?,
                "answer": row.get::<_, String>(4)?,
                "created_at": row.get::<_, String>(5)?,
            }))
        })?;

        let mut results = Vec::new();
        for row in rows {
            results.push(row?);
        }
        Ok(results)
    }

    pub fn delete_question(&self, id: i64) -> SqliteResult<()> {
        self.conn.execute("DELETE FROM questions WHERE id = ?1", [id])?;
        Ok(())
    }

    pub fn clear_all(&self) -> SqliteResult<()> {
        self.conn.execute("DELETE FROM questions", [])?;
        Ok(())
    }

    pub fn search_for_api(&self, query: &str, options: &[String]) -> SqliteResult<Option<serde_json::Value>> {
        let clean_query = Self::remove_punctuation(query);
        let clean_options: Vec<String> = options.iter().map(|o| Self::remove_punctuation(o)).collect();

        let mut stmt = self.conn.prepare(
            "SELECT question, options, type, answer, search_question, search_options FROM questions"
        )?;

        let rows = stmt.query_map([], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, i32>(2)?,
                row.get::<_, String>(3)?,
                row.get::<_, String>(4)?,
                row.get::<_, String>(5)?,
            ))
        })?;

        let mut scored: Vec<(i32, (String, String, i32, String))> = Vec::new();

        for row in rows {
            let (q, opts, qtype, ans, sq, so) = row?;
            let mut score = 0;

            if !clean_query.is_empty() && !sq.is_empty() {
                if clean_query == sq {
                    score += 100;
                } else if sq.contains(&clean_query) || clean_query.contains(&sq) {
                    score += 50;
                }
            }

            if !clean_options.is_empty() && !so.is_empty() {
                let matches = clean_options.iter().filter(|o| so.contains(&o.as_str())).count();
                if matches == clean_options.len() {
                    score += 50;
                } else if matches > 0 {
                    score += matches as i32 * 10;
                }
            }

            if score > 0 {
                scored.push((score, (q, opts, qtype, ans)));
            }
        }

        scored.sort_by(|a, b| b.0.cmp(&a.0));

        if let Some((_, (question, options_json, qtype, answer))) = scored.into_iter().next() {
            let opts: Vec<String> = serde_json::from_str(&options_json).unwrap_or_default();
            let answer_obj = build_answer(&answer, &opts, qtype);

            Ok(Some(serde_json::json!({
                "plat": 0,
                "question": question,
                "options": opts,
                "type": qtype,
                "answer": answer_obj
            })))
        } else {
            Ok(None)
        }
    }
}

fn build_answer(answer_text: &str, options: &[String], qtype: i32) -> serde_json::Value {
    let mut answer = serde_json::json!({
        "answerKey": [],
        "answerKeyText": "",
        "answerIndex": [],
        "answerText": answer_text,
        "bestAnswer": [],
        "allAnswer": [[]]
    });

    if qtype == 0 || qtype == 1 {
        let re = regex::Regex::new(r"[A-Za-z]").unwrap();
        let keys: Vec<String> = re.find_iter(answer_text).map(|m| m.as_str().to_uppercase()).collect();

        answer["answerKey"] = serde_json::to_value(&keys).unwrap();
        answer["answerKeyText"] = serde_json::to_value(keys.join("")).unwrap();

        let indices: Vec<i32> = keys
            .iter()
            .filter_map(|k| {
                let idx = k.chars().next()? as i32 - 'A' as i32;
                if (idx as usize) < options.len() {
                    Some(idx)
                } else {
                    None
                }
            })
            .collect();
        answer["answerIndex"] = serde_json::to_value(&indices).unwrap();

        let best: Vec<String> = keys
            .iter()
            .filter_map(|k| {
                let idx = k.chars().next()? as usize - 'A' as usize;
                options.get(idx).cloned()
            })
            .collect();

        if !best.is_empty() {
            answer["bestAnswer"] = serde_json::to_value(&best).unwrap();
            answer["answerText"] = serde_json::to_value(best.join("#")).unwrap();
            answer["allAnswer"] = serde_json::to_value(vec![best]).unwrap();
        }
    } else if qtype == 3 {
        let key = if ["对", "正确", "A"].contains(&answer_text) {
            "对"
        } else if ["错", "错误", "B"].contains(&answer_text) {
            "错"
        } else {
            answer_text
        };
        answer["answerKey"] = serde_json::to_value(vec![key]).unwrap();
        answer["answerKeyText"] = serde_json::to_value(key).unwrap();
    }

    answer
}
