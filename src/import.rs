use crate::db::Question;
use anyhow::{bail, Context, Result};
use quick_xml::{events::Event, Reader};
use regex::Regex;
use std::{fs::File, io::Read, path::Path};
use zip::ZipArchive;

pub fn from_path(path: &Path) -> Result<Vec<Question>> {
    match path
        .extension()
        .and_then(|x| x.to_str())
        .unwrap_or("")
        .to_lowercase()
        .as_str()
    {
        "json" => from_json(path),
        "docx" => from_docx(path),
        ext => bail!("Unsupported input format: {ext}"),
    }
}
pub fn from_json(path: &Path) -> Result<Vec<Question>> {
    let value: serde_json::Value = serde_json::from_reader(File::open(path)?)?;
    let list = if value.is_array() {
        value
    } else {
        value
            .get("questions")
            .cloned()
            .context("Expected array or questions array")?
    };
    let rows = list.as_array().context("questions must be an array")?;
    let mut result = Vec::new();
    for item in rows {
        let question = item
            .get("question")
            .or_else(|| item.get("content"))
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .trim()
            .to_string();
        let answer = item
            .get("answer")
            .map(|v| {
                v.as_str()
                    .map(str::to_string)
                    .unwrap_or_else(|| v.to_string())
            })
            .unwrap_or_default();
        let options = item
            .get("options")
            .and_then(|v| v.as_array())
            .map(|items| {
                items
                    .iter()
                    .filter_map(|v| v.as_str().map(str::to_string))
                    .collect()
            })
            .unwrap_or_default();
        let kind = item.get("type").and_then(|v| v.as_i64()).unwrap_or(0) as i32;
        if !question.is_empty() && !answer.is_empty() {
            result.push(Question {
                question,
                answer,
                options,
                kind,
            });
        }
    }
    Ok(result)
}
fn docx_paragraphs(path: &Path) -> Result<Vec<String>> {
    let mut archive = ZipArchive::new(File::open(path)?)?;
    let mut xml = String::new();
    archive
        .by_name("word/document.xml")?
        .read_to_string(&mut xml)?;
    let mut reader = Reader::from_str(&xml);
    reader.config_mut().trim_text(false);
    let mut lines = Vec::new();
    let mut para = String::new();
    let mut in_text = false;
    let mut inside_para = false;
    loop {
        match reader.read_event()? {
            Event::Start(e) => match e.local_name().as_ref() {
                b"p" => {
                    inside_para = true;
                    para.clear();
                }
                b"t" => in_text = true,
                b"br" | b"cr" if inside_para => para.push('\n'),
                b"tab" if inside_para => para.push(' '),
                _ => {}
            },
            Event::Empty(e) => match e.local_name().as_ref() {
                b"br" | b"cr" if inside_para => para.push('\n'),
                b"tab" if inside_para => para.push(' '),
                _ => {}
            },
            Event::Text(t) if in_text => para.push_str(&t.unescape()?.into_owned()),
            Event::End(e) => match e.local_name().as_ref() {
                b"t" => in_text = false,
                b"p" => {
                    inside_para = false;
                    for line in para.lines() {
                        let line = line.trim();
                        if !line.is_empty() {
                            lines.push(line.to_string());
                        }
                    }
                }
                _ => {}
            },
            Event::Eof => break,
            _ => {}
        }
    }
    Ok(lines)
}
pub fn from_docx(path: &Path) -> Result<Vec<Question>> {
    parse_paragraphs(&docx_paragraphs(path)?)
}
fn push_verified(
    out: &mut Vec<Question>,
    pending: Option<Question>,
    my_answer: &Option<String>,
    correct_status: bool,
) {
    if let Some(mut q) = pending {
        if q.answer.is_empty() && correct_status {
            q.answer = my_answer.clone().unwrap_or_default();
        }
        if !q.question.trim().is_empty() && !q.answer.trim().is_empty() {
            out.push(q);
        }
    }
}
pub fn parse_paragraphs(lines: &[String]) -> Result<Vec<Question>> {
    let header = Regex::new(r"^(\d+)(?:[.、．]|\s+)\s*【(单选题|多选题|填空题|判断题|问答题)】")?;
    let option = Regex::new(r"^([A-Za-z])[、.．:：]\s*(.+)$")?;
    let answers = Regex::new(r"^(正确答案|标准答案|参考答案)[:：]\s*(.*)$")?;
    let my_answer_line = Regex::new(r"^我的答案[:：]\s*(.*)$")?;
    let status_line = Regex::new(r"^答案状态[:：]\s*(.*)$")?;
    let blank = Regex::new(r"第[一二三四五六七八九十\d]+空[:：]\s*([^第]+)")?;
    let mut questions = Vec::new();
    let mut current: Option<Question> = None;
    let mut my_answer: Option<String> = None;
    let mut correct_status = false;
    for raw in lines {
        let text = raw.trim();
        if text.is_empty() {
            continue;
        }
        if let Some(cap) = header.captures(text) {
            push_verified(&mut questions, current.take(), &my_answer, correct_status);
            my_answer = None;
            correct_status = false;
            let kind = match &cap[2] {
                "单选题" => 0,
                "多选题" => 1,
                "填空题" => 2,
                "判断题" => 3,
                _ => 4,
            };
            current = Some(Question {
                question: String::new(),
                options: vec![],
                kind,
                answer: String::new(),
            });
            continue;
        }
        let Some(q) = current.as_mut() else {
            continue;
        };
        if text == "选项：" || text == "选项:" {
            continue;
        }
        if let Some(cap) = answers.captures(text) {
            let value = cap[2].trim();
            let values: Vec<_> = blank
                .captures_iter(value)
                .map(|c| c[1].trim().to_string())
                .collect();
            if !value.is_empty() && value != "暂无" && value != "无" {
                q.answer = if values.is_empty() {
                    value.to_string()
                } else {
                    values.join("；")
                };
            }
            continue;
        }
        if let Some(cap) = my_answer_line.captures(text) {
            let value = cap[1].trim();
            let values: Vec<_> = blank
                .captures_iter(value)
                .map(|c| c[1].trim().to_string())
                .collect();
            if !value.is_empty() && value != "暂无" && value != "无" {
                my_answer = Some(if values.is_empty() {
                    value.to_string()
                } else {
                    values.join("；")
                });
            }
            continue;
        }
        if let Some(cap) = status_line.captures(text) {
            correct_status = matches!(cap[1].trim(), "正确" | "回答正确" | "答题正确");
            continue;
        }
        if ["得分", "解析", "答案解析"]
            .iter()
            .any(|p| text.starts_with(p))
        {
            continue;
        }
        if let Some(cap) = option.captures(text) {
            q.options.push(cap[2].trim().to_string());
            continue;
        }
        if q.question.is_empty() {
            q.question = text.to_string();
        } else if q.options.is_empty() && q.answer.is_empty() {
            q.question.push_str(text);
        }
    }
    push_verified(&mut questions, current, &my_answer, correct_status);
    Ok(questions)
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn explicitly_correct_my_answer_is_accepted() {
        let input = [
            "1.【单选题】",
            "题干",
            "A、甲",
            "B、乙",
            "我的答案：A",
            "答案状态：正确",
            "2.【单选题】",
            "另一题",
            "A、甲",
            "B、乙",
            "正确答案：B",
        ];
        let got =
            parse_paragraphs(&input.iter().map(|s| s.to_string()).collect::<Vec<_>>()).unwrap();
        assert_eq!(got.len(), 2);
        assert_eq!(got[0].answer, "A");
        assert_eq!(got[1].answer, "B");
    }
    #[test]
    fn explicit_correct_answer_takes_priority() {
        let input = [
            "1.【单选题】",
            "题干",
            "A、甲",
            "B、乙",
            "我的答案：A",
            "答案状态：正确",
            "正确答案：B",
        ];
        let got =
            parse_paragraphs(&input.iter().map(|s| s.to_string()).collect::<Vec<_>>()).unwrap();
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].answer, "B");
    }
    #[test]
    fn wrong_and_ungraded_my_answers_are_ignored() {
        let input = [
            "1.【单选题】",
            "第一题",
            "我的答案：A",
            "答案状态：错误",
            "2.【单选题】",
            "第二题",
            "我的答案：B",
            "3.【单选题】",
            "第三题",
            "我的答案：C",
            "答案状态：正确",
        ];
        let got =
            parse_paragraphs(&input.iter().map(|s| s.to_string()).collect::<Vec<_>>()).unwrap();
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].question, "第三题");
        assert_eq!(got[0].answer, "C");
    }
}
