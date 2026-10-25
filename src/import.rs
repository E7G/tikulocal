use crate::db::Question;
use anyhow::{bail, Context, Result};
use quick_xml::{events::Event, Reader};
use regex::Regex;
use std::{
    fs::File,
    io::{Cursor, Read, Seek},
    path::Path,
};
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
        "zip" => from_batch_zip(path),
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
fn docx_paragraphs<R: Read + Seek>(source: R) -> Result<Vec<String>> {
    let mut archive = ZipArchive::new(source)?;
    let mut xml = String::new();
    let document = archive.by_name("word/document.xml")?;
    if document.size() > MAX_DOCUMENT_XML_BYTES {
        bail!("DOCX document.xml exceeds the 16 MiB safety limit");
    }
    document
        .take(MAX_DOCUMENT_XML_BYTES + 1)
        .read_to_string(&mut xml)?;
    if xml.len() as u64 > MAX_DOCUMENT_XML_BYTES {
        bail!("DOCX XML exceeds the 16 MiB safety limit");
    }
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
    parse_paragraphs(&docx_paragraphs(File::open(path)?)?)
}

const MAX_DOCUMENT_XML_BYTES: u64 = 16 * 1024 * 1024;
const MAX_BATCH_ENTRIES: usize = 2048;
const MAX_BATCH_FILE_BYTES: u64 = 128 * 1024 * 1024;
const MAX_DOCX_BYTES: u64 = 32 * 1024 * 1024;
const MAX_TOTAL_UNCOMPRESSED_DOCX: u64 = 256 * 1024 * 1024;

/// Import the upstream v0.2.1 batch export: a ZIP of numbered DOCX files
/// plus 导出清单.txt. Invalid/failed members do not discard valid documents.
pub fn from_batch_zip(path: &Path) -> Result<Vec<Question>> {
    let file = File::open(path)?;
    if file.metadata()?.len() > MAX_BATCH_FILE_BYTES {
        bail!("批量 ZIP 超过 128 MiB 限制");
    }
    let mut archive = ZipArchive::new(file).context("批量文件不是有效 ZIP")?;
    if archive.len() > MAX_BATCH_ENTRIES {
        bail!("ZIP 内文件数量超过 2048 个");
    }
    let mut output = Vec::new();
    let mut docx_count = 0usize;
    let mut failed_count = 0usize;
    let mut total_size = 0u64;
    for index in 0..archive.len() {
        let entry = archive.by_index(index)?;
        if entry.is_dir() || !entry.name().to_ascii_lowercase().ends_with(".docx") {
            continue; // skip 导出清单.txt, folders and unrelated attachments
        }
        docx_count += 1;
        if entry.size() > MAX_DOCX_BYTES {
            failed_count += 1;
            eprintln!("Skipping oversize DOCX in ZIP: {}", entry.name());
            continue;
        }
        total_size = total_size.saturating_add(entry.size());
        if total_size > MAX_TOTAL_UNCOMPRESSED_DOCX {
            bail!("ZIP 内 DOCX 解压总量超过 256 MiB 限制");
        }
        let name = entry.name().to_string();
        let parsed = (|| -> Result<Vec<Question>> {
            let mut bytes = Vec::with_capacity(entry.size() as usize);
            entry.take(MAX_DOCX_BYTES + 1).read_to_end(&mut bytes)?;
            if bytes.len() as u64 > MAX_DOCX_BYTES {
                bail!("DOCX 解压大小超限");
            }
            parse_paragraphs(&docx_paragraphs(Cursor::new(bytes))?)
        })();
        match parsed {
            Ok(rows) if !rows.is_empty() => output.extend(rows),
            Ok(_) => {
                failed_count += 1;
                eprintln!("No verified answers in batch DOCX: {name}");
            }
            Err(err) => {
                failed_count += 1;
                eprintln!("Skipping unreadable batch DOCX {name}: {err:#}");
            }
        }
    }
    if docx_count == 0 {
        bail!("ZIP 内没有 DOCX 文件；请选取批量导出的 ZIP");
    }
    if output.is_empty() {
        bail!("ZIP 中 {docx_count} 个 DOCX 均未提取到有效的正确答案");
    }
    if failed_count > 0 {
        eprintln!("Batch ZIP import: {failed_count}/{docx_count} DOCX were skipped");
    }
    Ok(output)
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
    use std::io::{Cursor, Write};
    use std::sync::atomic::{AtomicUsize, Ordering};
    use zip::{write::SimpleFileOptions, ZipWriter};

    static ZIP_TEST_NUMBER: AtomicUsize = AtomicUsize::new(0);

    fn make_zip(files: &[(&str, Vec<u8>)]) -> Vec<u8> {
        let mut archive = ZipWriter::new(Cursor::new(Vec::new()));
        for (name, bytes) in files {
            archive
                .start_file(*name, SimpleFileOptions::default())
                .unwrap();
            archive.write_all(bytes).unwrap();
        }
        archive.finish().unwrap().into_inner()
    }

    // Mimics the upstream JSZip createDocx() output: one <w:p><w:t> per line.
    fn make_docx(paragraphs: &[&str]) -> Vec<u8> {
        let mut xml = String::from("<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\"><w:body>");
        for line in paragraphs {
            let escaped = line
                .replace('&', "&amp;")
                .replace('<', "&lt;")
                .replace('>', "&gt;");
            xml.push_str(&format!("<w:p><w:r><w:t>{escaped}</w:t></w:r></w:p>"));
        }
        xml.push_str("</w:body></w:document>");
        make_zip(&[("word/document.xml", xml.into_bytes())])
    }

    fn import_temp_zip(bytes: Vec<u8>) -> Result<Vec<Question>> {
        let serial = ZIP_TEST_NUMBER.fetch_add(1, Ordering::Relaxed);
        let path = std::env::temp_dir().join(format!(
            "tikulocal-batch-{}-{serial}.zip",
            std::process::id()
        ));
        std::fs::write(&path, bytes)?;
        let result = from_path(&path);
        let _ = std::fs::remove_file(path);
        result
    }

    #[test]
    fn upstream_batch_zip_imports_multiple_docx_and_ignores_manifest() {
        let chapter_a = make_docx(&[
            "1 【单选题】",
            "测试题干 & 内容",
            "选项：",
            "A、 选项甲",
            "B、 选项乙",
            "我的答案：A",
            "答案状态：正确",
            "2 【单选题】",
            "明确标准答案优先",
            "我的答案：A",
            "答案状态：错误",
            "正确答案：B",
        ]);
        let chapter_b = make_docx(&[
            "1 【填空题】",
            "第一章节填空",
            "我的答案：内容",
            "答案状态：部分正确",
            "2 【判断题】",
            "确实如此",
            "正确答案：对",
            "3 【多选题】",
            "尚未公开答案",
            "我的答案：A,B",
        ]);
        let archive = make_zip(&[
            ("001_专题六.docx", chapter_a),
            ("课程/002_专题六.docx", chapter_b),
            ("导出清单.txt", "成功 2，失败 0".as_bytes().to_vec()),
        ]);
        let got = import_temp_zip(archive).unwrap();
        assert_eq!(
            got.len(),
            3,
            "only verified/explicit answers should be imported"
        );
        assert_eq!(got[0].question, "测试题干 & 内容");
        assert_eq!(got[0].options, vec!["选项甲", "选项乙"]);
        assert_eq!(got[0].answer, "A");
        assert_eq!(got[1].answer, "B");
        assert_eq!(got[2].answer, "对");
    }

    #[test]
    fn upstream_batch_zip_skips_bad_member_but_keeps_valid_docx() {
        let doc = make_docx(&["1 【单选题】", "有效题", "正确答案：C"]);
        let archive = make_zip(&[
            ("001_坏文件.docx", b"not a docx".to_vec()),
            ("002_好文件.docx", doc),
            ("导出清单.txt", vec![]),
        ]);
        let got = import_temp_zip(archive).unwrap();
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].answer, "C");
    }

    #[test]
    fn upstream_batch_zip_without_docx_or_answers_is_rejected() {
        assert!(import_temp_zip(make_zip(&[("导出清单.txt", b"nothing".to_vec())])).is_err());
        let doc = make_docx(&[
            "1 【单选题】",
            "没有公布答案",
            "我的答案：A",
            "答案状态：错误",
        ]);
        assert!(import_temp_zip(make_zip(&[("001_空.docx", doc)])).is_err());
    }

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
