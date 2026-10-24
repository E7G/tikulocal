use crate::db::{self, Question};
use serde_json::{json, Value};
use std::{io::Read, path::PathBuf, thread};
use tiny_http::{Header, Method, Response, Server, StatusCode};

fn answer_for(q: &Question) -> Value {
    let text = q.answer.trim();
    let mut keys = Vec::<String>::new();
    let mut indices = Vec::<usize>::new();
    let mut best = Vec::<String>::new();
    if q.kind == 0 || q.kind == 1 {
        for ch in text.chars().filter(|c| c.is_ascii_alphabetic()) {
            let index = ch.to_ascii_uppercase() as usize - 'A' as usize;
            if index < q.options.len() {
                keys.push(ch.to_ascii_uppercase().to_string());
                indices.push(index);
                best.push(q.options[index].clone());
            }
        }
    } else if q.kind == 3 {
        let yes = matches!(text, "对" | "正确" | "A" | "true" | "True" | "√");
        let no = matches!(text, "错" | "错误" | "B" | "false" | "False" | "×");
        if yes || no {
            keys.push(text.to_string());
            if q.options.len() >= 2 {
                let index = if yes { 0 } else { 1 };
                indices.push(index);
                best.push(q.options[index].clone());
            } else {
                best.push(if yes { "对" } else { "错" }.to_string());
            }
        }
    } else if q.kind == 2 {
        best = text
            .split(['；', ';'])
            .map(str::trim)
            .filter(|s| !s.is_empty())
            .map(str::to_string)
            .collect();
    } else if !text.is_empty() {
        best.push(text.to_string());
    }
    if best.is_empty() && !text.is_empty() {
        best.push(text.to_string());
    }
    let with_prefix: Vec<_> = indices
        .iter()
        .zip(best.iter())
        .map(|(i, b)| format!("{}{}", (b'A' + *i as u8) as char, b))
        .collect();
    let all = if best.is_empty() {
        vec![]
    } else if with_prefix.is_empty() {
        vec![best.clone()]
    } else {
        vec![best.clone(), with_prefix]
    };
    json!({"answerKey":keys,"answerKeyText":keys.join(""),"answerIndex":indices,
        "answerText":if (q.kind==0||q.kind==1)&&!indices.is_empty(){best.join("#")}else{text.to_string()},
        "bestAnswer":best,"allAnswer":all})
}
pub fn response(db: &rusqlite::Connection, payload: &Value) -> Value {
    let input = payload
        .get("question")
        .and_then(Value::as_str)
        .unwrap_or("");
    let opts: Vec<String> = payload
        .get("options")
        .and_then(Value::as_array)
        .map(|v| {
            v.iter()
                .filter_map(|e| e.as_str().map(str::to_string))
                .collect()
        })
        .unwrap_or_default();
    let kind = payload.get("type").and_then(Value::as_i64).unwrap_or(0) as i32;
    let hit = db::search(db, input, &opts, None, 10)
        .unwrap_or_default()
        .into_iter()
        .next()
        .map(|(_, q)| q);
    match hit {
        Some(q) => {
            json!({"plat":0,"question":q.question,"options":q.options,"type":q.kind,"answer":answer_for(&q)})
        }
        None => json!({"plat":0,"question":input,"options":opts,"type":kind,
            "answer":{"answerKey":[],"answerKeyText":"","answerIndex":[],"answerText":"","bestAnswer":[],"allAnswer":[]}}),
    }
}
pub fn start(database: PathBuf) -> std::io::Result<()> {
    let server = Server::http("127.0.0.1:8060").map_err(std::io::Error::other)?;
    thread::spawn(move || {
        for mut request in server.incoming_requests() {
            let path = request.url().split('?').next().unwrap_or("");
            let (code, data) = if request.method() == &Method::Options {
                (204, String::new())
            } else if request.method() == &Method::Post && path == "/adapter-service/search" {
                let mut body = String::new();
                match request
                    .as_reader()
                    .take(1024 * 1024)
                    .read_to_string(&mut body)
                {
                    Ok(_) => match serde_json::from_str::<Value>(&body) {
                        Ok(input) => match db::open(&database) {
                            Ok(conn) => (200, response(&conn, &input).to_string()),
                            Err(e) => (500, json!({"error":e.to_string()}).to_string()),
                        },
                        Err(_) => (400, json!({"error":"Invalid JSON data"}).to_string()),
                    },
                    Err(_) => (400, json!({"error":"Invalid request body"}).to_string()),
                }
            } else if request.method() == &Method::Get
                && (path == "/adapter-service" || path == "/adapter-service/")
            {
                (200, json!({"status":"ok"}).to_string())
            } else if request.method() == &Method::Get && path == "/" {
                (
                    200,
                    json!({"status":"ok","service":"tikulocal","search":"/adapter-service/search"})
                        .to_string(),
                )
            } else {
                (404, json!({"error":"Not found"}).to_string())
            };
            let mut reply = Response::from_string(data).with_status_code(StatusCode(code));
            if let Ok(h) = Header::from_bytes("Content-Type", "application/json; charset=utf-8") {
                reply.add_header(h);
            }
            if let Ok(h) = Header::from_bytes("Access-Control-Allow-Origin", "*") {
                reply.add_header(h);
            }
            if let Ok(h) = Header::from_bytes("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            {
                reply.add_header(h);
            }
            if let Ok(h) = Header::from_bytes("Access-Control-Allow-Headers", "Content-Type") {
                reply.add_header(h);
            }
            let _ = request.respond(reply);
        }
    });
    Ok(())
}
