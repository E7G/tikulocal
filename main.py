import sys
import json
import sqlite3
import os
import re
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from docx import Document
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QStackedWidget, QTableWidgetItem, QFileDialog)
from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, QEasingCurve
from PyQt5.QtGui import QFont, QColor, QPainter, QBrush, QLinearGradient
from qfluentwidgets import (NavigationInterface, FluentIcon,
                            PushButton, LineEdit, TextEdit, ComboBox, BodyLabel, 
                            TitleLabel, SubtitleLabel, StrongBodyLabel, CaptionLabel,
                            PrimaryPushButton, CardWidget, SmoothScrollArea, InfoBar,
                            TableWidget, setTheme, Theme, setThemeColor, MessageBox,
                            FluentWindow, NavigationItemPosition)
from parser import QuestionParser


def apply_system_theme(app):
    try:
        setThemeColor("#0078d4")
        
        if sys.platform == 'win32':
            import winreg
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                winreg.CloseKey(key)
                if value == 0:
                    setTheme(Theme.DARK)
                    app.themeMode = Theme.DARK
                else:
                    setTheme(Theme.LIGHT)
                    app.themeMode = Theme.LIGHT
            except:
                setTheme(Theme.LIGHT)
                app.themeMode = Theme.LIGHT
        else:
            setTheme(Theme.LIGHT)
            app.themeMode = Theme.LIGHT
    except Exception:
        setTheme(Theme.LIGHT)
        app.themeMode = Theme.LIGHT


class ModernCard(CardWidget):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setBorderRadius(12)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(16)
        
        if title:
            title_label = StrongBodyLabel(title)
            layout.addWidget(title_label)
        
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(12)
        layout.addLayout(self.content_layout)
    
    def addWidget(self, widget):
        self.content_layout.addWidget(widget)
    
    def addLayout(self, layout):
        self.content_layout.addLayout(layout)


class SearchPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SearchPage")
        self.parent_window = parent
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)
        
        header_layout = QVBoxLayout()
        header_layout.setSpacing(8)
        
        title = TitleLabel("搜索题目")
        subtitle = CaptionLabel("输入题目关键词，快速查找答案")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addLayout(header_layout)
        
        search_card = ModernCard("题目搜索")
        layout.addWidget(search_card)
        
        question_layout = QHBoxLayout()
        question_layout.setSpacing(12)
        
        question_label = BodyLabel("题目内容")
        question_label.setFixedWidth(80)
        
        self.question_entry = LineEdit()
        self.question_entry.setPlaceholderText("请输入题目关键词...")
        self.question_entry.setClearButtonEnabled(True)
        
        question_layout.addWidget(question_label)
        question_layout.addWidget(self.question_entry)
        search_card.addLayout(question_layout)
        
        type_layout = QHBoxLayout()
        type_layout.setSpacing(12)
        
        type_label = BodyLabel("题目类型")
        type_label.setFixedWidth(80)
        
        self.type_combo = ComboBox()
        self.type_combo.addItems(['全部类型', '单选题', '多选题', '填空题', '判断题', '问答题'])
        
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_combo)
        type_layout.addStretch()
        search_card.addLayout(type_layout)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        search_btn = PrimaryPushButton("开始搜索")
        search_btn.setFixedHeight(38)
        search_btn.setFixedWidth(120)
        search_btn.clicked.connect(self.search_question)
        
        button_layout.addWidget(search_btn)
        search_card.addLayout(button_layout)
        
        result_card = ModernCard("搜索结果")
        layout.addWidget(result_card)
        
        self.result_text = TextEdit()
        self.result_text.setReadOnly(True)
        result_card.addWidget(self.result_text)
        
        layout.addStretch()
    
    def search_question(self):
        if self.parent_window:
            self.parent_window.search_question(self.question_entry.text(), self.type_combo.currentText(), self.result_text)


class ImportPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ImportPage")
        self.parent_window = parent
        self.initUI()
        self.setAcceptDrops(True)
    
    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)
        
        header_layout = QVBoxLayout()
        header_layout.setSpacing(8)
        
        title = TitleLabel("导入题库")
        subtitle = CaptionLabel("支持Word文档和JSON格式导入，可拖拽文件到此处")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addLayout(header_layout)
        
        import_card = ModernCard("文件导入")
        layout.addWidget(import_card)
        
        type_layout = QHBoxLayout()
        type_layout.setSpacing(12)
        
        type_label = BodyLabel("导入方式")
        type_label.setFixedWidth(80)
        
        self.import_type_combo = ComboBox()
        self.import_type_combo.addItems(['Word文档 (.docx)', 'JSON文件 (.json)'])
        
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.import_type_combo)
        type_layout.addStretch()
        import_card.addLayout(type_layout)
        
        path_layout = QHBoxLayout()
        path_layout.setSpacing(12)
        
        path_label = BodyLabel("文件路径")
        path_label.setFixedWidth(80)
        
        self.file_path_edit = LineEdit()
        self.file_path_edit.setPlaceholderText("请选择要导入的文件，或拖拽文件到此处...")
        self.file_path_edit.setClearButtonEnabled(True)
        
        browse_btn = PushButton("浏览...")
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self.browse_file)
        
        path_layout.addWidget(path_label)
        path_layout.addWidget(self.file_path_edit)
        path_layout.addWidget(browse_btn)
        import_card.addLayout(path_layout)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        import_btn = PrimaryPushButton("开始导入")
        import_btn.setFixedHeight(38)
        import_btn.setFixedWidth(120)
        import_btn.clicked.connect(self.import_file)
        
        button_layout.addWidget(import_btn)
        import_card.addLayout(button_layout)
        
        result_card = ModernCard("导入结果")
        layout.addWidget(result_card)
        
        self.import_result_text = TextEdit()
        self.import_result_text.setReadOnly(True)
        result_card.addWidget(self.import_result_text)
        
        layout.addStretch()
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
    
    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        
        if not files:
            return
        
        valid_files = []
        for file_path in files:
            if file_path.endswith('.docx') or file_path.endswith('.json'):
                valid_files.append(file_path)
        
        if not valid_files:
            InfoBar.warning(
                title='提示',
                content='请拖入 .docx 或 .json 文件',
                parent=self,
                duration=2000
            )
            return
        
        if len(valid_files) == 1:
            self.file_path_edit.setText(valid_files[0])
            if valid_files[0].endswith('.docx'):
                self.import_type_combo.setCurrentIndex(0)
            else:
                self.import_type_combo.setCurrentIndex(1)
        else:
            self.import_multiple_files(valid_files)
    
    def import_multiple_files(self, files):
        if self.parent_window:
            total_count = 0
            failed_files = []
            
            for file_path in files:
                try:
                    if file_path.endswith('.docx'):
                        count = self.parent_window.import_from_docx(file_path)
                    else:
                        count = self.parent_window.import_from_json(file_path)
                    total_count += count
                except Exception as e:
                    failed_files.append(os.path.basename(file_path))
            
            result_text = f"批量导入完成！\n成功导入 {total_count} 道题目"
            if failed_files:
                result_text += f"\n\n失败文件：\n" + "\n".join(failed_files)
            
            self.import_result_text.setText(result_text)
            
            if total_count > 0:
                InfoBar.success(
                    title='成功',
                    content=f'成功导入 {total_count} 道题目',
                    parent=self,
                    duration=2000
                )
            
            if failed_files:
                InfoBar.warning(
                    title='警告',
                    content=f'{len(failed_files)} 个文件导入失败',
                    parent=self,
                    duration=2000
                )
    
    def browse_file(self):
        if self.parent_window:
            self.parent_window.browse_file(self.import_type_combo.currentText(), self.file_path_edit)
    
    def import_file(self):
        if self.parent_window:
            self.parent_window.import_file(
                self.import_type_combo.currentText(),
                self.file_path_edit.text(),
                self.import_result_text
            )


class ManagePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ManagePage")
        self.parent_window = parent
        self.initUI()
        self.refresh_list()
    
    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)
        
        header_layout = QVBoxLayout()
        header_layout.setSpacing(8)
        
        title = TitleLabel("题库管理")
        subtitle = CaptionLabel("查看、删除和管理已导入的题目")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addLayout(header_layout)
        
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)
        
        self.total_card = self.create_stat_card("总题数", "0", "#0078d4")
        stats_layout.addWidget(self.total_card)
        
        self.single_card = self.create_stat_card("单选题", "0", "#107c10")
        stats_layout.addWidget(self.single_card)
        
        self.multi_card = self.create_stat_card("多选题", "0", "#e81123")
        stats_layout.addWidget(self.multi_card)
        
        self.judge_card = self.create_stat_card("判断题", "0", "#00897b")
        stats_layout.addWidget(self.judge_card)
        
        layout.addLayout(stats_layout)
        
        list_card = ModernCard("题目列表")
        layout.addWidget(list_card)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        refresh_btn = PushButton("刷新列表")
        refresh_btn.clicked.connect(self.refresh_list)
        
        delete_btn = PushButton("删除选中")
        delete_btn.clicked.connect(self.delete_selected)
        
        clear_btn = PushButton("清空题库")
        clear_btn.clicked.connect(self.clear_all)
        
        for btn in [refresh_btn, delete_btn, clear_btn]:
            btn_layout.addWidget(btn)
        
        btn_layout.addStretch()
        list_card.addLayout(btn_layout)
        
        from qfluentwidgets import TableWidget
        self.table = TableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(['ID', '题目内容', '题型', '选项', '答案', '导入时间'])
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 300)
        self.table.setColumnWidth(2, 70)
        self.table.setColumnWidth(3, 200)
        self.table.setColumnWidth(4, 100)
        self.table.setColumnWidth(5, 120)
        list_card.addWidget(self.table)
    
    def create_stat_card(self, title, value, color):
        card = CardWidget()
        card.setBorderRadius(12)
        card.setFixedSize(150, 100)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        
        title_label = CaptionLabel(title)
        value_label = TitleLabel(value)
        value_label.setStyleSheet(f"font-size: 24px; font-weight: 600; color: {color};")
        
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        
        return card
    
    def refresh_list(self):
        if self.parent_window:
            self.parent_window.refresh_question_list(self.table, self.total_card, self.single_card, self.multi_card, self.judge_card)
    
    def delete_selected(self):
        if self.parent_window:
            self.parent_window.delete_selected(self.table)
            self.refresh_list()
    
    def clear_all(self):
        if self.parent_window:
            self.parent_window.clear_all()
            self.refresh_list()


class TikuApp(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("题库适配器")
        self.resize(1000, 750)
        
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(base_path, "tiku.db")
        self.init_database()
        
        self.search_page = SearchPage(self)
        self.import_page = ImportPage(self)
        self.manage_page = ManagePage(self)
        
        self.addSubInterface(self.search_page, FluentIcon.SEARCH, '搜索题目')
        self.addSubInterface(self.import_page, FluentIcon.DOWNLOAD, '导入题库')
        self.addSubInterface(self.manage_page, FluentIcon.SETTING, '题库管理')
        
        self.start_http_server()
    
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            options TEXT,
            type INTEGER NOT NULL,
            answer TEXT NOT NULL,
            search_question TEXT,
            search_options TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        try:
            cursor.execute("SELECT search_question FROM questions LIMIT 1")
        except:
            cursor.execute("ALTER TABLE questions ADD COLUMN search_question TEXT")
        
        try:
            cursor.execute("SELECT search_options FROM questions LIMIT 1")
        except:
            cursor.execute("ALTER TABLE questions ADD COLUMN search_options TEXT")
        
        conn.commit()
        
        import string
        chinese_punctuation = '，。！？；：""''【】（）《》〈〉〔〕【】｛｝'
        all_punctuation = string.punctuation + chinese_punctuation + ' \t\n\r　\xa0'

        def remove_punctuation(text):
            return text.translate(str.maketrans('', '', all_punctuation))
        
        cursor.execute("SELECT id, question, options FROM questions WHERE search_question IS NULL OR search_question = ''")
        rows_to_update = cursor.fetchall()
        for row in rows_to_update:
            qid, qquestion, qoptions = row
            search_q = remove_punctuation(qquestion) if qquestion else ''
            search_o = remove_punctuation(qoptions) if qoptions else ''
            cursor.execute("UPDATE questions SET search_question = ?, search_options = ? WHERE id = ?", (search_q, search_o, qid))
        
        conn.commit()
        conn.close()
    
    def search_question(self, question_text, type_text, result_widget):
        import string
        
        chinese_punctuation = '，。！？；：""''【】（）《》〈〉〔〕【】｛｝'
        all_punctuation = string.punctuation + chinese_punctuation + ' \t\n\r　\xa0'
        
        def remove_punctuation(text):
            return text.translate(str.maketrans('', '', all_punctuation))
        
        if not question_text.strip():
            InfoBar.warning(
                title='提示',
                content='请输入题目内容',
                parent=self,
                duration=2000
            )
            return
        
        type_map = {'全部类型': -1, '单选题': 0, '多选题': 1, '填空题': 2, '判断题': 3, '问答题': 4}
        type_text_map = {0: '单选题', 1: '多选题', 2: '填空题', 3: '判断题', 4: '问答题'}
        type_ = type_map.get(type_text, -1)
        
        clean_search = remove_punctuation(question_text)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if type_ == -1:
            cursor.execute(
                "SELECT question, options, type, answer, search_question, search_options FROM questions"
            )
        else:
            cursor.execute(
                "SELECT question, options, type, answer, search_question, search_options FROM questions WHERE type = ?",
                (type_,)
            )
        
        all_questions = cursor.fetchall()
        conn.close()
        
        results = []
        for q in all_questions:
            db_search_question = q[4] if len(q) > 4 else ''
            db_search_options = q[5] if len(q) > 5 else ''
            
            if db_search_question and (clean_search in db_search_question or db_search_question in clean_search):
                results.append(q)
                continue
            
            if db_search_options:
                if clean_search in db_search_options:
                    results.append(q)
                    continue
        
        if not results:
            result_widget.setText("未找到相关题目")
            return
        
        output_lines = []
        output_lines.append(f"共找到 {len(results)} 道相关题目：")
        output_lines.append("")
        
        for i, r in enumerate(results, 1):
            question = r[0]
            options_json = r[1]
            db_type = r[2]
            answer_text = r[3]
            
            try:
                options = json.loads(options_json) if options_json else []
            except:
                options = []
            
            output_lines.append(f"【{i}】{type_text_map.get(db_type, '未知题型')} - 答案：{answer_text}")
            output_lines.append(f"题目：{question}")
            
            if options:
                output_lines.append("选项：")
                for j, opt in enumerate(options):
                    label = chr(65 + j) if j < 26 else str(j)
                    output_lines.append(f"  {label}. {opt}")
            
            output_lines.append("")
        
        result_widget.setText("\n".join(output_lines))
    
    def browse_file(self, type_text, path_widget):
        if 'Word' in type_text:
            file_path, _ = QFileDialog.getOpenFileName(self, "选择Word文件", "", "Word文档 (*.docx);;所有文件 (*.*)")
        else:
            file_path, _ = QFileDialog.getOpenFileName(self, "选择JSON文件", "", "JSON文件 (*.json);;所有文件 (*.*)")
        
        if file_path:
            path_widget.setText(file_path)
    
    def import_file(self, type_text, file_path, result_widget):
        if not file_path.strip():
            InfoBar.warning(
                title='提示',
                content='请选择文件',
                parent=self,
                duration=2000
            )
            return
        
        if not os.path.exists(file_path):
            InfoBar.error(
                title='错误',
                content='文件不存在',
                parent=self,
                duration=2000
            )
            return
        
        try:
            if 'Word' in type_text:
                count = self.import_from_docx(file_path)
            else:
                count = self.import_from_json(file_path)
            
            result_widget.setText(f"成功导入 {count} 道题目")
            InfoBar.success(
                title='成功',
                content=f'成功导入 {count} 道题目',
                parent=self,
                duration=2000
            )
        except Exception as e:
            result_widget.setText(f"导入失败: {str(e)}")
            InfoBar.error(
                title='错误',
                content=f'导入失败: {str(e)}',
                parent=self,
                duration=3000
            )
    
    def import_from_docx(self, file_path):
        import string
        
        chinese_punctuation = '，。！？；：""''【】（）《》〈〉〔〕【】｛｝'
        all_punctuation = string.punctuation + chinese_punctuation + ' \t\n\r　\xa0'
        
        def remove_punctuation(text):
            return text.translate(str.maketrans('', '', all_punctuation))
        
        doc = Document(file_path)
        
        parser = QuestionParser()
        questions = parser.parse_from_docx(doc)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        count = 0
        for q in questions:
            if q.answer:
                options_json = json.dumps(q.options) if q.options else '[]'
                search_question = remove_punctuation(q.content)
                search_options = remove_punctuation(options_json)
                cursor.execute(
                    "INSERT INTO questions (question, options, type, answer, search_question, search_options) VALUES (?, ?, ?, ?, ?, ?)",
                    (q.content, options_json, q.question_type.value, q.answer, search_question, search_options)
                )
                count += 1
        
        conn.commit()
        conn.close()
        
        return count
    
    def import_from_json(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        count = 0
        for item in data:
            question = item.get('question', '')
            options = item.get('options', [])
            type_ = item.get('type', 0)
            answer = item.get('answer', '')
            
            if question and answer:
                options_json = json.dumps(options)
                cursor.execute(
                    "INSERT INTO questions (question, options, type, answer) VALUES (?, ?, ?, ?)",
                    (question, options_json, type_, answer)
                )
                count += 1
        
        conn.commit()
        conn.close()
        
        return count
    
    def build_answer(self, answer_text, options, question_type):
        answer = {
            "answerKey": [],
            "answerKeyText": "",
            "answerIndex": [],
            "answerText": answer_text,
            "bestAnswer": [],
            "allAnswer": [[]]
        }
        
        if question_type in [0, 1]:
            answer_keys = re.findall(r'[A-Za-z]', answer_text)
            answer["answerKey"] = answer_keys
            answer["answerKeyText"] = ''.join(answer_keys)
            
            answer["answerIndex"] = [ord(key.upper()) - ord('A') for key in answer_keys if ord(key.upper()) - ord('A') < len(options)]
            
            best_answers = []
            for key in answer_keys:
                idx = ord(key.upper()) - ord('A')
                if idx < len(options):
                    best_answers.append(options[idx])
            
            if best_answers:
                answer["bestAnswer"] = best_answers
                answer["answerText"] = '#'.join(best_answers)
                format1 = best_answers
                format2 = [f"{key}{options[ord(key.upper()) - ord('A')]}" for key in answer_keys if ord(key.upper()) - ord('A') < len(options)]
                answer["allAnswer"] = [format1, format2] if format2 else [format1]
            else:
                answer["bestAnswer"] = [answer_text]
                answer["allAnswer"] = [[answer_text]]
        
        elif question_type == 3:
            answer["answerKey"] = [answer_text] if answer_text in ['对', '错', '正确', '错误', 'A', 'B'] else []
            answer["answerKeyText"] = answer["answerKey"][0] if answer["answerKey"] else ''
            
            if answer_text in ['对', '正确', 'A']:
                answer["answerIndex"] = [0] if len(options) > 0 else []
                answer["bestAnswer"] = [options[0]] if len(options) > 0 else ['对']
                answer["allAnswer"] = [answer["bestAnswer"]]
            elif answer_text in ['错', '错误', 'B']:
                answer["answerIndex"] = [1] if len(options) > 1 else []
                answer["bestAnswer"] = [options[1]] if len(options) > 1 else ['错']
                answer["allAnswer"] = [answer["bestAnswer"]]
        
        return answer
    
    def refresh_question_list(self, table, total_card, single_card, multi_card, judge_card):
        table.clearContents()
        table.setRowCount(0)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM questions")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM questions WHERE type = 0")
        single = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM questions WHERE type = 1")
        multi = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM questions WHERE type = 3")
        judge = cursor.fetchone()[0]
        
        cursor.execute("SELECT id, question, type, options, answer, created_at FROM questions ORDER BY created_at DESC LIMIT 100")
        
        type_map = {0: '单选题', 1: '多选题', 2: '填空题', 3: '判断题', 4: '问答题'}
        
        for row in cursor.fetchall():
            question_text = row[1][:60] + '...' if len(row[1]) > 60 else row[1]
            
            try:
                options = json.loads(row[3]) if row[3] else []
                options_text = '; '.join([f"{chr(65+i)}.{opt}" for i, opt in enumerate(options[:3])])
                if len(options) > 3:
                    options_text += '...'
            except:
                options_text = ''
            
            answer_text = row[4][:20] + '...' if row[4] and len(row[4]) > 20 else (row[4] if row[4] else '')
            
            row_items = [QTableWidgetItem(str(row[0])), 
                        QTableWidgetItem(question_text),
                        QTableWidgetItem(type_map.get(row[2], '未知')),
                        QTableWidgetItem(options_text),
                        QTableWidgetItem(answer_text),
                        QTableWidgetItem(row[5])]
            table.insertRow(table.rowCount())
            for col, item in enumerate(row_items):
                table.setItem(table.rowCount() - 1, col, item)
        
        conn.close()
        
        for card, value in [(total_card, total), (single_card, single), (multi_card, multi), (judge_card, judge)]:
            layout = card.layout()
            if layout and layout.count() >= 2:
                value_item = layout.itemAt(1)
                if value_item and value_item.widget():
                    value_item.widget().setText(str(value))
    
    def delete_selected(self, table):
        selected = table.selectedItems()
        if not selected:
            InfoBar.warning(
                title='提示',
                content='请选择要删除的题目',
                parent=self,
                duration=2000
            )
            return
        
        messageBox = MessageBox("确认", "确定要删除选中的题目吗？", self)
        if messageBox.exec() != MessageBox.Accepted:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        rows = set(item.row() for item in selected)
        for row in rows:
            id_item = table.item(row, 0)
            if id_item:
                cursor.execute("DELETE FROM questions WHERE id = ?", (id_item.text(),))
        
        conn.commit()
        conn.close()
        
        InfoBar.success(
            title='成功',
            content='删除成功',
            parent=self,
            duration=2000
        )
    
    def clear_all(self):
        messageBox = MessageBox("确认", "确定要清空整个题库吗？此操作不可恢复！", self)
        if messageBox.exec() != MessageBox.Accepted:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM questions")
        conn.commit()
        conn.close()
        
        InfoBar.success(
            title='成功',
            content='题库已清空',
            parent=self,
            duration=2000
        )
    
    def start_http_server(self):
        import string
        
        chinese_punctuation = '，。！？；：""''【】（）《》〈〉〔〕【】｛｝'
        all_punctuation = string.punctuation + chinese_punctuation + ' \t\n\r　\xa0'
        
        def remove_punctuation(text):
            return text.translate(str.maketrans('', '', all_punctuation))
        
        class RequestHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                path = self.path.split('?')[0]
                if path == '/adapter-service/search':
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    
                    try:
                        request_data = json.loads(post_data)
                        question = request_data.get('question', '')
                        options = request_data.get('options', [])
                        type_ = request_data.get('type', 0)
                        
                        clean_question = remove_punctuation(question)
                        clean_options = [remove_punctuation(opt) for opt in options]
                        
                        conn = sqlite3.connect(self.server.app.db_path)
                        cursor = conn.cursor()
                        
                        cursor.execute(
                            "SELECT question, options, type, answer, search_question, search_options FROM questions"
                        )
                        
                        all_questions = cursor.fetchall()
                        conn.close()
                        
                        scored_results = []
                        for q in all_questions:
                            db_question = q[0]
                            db_search_question = q[4]
                            db_search_options = q[5] if len(q) > 5 else ''
                            
                            score = 0
                            
                            if db_search_question:
                                if clean_question == db_search_question:
                                    score += 100
                                elif clean_question in db_search_question or db_search_question in clean_question:
                                    score += 50
                                
                                if clean_options and db_search_options:
                                    option_matches = 0
                                    for clean_opt in clean_options:
                                        if clean_opt and clean_opt in db_search_options:
                                            option_matches += 1
                                    
                                    if option_matches == len(clean_options) and len(clean_options) > 0:
                                        score += 50
                                    elif option_matches > 0:
                                        score += option_matches * 10
                            
                            if score > 0:
                                scored_results.append((score, q))
                        
                        scored_results.sort(key=lambda x: x[0], reverse=True)
                        
                        results = [r[1] for r in scored_results[:10]]
                        
                        if not results:
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps({
                                "plat": 0,
                                "question": question,
                                "options": options,
                                "type": type_,
                                "answer": {
                                    "answerKey": [],
                                    "answerKeyText": "",
                                    "answerIndex": [],
                                    "answerText": "",
                                    "bestAnswer": [],
                                    "allAnswer": []
                                }
                            }).encode('utf-8'))
                            return
                        
                        best_match = results[0]
                        question_text = best_match[0]
                        options_json = best_match[1]
                        db_type = best_match[2]
                        answer_text = best_match[3]
                        
                        try:
                            db_options = json.loads(options_json) if options_json else []
                        except:
                            db_options = []
                        
                        answer = self.server.app.build_answer(answer_text, db_options, db_type)
                        
                        response = {
                            "plat": 0,
                            "question": question_text,
                            "options": db_options,
                            "type": db_type,
                            "answer": answer
                        }
                        
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
                        
                    except Exception as e:
                        self.send_response(500)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
                else:
                    self.send_response(404)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b'404 Not Found')
            
            def do_GET(self):
                path = self.path.split('?')[0]
                if path == '/':
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    html = '''<html><head><title>题库适配器 API</title></head>
                    <body><h1>题库适配器 API</h1>
                    <p>使用 POST 请求访问 /adapter-service/search 端点</p></body></html>'''
                    self.wfile.write(html.encode('utf-8'))
                elif path.startswith('/adapter-service'):
                    response_body = b'{"status": "ok"}'
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Content-Length', str(len(response_body)))
                    self.end_headers()
                    self.wfile.write(response_body)
                else:
                    self.send_response(404)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
            
            def do_HEAD(self):
                path = self.path.split('?')[0]
                if path == '/':
                    html = '''<html><head><title>题库适配器 API</title></head>
                    <body><h1>题库适配器 API</h1>
                    <p>使用 POST 请求访问 /adapter-service/search 端点</p></body></html>'''
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.send_header('Content-Length', str(len(html)))
                    self.end_headers()
                    self.wfile.write(html.encode('utf-8'))
                elif path.startswith('/adapter-service'):
                    response_body = b'{"status": "ok"}'
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Content-Length', str(len(response_body)))
                    self.end_headers()
                    self.wfile.write(response_body)
                else:
                    self.send_response(404)
                    self.send_header('Content-type', 'text/plain')
                    self.send_header('Content-Length', '0')
                    self.end_headers()
        
        server = HTTPServer(('localhost', 8060), RequestHandler)
        server.app = self
        
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        print("HTTP 服务器已启动，监听端口 8060")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_system_theme(app)
    window = TikuApp()
    window.show()
    sys.exit(app.exec_())
