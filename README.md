# TikuLocal — Rust Material Edition (Desktop + Android)

本分支从 commit `583fd341d463f6425cea8caefc656b1d7b361046` 开始迁移。纯 Rust 实现（不需要 Python 运行时），桌面 GUI 使用 Slint 官方 Material 样式与标准控件实现（无需 Qt、WebView 或 Python 运行时），SQLite 数据格式尽量兼容旧版。

Android ARM64 原生 APK 已支持，构建、安装和手机端交互说明见 [ANDROID.md](ANDROID.md)。Windows、Linux、macOS 使用 Material 工作台布局（左侧固定导航、右侧工作区、统计卡片、文件和搜索列表），Android 采用适合触控的单列页面与底部导航。业务表单、按钮、选择器、列表与表格继续使用 Slint 官方 Material 控件；桌面左侧采用独立的 Material Navigation Drawer 导航结构（Slint 1.13 尚无内置 NavigationDrawer 控件），包含分组、选中指示与 SVG 图标。底层题库、导入和 API 共用 Rust 实现。

## 操作

1. 安装 Rust 工具链及相应平台的编译环境。
2. 执行 `cargo run --release` 打开 GUI。
3. 首页选择多个 `.docx` 或 `.json` 文件，核对后点击「导入全部文件」。导入在后台线程进行，不阻塞窗口。
4. 「搜索题库」支持题型筛选。「管理题库」支持多选删除、统计、清空确认。
5. API 在 `127.0.0.1:8060` 监听，支持 `GET /adapter-service` 和 `POST /adapter-service/search`。

## 兼容数据

- Word：从 `E7G/chaoxing_ulearning_Answer_to_Word` 导出的 DOCX 解析段落、题型、选项及「正确答案/标准答案/参考答案」，优先使用文档明确列出的标准答案；如果没有标准答案、但同时包含「我的答案」和「答案状态：正确」，就使用该作答。答错、未批改或状态不明的个人答案均跳过。
- JSON：接受题目数组或 `{"questions":[...]}`，字段 `question`（或 `content`）、`options`、`type`、`answer`。
- 数据库：沿用既有 `tiku.db`、表 `questions` 和旧版列名。如果可执行文件旁已有旧版数据库，将直接使用；否则创建在用户数据目录（Windows：`%LOCALAPPDATA%/TikuLocal`）。
- OCS/tikuAdapter：`POST http://127.0.0.1:8060/adapter-service/search`，入参 `question`、`options`、`type`，响应包含 `plat`、`question`、`options`、`type`、`answer`（带 `answerKey`、`answerKeyText`、`answerIndex`、`answerText`、`bestAnswer`、`allAnswer`）。

## 构建

```sh
cargo test
cargo build --release
```

GUI 以 Slint 官方 `std-widgets.slint` 的 `material` 样式组件为主体：`TabWidget`、`GroupBox`、`StandardListView`、`StandardTableView`、`Button`、`LineEdit`、`ComboBox`、`TextEdit`。原先手写的 NavEntry、MetricCard、题目行委托已移除。导航改为官方横向选项卡；剩余 `Rectangle` 仅用作空白布局弹性占位。外观支持「跟随系统 / 浅色 / 深色」，并记住选择。Windows Release 使用 GUI 子系统，双击 .exe 不会弹出控制台；Debug 构建保留终端诊断信息。Windows 标题栏也会跟随主题变化。

HTTP API 仅绑定本机回环地址；请勿将 API 代理公开到公网。

## 项目结构

```
ui/app.slint    # Material Design 桌面界面
build.rs        # Material 样式（支持系统/手动主题切换）
src/main.rs    # Rust GUI 交互与异步导入
src/db.rs      # SQLite & 搜索
src/import.rs  # DOCX/JSON
src/api.rs     # tikuAdapter-compatible HTTP service
```
