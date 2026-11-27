# TikuLocal

**离线题库管理工具 + OCS / TikuAdapter 本地接口**。当前维护主分支为 main。项目使用 Rust、Slint 和 SQLite 实现，桌面端与 Android 共用题库、导入、搜索和 HTTP API 逻辑，不需要 Python、Qt 或 WebView。

- **平台**：Windows x64、Linux x64、macOS x64 / ARM64、Android ARM64。
- **导入**：Word（DOCX）、JSON、学习通批量导出 ZIP。
- **管理**：题库搜索、题型筛选、批量删除、统计和 JSON 导出。
- **接口**：本机 127.0.0.1:8060，兼容 OCS / TikuAdapter。
- **数据**：SQLite 本地存储，题目查询不依赖云端。

下载与构建产物：[GitHub Releases](https://github.com/E7G/tikulocal/releases) · [GitHub Actions](https://github.com/E7G/tikulocal/actions)

## 快速开始

1. 从 Releases 下载对应平台的程序；也可以按下方说明自行构建。
2. 启动 TikuLocal。桌面端启动时会自动尝试启动本地题库 API。
3. 进入「导入题库」，选择一个或多个 DOCX、JSON 或 ZIP 文件，检查待导入列表后点击「导入全部」。
4. 在「搜索答案」中检索题目；在「题库管理」中查看、筛选、删除题目或导出 JSON。
5. 如果要让 OCS 脚本调用本地题库，请保持 TikuLocal 运行，并按 [OCS 与 TikuAdapter 配置](#ocs-与-tikuadapter-配置) 设置接口地址。

桌面版提供导入、搜索、题库管理和设置页面；Android 使用适合触控的单列布局。界面支持跟随系统、浅色和深色主题。Android 的构建、安装及文件选择说明见 [ANDROID.md](ANDROID.md)。

## 支持的导入格式

### Word（DOCX）

支持从 [E7G/chaoxing_ulearning_Answer_to_Word](https://github.com/E7G/chaoxing_ulearning_Answer_to_Word) 导出的题库文档，读取题目、题型、选项和答案。

答案采用较严格的筛选规则：

- 优先使用文档中的「正确答案」「标准答案」或「参考答案」。
- 如果没有明确答案，只有同时存在「我的答案」和「答案状态：正确」时，才会采用个人作答。
- 答错、未批改或答案状态不明确的个人作答不会作为标准答案导入。

### 学习通批量 ZIP

支持上游 v0.2.1 格式的 学习通批量导出_日期.zip。程序会遍历 ZIP 中的 DOCX 并合并导入，自动忽略 导出清单.txt 等非题目文件；单个文档损坏或没有有效答案时会跳过，不影响其他正常文档。

导入有文件大小、成员数量和解压总量限制；ZIP 不会被整体解压到磁盘。

### JSON

接受题目数组，或包含 questions 数组的对象。每道题支持以下字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| question | string | 题目内容；也可使用 content |
| options | string[] | 选项，没有选项时可省略 |
| type | integer | 题型编码，默认 0 |
| answer | string | 答案；没有有效答案的题目不会导入 |

题型编码：0 单选、1 多选、2 填空、3 判断、4 问答。

示例：

~~~json
[
  {
    "question": "下列哪项是示例答案？",
    "options": ["选项 A", "选项 B"],
    "type": 0,
    "answer": "B"
  }
]
~~~

## OCS 与 TikuAdapter 配置

TikuLocal 启动后会在本机回环地址监听 HTTP API：

~~~text
http://127.0.0.1:8060
~~~

在 OCS 脚本的题库设置中：

1. 先启动 TikuLocal，并确认「设置与连接」页面显示本地 API 正在监听（端口 8060）。
2. 将题库解析器选择为 **TikuAdapter**。
3. 将自定义题库接口地址填写为：

   ~~~text
   http://127.0.0.1:8060/adapter-service/search
   ~~~

4. 请求方式使用 **POST**，请求体为 JSON。

旧配置中的 ?use=local 查询参数仍可使用，例如：

~~~text
http://127.0.0.1:8060/adapter-service/search?use=local
~~~

接口会忽略查询参数，并兼容路径末尾多一个斜杠的情况。对接口地址进行 GET 探测时，/adapter-service 和 /adapter-service/search 都会返回服务状态，不会因为探测请求而返回 404。OPTIONS 预检请求也会得到响应。

### API 请求示例

~~~http
POST /adapter-service/search HTTP/1.1
Host: 127.0.0.1:8060
Content-Type: application/json

{
  "question": "下列哪项是示例答案？",
  "options": ["选项 A", "选项 B"],
  "type": 0
}
~~~

### API 响应格式

命中题目时，响应包含 TikuAdapter 所需的题目和答案字段：

~~~json
{
  "plat": 0,
  "question": "下列哪项是示例答案？",
  "options": ["选项 A", "选项 B"],
  "type": 0,
  "answer": {
    "answerKey": ["B"],
    "answerKeyText": "B",
    "answerIndex": [1],
    "answerText": "选项 B",
    "bestAnswer": ["选项 B"],
    "allAnswer": [["选项 B"], ["B选项 B"]]
  }
}
~~~

未命中时接口仍返回正常 JSON，答案字段为空数组或空字符串，不会将 404 当作「没有答案」。

### 连接问题排查

- **检查服务是否启动**：在浏览器打开 http://127.0.0.1:8060/，正常时会返回包含 status: ok 的 JSON。
- **检查接口路径**：打开 http://127.0.0.1:8060/adapter-service/search，GET 探测应返回服务状态；正式查题使用 POST。
- **出现 404**：确认路径为 /adapter-service/search，解析器选择的是 TikuAdapter，并确认运行的是包含 OCS 兼容修复的版本。
- **连接被拒绝或超时**：确认 TikuLocal 没有退出，并检查「设置与连接」页面是否提示 API 启动失败；端口 8060 被其他程序占用时服务无法监听。
- **接口正常但没有答案**：确认题目已导入，并检查题干和选项是否与题库中的内容相符。

建议使用 127.0.0.1 而不是 localhost，避免部分系统将 localhost 优先解析到 IPv6 地址，而服务当前只监听 IPv4 回环地址。

> **Android 提示：** Android 上的 127.0.0.1 指手机本机，不是电脑。手机端 API 供同一设备上的应用访问，不能直接当作电脑浏览器里的本地题库服务。

## 数据与隐私

- 题库保存在 SQLite 文件 tiku.db 中。
- 如果程序所在目录已经存在 tiku.db，会优先继续使用该数据库。
- 否则桌面端默认使用用户数据目录：Windows 为 %LOCALAPPDATA%/TikuLocal/tiku.db，macOS 为 ~/Library/Application Support/TikuLocal/tiku.db，Linux 为 $XDG_DATA_HOME/TikuLocal/tiku.db（未设置时回退到 ~/.local/share/TikuLocal/tiku.db）。
- Android 使用应用私有目录保存数据库。
- 本地 API 只绑定 127.0.0.1，不会主动向局域网或公网开放。不要自行将该接口反向代理或暴露到公网。

## 构建

需要 Rust stable 工具链及对应平台的原生构建依赖。

桌面端：

~~~sh
cargo test --locked
cargo run --release
# 或只编译，不启动
cargo build --release
~~~

Android ARM64 的完整步骤（Android SDK、NDK、Java 和 cargo-ndk）见 [ANDROID.md](ANDROID.md)。

GitHub Actions 的 Rust release 工作流分为验证与发布两阶段：向 main 推送代码或提交 PR 时，只在 Linux 上运行 Rust 测试；仅修改 Markdown、docs、LICENSE 或 .gitignore 时会跳过 CI。推送 `v*` 标签后才会构建 Windows、Linux、macOS（ARM64 / x64）和 Android APK，并由单一发布任务统一创建或更新 GitHub Release，同时生成 SHA-256 校验文件。重复运行同一标签时会覆盖同名资产并清理过期资产，不会由多个构建任务并发修改 Release。需要手动获取全平台预览包时，可在 Actions 页面运行 `Rust release` 并勾选 `build_preview`；该模式只保存临时工作流产物，不创建 Release。

## 项目结构

~~~text
ui/app.slint       # 桌面端 Slint 界面
ui/mobile.slint    # Android 触控界面
src/lib.rs         # 应用入口、界面事件和数据路径
src/db.rs          # SQLite 数据库、统计和搜索
src/import.rs      # DOCX / JSON / ZIP 导入
src/api.rs         # OCS / TikuAdapter HTTP API
src/android.rs     # Android 文件选择与平台桥接
android/           # Android 工程与 Gradle 构建
.github/workflows/ # GitHub Actions 构建工作流
~~~

## License

[MIT](LICENSE)
