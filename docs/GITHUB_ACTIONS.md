# GitHub Actions 使用指南

本文档介绍如何使用GitHub Actions来自动构建和发布题库管理系统。

## 📋 工作流文件

项目包含三个GitHub Actions工作流文件：

### 1. 完整版工作流 (`build.yml`)
- 支持多平台并行构建
- 自动创建GitHub Release
- 包含测试和验证步骤
- 适合正式发布使用

### 2. 简化版工作流 (`build-simple.yml`)
- 单平台构建
- 快速构建和测试
- 适合日常开发和测试使用

### 3. 直接发布工作流 (`build-direct.yml`) ⭐ 推荐
- 单平台构建
- **直接创建Release，不使用Artifacts中间步骤**
- 构建完成后立即发布
- 适合快速发布使用

## 🚀 使用方法

### 手动触发构建

1. **访问Actions页面**
   - 在GitHub仓库页面点击 "Actions" 标签
   - 选择对应的工作流文件

2. **配置构建参数**
   - **版本号**: 输入版本号（如 `v1.2.6`）
   - **目标平台**: 选择构建平台
     - `windows`: Windows平台
     - `linux`: Linux平台  
     - `macos`: macOS平台
   - **构建类型**: 选择构建类型（仅完整版）
     - `release`: 正式发布版本
     - `debug`: 调试版本

3. **启动构建**
   - 点击 "Run workflow" 按钮
   - 等待构建完成

### 构建产物

构建完成后，可以在以下位置找到构建产物：

1. **Actions页面**（完整版和简化版）
   - 点击对应的构建任务
   - 在 "Artifacts" 部分下载构建产物

2. **Release页面**（直接发布工作流）
   - 自动创建GitHub Release
   - 直接包含构建产物
   - 无需手动下载Artifacts

## 📦 构建产物说明

### Windows平台
- `题库管理系统.exe`: 使用fyne打包的Windows可执行文件
- `tikulocal.exe`: 原始构建的可执行文件

### Linux平台
- `题库管理系统.tar.gz`: 使用fyne打包的Linux安装包
- `tikulocal`: 原始构建的可执行文件

### macOS平台
- `题库管理系统.app`: 使用fyne打包的macOS应用程序
- `tikulocal`: 原始构建的可执行文件

## ⚙️ 配置说明

### 环境变量
- `GO_VERSION`: Go语言版本（默认1.21）
- `FYNE_VERSION`: Fyne工具版本（默认latest）

### 构建参数
- `version`: 版本号，用于命名构建产物和Release
- `platform`: 目标平台，支持windows/linux/macos
- `build_type`: 构建类型，支持release/debug

## 🔧 自定义配置

### 修改Go版本
```yaml
env:
  GO_VERSION: '1.22'  # 修改为需要的Go版本
```

### 添加新的构建平台
```yaml
platform:
  description: '目标平台'
  options:
  - windows
  - linux
  - macos
  - android  # 添加新平台
```

### 修改构建参数
```yaml
go build -ldflags="-s -w -X main.Version=${{ github.event.inputs.version }}" -o tikulocal .
```

## 🐛 常见问题

### 1. 构建失败
- 检查Go版本兼容性
- 确认所有依赖都已正确安装
- 查看构建日志获取详细错误信息

### 2. 找不到构建产物
- 确认构建步骤执行成功
- 检查文件路径和命名规则
- 查看Artifacts上传步骤的日志

### 3. Release创建失败
- 确认GitHub Token权限
- 检查版本号格式是否正确
- 确认仓库有创建Release的权限

## 📝 最佳实践

1. **版本管理**
   - 使用语义化版本号（如v1.2.3）
   - 在CHANGELOG.md中记录更新内容
   - 为重要版本创建Git标签

2. **构建测试**
   - 先使用简化版工作流测试
   - 确认无误后再使用完整版发布
   - 定期清理旧的构建产物

3. **发布流程**
   - 更新版本号和更新日志
   - 提交代码到主分支
   - 手动触发release构建
   - 检查Release内容并发布

## 🔗 相关链接

- [GitHub Actions 官方文档](https://docs.github.com/en/actions)
- [Fyne 打包工具文档](https://developer.fyne.io/started/packaging)
- [Go 交叉编译指南](https://golang.org/doc/install/source#environment)

---

**注意**: 首次使用GitHub Actions需要确保仓库已启用Actions功能，并且有足够的构建时间配额。 