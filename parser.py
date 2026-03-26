import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
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
            'question': self.content,
            'options': self.options,
            'type': self.question_type.value,
            'answer': self.answer,
            'my_answer': self.my_answer,
            'answer_status': self.answer_status,
            'score': self.score
        }


class QuestionParser:
    def __init__(self):
        self.questions: List[Question] = []
    
    def parse(self, paragraphs: List[str]) -> List[Question]:
        self.questions = []
        current_question = None
        current_options = []
        i = 0
        
        while i < len(paragraphs):
            text = paragraphs[i].strip()
            
            if not text:
                i += 1
                continue
            
            question_match = self._match_question_header(text)
            if question_match:
                if current_question:
                    self._finalize_question(current_question, current_options)
                
                question_number = question_match.group(1)
                question_type_text = question_match.group(2)
                question_type = self._parse_question_type(question_type_text)
                
                current_question = Question(
                    number=int(question_number),
                    content="",
                    options=[],
                    question_type=question_type
                )
                current_options = []
                i += 1
                
                if i < len(paragraphs):
                    content = paragraphs[i].strip()
                    if content and not self._is_option_line(content) and not self._is_answer_line(content):
                        current_question.content = content
                        i += 1
                continue
            
            if current_question:
                if text == "选项：":
                    i += 1
                    continue
                
                option_match = self._match_option(text)
                if option_match:
                    option_text = option_match.group(2).strip()
                    current_options.append(option_text)
                    i += 1
                    continue
                
                answer_match = self._match_my_answer(text)
                if answer_match:
                    current_question.my_answer = answer_match.group(1).strip()
                    i += 1
                    continue
                
                status_match = self._match_answer_status(text)
                if status_match:
                    current_question.answer_status = status_match.group(1).strip()
                    i += 1
                    continue
                
                correct_match = self._match_correct_answer(text)
                if correct_match:
                    current_question.answer = correct_match.group(1).strip()
                    i += 1
                    continue
                
                score_match = self._match_score(text)
                if score_match:
                    current_question.score = score_match.group(1).strip()
                    i += 1
                    continue
            
            i += 1
        
        if current_question:
            self._finalize_question(current_question, current_options)
        
        return self.questions
    
    def parse_from_docx(self, doc: Document) -> List[Question]:
        self.questions = []
        current_question = None
        current_options = []
        
        for para in doc.paragraphs:
            text = para.text.strip()
            
            if not text:
                continue
            
            question_match = self._match_question_header(text)
            if question_match:
                if current_question:
                    self._finalize_question(current_question, current_options)
                
                question_number = question_match.group(1)
                question_type_text = question_match.group(2)
                question_type = self._parse_question_type(question_type_text)
                
                current_question = Question(
                    number=int(question_number),
                    content="",
                    options=[],
                    question_type=question_type
                )
                current_options = []
                continue
            
            if current_question:
                if text == "选项：":
                    continue
                
                if self._is_option_line(text):
                    options = self._extract_options_from_paragraph(para)
                    current_options.extend(options)
                    continue
                
                answer_match = self._match_my_answer(text)
                if answer_match:
                    current_question.my_answer = answer_match.group(1).strip()
                    continue
                
                status_match = self._match_answer_status(text)
                if status_match:
                    current_question.answer_status = status_match.group(1).strip()
                    continue
                
                correct_match = self._match_correct_answer(text)
                if correct_match:
                    current_question.answer = correct_match.group(1).strip()
                    continue
                
                score_match = self._match_score(text)
                if score_match:
                    current_question.score = score_match.group(1).strip()
                    continue
                
                if not current_question.content:
                    current_question.content = text
        
        if current_question:
            self._finalize_question(current_question, current_options)
        
        return self.questions
    
    def _extract_options_from_paragraph(self, para) -> List[str]:
        options = []
        
        for run in para.runs:
            for child in run._element:
                if child.tag.endswith('}t'):
                    text = child.text
                    if text:
                        option_parts = [text]
                        
                        # 检查子元素中的<w:br/>标签
                        for subchild in child:
                            if subchild.tag.endswith('}br') and subchild.tail:
                                option_parts.append(subchild.tail.strip())
                        
                        for part in option_parts:
                            part = part.strip()
                            if part and self._is_option_line(part):
                                option_match = self._match_option(part)
                                if option_match:
                                    option_text = option_match.group(2).strip()
                                    options.append(option_text)
        
        return options
    
    def _match_question_header(self, text: str) -> Optional[re.Match]:
        return re.match(r'^(\d+)[.、．]\s*【(.+题)】$', text)
    
    def _match_option(self, text: str) -> Optional[re.Match]:
        return re.match(r'^([A-Z])、\s*(.+)$', text)
    
    def _match_my_answer(self, text: str) -> Optional[re.Match]:
        return re.match(r'^我的答案[:：]\s*(.+)$', text)
    
    def _match_answer_status(self, text: str) -> Optional[re.Match]:
        return re.match(r'^答案状态[:：]\s*(.+)$', text)
    
    def _match_correct_answer(self, text: str) -> Optional[re.Match]:
        return re.match(r'^正确答案[:：]\s*(.+)$', text)
    
    def _match_score(self, text: str) -> Optional[re.Match]:
        return re.match(r'^得分[:：]\s*(.+)$', text)
    
    def _is_option_line(self, text: str) -> bool:
        return bool(re.match(r'^[A-Z]、', text))
    
    def _is_answer_line(self, text: str) -> bool:
        return bool(re.match(r'^(我的答案|答案状态|正确答案|得分)[:：]', text))
    
    def _parse_question_type(self, type_text: str) -> QuestionType:
        type_mapping = {
            '单选题': QuestionType.SINGLE_CHOICE,
            '多选题': QuestionType.MULTIPLE_CHOICE,
            '填空题': QuestionType.FILL_BLANK,
            '判断题': QuestionType.TRUE_FALSE,
            '问答题': QuestionType.ESSAY
        }
        return type_mapping.get(type_text, QuestionType.ESSAY)
    
    def _finalize_question(self, question: Question, options: List[str]):
        question.options = options
        if question.answer is None and question.answer_status == "正确" and question.my_answer:
            question.answer = question.my_answer
        self.questions.append(question)
