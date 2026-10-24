import sys
import json
import sqlite3
import os
import re
import threading
import string
from flask import Flask, request, jsonify
from docx import Document
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QStackedWidget, QTableWidgetItem, QFileDialog,
                             QAbstractItemView, QListWidget, QListWidgetItem)
from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, QEasingCurve
from PyQt5.QtGui import QFont, QColor, QPainter, QBrush, QLinearGradient
from qfluentwidgets import (NavigationInterface, FluentIcon,
                            PushButton, LineEdit, TextEdit, ComboBox, BodyLabel, 
                            TitleLabel, SubtitleLabel, StrongBodyLabel, CaptionLabel,
                            PrimaryPushButton, CardWidget, SmoothScrollArea, InfoBar,
                            TableWidget, setTheme, Theme, setThemeColor, MessageBox,
                            FluentWindow, NavigationItemPosition)
from parser import QuestionParser


NORMALIZATION_PUNCTUATION = string.punctuation + '，。！？；：""''【】（）《》〈〉〔〕｛｝ \t\n\r\u3000\u00a0'
NORMALIZATION_TRANSLATION = str.maketrans('', '', NORMALIZATION_PUNCTUATION)


def normalize_text(value):
    """Normalize text consistently for desktop search, API search and imports."""
    return str(value or '').casefold().translate(NORMALIZATION_TRANSLATION)


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
        self.question_entry.returnPressed.connect(self.search_question)

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
        search_btn.setDefault(True)

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


class FileDropList(QListWidget):
    """A file list that accepts external .docx/.json files by drag and drop."""

    def __init__(self, on_files_dropped, parent=None):
        super().__init__(parent)
        self.on_files_dropped = on_files_dropped
        self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setMinimumHeight(180)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self.on_files_dropped(paths)
            event.acceptProposedAction()
        else:
            event.ignore()


class ImportPage(QWidget):
    """Home page: select, review and import one or many question-bank files."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ImportPage")
        self.parent_window = parent
        self.selected_files = []
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        header_layout = QVBoxLayout()
        header_layout.setSpacing(6)
        header_layout.addWidget(TitleLabel("导入题库"))
        header_layout.addWidget(CaptionLabel(
            "把 Word 或 JSON 题库添加到这里。支持多选和拖拽，确认清单后再统一导入。"
        ))
        layout.addLayout(header_layout)

        import_card = ModernCard("选择题库文件")
        layout.addWidget(import_card)

        action_layout = QHBoxLayout()
        action_layout.setSpacing(8)

        browse_btn = PrimaryPushButton("选择文件（可多选）")
        browse_btn.clicked.connect(self.browse_files)
        remove_btn = PushButton("移除选中")
        remove_btn.clicked.connect(self.remove_selected)
        self.clear_btn = PushButton("清空列表")
        self.clear_btn.clicked.connect(self.clear_files)

        action_layout.addWidget(browse_btn)
        action_layout.addWidget(remove_btn)
        action_layout.addWidget(self.clear_btn)
        action_layout.addStretch()
        import_card.addLayout(action_layout)

        self.file_list = FileDropList(self.add_files, self)
        self.file_list.setToolTip("将 .docx 或 .json 文件拖到这里，也可以点击上方按钮多选文件。")
        self.file_list.itemSelectionChanged.connect(self._update_selection_summary)
        import_card.addWidget(self.file_list)

        self.selection_summary = CaptionLabel("尚未选择文件。可一次导入多个 Word / JSON 文件。")
        import_card.addWidget(self.selection_summary)

        import_layout = QHBoxLayout()
        import_layout.addStretch()
        self.import_btn = PrimaryPushButton("导入全部文件")
        self.import_btn.setFixedHeight(40)
        self.import_btn.setMinimumWidth(150)
        self.import_btn.clicked.connect(self.import_selected)
        self.import_btn.setEnabled(False)
        import_layout.addWidget(self.import_btn)
        import_card.addLayout(import_layout)

        result_card = ModernCard("导入结果")
        layout.addWidget(result_card)
        self.import_result_text = TextEdit()
        self.import_result_text.setReadOnly(True)
        self.import_result_text.setPlaceholderText("导入后会在这里显示每个文件的处理结果。")
        self.import_result_text.setMinimumHeight(120)
        result_card.addWidget(self.import_result_text)

        tip = CaptionLabel("小提示：支持 .docx 和 .json；拖入多个文件不会立即导入，你可以先检查列表。")
        layout.addWidget(tip)
        layout.addStretch()

    def browse_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择题库文件",
            "",
            "题库文件 (*.docx *.json);;Word 文档 (*.docx);;JSON 文件 (*.json)"
        )
        if paths:
            self.add_files(paths)

    def add_files(self, paths):
        invalid_count = 0
        for path in paths:
            if not path:
                continue
            suffix = os.path.splitext(path)[1].lower()
            if suffix not in (".docx", ".json"):
                invalid_count += 1
                continue
            normalized_path = os.path.abspath(path)
            existing = {os.path.normcase(p) for p in self.selected_files}
            if os.path.normcase(normalized_path) not in existing:
                self.selected_files.append(normalized_path)

        self._render_file_list()
        if invalid_count:
            InfoBar.warning(
                title="已忽略不支持的文件",
                content=f"{invalid_count} 个文件不是 .docx 或 .json 格式。",
                parent=self,
                duration=2500
            )

    def _render_file_list(self):
        self.file_list.clear()
        for path in self.selected_files:
            suffix = os.path.splitext(path)[1].lower()
            kind = "Word 文档" if suffix == ".docx" else "JSON 文件"
            item = QListWidgetItem(f"{os.path.basename(path)}    ·    {kind}")
            item.setData(Qt.UserRole, path)
            item.setToolTip(path)
            self.file_list.addItem(item)
        self._update_selection_summary()

    def _update_selection_summary(self):
        count = len(self.selected_files)
        selected_count = len(self.file_list.selectedItems())
        if count:
            self.selection_summary.setText(
                f"待导入 {count} 个文件；当前选中 {selected_count} 个。"
                "双击文件名不会立即导入，请点击“导入全部文件”。"
            )
        else:
            self.selection_summary.setText("尚未选择文件。可一次导入多个 Word / JSON 文件。")
        self.import_btn.setEnabled(count > 0)
        self.clear_btn.setEnabled(count > 0)

    def remove_selected(self):
        selected_items = self.file_list.selectedItems()
        if not selected_items:
            InfoBar.warning(
                title="提示",
                content="请先在文件列表中选择要移除的文件。",
                parent=self,
                duration=2000
            )
            return
        remove_paths = {item.data(Qt.UserRole) for item in selected_items}
        self.selected_files = [path for path in self.selected_files if path not in remove_paths]
        self._render_file_list()

    def clear_files(self):
        self.selected_files = []
        self._render_file_list()

    def import_selected(self):
        if not self.selected_files:
            InfoBar.warning(
                title="还没有选择文件",
                content="请先选择文件，或把 .docx / .json 文件拖到列表中。",
                parent=self,
                duration=2200
            )
            return

        results = self.parent_window.import_files(list(self.selected_files))
        total_questions = sum(result["count"] for result in results)
        retry_paths = []
        lines = [
            f"本次处理 {len(results)} 个文件，共导入 {total_questions} 道题目。",
            ""
        ]

        for result in results:
            filename = os.path.basename(result["path"])
            if result["error"]:
                lines.append(f"✗ {filename}：导入失败 — {result['error']}")
                retry_paths.append(result["path"])
            elif result["count"] > 0:
                lines.append(f"✓ {filename}：成功导入 {result['count']} 道题目")
            else:
                lines.append(
                    f"⚠ {filename}：没有导入题目。请检查题目格式，以及是否包含题目内容和正确答案。"
                )
                retry_paths.append(result["path"])

        self.import_result_text.setPlainText("\n".join(lines))
        # Keep failed/empty files in the queue so the user can correct or retry them.
        self.selected_files = retry_paths
        self._render_file_list()

        if total_questions:
            InfoBar.success(
                title="导入完成",
                content=f"共导入 {total_questions} 道题目。",
                parent=self,
                duration=2500
            )
        if retry_paths:
            InfoBar.warning(
                title="部分文件需要检查",
                content=f"{len(retry_paths)} 个文件未成功导入，可查看下方结果。",
                parent=self,
                duration=3000
            )
        elif not total_questions:
            InfoBar.warning(
                title="没有导入题目",
                content="请检查文件内容和题目格式后重试。",
                parent=self,
                duration=2500
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
        
        self.list_hint = CaptionLabel("显示最近 100 道题目；可按住 Ctrl / Shift 多选整行后删除。")
        list_card.addWidget(self.list_hint)

        self.table = TableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(['ID', '题目内容', '题型', '选项', '答案', '导入时间'])
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 300)
        self.table.setColumnWidth(2, 70)
        self.table.setColumnWidth(3, 200)
        self.table.setColumnWidth(4, 100)
        self.table.setColumnWidth(5, 120)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
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
        with sqlite3.connect(self.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
        if count == 0:
            InfoBar.information(
                title="题库已经为空",
                content="当前没有需要清空的题目。",
                parent=self,
                duration=2000
            )
            return

        message_box = MessageBox(
            "确认清空题库",
            f"当前共有 {count} 道题目。确定全部删除吗？此操作无法撤销。",
            self
        )
        if message_box.exec() != MessageBox.Accepted:
            return

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM questions")

        InfoBar.success(
            title="清空完成",
            content=f"已清空 {count} 道题目。",
            parent=self,
            duration=2200
        )

    def start_http_server(self):
        app = Flask(__name__)
        app_instance = self
        
        def remove_punctuation(text):
            return normalize_text(text)
        
        @app.route('/')
        def index():
            return '''<html><head><title>题库适配器 API</title></head>
            <body><h1>题库适配器 API</h1>
            <p>使用 POST 请求访问 /adapter-service/search 端点</p></body></html>'''
        
        @app.route('/adapter-service')
        @app.route('/adapter-service/')
        def adapter_status():
            return jsonify({"status": "ok"})
        
        @app.route('/adapter-service/search', methods=['POST'])
        def search():
            try:
                request_data = request.get_json(force=True, silent=True)
                if request_data is None:
                    return jsonify({"error": "Invalid JSON data"}), 400
                
                question = request_data.get('question', '')
                options = request_data.get('options', [])
                type_ = request_data.get('type', 0)
                
                clean_question = remove_punctuation(question)
                clean_options = [remove_punctuation(opt) for opt in options]
                
                conn = sqlite3.connect(app_instance.db_path)
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
                    return jsonify({
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
                    })
                
                best_match = results[0]
                question_text = best_match[0]
                options_json = best_match[1]
                db_type = best_match[2]
                answer_text = best_match[3]
                
                try:
                    db_options = json.loads(options_json) if options_json else []
                except:
                    db_options = []
                
                answer = app_instance.build_answer(answer_text, db_options, db_type)
                
                return jsonify({
                    "plat": 0,
                    "question": question_text,
                    "options": db_options,
                    "type": db_type,
                    "answer": answer
                })
                
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        def run_server():
            app.run(host='localhost', port=8060, threaded=True, use_reloader=False)
        
        server_thread = threading.Thread(target=run_server)
        server_thread.daemon = True
        server_thread.start()
        print("HTTP 服务器已启动，监听端口 8060")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_system_theme(app)
    window = TikuApp()
    window.show()
    sys.exit(app.exec_())
