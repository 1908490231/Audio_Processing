#!/usr/bin/env python3
"""
基于HTTP API的批量音频转录工具
使用稳定的HTTP方式，避免Python SDK的网络问题
支持并行处理多个文件
"""

import os
import json
import requests
import time
from pathlib import Path
from dotenv import load_dotenv
import datetime
import concurrent.futures
import threading
from queue import Queue
from key_manager import api_key_queue


class HTTPGeminiClient:
    """基于HTTP的Gemini客户端"""
    
    def __init__(self):
        self.base_url = "https://generativelanguage.googleapis.com"
        self.model = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash")
        
    def upload_file(self, file_path):
        """上传文件"""
        print(f"📤 开始上传文件: {Path(file_path).name}")
        upload_url = f"{self.base_url}/upload/v1beta/files"
        
        # +++ 密钥轮询核心逻辑 +++
        api_key = None
        try:
            # 1. 从队列获取一个API Key
            api_key = api_key_queue.get()
            print(f"    (使用Key: ...{api_key[-4:]})")

            # 2. 使用获取到的Key构建请求头
            headers = {'X-goog-api-key': api_key}
            
            # 准备文件数据
            with open(file_path, 'rb') as f:
                files = {
                    'metadata': (None, json.dumps({
                        "file": {"display_name": Path(file_path).name}
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
        
        finally:
            # 3. 无论成功还是失败，都必须将Key放回队列
            if api_key:
                api_key_queue.put(api_key)

    def wait_for_file_processing(self, file_name):
        """等待文件处理完成"""
        print(f"⏳ 等待文件处理完成...")
        get_url = f"{self.base_url}/v1beta/{file_name}"
        
        max_wait = 300
        start_time = time.time()
        
        # +++ 密钥轮询核心逻辑 +++
        # 由于这个方法是循环检查，我们只在循环外获取一次key，检查完再归还
        api_key = None
        try:
            api_key = api_key_queue.get()
            print(f"    (使用Key: ...{api_key[-4:]} 进行状态检查)")
            headers = {'X-goog-api-key': api_key}

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

        finally:
            if api_key:
                api_key_queue.put(api_key)
    def transcribe_audio(self, file_uri):
        """转录音频"""
        print(f"🎤 开始转录音频...")
        url = f"{self.base_url}/v1beta/models/{self.model}:generateContent"
        
        # 加载提示词
        prompt_file = Path("config/default_prompt.txt")
        if prompt_file.exists():
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt = f.read().strip()
        else:
            raise FileNotFoundError(f"提示词文件不存在: {prompt_file}")
        if not prompt:
            raise ValueError("提示词文件为空")

        data = {
            "contents": [{"parts": [{"text": prompt}, {"file_data": {"file_uri": file_uri, "mime_type": "audio/mpeg"}}]}]
        }
        
        # +++ 密钥轮询核心逻辑 +++
        api_key = None
        try:
            api_key = api_key_queue.get()
            print(f"    (使用Key: ...{api_key[-4:]})")
            
            headers = {
                'Content-Type': 'application/json',
                'X-goog-api-key': api_key
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
        
        finally:
            if api_key:
                api_key_queue.put(api_key)

def process_single_file(client, audio_file_path, output_path=None):
    """处理单个音频文件"""
    audio_file = Path(audio_file_path)

    # 生成输出路径
    if output_path is None:
        output_path = audio_file.parent / f"{audio_file.stem}.srt"
    else:
        output_path = Path(output_path)

    try:
        # 上传文件
        file_uri, file_name = client.upload_file(audio_file)

        # 等待处理
        client.wait_for_file_processing(file_name)

        # 转录音频
        transcription = client.transcribe_audio(file_uri)

        # 保存结果
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(transcription)

        print(f"✅ 成功处理: {audio_file.name} -> {output_path.name}")
        return True, None

    except Exception as e:
        print(f"❌ 处理失败: {audio_file.name} - {e}")
        return False, str(e)


def process_single_file_parallel(args):
    """并行处理的包装函数"""
    audio_file_path, output_path, thread_id = args

    # 为每个线程创建独立的客户端
    client = HTTPGeminiClient()
    audio_file = Path(audio_file_path)

    print(f"[线程{thread_id}] 开始处理: {audio_file.name}")

    try:
        success, error_msg = process_single_file(client, audio_file_path, output_path)

        result = {
            'file_path': str(audio_file_path),
            'output_path': str(output_path) if output_path else None,
            'success': success,
            'error': error_msg,
            'thread_id': thread_id,
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
        }

        if success:
            print(f"[线程{thread_id}] ✅ 完成: {audio_file.name}")
        else:
            print(f"[线程{thread_id}] ❌ 失败: {audio_file.name} - {error_msg}")

        return result

    except Exception as e:
        error_msg = str(e)
        print(f"[线程{thread_id}] ❌ 异常: {audio_file.name} - {error_msg}")

        return {
            'file_path': str(audio_file_path),
            'output_path': str(output_path) if output_path else None,
            'success': False,
            'error': error_msg,
            'thread_id': thread_id,
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
        }


def process_folder(folder_path, output_folder=None, parallel=False, max_workers=2):
    """批量处理文件夹中的音频文件"""
    if parallel:
        return process_folder_parallel(folder_path, output_folder, max_workers)
    else:
        return process_folder_sequential(folder_path, output_folder)


def process_folder_sequential(folder_path, output_folder=None):
    """顺序处理文件夹中的音频文件（原版本）"""
    folder_path = Path(folder_path)

    if not folder_path.exists():
        print(f"❌ 文件夹不存在: {folder_path}")
        return False

    if not folder_path.is_dir():
        print(f"❌ 不是文件夹: {folder_path}")
        return False

    # 递归查找所有子文件夹中的音频文件
    print(f"🔍 正在扫描文件夹及其子文件夹...")
    audio_extensions = ['*.mp3', '*.wav', '*.m4a', '*.flac', '*.ogg']
    audio_files = set()

    for extension in audio_extensions:
        # 使用 rglob 递归搜索所有子文件夹
        audio_files.update(folder_path.rglob(extension))
        audio_files.update(folder_path.rglob(extension.upper()))

    audio_files = list(audio_files)
    audio_files.sort()

    if not audio_files:
        print(f"❌ 在文件夹及其子文件夹中没有找到音频文件: {folder_path}")
        return False

    print(f"📁 找到 {len(audio_files)} 个音频文件:")
    for i, file in enumerate(audio_files, 1):
        size_mb = file.stat().st_size / 1024 / 1024
        # 显示相对于根文件夹的路径
        relative_path = file.relative_to(folder_path)
        print(f"  {i}. {relative_path} ({size_mb:.1f} MB)")

    # 创建客户端
    client = HTTPGeminiClient()

    print("\n🚀 开始顺序处理...")
    print("=" * 50)

    successful_count = 0
    failed_files = []

    for i, audio_file in enumerate(audio_files, 1):
        relative_path = audio_file.relative_to(folder_path)
        print(f"\n[{i}/{len(audio_files)}] 正在处理: {relative_path}")
        print("-" * 30)

        # 确定输出路径
        if output_folder:
            output_dir = Path(output_folder)
            # 保持原有的子文件夹结构
            relative_path = audio_file.relative_to(folder_path)
            output_path = output_dir / relative_path.parent / f"{audio_file.stem}.srt"
        else:
            output_path = None  # 使用默认路径（同文件夹）

        # 处理文件
        success, error_msg = process_single_file(client, audio_file, output_path)
        if success:
            successful_count += 1
        else:
            failed_files.append({
                'file_path': str(relative_path),
                'full_path': str(audio_file),
                'error': error_msg,
                'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
            })

        # 文件间延迟
        if i < len(audio_files):
            print("⏳ 等待5秒后处理下一个文件...")
            time.sleep(5)

    # 输出结果统计
    print("\n" + "=" * 50)
    print("🎉 批量处理完成！")
    print(f"📊 总文件数: {len(audio_files)}")
    print(f"✅ 成功处理: {successful_count}")
    print(f"❌ 处理失败: {len(failed_files)}")

    if failed_files:
        print("\n失败的文件:")
        for failed_file in failed_files:
            print(f"  - {failed_file['file_path']}")

        # 保存失败文件信息到文件
        save_failed_files_info(failed_files, folder_path)

    return successful_count > 0


def process_folder_parallel(folder_path, output_folder=None, max_workers=2):
    """并行处理文件夹中的音频文件"""
    folder_path = Path(folder_path)

    if not folder_path.exists():
        print(f"❌ 文件夹不存在: {folder_path}")
        return False

    if not folder_path.is_dir():
        print(f"❌ 不是文件夹: {folder_path}")
        return False

    # 递归查找所有子文件夹中的音频文件
    print(f"🔍 正在扫描文件夹及其子文件夹...")
    audio_extensions = ['*.mp3', '*.wav', '*.m4a', '*.flac', '*.ogg']
    audio_files = set()

    for extension in audio_extensions:
        # 使用 rglob 递归搜索所有子文件夹
        audio_files.update(folder_path.rglob(extension))
        audio_files.update(folder_path.rglob(extension.upper()))

    audio_files = list(audio_files)
    audio_files.sort()

    if not audio_files:
        print(f"❌ 在文件夹及其子文件夹中没有找到音频文件: {folder_path}")
        return False

    print(f"📁 找到 {len(audio_files)} 个音频文件:")
    for i, file in enumerate(audio_files, 1):
        size_mb = file.stat().st_size / 1024 / 1024
        # 显示相对于根文件夹的路径
        relative_path = file.relative_to(folder_path)
        print(f"  {i}. {relative_path} ({size_mb:.1f} MB)")

    print(f"\n🚀 开始并行处理 (最大 {max_workers} 个线程)...")
    print("=" * 50)

    # 准备任务参数
    tasks = []
    for i, audio_file in enumerate(audio_files):
        # 确定输出路径
        if output_folder:
            output_dir = Path(output_folder)
            # 保持原有的子文件夹结构
            relative_path = audio_file.relative_to(folder_path)
            output_path = output_dir / relative_path.parent / f"{audio_file.stem}.srt"
        else:
            output_path = None  # 使用默认路径（同文件夹）

        tasks.append((str(audio_file), output_path, i + 1))

    # 使用线程池并行处理
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_task = {executor.submit(process_single_file_parallel, task): task for task in tasks}

        # 收集结果
        for future in concurrent.futures.as_completed(future_to_task):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                task = future_to_task[future]
                print(f"❌ 任务异常: {task[0]} - {e}")
                results.append({
                    'file_path': task[0],
                    'output_path': str(task[1]) if task[1] else None,
                    'success': False,
                    'error': str(e),
                    'thread_id': task[2],
                    'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
                })

    # 统计结果
    successful_count = sum(1 for r in results if r['success'])
    failed_files = [r for r in results if not r['success']]

    # 输出结果统计
    print("\n" + "=" * 50)
    print("🎉 并行处理完成！")
    print(f"📊 总文件数: {len(audio_files)}")
    print(f"✅ 成功处理: {successful_count}")
    print(f"❌ 处理失败: {len(failed_files)}")

    if failed_files:
        print("\n失败的文件:")
        for failed_file in failed_files:
            relative_path = Path(failed_file['file_path']).relative_to(folder_path)
            print(f"  - {relative_path}")

        # 转换为原格式保存失败文件信息
        failed_files_formatted = []
        for failed_file in failed_files:
            relative_path = Path(failed_file['file_path']).relative_to(folder_path)
            failed_files_formatted.append({
                'file_path': str(relative_path),
                'full_path': failed_file['file_path'],
                'error': failed_file['error'],
                'timestamp': failed_file['timestamp']
            })

        save_failed_files_info(failed_files_formatted, folder_path)

    return successful_count > 0


def save_failed_files_info(failed_files, folder_path):
    """保存失败文件信息到文件"""
    if not failed_files:
        return

    # 创建失败文件信息目录
    failed_dir = Path("failed_files")
    failed_dir.mkdir(exist_ok=True)

    # 生成文件名（包含时间戳）
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    failed_info_file = failed_dir / f"failed_files_{timestamp}.json"
    failed_list_file = failed_dir / f"failed_list_{timestamp}.txt"

    # 保存详细信息（JSON格式）
    failed_info = {
        "processing_time": datetime.datetime.now().isoformat(),
        "source_folder": str(folder_path),
        "total_failed": len(failed_files),
        "failed_files": failed_files
    }

    with open(failed_info_file, 'w', encoding='utf-8') as f:
        json.dump(failed_info, f, ensure_ascii=False, indent=2)

    # 保存简单列表（文本格式，便于复制文件）
    with open(failed_list_file, 'w', encoding='utf-8') as f:
        f.write(f"处理失败的文件列表\n")
        f.write(f"处理时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"源文件夹: {folder_path}\n")
        f.write(f"失败文件数: {len(failed_files)}\n")
        f.write("=" * 50 + "\n\n")

        for i, failed_file in enumerate(failed_files, 1):
            f.write(f"{i}. 文件路径: {failed_file['file_path']}\n")
            f.write(f"   完整路径: {failed_file['full_path']}\n")
            f.write(f"   失败时间: {failed_file['timestamp']}\n")
            f.write(f"   错误信息: {failed_file['error']}\n")
            f.write("-" * 30 + "\n")

    print(f"\n📄 失败文件信息已保存:")
    print(f"   详细信息: {failed_info_file}")
    print(f"   文件列表: {failed_list_file}")


def main():
    """主函数"""
    print("🎵 HTTP批量音频转录工具")
    # ...
    
    # # 加载环境变量 (这行已被移除或注释掉，因为 key_manager 已经加载过了)
    # load_dotenv()

    model_name = os.getenv('GEMINI_MODEL_NAME', 'gemini-2.0-flash')
    print(f"🤖 使用模型: {model_name}")
    
    # ... 后续代码不变 ...

    # 获取文件夹路径
    folder_path = input("请输入音频文件夹路径: ").strip()
    if not folder_path:
        print("❌ 文件夹路径不能为空")
        return

    # 询问处理模式
    print("\n处理模式:")
    print("1. 顺序处理 (一个接一个，稳定但较慢)")
    print("2. 并行处理 (同时处理多个，更快但消耗更多资源)")

    mode_choice = input("请选择处理模式 (1 或 2): ").strip()

    parallel = False
    max_workers = 2

    if mode_choice == "2":
        parallel = True
        print("\n并行设置:")
        print("建议同时处理的文件数量:")
        print("1. 2个文件 (推荐，平衡速度和稳定性)")
        print("2. 3个文件 (更快，但可能不稳定)")
        print("3. 4个文件 (最快，但风险较高)")

        worker_choice = input("请选择 (1-3): ").strip()
        if worker_choice == "2":
            max_workers = 3
        elif worker_choice == "3":
            max_workers = 4
        else:
            max_workers = 2

        print(f"✅ 将同时处理 {max_workers} 个文件")

    # 询问输出位置
    print("\n输出选项:")
    print("1. 在原文件夹中生成 SRT 文件")
    print("2. 指定输出文件夹")

    choice = input("请选择 (1 或 2): ").strip()

    output_folder = None
    if choice == "2":
        output_folder = input("请输入输出文件夹路径: ").strip()
        if not output_folder:
            print("使用原文件夹作为输出位置")
            output_folder = None

    # 开始处理
    print(f"\n🚀 开始处理文件夹: {folder_path}")
    if parallel:
        print(f"🔄 并行模式，最大 {max_workers} 个线程")
    else:
        print("🔄 顺序模式")

    success = process_folder(folder_path, output_folder, parallel, max_workers)

    if success:
        print("\n🎉 处理完成！")
    else:
        print("\n❌ 处理失败或被取消")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ 操作被用户中断")
    except Exception as e:
        print(f"\n❌ 程序发生错误: {e}")
    
    input("\n按回车键退出...")
