# 字体配置说明

## 字体支持

题库管理系统支持中文字体显示，会自动尝试加载以下字体：

### 1. 本地字体文件
- `NotoSansCJKsc-Regular.otf` - Google Noto Sans CJK 简体中文字体

### 2. 系统字体（Windows）
- `C:/Windows/Fonts/msyh.ttc` - 微软雅黑
- `C:/Windows/Fonts/simsun.ttc` - 宋体
- `C:/Windows/Fonts/simhei.ttf` - 黑体
- `C:/Windows/Fonts/simkai.ttf` - 楷体

## 字体优先级

程序会按以下顺序尝试加载字体：
1. 本地字体文件（fonts/NotoSansCJKsc-Regular.otf）
2. 系统字体（按上述顺序）
3. Fyne默认字体

## 添加自定义字体

如需使用其他字体，请：
1. 将字体文件放入 `fonts/` 目录
2. 修改 `main.go` 中的 `customTheme.Font()` 方法
3. 添加新字体的路径

## 字体格式支持

支持的字体格式：
- `.ttf` - TrueType字体
- `.otf` - OpenType字体
- `.ttc` - TrueType集合

## 注意事项

- 确保字体文件具有完整的中文字符集
- 字体文件大小建议不超过10MB
- 程序会自动处理字体加载失败的情况 