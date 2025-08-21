#!/usr/bin/env python3
"""
重新处理失败的文件
从失败文件列表中读取文件并重新处理
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
from 批量处理 import HTTPGeminiClient, process_single_file


def list_failed_files():
    """列出所有失败文件记录"""
    failed_dir = Path("failed_files")
    if not failed_dir.exists():
        print("❌ 没有找到失败文件记录")
        return []
    
    json_files = list(failed_dir.glob("failed_files_*.json"))
    if not json_files:
        print("❌ 没有找到失败文件记录")
        return []
    
    print(f"📁 找到 {len(json_files)} 个失败文件记录:")
    for i, file in enumerate(json_files, 1):
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"  {i}. {file.name}")
        print(f"     处理时间: {data['processing_time']}")
        print(f"     源文件夹: {data['source_folder']}")
        print(f"     失败文件数: {data['total_failed']}")
    
    return json_files


def load_failed_files(json_file):
    """加载失败文件信息"""
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['failed_files']


def retry_failed_files(failed_files):
    """重新处理失败的文件"""
    if not failed_files:
        print("❌ 没有失败文件需要重新处理")
        return
    
    print(f"🔄 准备重新处理 {len(failed_files)} 个失败文件")
    
    # 创建客户端
    client = HTTPGeminiClient()
    
    successful_count = 0
    still_failed = []
    
    for i, failed_file in enumerate(failed_files, 1):
        file_path = Path(failed_file['full_path'])
        relative_path = failed_file['file_path']
        
        print(f"\n[{i}/{len(failed_files)}] 重新处理: {relative_path}")
        print("-" * 30)
        
        if not file_path.exists():
            print(f"❌ 文件不存在: {file_path}")
            still_failed.append({
                **failed_file,
                'retry_error': '文件不存在',
                'retry_time': time.strftime("%Y-%m-%d %H:%M:%S")
            })
            continue
        
        # 重新处理文件
        success, error_msg = process_single_file(client, file_path)
        
        if success:
            successful_count += 1
            print(f"✅ 重新处理成功: {relative_path}")
        else:
            print(f"❌ 重新处理仍然失败: {relative_path}")
            still_failed.append({
                **failed_file,
                'retry_error': error_msg,
                'retry_time': time.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        # 文件间延迟
        if i < len(failed_files):
            print("⏳ 等待5秒后处理下一个文件...")
            time.sleep(5)
    
    # 输出结果
    print("\n" + "=" * 50)
    print("🔄 重新处理完成！")
    print(f"📊 总文件数: {len(failed_files)}")
    print(f"✅ 成功处理: {successful_count}")
    print(f"❌ 仍然失败: {len(still_failed)}")
    
    # 如果还有失败的文件，保存新的失败记录
    if still_failed:
        print("\n仍然失败的文件:")
        for failed_file in still_failed:
            print(f"  - {failed_file['file_path']}")
        
        # 保存新的失败记录
        from 批量处理 import save_failed_files_info
        save_failed_files_info(still_failed, Path("重新处理"))


def main():
    """主函数"""
    print("🔄 失败文件重新处理工具")
    print("=" * 50)
    
    # 加载环境变量
    load_dotenv()
    
    # 检查API密钥
    api_key = os.getenv('GEMINI_API_KEY')
    model_name = os.getenv('GEMINI_MODEL_NAME', 'gemini-2.0-flash')
    
    if not api_key:
        print("❌ 错误：未找到API密钥")
        print("请确保在 .env 文件中设置了 GEMINI_API_KEY")
        return
    
    print("✅ API密钥已加载")
    print(f"🤖 使用模型: {model_name}")
    
    # 列出失败文件记录
    json_files = list_failed_files()
    if not json_files:
        return
    
    # 选择要重新处理的记录
    if len(json_files) == 1:
        selected_file = json_files[0]
        print(f"\n📄 自动选择: {selected_file.name}")
    else:
        print(f"\n请选择要重新处理的失败文件记录:")
        for i, file in enumerate(json_files, 1):
            print(f"  {i}. {file.name}")
        
        try:
            choice = int(input("请输入序号: ")) - 1
            if 0 <= choice < len(json_files):
                selected_file = json_files[choice]
            else:
                print("❌ 无效的选择")
                return
        except ValueError:
            print("❌ 请输入有效的数字")
            return
    
    # 加载失败文件信息
    failed_files = load_failed_files(selected_file)
    
    print(f"\n📋 失败文件详情:")
    for i, failed_file in enumerate(failed_files, 1):
        print(f"  {i}. {failed_file['file_path']}")
        print(f"     错误: {failed_file['error'][:100]}...")
    
    # 确认重新处理
    response = input(f"\n是否重新处理这 {len(failed_files)} 个文件？(y/n): ").lower().strip()
    if response not in ['y', 'yes', '是']:
        print("操作已取消")
        return
    
    # 重新处理
    retry_failed_files(failed_files)


if __name__ == "__main__":
    import time
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ 操作被用户中断")
    except Exception as e:
        print(f"\n❌ 程序发生错误: {e}")
    
    input("\n按回车键退出...")
