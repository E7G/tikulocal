import unittest
from docx import Document

from parser import QuestionParser, QuestionType


class QuestionParserTests(unittest.TestCase):
    def setUp(self):
        self.parser = QuestionParser()

    def test_common_option_punctuation_is_supported(self):
        cases = [
            ("A. 第一项", "第一项"),
            ("B、第二项", "第二项"),
            ("C．第三项", "第三项"),
            ("D) 第四项", "第四项"),
            ("E）第五项", "第五项"),
        ]
        for source, expected in cases:
            with self.subTest(source=source):
                match = self.parser._match_option(source)
                self.assertIsNotNone(match)
                self.assertEqual(match.group(2), expected)

    def test_plain_text_parser_reads_options_and_answer(self):
        questions = self.parser.parse([
            "1 【单选题】",
            "下列哪一项是示例题目？",
            "A. 第一项",
            "B、第二项",
            "正确答案：B",
        ])
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0].question_type, QuestionType.SINGLE_CHOICE)
        self.assertEqual(questions[0].options, ["第一项", "第二项"])
        self.assertEqual(questions[0].answer, "B")

    def test_word_paragraph_with_line_breaks_reads_all_options(self):
        document = Document()
        paragraph = document.add_paragraph()
        paragraph.add_run("A. 第一项\nB、第二项\nC．第三项")
        options = self.parser._extract_options_from_paragraph(paragraph)
        self.assertEqual(options, ["第一项", "第二项", "第三项"])


if __name__ == "__main__":
    unittest.main()