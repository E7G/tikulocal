# 开发文档

这里是题库管理系统 (TikuLocal) 的详细开发文档。

## 📚 文档目录

### 🔧 核心功能文档
- [字体配置说明](FONT_CONFIG.md) - 中文字体支持和配置详解
- [界面优化说明](DISPLAY_IMPROVEMENT.md) - 界面显示优化和改进
- [拖放功能说明](DRAG_DROP_FIX.md) - 文件拖放功能实现
- [代码优化总结](OPTIMIZATION.md) - 性能优化和代码改进
- [项目结构说明](PROJECT_STRUCTURE.md) - 项目结构和文件组织

### 🌐 API文档
- [API接口文档](API.md) - RESTful API接口详细说明

### 🧪 测试文档
- [卡片显示测试](test_cards.md) - 卡片式显示功能测试指南
- [拖放功能测试](test_drag_drop.md) - 文件拖放功能测试指南
- [字体功能测试](test_font.md) - 字体加载功能测试指南

## 🎯 快速导航

### 新用户
1. 查看主项目 [README.md](../README.md) 了解基本功能
2. 阅读 [字体配置说明](FONT_CONFIG.md) 了解中文字体支持
3. 参考 [拖放功能说明](DRAG_DROP_FIX.md) 学习文件导入

### 开发者
1. 阅读 [代码优化总结](OPTIMIZATION.md) 了解代码架构
2. 查看 [界面优化说明](DISPLAY_IMPROVEMENT.md) 了解UI改进
3. 参考 [API接口文档](API.md) 了解接口设计
4. 运行测试文档验证功能

### 测试人员
1. 按照 [拖放功能测试](test_drag_drop.md) 测试文件导入
2. 使用 [字体功能测试](test_font.md) 验证中文显示
3. 参考 [卡片显示测试](test_cards.md) 检查界面显示

### API使用者
1. 查看 [API接口文档](API.md) 了解接口规范
2. 参考示例代码进行接口调用
3. 了解错误处理和响应格式


### 使用测试功能
项目包含完整的测试功能，位于 `test/` 目录下：

#### 运行测试
```bash
# 进入测试目录
cd test

# 运行验证测试（Windows）
..\run_tests.bat

# 或直接运行测试
# 注意：测试文件需要与主代码一起编译运行
cd .. && go run test\verify_fix.go parser.go models.go
```

#### 测试内容
- **选项解析测试**: 验证A-Z选项正确解析，不合并选项
- **答案显示测试**: 验证答案显示选项文本而非字母
- **多选项支持**: 测试复杂格式选项的解析能力
- **编码处理**: 验证UTF-8编码选项文本的正确显示

#### 测试文件说明
- `test\verify_fix.go` - 解析器修复效果验证
- `test\test_parser.go` - 解析器功能测试
- `test\run_tests.bat` - Windows测试运行脚本

## 📝 文档维护

这些文档会随着项目的发展持续更新。如果您发现文档有误或需要补充，欢迎提交Issue或Pull Request。

## 🔗 相关链接

- [主项目README](../README.md)
- [变更日志](../CHANGELOG.md)
- [项目源码](../main.go)
- [许可证](../LICENSE) 