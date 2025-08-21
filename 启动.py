#!/usr/bin/env python3
"""
HTTP版本的简单启动脚本
基于稳定的HTTP API，只需要输入文件夹路径
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from 批量处理 import process_folder


def main():
    """简化的主函数"""
    print("🎵 HTTP音频转录工具")
    print("=" * 40)
    print("✨ 使用稳定的HTTP API")

    # 加载环境变量
    load_dotenv()

    # 检查API密钥和模型
    api_key = os.getenv('GEMINI_API_KEY')
    model_name = os.getenv('GEMINI_MODEL_NAME', 'gemini-2.0-flash')

    if not api_key:
        print("❌ 错误：未找到API密钥")
        print("请确保在 .env 文件中设置了 GEMINI_API_KEY")
        return

    print("✅ API密钥已加载")
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
    
    print(f"\n📁 目标文件夹: {folder_path}")
    print("🔄 开始处理...")
    
    # 开始批量处理（在原文件夹中生成SRT文件）
    success = process_folder(
        folder_path=str(folder_path),
        output_folder=None
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
