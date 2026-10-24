"""Read question/answer documents from the Chaoxing/Ulearning/Yuketang Word exporter.

Only an explicit, usable 正确答案/标准答案/参考答案 is accepted.
"我的答案" and "答案状态：正确" are never promoted to a correct answer.
"""
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from docx import Document


class QuestionType(Enum):
    SINGLE_CHOICE = 0
    MULTIPLE_CHOICE = 1
    FILL_BLANK = 2
    TRUE_FALSE = 3
    ESSAY = 4


@dataclass
class Question:
    number: int
    content: str
    options: List[str]
    question_type: QuestionType
    answer: Optional[str] = None
    my_answer: Optional[str] = None
    answer_status: Optional[str] = None
    score: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question": self.content,
            "options": self.options,
            "type": self.question_type.value,
            "answer": self.answer,
            "my_answer": self.my_answer,
            "answer_status": self.answer_status,
            "score": self.score,
        }


TYPE_NAMES = {
    "单选题": QuestionType.SINGLE_CHOICE,
    "单项选择题": QuestionType.SINGLE_CHOICE,
    "多选题": QuestionType.MULTIPLE_CHOICE,
    "多项选择题": QuestionType.MULTIPLE_CHOICE,
    "填空题": QuestionType.FILL_BLANK,
    "判断题": QuestionType.TRUE_FALSE,
    "判断正误题": QuestionType.TRUE_FALSE,
    "是非题": QuestionType.TRUE_FALSE,
    "问答题": QuestionType.ESSAY,
    "简答题": QuestionType.ESSAY,
    "论述题": QuestionType.ESSAY,
}

TYPE_PATTERN = "|".join(sorted(map(re.escape, TYPE_NAMES), key=len, reverse=True))
# Exporter examples: "1 【单选题】", "【多选题】", "1. 单选题",
# "2 (判断题)", "3、单选题", "单选题：".
HEADER_RE = re.compile(
    r"^\s*(?:(?:第\s*)?(\d+)\s*(?:[.．、):：号题]\s*)?)?"
    r"[【\[\(（]?\s*(" + TYPE_PATTERN + r")\s*[】\]\)）]?"
    r"(?:\s*[:：]\s*|\s+)?(.*)$"
)
ANSWER_RE = re.compile(r"^\s*(?:正确|标准|参考)答案\s*[:：]\s*(.*)$")
MY_ANSWER_RE = re.compile(r"^\s*(?:我的|用户|学生)答案\s*[:：]\s*(.*)$")
STATUS_RE = re.compile(r"^\s*(?:答案状态|作答状态|批改状态)\s*[:：]\s*(.*)$")
SCORE_RE = re.compile(r"^\s*(?:得分|分数)\s*[:：]\s*(.*)$")
ANALYSIS_RE = re.compile(r"^\s*(?:答案解析|试题解析|解析)\s*[:：]")
OPTION_RE = re.compile(r"^\s*([A-ZＡ-Ｚ])\s*[.．、:：)）]\s*(.+?)\s*$")
RELAXED_OPTION_RE = re.compile(r"^\s*([A-ZＡ-Ｚ])\s+(.+?)\s*$")
FILL_LABEL_RE = re.compile(r"(?:第\s*[一二三四五六七八九十百\d]+\s*空\s*[:：]\s*)")
EMPTY_ANSWERS = {
    "", "无", "暂无", "暂无答案", "未公布", "未提供", "未知", "不详", "null",
    "none", "-", "--", "未作答", "无答案", "待公布", "待批改",
}


def _unify_option_label(value: str) -> str:
    # Convert full-width ABC to ASCII and preserve the option text.
    return "".join(
        chr(ord(ch) - ord("Ａ") + ord("A")) if "Ａ" <= ch <= "Ｚ" else ch
        for ch in value
    )


def _answer_is_known(answer: str) -> bool:
    return bool(answer.strip()) and answer.strip().casefold() not in EMPTY_ANSWERS


class QuestionParser:
    """Extract reliable (question, correct answer) records from exported Word."""

    def __init__(self):
        self.questions: List[Question] = []
        self.stats: Dict[str, int] = {}

    def parse(self, paragraphs: List[str]) -> List[Question]:
        return self._parse_records(paragraphs)

    def parse_from_docx(self, doc: Document) -> List[Question]:
        # The userscript writes one Word paragraph per "parts.push(...)" and
        # inserts an empty paragraph between questions. Some old files instead
        # put several logical lines in a single paragraph.
        return self._parse_records([para.text for para in doc.paragraphs])

    def _extract_options_from_paragraph(self, para) -> List[str]:
        """Compatibility helper used by Word option-parsing callers."""
        options = []
        for line in para.text.splitlines():
            match = self._match_option(line.strip(), in_options=True)
            if match:
                options.append(match.group(2).strip())
        return options

    def _match_question_header(self, text: str):
        match = HEADER_RE.match(text)
        if not match:
            return None
        # Avoid identifying ordinary words that happen to begin with a type name.
        if match.group(3) and not (
            re.match(r"^\s*(?:\d+|第|[【\[\(（])", text)
            or re.match(r"^\s*(" + TYPE_PATTERN + r")\s*[:：(（]", text)
            or re.match(r"^\s*(" + TYPE_PATTERN + r")\s+第\s*\d+", text)
        ):
            return None
        return match

    def _match_option(self, text: str, in_options=False):
        match = OPTION_RE.match(text)
        if not match and in_options:
            match = RELAXED_OPTION_RE.match(text)
        return match

    def _parse_records(self, paragraphs: List[str]) -> List[Question]:
        self.questions = []
        self.stats = {
            "seen": 0,
            "imported": 0,
            "skipped_no_correct_answer": 0,
            "skipped_empty_question": 0,
            "skipped_unusable_answer": 0,
        }
        current = None
        in_options = False
        in_analysis = False
        has_explicit_correct_answer = False
        awaiting_correct_answer = False

        def create_question(number=None, question_type=None):
            return Question(
                number=number or (self.stats["seen"] + 1),
                content="",
                options=[],
                question_type=question_type or QuestionType.ESSAY,
            )

        def finalize():
            nonlocal current, in_options, in_analysis, has_explicit_correct_answer, awaiting_correct_answer
            if current is None:
                return
            self.stats["seen"] += 1
            current.content = current.content.strip()
            current.answer = (current.answer or "").strip()

            if not current.content:
                self.stats["skipped_empty_question"] += 1
            elif not has_explicit_correct_answer or not _answer_is_known(current.answer):
                self.stats["skipped_no_correct_answer"] += 1
            else:
                normalized = self._normalize_answer(current.answer, current)
                if not normalized:
                    self.stats["skipped_unusable_answer"] += 1
                else:
                    current.answer = normalized
                    self.questions.append(current)
                    self.stats["imported"] += 1

            current = None
            in_options = False
            in_analysis = False
            has_explicit_correct_answer = False
            awaiting_correct_answer = False

        for paragraph in paragraphs:
            if paragraph is None:
                paragraph = ""
            # A paragraph can contain manual line breaks from an old Word file.
            lines = str(paragraph).splitlines() or [""]
            for raw_line in lines:
                line = raw_line.strip()
                if not line:
                    # Exporter inserts a blank paragraph after each question.
                    # A blank line within options/question content does not
                    # delimit a record; only a blank after an answer/analysis does.
                    if current and not awaiting_correct_answer and (
                        has_explicit_correct_answer or current.my_answer
                        or current.answer_status or in_analysis
                    ):
                        finalize()
                    continue

                header = self._match_question_header(line)
                if header:
                    finalize()
                    number_text, type_text, remainder = header.groups()
                    current = create_question(
                        int(number_text) if number_text else None, TYPE_NAMES[type_text]
                    )
                    remainder = remainder.strip()
                    if remainder and not re.fullmatch(r"[（(][^）)]*(?:分|题号)[^）)]*[）)]", remainder):
                        current.content = remainder
                    in_options = False
                    in_analysis = False
                    continue

                # Source may omit a type heading (some Ulearning / raw Chaoxing).
                # We still only keep it when an explicit "正确答案" appears.
                if current is None:
                    current = create_question()

                correct = ANSWER_RE.match(line)
                if correct:
                    current.answer = correct.group(1).strip()
                    has_explicit_correct_answer = True
                    awaiting_correct_answer = not bool(current.answer)
                    in_options = False
                    in_analysis = False
                    continue

                my_answer = MY_ANSWER_RE.match(line)
                if my_answer:
                    current.my_answer = my_answer.group(1).strip()
                    in_options = False
                    continue

                status = STATUS_RE.match(line)
                if status:
                    current.answer_status = status.group(1).strip()
                    in_options = False
                    continue

                score = SCORE_RE.match(line)
                if score:
                    current.score = score.group(1).strip()
                    in_options = False
                    continue

                if ANALYSIS_RE.match(line):
                    in_analysis = True
                    in_options = False
                    continue

                if in_analysis:
                    continue

                if awaiting_correct_answer:
                    if not re.match(r"^(?:我的答案|答案状态|得分|选项)\s*[:：]", line):
                        current.answer = line
                        awaiting_correct_answer = False
                        continue
                    awaiting_correct_answer = False

                if re.fullmatch(r"选项\s*[:：]", line):
                    in_options = True
                    continue

                option_match = self._match_option(line, in_options=in_options)
                if option_match and not has_explicit_correct_answer:
                    current.options.append(option_match.group(2).strip())
                    in_options = True
                    continue

                # The Chaoxing / Yuketang exporter sometimes places the image in
                # its own paragraph. An image-only stem cannot be queried as text;
                # empty stems will be omitted safely rather than corrupting others.
                if not has_explicit_correct_answer and not in_options:
                    current.content += ("\n" if current.content else "") + line

        finalize()
        return self.questions

    def _normalize_answer(self, raw_answer: str, question: Question) -> Optional[str]:
        answer = raw_answer.strip()
        if not _answer_is_known(answer):
            return None

        answer = _unify_option_label(answer)
        if question.question_type == QuestionType.TRUE_FALSE:
            normalized = answer.casefold().strip()
            normalized = re.sub(r"^[ab]\s*[.．、:：)）]\s*", "", normalized)
            if normalized in {"对", "正确", "是", "√", "true", "t", "a"}:
                return "对"
            if normalized in {"错", "错误", "否", "×", "false", "f", "b"}:
                return "错"
            return None

        # If the type was omitted by the exporter, infer only from a trustworthy
        # explicit answer + options, never from "我的答案".
        if question.question_type == QuestionType.ESSAY and question.options:
            labels = self._choice_answer_keys(answer, question.options)
            if labels:
                question.question_type = (
                    QuestionType.SINGLE_CHOICE if len(labels) == 1
                    else QuestionType.MULTIPLE_CHOICE
                )
                return "".join(labels)

        if question.question_type in (
            QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE
        ):
            labels = self._choice_answer_keys(answer, question.options)
            if not labels:
                return None
            if question.question_type == QuestionType.SINGLE_CHOICE and len(labels) != 1:
                return None
            return "".join(labels)

        if question.question_type == QuestionType.FILL_BLANK:
            # The exporter emits "第1空：x；第2空：y" or "x；y".
            answer = FILL_LABEL_RE.sub("", answer).strip()
            return answer if _answer_is_known(answer) else None

        # Unknown type with a true/false answer.
        if question.question_type == QuestionType.ESSAY and not question.options:
            if answer in {"对", "错", "正确", "错误", "√", "×"}:
                question.question_type = QuestionType.TRUE_FALSE
                return "对" if answer in {"对", "正确", "√"} else "错"
        return answer

    @staticmethod
    def _choice_answer_keys(answer: str, options: List[str]) -> List[str]:
        # Some exporter pages expose the correct option label but not the option
        # content. The explicit label is still usable as an answer.
        if not options:
            cleaned = re.sub(r"[\s,，、;；/&＋+]+", "", answer.upper())
            if re.fullmatch(r"[A-Z]+", cleaned):
                return list(dict.fromkeys(cleaned))
            return []
        max_label = min(26, len(options))
        valid_keys = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ"[:max_label])
        text = answer.strip().upper()

        # Plain "AB", "A,C", "A、C", "A/C".
        if re.fullmatch(r"[A-Z\s,，、;；/&＋+]+", text):
            labels = [ch for ch in text if ch in valid_keys]
            if labels and not any(ch not in valid_keys for ch in text if "A" <= ch <= "Z"):
                return list(dict.fromkeys(labels))

        # "A. 选项内容；C. 选项内容" (if multiple labeled choices).
        leading_labels = re.findall(r"(?:^|[;；,，\n])\s*([A-Z])\s*[.．、:：)）]", text)
        if leading_labels and all(ch in valid_keys for ch in leading_labels):
            return list(dict.fromkeys(leading_labels))

        # Full answer text matching a choice exactly, with or without A. prefix.
        for index, option in enumerate(options[:26]):
            candidate = str(option).strip()
            candidate = re.sub(r"^\s*[A-ZＡ-Ｚ]\s*[.．、:：)）]\s*", "", candidate)
            if candidate and candidate.casefold() == answer.strip().casefold():
                return [chr(65 + index)]
        return []
