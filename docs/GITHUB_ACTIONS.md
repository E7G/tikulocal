# GitHub Actions 使用指南

本文档介绍如何使用GitHub Actions来自动构建、测试和发布题库管理系统。

## 📋 工作流文件

项目包含以下GitHub Actions工作流文件：

### 1. **CI 工作流** (`.github/workflows/ci.yml`)
- **触发条件**: 推送到 `main` 或 `develop` 分支，或创建 Pull Request
- **功能**: 代码质量检查、测试、跨平台构建验证
- **平台**: Ubuntu、Windows、macOS
- **包含**: 代码格式检查、静态分析、单元测试、构建验证

### 2. **发布工作流** (`.github/workflows/release.yml`) ⭐ **主要推荐**
- **触发条件**: 推送到 `main` 分支，或手动触发
- **功能**: 自动版本管理、多平台构建、GitHub Release 发布
- **版本格式**: `vyyyy.mm.dd.i` (如: `v2024.12.28.1`)
- **平台**: Linux (amd64/arm64)、Windows (amd64)、macOS (amd64/arm64)

### 3. **解析器测试工作流** (`.github/workflows/parser-tests.yml`)
- **触发条件**: `parser.go`、`models.go`、`test/` 目录变更
- **功能**: 专门的解析器功能测试
- **覆盖**: 集成测试、单元测试、多平台验证
- **测试内容**: 选项解析、多选题处理、UTF-8 编码、题型识别

### 4. **依赖更新工作流** (`.github/workflows/dependencies.yml`)
- **触发条件**: 每周一自动运行，或手动触发
- **功能**: 自动检查并更新 Go 依赖
- **输出**: 自动创建 Pull Request

### 5. **传统工作流** (保留兼容性)
- `build.yml`: 完整版多平台构建
- `build-simple.yml`: 简化版单平台构建  
- `build-direct.yml`: 直接发布工作流

## 🚀 使用方法

### 自动触发
- **CI 工作流**: 每次代码推送自动运行
- **发布工作流**: 推送到 `main` 分支时自动创建发布
- **解析器测试**: 解析器相关文件变更时自动运行
- **依赖更新**: 每周一自动检查更新

### 手动触发工作流

1. 进入 GitHub 仓库的 **Actions** 标签页
2. 选择相应的工作流（如 "Build and Release"）
3. 点击 **Run workflow** 按钮
4. 选择分支并确认运行

### 查看构建结果

1. 在 **Actions** 页面查看工作流运行状态
2. 点击具体的工作流运行记录
3. 查看构建日志和测试结果
4. 下载构建产物（如需要）

## 📦 发布工作流详解

### 版本管理
使用 `amitsingh-007/next-release-tag` 自动生成版本号：
- 格式: `vyyyy.mm.dd.i`
- 示例: `v2024.12.28.1`
- 自动递增修订号

### 构建矩阵
```yaml
- Linux: amd64, arm64
- Windows: amd64  
- macOS: amd64 (Intel), arm64 (M1/M2)
```

### 发布内容
- 多平台可执行文件
- 详细的发布说明和使用指南
- 自动生成的版本对比
- 平台特定的安装说明

## 🧪 测试工作流详解

### CI 测试内容
```yaml
- 代码格式检查 (gofmt)
- 静态分析 (go vet)  
- 单元测试执行
- 跨平台构建验证
- 依赖完整性检查
```

### 解析器专项测试
```yaml
- 选项解析验证
- 多选题处理测试
- UTF-8 编码支持测试
- 题型识别准确性
- 答案提取正确性
- 跨平台兼容性
```

## 🔧 配置说明

### 环境要求
- **Go 版本**: 1.21+ (可配置)
- **操作系统**: Ubuntu, Windows, macOS
- **权限**: 内容写入、包管理权限

### 必需的环境变量
```yaml
GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}  # 自动提供
```

### 可选配置
可以在仓库设置中添加以下密钥用于高级功能：
```yaml
ANDROID_RELEASE_KEY: Android 发布密钥别名
ANDROID_RELEASE_KEY_PASSWORD: Android 密钥密码  
ANDROID_RELEASE_KEYSTORE: Android 密钥库文件 (base64)
```

## 🛠️ 自定义配置

### 修改 Go 版本
在 `ci.yml` 或 `release.yml` 中修改：
```yaml
- name: Set up Go
  uses: actions/setup-go@v4
  with:
    go-version: '1.22'  # 修改为需要的版本
```

### 添加新的构建平台
在 `release.yml` 的构建矩阵中添加：
```yaml
strategy:
  matrix:
    include:
      - platform: "ubuntu-latest"
        goos: "linux"
        goarch: "amd64"
        binary_name: "tikulocal-linux-amd64"
      # 添加新平台配置
```

### 自定义构建参数
```yaml
- name: Build binary
  run: |
    go build -ldflags="-s -w -X main.Version=${{ needs.prepare.outputs.next_release_tag }}" -o ${{ matrix.binary_name }} .
```

## 🐛 常见问题与解决方案

### 1. 构建失败
**症状**: 工作流运行失败，构建步骤报错
**原因**: 
- 依赖问题或代码错误
- 平台特定的构建配置问题
**解决**: 
- 检查构建日志中的具体错误信息
- 本地运行 `go build` 验证代码
- 检查跨平台构建配置

### 2. 测试失败
**症状**: 测试步骤失败
**原因**: 
- 测试用例失败
- 环境配置问题
**解决**: 
- 本地运行 `go test ./...` 
- 检查测试环境依赖
- 验证测试数据完整性

### 3. 发布失败
**症状**: Release 创建失败或版本号冲突
**原因**: 
- 版本号格式问题
- GitHub Token 权限不足
**解决**: 
- 检查版本号生成逻辑
- 确认仓库有创建 Release 的权限
- 验证 GitHub Token 配置

### 4. 跨平台构建问题
**症状**: 特定平台构建失败
**原因**: 
- 平台特定的依赖或配置
- 交叉编译参数错误
**解决**: 
- 检查平台特定的构建配置
- 验证交叉编译环境变量
- 分别测试各平台构建

### 5. 依赖更新失败
**症状**: 依赖更新工作流失败
**原因**: 
- 依赖冲突
- 新版本不兼容
**解决**: 
- 手动运行 `go mod tidy`
- 检查依赖版本冲突
- 逐步更新关键依赖

## 🔒 安全注意事项

### 权限管理
- **最小权限原则**: 只授予工作流必要的权限
- **定期审查**: 检查工作流权限设置
- **密钥管理**: 使用 GitHub Secrets 管理敏感信息

### 代码安全
- **依赖审查**: 定期检查和更新依赖包
- **漏洞扫描**: 监控依赖的安全漏洞
- **访问控制**: 限制工作流对敏感资源的访问

## 📈 性能优化建议

### 构建优化
```yaml
- 使用模块缓存加速依赖下载
- 并行构建多平台版本
- 优化构建参数 (-ldflags="-s -w")
- 合理设置构建超时时间
```

### 测试优化
```yaml
- 并行运行测试用例
- 使用测试缓存机制
- 分层测试策略（单元测试、集成测试）
- 设置合理的测试超时
```

## 🔄 维护指南

### 定期维护任务
- **每周**: 检查依赖更新工作流结果
- **每月**: 审查工作流性能和资源使用
- **每季度**: 更新工作流版本和配置

### 工作流更新流程
1. 在功能分支测试新配置
2. 验证所有测试通过
3. 代码审查和批准
4. 合并到主分支
5. 监控更新后的运行状态

### 监控和报警
- 设置工作流失败通知
- 监控构建时间和资源使用
- 定期检查构建产物完整性

## 📚 参考链接

- [GitHub Actions 官方文档](https://docs.github.com/actions)
- [Go GitHub Actions](https://github.com/actions/setup-go)
- [发布管理最佳实践](https://docs.github.com/repositories/releasing-projects-on-github)
- [跨平台构建指南](https://docs.github.com/actions/using-jobs/running-jobs-in-a-container)
- [工作流语法参考](https://docs.github.com/actions/using-workflows/workflow-syntax-for-github-actions)

---

**💡 提示**: 首次使用 GitHub Actions 需要确保仓库已启用 Actions 功能，并且有足够的构建时间配额。建议先在测试分支验证工作流配置，再应用到主分支。

工作流配置会根据项目需求持续更新，建议定期查看本文档获取最新信息。