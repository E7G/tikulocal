use crate::db::{self, Question};
use serde_json::{json, Value};
use std::{io::Read, path::PathBuf, thread};
use tiny_http::{Header, Method, Response, Server, StatusCode};

/// Match complete options by their actual text, not by substring or position.
/// Duplicate/empty options cannot be mapped unambiguously.
fn option_mapping(stored: &[String], incoming: &[String]) -> Option<Vec<usize>> {
    if stored.len() != incoming.len() || stored.len() > 26 {
        return None;
    }
    let mut mapping = Vec::with_capacity(stored.len());
    for option in stored {
        let text = db::strict_text(option);
        if text.is_empty() {
            return None;
        }
        let mut matches = incoming
            .iter()
            .enumerate()
            .filter(|(_, s)| db::strict_text(s) == text);
        let index = matches.next()?.0;
        if matches.next().is_some() || mapping.contains(&index) {
            return None;
        }
        mapping.push(index);
    }
    Some(mapping)
}

fn unique_text_index(text: &str, options: &[String]) -> Option<usize> {
    let key = db::strict_text(text);
    let mut matches = options
        .iter()
        .enumerate()
        .filter(|(_, o)| db::strict_text(o) == key);
    let index = matches.next()?.0;
    if key.is_empty() || matches.next().is_some() {
        None
    } else {
        Some(index)
    }
}

pub(crate) fn choice_indices(answer: &str, options: &[String]) -> Vec<usize> {
    let answer = answer.trim();
    if options.is_empty() || options.len() > 26 || answer.is_empty() {
        return Vec::new();
    }
    let exact = unique_text_index(answer, options);
    let alphabet: String = answer
        .chars()
        .filter(|c| !matches!(c, ' ' | ',' | '，' | '、' | '；' | ';' | '#' | '/' | '&'))
        .collect();
    if !alphabet.is_empty()
        && alphabet.chars().all(|c| {
            c.is_ascii_alphabetic()
                && (c.to_ascii_uppercase() as usize - 'A' as usize) < options.len()
        })
    {
        let mut indices = alphabet
            .chars()
            .map(|c| c.to_ascii_uppercase() as usize - 'A' as usize)
            .collect::<Vec<_>>();
        indices.sort_unstable();
        indices.dedup();
        // A literal option text and an answer-key interpretation must not disagree.
        if exact.is_some_and(|i| indices != [i]) {
            return Vec::new();
        }
        return indices;
    }
    if let Some(i) = exact {
        return vec![i];
    }
    let mut indices = Vec::new();
    for item in answer.split(['；', ';', ',', '，', '#']) {
        let part = item.trim();
        if part.is_empty() {
            return Vec::new();
        }
        let text_index = unique_text_index(part, options);
        let mut chars = part.chars();
        let label_index = chars
            .next()
            .filter(|c| c.is_ascii_alphabetic())
            .and_then(|c| {
                let index = c.to_ascii_uppercase() as usize - 'A' as usize;
                let option = options.get(index)?;
                let rest = chars.as_str();
                if rest.is_empty() {
                    return Some(index);
                }
                // Explicit "B. text" must agree with the option at B.
                // Strip just one explicit label separator; do not discard a sign or punctuation in the option itself.
                let mut rest_chars = rest.chars();
                let first = rest_chars.next()?;
                let suffix = if matches!(first, '.' | '．' | '、' | ':' | '：' | ')' | '）') {
                    rest_chars.as_str().trim_start()
                } else if first.is_whitespace() {
                    rest.trim_start()
                } else {
                    return None;
                };
                if db::strict_text(suffix) == db::strict_text(option) {
                    Some(index)
                } else {
                    None
                }
            });
        let index = match (text_index, label_index) {
            (Some(a), Some(b)) if a != b => return Vec::new(),
            (Some(i), _) | (_, Some(i)) => i,
            _ => return Vec::new(),
        };
        if !indices.contains(&index) {
            indices.push(index);
        }
    }
    indices.sort_unstable();
    indices
}

fn truth_value(s: &str) -> Option<bool> {
    match s.trim().to_ascii_lowercase().as_str() {
        "对" | "正确" | "是" | "true" | "√" | "✓" => Some(true),
        "错" | "错误" | "否" | "false" | "×" | "✗" => Some(false),
        _ => None,
    }
}

fn answer_for(q: &Question, incoming: &[String]) -> Option<Value> {
    let text = q.answer.trim();
    if text.is_empty() {
        return None;
    }
    let mapping = option_mapping(&q.options, incoming)?;
    let mut indices = Vec::new();
    let best: Vec<String> = match q.kind {
        0 | 1 => {
            if incoming.len() < 2 {
                return None;
            }
            let stored_indices = choice_indices(text, &q.options);
            if stored_indices.is_empty() || (q.kind == 0 && stored_indices.len() != 1) {
                return None;
            }
            indices = stored_indices.into_iter().map(|i| mapping[i]).collect();
            indices.sort_unstable();
            indices.iter().map(|&i| incoming[i].clone()).collect()
        }
        3 => {
            // Resolve true/false by meaning, never assume the first option is true.
            let truth = truth_value(text).or_else(|| {
                let ix = choice_indices(text, &q.options);
                if ix.len() != 1 {
                    return None;
                }
                truth_value(&q.options[ix[0]])
            })?;
            if incoming.is_empty() {
                vec![if truth { "对" } else { "错" }.to_string()]
            } else {
                if incoming.len() != 2 || truth_value(&incoming[0])? == truth_value(&incoming[1])? {
                    return None;
                }
                let i = incoming
                    .iter()
                    .position(|o| truth_value(o) == Some(truth))?;
                indices.push(i);
                vec![incoming[i].clone()]
            }
        }
        2 => {
            if !incoming.is_empty() {
                return None;
            }
            text.split(['；', ';'])
                .map(str::trim)
                .filter(|s| !s.is_empty())
                .map(str::to_string)
                .collect()
        }
        4 => {
            if !incoming.is_empty() {
                return None;
            }
            vec![text.to_string()]
        }
        _ => return None,
    };
    if best.is_empty() {
        return None;
    }
    let keys: Vec<String> = indices
        .iter()
        .map(|&i| ((b'A' + i as u8) as char).to_string())
        .collect();
    let with_prefix: Vec<String> = keys
        .iter()
        .zip(&best)
        .map(|(k, b)| format!("{k}{b}"))
        .collect();
    let all = if with_prefix.is_empty() {
        vec![best.clone()]
    } else {
        vec![best.clone(), with_prefix]
    };
    Some(
        json!({"answerKey":keys,"answerKeyText":keys.join(""),"answerIndex":indices,
        "answerText":best.join("#"),"bestAnswer":best,"allAnswer":all}),
    )
}

pub fn response(db: &rusqlite::Connection, payload: &Value) -> Value {
    let input = payload
        .get("question")
        .and_then(Value::as_str)
        .unwrap_or("");
    let raw_opts = payload.get("options");
    let mut opts = Vec::new();
    let valid_options = match raw_opts {
        None | Some(Value::Null) => true,
        Some(Value::Array(items)) => {
            if items.iter().all(Value::is_string) {
                opts = items
                    .iter()
                    .map(|v| v.as_str().unwrap().to_string())
                    .collect();
                if opts.iter().all(|s| s.trim().is_empty()) {
                    opts.clear();
                }
                opts.iter().all(|s| !s.trim().is_empty())
            } else {
                false
            }
        }
        _ => false,
    };
    let kind = match payload.get("type") {
        None | Some(Value::Null) => None,
        Some(v) => v.as_i64().filter(|n| (0..=4).contains(n)).map(|n| n as i32),
    };
    let valid_type = kind.is_some() || matches!(payload.get("type"), None | Some(Value::Null));
    let empty = || {
        json!({"plat":0,"question":input,"options":opts,"type":kind.unwrap_or(0),
        "answer":{"answerKey":[],"answerKeyText":"","answerIndex":[],"answerText":"","bestAnswer":[],"allAnswer":[]}})
    };
    if !valid_type || !valid_options || db::strict_text(input).is_empty() {
        return empty();
    }
    let Ok(candidates) = db::exact_candidates(db, input, kind) else {
        return empty();
    };
    let mut matched: Option<(i32, Value)> = None;
    for q in candidates {
        if option_mapping(&q.options, &opts).is_none() {
            continue;
        }
        // A matching record with an invalid or conflicting answer must not be guessed.
        let Some(answer) = answer_for(&q, &opts) else {
            return empty();
        };
        if let Some((previous_kind, previous_answer)) = &matched {
            if *previous_kind != q.kind || *previous_answer != answer {
                return empty();
            }
        } else {
            matched = Some((q.kind, answer));
        }
    }
    match matched {
        Some((kind, answer)) => {
            json!({"plat":0,"question":input,"options":opts,"type":kind,"answer":answer})
        }
        None => empty(),
    }
}

pub fn start(database: PathBuf) -> std::io::Result<()> {
    let server = Server::http("127.0.0.1:8060").map_err(std::io::Error::other)?;
    thread::spawn(move || {
        for request in server.incoming_requests() {
            handle_request(request, &database);
        }
    });
    Ok(())
}

fn handle_request(mut request: tiny_http::Request, database: &std::path::Path) {
    // Ignore query strings and optional trailing slashes so legacy OCS/TikuAdapter
    // URLs (including ?use=local) resolve to the same endpoint.
    let path = request
        .url()
        .split('?')
        .next()
        .unwrap_or("")
        .trim_end_matches('/');
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
                Ok(input) => match db::open(database) {
                    Ok(conn) => (200, response(&conn, &input).to_string()),
                    Err(e) => (500, json!({"error":e.to_string()}).to_string()),
                },
                Err(_) => (400, json!({"error":"Invalid JSON data"}).to_string()),
            },
            Err(_) => (400, json!({"error":"Invalid request body"}).to_string()),
        }
    } else if matches!(request.method(), Method::Get | Method::Head)
        && (path == "/adapter-service" || path == "/adapter-service/search")
    {
        // OCS probes the configured URL with HEAD (or GET)
        // before sending the actual POST lookup request.
        (
            200,
            json!({"status":"ok","service":"tikuAdapter"}).to_string(),
        )
    } else if matches!(request.method(), Method::Get | Method::Head) && path.is_empty() {
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
    if let Ok(h) = Header::from_bytes("Access-Control-Allow-Methods", "GET, HEAD, POST, OPTIONS") {
        reply.add_header(h);
    }
    if let Ok(h) = Header::from_bytes("Access-Control-Allow-Headers", "Content-Type") {
        reply.add_header(h);
    }
    let _ = request.respond(reply);
}

#[cfg(test)]
mod tests {
    use super::*;
    fn fixture(rows: &[(&str, &[&str], i32, &str)]) -> rusqlite::Connection {
        let mut db = db::open(std::path::Path::new(":memory:")).unwrap();
        let questions = rows
            .iter()
            .map(|(title, opts, kind, answer)| Question {
                question: (*title).into(),
                options: opts.iter().map(|s| (*s).into()).collect(),
                kind: *kind,
                answer: (*answer).into(),
            })
            .collect::<Vec<_>>();
        db::add_many(&mut db, &questions).unwrap();
        db
    }

    fn assert_no_hit(db: &rusqlite::Connection, payload: Value) {
        let r = response(db, &payload);
        assert_eq!(r["question"], payload["question"]);
        assert_eq!(r["answer"]["allAnswer"], json!([]), "{r}");
        assert_eq!(r["answer"]["bestAnswer"], json!([]), "{r}");
        assert_eq!(r["answer"]["answerIndex"], json!([]), "{r}");
        assert_eq!(r["answer"]["answerText"], "");
    }

    #[test]
    fn adapter_rejects_unrelated_or_partial_titles_even_with_identical_options() {
        let db = fixture(&[("Which fruit is yellow?", &["Apple", "Banana"], 0, "B")]);
        for title in [
            "Which fruit is red?",
            "Which fruit",
            "Which fruit is yellow? Explain.",
            "which fruit is yellow?",
            "Which fruit is yellow",
        ] {
            let payload = json!({"question":title,"options":["Apple","Banana"],"type":0});
            assert_no_hit(&db, payload);
            let r = response(
                &db,
                &json!({"question":title,"options":["Other","Banana"],"type":0}),
            );
            assert_eq!(r["options"], json!(["Other", "Banana"]));
            assert_eq!(r["answer"]["allAnswer"], json!([]));
        }
    }

    #[test]
    fn adapter_preserves_mathematical_symbols_and_option_contents() {
        let db = fixture(&[("2+3=?", &["-5", "5", "6"], 0, "B")]);
        assert_no_hit(
            &db,
            json!({"question":"2-3=?","options":["-5","5","6"],"type":0}),
        );
        assert_no_hit(
            &db,
            json!({"question":"2+3=?","options":["-5","5","7"],"type":0}),
        );
        assert_no_hit(
            &db,
            json!({"question":"2+3=?","options":["5","6"],"type":0}),
        );
        assert_no_hit(
            &db,
            json!({"question":"2+3=?","options":["-5","5","6","7"],"type":0}),
        );
        assert_no_hit(
            &db,
            json!({"question":"2+3=?","options":["5","5","6"],"type":0}),
        );
        assert_no_hit(&db, json!({"question":"2+3=?","options":[],"type":0}));
        assert_no_hit(
            &db,
            json!({"question":"2+3=?","options":["-5",5,"6"],"type":0}),
        );
        assert_no_hit(
            &db,
            json!({"question":"2+3=?","options":["-5","5","6"],"type":1}),
        );
        assert_no_hit(
            &db,
            json!({"question":"2+3=?","options":["-5","5","6"],"type":"0"}),
        );
        let r = response(
            &db,
            &json!({"question":"  2+3=?  ","options":["6","-5","5"],"type":0}),
        );
        assert_eq!(r["options"], json!(["6", "-5", "5"]));
        assert_eq!(r["answer"]["answerIndex"], json!([2]));
        assert_eq!(r["answer"]["answerKeyText"], "C");
        assert_eq!(r["answer"]["bestAnswer"], json!(["5"]));
    }

    #[test]
    fn adapter_reorders_multiple_choices_and_rejects_conflicts() {
        let mut db = fixture(&[
            ("Pick two", &["One", "Two", "Three"], 1, "A,C"),
            ("Pick two", &["Three", "One", "Two"], 1, "A,B"),
        ]);
        let payload = json!({"question":"Pick two","options":["Two","Three","One"],"type":1});
        let r = response(&db, &payload);
        assert_eq!(r["answer"]["answerIndex"], json!([1, 2]));
        assert_eq!(r["answer"]["bestAnswer"], json!(["Three", "One"]));
        db::add_many(
            &mut db,
            &[Question {
                question: "Pick two".into(),
                options: vec!["One".into(), "Two".into(), "Three".into()],
                kind: 1,
                answer: "A,B".into(),
            }],
        )
        .unwrap();
        assert_no_hit(&db, payload);
    }

    #[test]
    fn adapter_rejects_invalid_and_ambiguous_answers() {
        let db = fixture(&[
            ("Wrong key", &["One", "Two"], 0, "C"),
            ("Too many", &["One", "Two"], 0, "AB"),
            ("Duplicate", &["One", "One"], 0, "A"),
            ("Ambiguous", &["B", "A"], 0, "A"),
            ("Sign", &["1", "2"], 0, "A. -1"),
        ]);
        for (question, options) in [
            ("Wrong key", json!(["One", "Two"])),
            ("Too many", json!(["One", "Two"])),
            ("Duplicate", json!(["One", "One"])),
            ("Ambiguous", json!(["B", "A"])),
            ("Sign", json!(["1", "2"])),
        ] {
            assert_no_hit(&db, json!({"question":question,"options":options,"type":0}));
        }
    }

    #[test]
    fn adapter_matches_non_choice_types_without_guessing() {
        let db = fixture(&[
            ("Fill blank", &[], 2, "one;two"),
            ("Write explanation", &[], 4, "Explanation"),
            ("True or false", &["错误", "正确"], 3, "正确"),
            ("No options", &[], 3, "错"),
            ("Ambiguous type", &[], 2, "one"),
            ("Ambiguous type", &[], 4, "one"),
        ]);
        assert_eq!(
            response(
                &db,
                &json!({"question":"Fill blank","options":[""],"type":2})
            )["answer"]["bestAnswer"],
            json!(["one", "two"])
        );
        assert_eq!(
            response(&db, &json!({"question":"Write explanation","options":[]}))["answer"]
                ["bestAnswer"],
            json!(["Explanation"])
        );
        assert_eq!(
            response(
                &db,
                &json!({"question":"True or false","options":["正确","错误"],"type":3})
            )["answer"]["answerIndex"],
            json!([0])
        );
        assert_eq!(
            response(&db, &json!({"question":"No options","type":3}))["answer"]["bestAnswer"],
            json!(["错"])
        );
        assert_no_hit(&db, json!({"question":"Fill","options":[],"type":2}));
        assert_no_hit(&db, json!({"question":"Fill blank","options":[],"type":4}));
        assert_no_hit(&db, json!({"question":"Ambiguous type","options":[]}));
    }

    #[test]
    fn adapter_verifies_legacy_cached_title_instead_of_trusting_it() {
        let db = fixture(&[("a+b", &["one", "two"], 0, "A")]);
        db.execute("UPDATE questions SET search_question=NULL", [])
            .unwrap();
        let r = response(
            &db,
            &json!({"question":"a+b","options":["one","two"],"type":0}),
        );
        assert_eq!(r["answer"]["bestAnswer"], json!(["one"]));
        db.execute("UPDATE questions SET search_question='ab'", [])
            .unwrap();
        assert_no_hit(
            &db,
            json!({"question":"a-b","options":["one","two"],"type":0}),
        );
    }

    #[test]
    fn ocs_head_probe_and_root_health_return_success() {
        use std::io::{Read, Write};
        use std::net::TcpStream;
        use std::time::Duration;

        let server = Server::http("127.0.0.1:0").unwrap();
        let addr = server.server_addr().to_ip().unwrap();
        let cases = [
            ("HEAD", "/adapter-service/search?use=local&t=123456", 200),
            ("HEAD", "/adapter-service/search/?use=local", 200),
            ("GET", "/", 200),
            ("HEAD", "/", 200),
            ("HEAD", "/unknown", 404),
        ];
        let worker = thread::spawn(move || {
            for _ in 0..cases.len() {
                let request = server
                    .recv_timeout(Duration::from_secs(5))
                    .unwrap()
                    .unwrap();
                handle_request(request, std::path::Path::new("unused.db"));
            }
        });
        for (method, path, expected) in cases {
            let mut stream = TcpStream::connect(addr).unwrap();
            stream
                .set_read_timeout(Some(Duration::from_secs(5)))
                .unwrap();
            write!(
                stream,
                "{method} {path} HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
            )
            .unwrap();
            let mut reply = String::new();
            stream.read_to_string(&mut reply).unwrap();
            assert!(
                reply.starts_with(&format!("HTTP/1.1 {expected} ")),
                "{reply}"
            );
            if method == "HEAD" {
                assert_eq!(reply.split_once("\r\n\r\n").unwrap().1, "");
            }
        }
        worker.join().unwrap();
    }

    #[test]
    fn choice_answers_never_guess_from_english_option_text() {
        let opts = vec![
            "Apple".to_string(),
            "Banana".to_string(),
            "Cherry".to_string(),
        ];
        assert_eq!(choice_indices("B", &opts), vec![1]);
        assert_eq!(choice_indices("A,C", &opts), vec![0, 2]);
        assert_eq!(choice_indices("B. Banana", &opts), vec![1]);
        assert_eq!(choice_indices("B、Banana", &opts), vec![1]);
        assert!(choice_indices("A、Banana", &opts).is_empty());
        assert_eq!(choice_indices("Banana", &opts), vec![1]);
        assert_eq!(choice_indices("Banana split", &opts), Vec::<usize>::new());
    }
    #[test]
    fn adapter_response_exposes_answer_contract() {
        let q = Question {
            question: "Which fruit?".into(),
            options: vec!["Apple".into(), "Banana".into()],
            kind: 0,
            answer: "B. Banana".into(),
        };
        let a = answer_for(&q, &q.options).unwrap();
        assert_eq!(a["answerKeyText"], "B");
        assert_eq!(a["answerIndex"], serde_json::json!([1]));
        assert_eq!(a["bestAnswer"], serde_json::json!(["Banana"]));
    }
}
