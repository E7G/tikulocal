use regex::Regex;
use std::io::Read;
use zip::ZipArchive;

pub struct QuestionParser;

impl QuestionParser {
    pub fn parse_docx(path: &str) -> Result<Vec<serde_json::Value>, Box<dyn std::error::Error>> {
        let file = std::fs::File::open(path)?;
        let mut archive = ZipArchive::new(file)?;

        let mut xml_content = String::new();
        archive.by_name("word/document.xml")?.read_to_string(&mut xml_content)?;

        let paragraphs = Self::extract_paragraphs(&xml_content)?;
        Ok(Self::parse_paragraphs(&paragraphs))
    }

    fn extract_paragraphs(xml: &str) -> Result<Vec<String>, Box<dyn std::error::Error>> {
        let mut paragraphs = Vec::new();
        let mut current_text = String::new();

        let mut reader = quick_xml::Reader::from_str(xml);
        let mut in_text = false;
        let mut buf = Vec::new();

        loop {
            use quick_xml::events::Event;
            match reader.read_event_into(&mut buf) {
                Ok(Event::Start(ref e)) | Ok(Event::Empty(ref e)) => {
                    if e.name().as_ref() == b"w:t" {
                        in_text = true;
                    }
                }
                Ok(Event::End(ref e)) => {
                    if e.name().as_ref() == b"w:p" {
                        if !current_text.trim().is_empty() {
                            paragraphs.push(current_text.trim().to_string());
                        }
                        current_text = String::new();
                    } else if e.name().as_ref() == b"w:t" {
                        in_text = false;
                    }
                }
                Ok(Event::Text(ref e)) => {
                    if in_text {
                        current_text.push_str(&e.unescape()?);
                    }
                }
                Ok(Event::Eof) => break,
                Err(_) => break,
                _ => {}
            }
            buf.clear();
        }

        if !current_text.trim().is_empty() {
            paragraphs.push(current_text.trim().to_string());
        }

        Ok(paragraphs)
    }

    fn parse_paragraphs(paragraphs: &[String]) -> Vec<serde_json::Value> {
        let mut questions = Vec::new();
        let mut current: Option<(String, Vec<String>, i32, Option<String>)> = None;

        let header_re = Regex::new(r"^(\d+)[.、．]\s*【(.+题)】$").unwrap();
        let option_re = Regex::new(r"^([A-Z])、\s*(.+)$").unwrap();
        let answer_re = Regex::new(r"^正确答案[:：]\s*(.+)$").unwrap();
        let my_answer_re = Regex::new(r"^我的答案[:：]\s*(.+)$").unwrap();
        let status_re = Regex::new(r"^答案状态[:：]\s*(.+)$").unwrap();

        let type_map = [
            ("单选题", 0),
            ("多选题", 1),
            ("填空题", 2),
            ("判断题", 3),
            ("问答题", 4),
        ];

        for para in paragraphs {
            if let Some(caps) = header_re.captures(para) {
                if let Some((q, opts, t, a)) = current.take() {
                    if let Some(answer) = a {
                        questions.push(serde_json::json!({
                            "question": q,
                            "options": opts,
                            "type": t,
                            "answer": answer
                        }));
                    }
                }

                let type_text = caps.get(2).unwrap().as_str();
                let qtype = type_map
                    .iter()
                    .find(|(k, _)| type_text.contains(k))
                    .map(|(_, v)| *v)
                    .unwrap_or(4);

                current = Some((String::new(), Vec::new(), qtype, None));
                continue;
            }

            if let Some((ref mut q, ref mut opts, _, ref mut ans)) = current {
                if para == "选项：" {
                    continue;
                }

                if let Some(caps) = option_re.captures(para) {
                    opts.push(caps.get(2).unwrap().as_str().to_string());
                    continue;
                }

                if let Some(caps) = answer_re.captures(para) {
                    *ans = Some(caps.get(1).unwrap().as_str().to_string());
                    continue;
                }

                if let Some(caps) = my_answer_re.captures(para) {
                    if ans.is_none() {
                        *ans = Some(caps.get(1).unwrap().as_str().to_string());
                    }
                    continue;
                }

                if let Some(caps) = status_re.captures(para) {
                    if caps.get(1).unwrap().as_str() == "正确" && ans.is_none() {
                        // Will be filled by my_answer
                    }
                    continue;
                }

                if q.is_empty() {
                    *q = para.clone();
                }
            }
        }

        if let Some((q, opts, t, a)) = current {
            if let Some(answer) = a {
                questions.push(serde_json::json!({
                    "question": q,
                    "options": opts,
                    "type": t,
                    "answer": answer
                }));
            }
        }

        questions
    }
}
