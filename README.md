# 🎵 音频转录工具

基于 Google Gemini API 的音频转录工具，支持将音频文件转换为 SRT 字幕文件。

## ✨ 主要功能

- 🎤 **音频转录**: 支持多种音频格式 (MP3, WAV, M4A, FLAC, OGG)
- 📝 **SRT 字幕生成**: 自动生成带时间戳的字幕文件
- 🔄 **递归批量处理**: 🆕 自动处理文件夹及所有子文件夹中的音频文件
- 📁 **保持文件夹结构**: SRT文件保存在与原音频文件相同的位置
- 🌐 **稳定的HTTP API**: 使用HTTP方式，避免网络问题
- ⚡ **高质量转录**: 基于 Google Gemini 2.0 Flash 模型
- 📊 **进度跟踪**: 实时显示处理进度和文件路径

## 🚀 快速开始

### 1. 环境准备

```bash
# 安装依赖
pip install -r requirements.txt
```

### 2. 配置 API 密钥

确保 `.env` 文件中有你的 API 密钥：

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL_NAME=gemini-2.0-flash
```

### 3. 使用方法

**最简单的方式**：
```bash
python 启动.py
```

然后输入包含音频文件的文件夹路径即可！

**完整功能版本**：
```bash
python 批量处理.py
```

## 📁 文件说明

- `启动.py` - 🌟 **推荐使用** - 最简单的启动方式
- `批量处理.py` - 完整功能版本，支持自定义输出文件夹
- `examples/working_audio_test.py` - 单文件测试脚本

## 🎯 使用示例

### 批量处理文件夹

```bash
python 启动.py
# 输入: 测试
# 程序会自动处理 "测试" 文件夹中的所有音频文件
```

### 处理结果

```
我的音频文件夹/
├── 第1课.mp3
├── 第1课.srt      ← 新生成
├── 第2课.wav
├── 第2课.srt      ← 新生成
└── 第3课.m4a
    └── 第3课.srt  ← 新生成
```

## 📋 支持的格式

- **输入**: MP3, WAV, M4A, FLAC, OGG
- **输出**: SRT 字幕文件

## ⚙️ 配置选项

### 环境变量配置

在 `.env` 文件中可以配置：

```env
# API 配置
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL_NAME=gemini-2.0-flash

# 文件处理
MAX_FILE_SIZE_MB=100
DEFAULT_OUTPUT_FORMAT=srt

# 其他设置
LOG_LEVEL=INFO
```

### 提示词配置

**重要**：程序只使用 `config/default_prompt.txt` 文件中的内容作为提示词。

- 📝 **修改提示词**：直接编辑 `config/default_prompt.txt` 文件
- 🔄 **立即生效**：保存后重新运行程序即可
- ❌ **不要硬编码**：不要在代码中添加提示词

## 🛠️ 故障排除

### 常见问题

1. **API密钥错误**: 检查 `.env` 文件中的 `GEMINI_API_KEY`
2. **网络连接问题**: 本工具使用稳定的HTTP API
3. **文件格式不支持**: 确保是支持的音频格式
4. **文件太大**: 建议单个文件不超过20MB

### 测试环境

运行单文件测试：
```bash
python examples/working_audio_test.py
```

## 📞 获取API密钥

1. 访问 [Google AI Studio](https://makersuite.google.com/app/apikey)
2. 登录Google账号
3. 点击"Create API Key"
4. 复制生成的API密钥到 `.env` 文件

## 🎉 开始使用

1. 确保API密钥已配置
2. 运行 `python 启动.py`
3. 输入音频文件夹路径
4. 等待处理完成

就这么简单！🚀
