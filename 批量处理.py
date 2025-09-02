#!/usr/bin/env python3
"""
基于HTTP API的批量音频转录工具
使用稳定的HTTP方式，避免Python SDK的网络问题
支持并行处理多个文件
"""

import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
import datetime
import concurrent.futures

# 导入全新的智能API管理器
from key_manager import api_manager


# ... (imports and other parts of the file remain the same) ...

class HTTPGeminiClient:
    """
    基于HTTP的Gemini客户端。
    本类只负责构建请求参数，实际的网络请求由 api_manager 执行。
    """
    def __init__(self):
        self.base_url = "https://generativelanguage.googleapis.com"
        self.model = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash-latest") # 建议使用最新模型

    def upload_file(self, file_path, api_key): # 接收 api_key
        """上传文件"""
        print(f"📤 开始上传文件: {Path(file_path).name}")
        upload_url = f"{self.base_url}/upload/v1beta/files"

        with open(file_path, 'rb') as f:
            files = {
                'metadata': (None, json.dumps({"file": {"display_name": Path(file_path).name}}), 'application/json'),
                'data': (Path(file_path).name, f, 'audio/mpeg')
            }
            
            # 将任务委托给api_manager执行，并传入固定的api_key
            response = api_manager.execute_request(
                api_key=api_key, # 传入 api_key
                method='post',
                url=upload_url,
                files=files,
                timeout=120
            )

        result = response.json()
        file_uri = result['file']['uri']
        file_name = result['file']['name']
        print(f"✅ 文件上传成功: {file_name}")
        return file_uri, file_name

    def wait_for_file_processing(self, file_name, api_key): # 接收 api_key
        """等待文件处理完成"""
        print(f"⏳ 等待文件处理完成...")
        get_url = f"{self.base_url}/v1beta/{file_name}"
        
        max_wait = 300
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            # 委托api_manager执行状态检查请求，并传入固定的api_key
            response = api_manager.execute_request(
                api_key=api_key, # 传入 api_key
                method='get',
                url=get_url,
                timeout=30
            )
            
            file_info = response.json()
            state = file_info.get('state', 'UNKNOWN')
            
            if state == 'ACTIVE':
                print(f"✅ 文件处理完成")
                return True
            elif state == 'FAILED':
                raise Exception(f"文件处理失败 (API返回FAILED状态)。详情: {file_info}")
            else:
                print(f"📋 文件状态: {state}")
                time.sleep(10)
        
        raise Exception("文件处理超时")

    def transcribe_audio(self, file_uri, api_key): # 接收 api_key
        """转录音频"""
        print(f"🎤 开始转录音频...")
        url = f"{self.base_url}/v1beta/models/{self.model}:generateContent"
        
        # ... (prompt loading logic is correct) ...
        prompt_file = Path("config/default_prompt.txt")
        if not prompt_file.exists():
            raise FileNotFoundError(f"提示词文件不存在: {prompt_file}")
        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompt = f.read().strip()
        if not prompt:
            raise ValueError("提示词文件为空")
            
        headers = {'Content-Type': 'application/json'}
        data = {
            "contents": [{"parts": [{"text": prompt}, {"file_data": {"file_uri": file_uri, "mime_type": "audio/mpeg"}}]}]
        }
        
        # 委托api_manager执行转录请求，并传入固定的api_key
        response = api_manager.execute_request(
            api_key=api_key, # 传入 api_key
            method='post',
            url=url,
            headers=headers,
            json=data,
            timeout=300
        )
        
        result = response.json()
        # 更健壮的错误检查
        if 'candidates' not in result or not result['candidates']:
             error_info = result.get('error', {})
             if error_info:
                 raise Exception(f"转录失败: {error_info.get('message', '未知错误')}")
             # 检查是否有安全阻止
             prompt_feedback = result.get('promptFeedback', {})
             if prompt_feedback.get('blockReason'):
                 raise Exception(f"转录被阻止，原因: {prompt_feedback['blockReason']}. 详情: {prompt_feedback.get('safetyRatings', '')}")
             raise Exception(f"转录返回空结果。完整响应: {result}")

        text = result['candidates'][0]['content']['parts'][0]['text']
        print(f"✅ 转录完成，内容长度: {len(text)} 字符")
        return text


def process_single_file(client, audio_file_path, output_path=None):
    """【已修改】处理单个音频文件"""
    audio_file = Path(audio_file_path)

    # 生成输出路径
    if output_path is None:
        output_path = audio_file.parent / f"{audio_file.stem}.srt"
    else:
        output_path = Path(output_path)

    try:
        # 使用上下文管理器为这个文件的处理流程获取一个固定的Key
        with api_manager.get_key_for_session() as api_key:
            print(f"  (为 {audio_file.name} 分配了Key ...{api_key[-4:]})")
            file_uri, file_name = client.upload_file(audio_file, api_key)
            client.wait_for_file_processing(file_name, api_key)
            transcription = client.transcribe_audio(file_uri, api_key)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(transcription)

        print(f"✅ 成功处理: {audio_file.name} -> {output_path.name}")
        return True, None

    except Exception as e:
        print(f"❌ 处理失败: {audio_file.name} - {e}")
        # 引入 traceback 来获取更详细的错误信息
        import traceback
        traceback.print_exc()
        return False, str(e)


def process_single_file_parallel(args):
    """【已修改】并行处理的包装函数"""
    audio_file_path, output_path, thread_id = args
    client = HTTPGeminiClient()
    audio_file = Path(audio_file_path)
    print(f"[线程{thread_id}] 开始处理: {audio_file.name}")

    # 并行处理也需要将整个流程包裹起来
    try:
        success, error_msg = process_single_file(client, audio_file_path, output_path)
        # ... (rest of the function is okay, but we can simplify since process_single_file does the work)
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


# ... (The rest of 批量处理.py: get_all_audio_files, process_folder, etc., do not need changes) ...

def get_all_audio_files(folder_path):
    """递归扫描并返回所有支持的音频文件列表"""
    print(f"🔍 正在扫描文件夹及其子文件夹: {folder_path}...")
    audio_extensions = ['*.mp3', '*.wav', '*.m4a', '*.flac', '*.ogg']
    audio_files = set()
    for extension in audio_extensions:
        audio_files.update(folder_path.rglob(extension))
        audio_files.update(folder_path.rglob(extension.upper()))
    
    audio_files = sorted(list(audio_files))
    
    if not audio_files:
        print(f"❌ 在文件夹及其子文件夹中没有找到音频文件: {folder_path}")
        return []

    print(f"📁 找到 {len(audio_files)} 个音频文件:")
    for i, file in enumerate(audio_files, 1):
        size_mb = file.stat().st_size / 1024 / 1024
        relative_path = file.relative_to(folder_path)
        print(f"  {i}. {relative_path} ({size_mb:.1f} MB)")
    return audio_files


def process_folder(folder_path_str, output_folder_str=None, parallel=False, max_workers=2):
    """批量处理文件夹中的音频文件的主入口"""
    folder_path = Path(folder_path_str)
    if not folder_path.is_dir():
        print(f"❌ 路径不是一个有效的文件夹: {folder_path}")
        return False

    audio_files = get_all_audio_files(folder_path)
    if not audio_files:
        return False

    if parallel:
        print(f"\n🚀 开始并行处理 (最大 {max_workers} 个线程)...")
    else:
        print("\n🚀 开始顺序处理...")
    print("=" * 50)
    
    tasks = []
    for i, audio_file in enumerate(audio_files):
        output_path = None
        if output_folder_str:
            output_dir = Path(output_folder_str)
            relative_path = audio_file.relative_to(folder_path)
            output_path = output_dir / relative_path.with_suffix('.srt')
        tasks.append((str(audio_file), output_path, i + 1))

    results = []
    if parallel:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {executor.submit(process_single_file_parallel, task): task for task in tasks}
            for future in concurrent.futures.as_completed(future_to_task):
                results.append(future.result())
    else:
        client = HTTPGeminiClient()
        for i, (audio_file_path, output_path, _) in enumerate(tasks):
            print(f"\n[{i+1}/{len(tasks)}] 正在处理: {Path(audio_file_path).name}")
            print("-" * 30)
            success, error_msg = process_single_file(client, audio_file_path, output_path)
            results.append({'success': success, 'file_path': audio_file_path, 'error': error_msg, 'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")})
            if i < len(tasks) - 1:
                print("⏳ 等待5秒后处理下一个文件...")
                time.sleep(5)

    # 统计和报告结果
    report_results(results, len(audio_files), folder_path)
    return any(r['success'] for r in results)


def report_results(results, total_files, folder_path):
    """统计并打印最终处理结果"""
    successful_count = sum(1 for r in results if r['success'])
    failed_results = [r for r in results if not r['success']]

    print("\n" + "=" * 50)
    print("🎉 批量处理完成！")
    print(f"📊 总文件数: {total_files}")
    print(f"✅ 成功处理: {successful_count}")
    print(f"❌ 处理失败: {len(failed_results)}")

    if failed_results:
        print("\n失败的文件:")
        failed_files_to_save = []
        for failed_file in failed_results:
            relative_path = Path(failed_file['file_path']).relative_to(folder_path)
            print(f"  - {relative_path}")
            failed_files_to_save.append({
                'file_path': str(relative_path),
                'full_path': failed_file['file_path'],
                'error': failed_file['error'],
                'timestamp': failed_file['timestamp']
            })
        save_failed_files_info(failed_files_to_save, folder_path)


def save_failed_files_info(failed_files, folder_path):
    """保存失败文件信息到文件"""
    if not failed_files: return
    failed_dir = Path("failed_files")
    failed_dir.mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    failed_info_file = failed_dir / f"failed_files_{timestamp}.json"
    failed_list_file = failed_dir / f"failed_list_{timestamp}.txt"

    with open(failed_info_file, 'w', encoding='utf-8') as f:
        json.dump({
            "processing_time": datetime.datetime.now().isoformat(),
            "source_folder": str(folder_path),
            "total_failed": len(failed_files),
            "failed_files": failed_files
        }, f, ensure_ascii=False, indent=2)

    with open(failed_list_file, 'w', encoding='utf-8') as f:
        f.write(f"处理失败的文件列表\n处理时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"源文件夹: {folder_path}\n失败文件数: {len(failed_files)}\n" + "=" * 50 + "\n\n")
        for i, failed in enumerate(failed_files, 1):
            f.write(f"{i}. 文件路径: {failed['file_path']}\n   完整路径: {failed['full_path']}\n")
            f.write(f"   失败时间: {failed['timestamp']}\n   错误信息: {failed['error']}\n" + "-" * 30 + "\n")

    print(f"\n📄 失败文件信息已保存:\n   详细信息: {failed_info_file}\n   文件列表: {failed_list_file}")


def main():
    """主函数"""
    print("🎵 HTTP批量音频转录工具")
    print("=" * 50)
    print("使用稳定的HTTP API，避免网络问题")
    print("支持并行处理，提高效率")
    print()

    # .env文件由key_manager在导入时自动加载
    model_name = os.getenv('GEMINI_MODEL_NAME', 'gemini-2.0-flash')
    print(f"🤖 使用模型: {model_name}")

    folder_path = input("请输入音频文件夹路径: ").strip()
    if not folder_path:
        print("❌ 文件夹路径不能为空")
        return

    print("\n处理模式:\n1. 顺序处理 (稳定)\n2. 并行处理 (高效)")
    mode_choice = input("请选择处理模式 (1 或 2): ").strip()
    parallel = mode_choice == "2"
    max_workers = 2
    if parallel:
        worker_choice = input("请选择并行数量 (推荐2-4): ").strip()
        if worker_choice.isdigit() and int(worker_choice) > 0:
            max_workers = int(worker_choice)
        print(f"✅ 将同时处理 {max_workers} 个文件")

    print("\n输出选项:\n1. 在原文件夹中生成 SRT 文件\n2. 指定输出文件夹")
    choice = input("请选择 (1 或 2): ").strip()
    output_folder = None
    if choice == "2":
        output_folder = input("请输入输出文件夹路径: ").strip() or None

    process_folder(folder_path, output_folder, parallel, max_workers)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ 操作被用户中断")
    except Exception as e:
        print(f"\n❌ 程序发生严重错误: {e}")
    
    input("\n按回车键退出...")