#!/usr/bin/env python3
"""
HTTP版本的简单启动脚本
基于稳定的HTTP API，只需要输入文件夹路径
"""

import os
from pathlib import Path
from 批量处理 import process_folder
from key_manager import api_manager # 导入API管理器


def main():
    """简化的主函数"""
    print("🎵 HTTP音频转录工具")
    print("=" * 40)
    print("✨ 使用稳定的HTTP API")

    # 检查API密钥和模型 (由key_manager处理)
    model_name = os.getenv('GEMINI_MODEL_NAME', 'gemini-2.0-flash')

    print("✅ API密钥已加载 (由key_manager管理)")
    print(f"🤖 使用模型: {model_name}")
    
    # 获取文件夹路径
    while True:
        folder_path = input("\n请输入音频文件夹路径: ").strip()
        
        if not folder_path:
            print("❌ 文件夹路径不能为空")
            continue
            
        folder_path = Path(folder_path)
        
        if not folder_path.exists():
            print(f"❌ 文件夹不存在: {folder_path}")
            continue
            
        if not folder_path.is_dir():
            print(f"❌ 不是文件夹: {folder_path}")
            continue
            
        break

    srt_input_folder = input("请输入对应的SRT文件文件夹路径 (如果不需要上传现有SRT文件，请留空): ").strip() or None
    
    print(f"\n📁 目标文件夹: {folder_path}")
    print("🔄 开始处理...")
    
    # 开始批量处理（在原文件夹中生成SRT文件）
    success = process_folder(
        folder_path_str=str(folder_path),
        output_folder_str=None,
        srt_input_folder_str=srt_input_folder # Pass srt_input_folder
    )
    
    if success:
        print("\n🎉 处理完成！")
        print("📄 SRT文件已生成在原文件夹中")
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
