"""
可工作的音频测试

基于HTTP API的音频处理，绕过Python SDK的网络问题
"""

import os
import sys
import json
import requests
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(project_root / ".env")


class HTTPGeminiClient:
    """基于HTTP的Gemini客户端"""
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.base_url = "https://generativelanguage.googleapis.com"
        self.model = "gemini-2.0-flash"
        
    def upload_file(self, file_path):
        """上传文件"""
        print(f"📤 开始上传文件: {file_path}")
        
        upload_url = f"{self.base_url}/upload/v1beta/files"
        
        headers = {
            'X-goog-api-key': self.api_key
        }
        
        # 准备文件数据
        with open(file_path, 'rb') as f:
            files = {
                'metadata': (None, json.dumps({
                    "file": {
                        "display_name": Path(file_path).name
                    }
                }), 'application/json'),
                'data': (Path(file_path).name, f, 'audio/mpeg')
            }
            
            response = requests.post(upload_url, headers=headers, files=files, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            file_uri = result['file']['uri']
            file_name = result['file']['name']
            print(f"✅ 文件上传成功: {file_name}")
            return file_uri, file_name
        else:
            raise Exception(f"文件上传失败: {response.status_code} - {response.text}")
    
    def wait_for_file_processing(self, file_name):
        """等待文件处理完成"""
        print(f"⏳ 等待文件处理完成...")
        
        get_url = f"{self.base_url}/v1beta/{file_name}"
        headers = {'X-goog-api-key': self.api_key}
        
        max_wait = 300  # 5分钟
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            response = requests.get(get_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                file_info = response.json()
                state = file_info.get('state', 'UNKNOWN')
                
                if state == 'ACTIVE':
                    print(f"✅ 文件处理完成")
                    return True
                elif state == 'FAILED':
                    raise Exception("文件处理失败")
                else:
                    print(f"📋 文件状态: {state}")
                    time.sleep(10)
            else:
                print(f"⚠️  检查文件状态失败: {response.status_code}")
                time.sleep(10)
        
        raise Exception("文件处理超时")
    
    def transcribe_audio(self, file_uri):
        """转录音频"""
        print(f"🎤 开始转录音频...")
        
        url = f"{self.base_url}/v1beta/models/{self.model}:generateContent"
        
        headers = {
            'Content-Type': 'application/json',
            'X-goog-api-key': self.api_key
        }
        
        # 加载提示词
        prompt_file = project_root / "config" / "default_prompt.txt"
        if prompt_file.exists():
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt = f.read().strip()
        else:
            prompt = """请对提供的音频文件进行精确的、逐字逐句的转录。

你的任务是生成一份完整的 SRT 格式的字幕文件，不得有任何遗漏。
请为每一句话或自然的停顿生成一个字幕条目，包含序号、精确的时间戳 (HH:MM:SS,mmm --> HH:MM:SS,mmm) 和文本内容。

确保输出严格遵循 SRT 格式，就像下面这个例子一样：

1
00:00:01,234 --> 00:00:05,678
今天我们开始讨论一个重要概念。

2
00:00:06,123 --> 00:00:09,876
这个概念对我们的理解很关键。

请开始转录："""
        
        data = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {"file_data": {"file_uri": file_uri, "mime_type": "audio/mpeg"}}
                    ]
                }
            ]
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=300)
        
        if response.status_code == 200:
            result = response.json()
            
            if 'candidates' in result and len(result['candidates']) > 0:
                text = result['candidates'][0]['content']['parts'][0]['text']
                print(f"✅ 转录完成，内容长度: {len(text)} 字符")
                return text
            else:
                raise Exception("转录返回空结果")
        else:
            raise Exception(f"转录失败: {response.status_code} - {response.text}")


def test_audio_processing():
    """测试音频处理"""
    print("🎵 开始音频处理测试...")
    
    # 检查音频文件
    audio_file = project_root / "测试" / "固体物理学 - 北京交通大学(精品课) (4).mp3"
    if not audio_file.exists():
        print(f"❌ 音频文件不存在: {audio_file}")
        return False
    
    # 检查文件大小
    file_size_mb = audio_file.stat().st_size / (1024 * 1024)
    print(f"📁 音频文件: {audio_file.name}")
    print(f"📊 文件大小: {file_size_mb:.1f}MB")
    
    if file_size_mb > 20:  # 限制文件大小以避免超时
        print("⚠️  文件较大，可能需要较长时间处理")
    
    try:
        # 创建客户端
        client = HTTPGeminiClient()
        
        # 上传文件
        file_uri, file_name = client.upload_file(audio_file)
        
        # 等待处理
        client.wait_for_file_processing(file_name)
        
        # 转录音频
        transcription = client.transcribe_audio(file_uri)
        
        # 保存结果
        output_dir = project_root / "output"
        output_dir.mkdir(exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"transcription_{timestamp}.srt"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(transcription)
        
        print(f"🎉 处理完成!")
        print(f"📄 输出文件: {output_file}")
        
        # 显示内容预览
        lines = transcription.split('\n')
        print(f"\n📝 内容预览 (前20行):")
        print("-" * 50)
        for line in lines[:20]:
            print(line)
        if len(lines) > 20:
            print(f"... (还有 {len(lines) - 20} 行)")
        print("-" * 50)
        
        # 统计信息
        print(f"\n📊 处理统计:")
        print(f"   - 总行数: {len(lines)}")
        print(f"   - 内容长度: {len(transcription)} 字符")
        
        # 尝试解析SRT条目
        try:
            from src.utils.srt_formatter import SRTFormatter
            formatter = SRTFormatter()
            entries = formatter.parse_srt_content(transcription)
            print(f"   - SRT条目数: {len(entries)}")
            if entries:
                print(f"   - 总时长: {entries[-1].end_time}")
        except:
            print(f"   - SRT解析: 无法解析")
        
        return True
        
    except Exception as e:
        print(f"❌ 处理失败: {e}")
        return False


def main():
    """主函数"""
    print("🚀 可工作的音频处理测试")
    print("=" * 60)
    
    # 检查API密钥
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ API密钥未设置")
        return False
    
    print(f"🔑 API密钥: {api_key[:10]}...")
    
    # 运行测试
    if test_audio_processing():
        print("\n🎉 音频处理测试成功!")
        print("\n💡 你的音频处理工具现在可以正常工作了!")
        print("   - 输出文件保存在 output/ 目录")
        print("   - 可以导入到视频编辑软件中使用")
    else:
        print("\n❌ 音频处理测试失败")
        print("\n🛠️  可能的原因:")
        print("   1. 网络连接问题")
        print("   2. 文件太大导致超时")
        print("   3. API配额限制")
    
    return True


if __name__ == "__main__":
    main()
