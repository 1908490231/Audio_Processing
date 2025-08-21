#!/usr/bin/env python3
"""
并行音频转录工具
专门用于同时处理多个mp3文件，提高处理效率
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from 批量处理 import process_folder


def main():
    """主函数 - 专门用于并行处理"""
    print("🎵 并行音频转录工具")
    print("=" * 50)
    print("🚀 同时处理多个mp3文件，大幅提高效率")
    print("⚠️  注意：并行处理会消耗更多系统资源")
    print()

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
    folder_path = input("\n请输入音频文件夹路径: ").strip()
    if not folder_path:
        print("❌ 文件夹路径不能为空")
        return
    
    # 验证文件夹
    folder_path = Path(folder_path)
    if not folder_path.exists():
        print(f"❌ 文件夹不存在: {folder_path}")
        return
    
    # 并行设置
    print("\n🔧 并行处理设置:")
    print("同时处理的文件数量 (建议根据你的网络和系统性能选择):")
    print("1. 2个文件 (推荐，平衡速度和稳定性)")
    print("2. 3个文件 (更快，适合网络较好的情况)")
    print("3. 4个文件 (最快，适合高性能系统)")
    print("4. 自定义数量")
    
    worker_choice = input("请选择 (1-4): ").strip()
    
    if worker_choice == "1":
        max_workers = 2
    elif worker_choice == "2":
        max_workers = 3
    elif worker_choice == "3":
        max_workers = 4
    elif worker_choice == "4":
        try:
            max_workers = int(input("请输入同时处理的文件数量 (1-8): "))
            if max_workers < 1 or max_workers > 8:
                print("⚠️  数量超出范围，使用默认值 2")
                max_workers = 2
        except ValueError:
            print("⚠️  输入无效，使用默认值 2")
            max_workers = 2
    else:
        max_workers = 2
    
    print(f"✅ 将同时处理 {max_workers} 个文件")
    
    # 询问输出位置
    print("\n📁 输出选项:")
    print("1. 在原文件夹中生成 SRT 文件")
    print("2. 指定输出文件夹")
    
    choice = input("请选择 (1 或 2): ").strip()
    
    output_folder = None
    if choice == "2":
        output_folder = input("请输入输出文件夹路径: ").strip()
        if not output_folder:
            print("使用原文件夹作为输出位置")
            output_folder = None
    
    # 显示处理信息
    print(f"\n📋 处理信息:")
    print(f"   源文件夹: {folder_path}")
    print(f"   输出位置: {'原文件夹' if not output_folder else output_folder}")
    print(f"   并行线程: {max_workers}")
    print(f"   处理模式: 并行处理")
    
    # 确认开始
    confirm = input("\n是否开始处理？(y/n): ").strip().lower()
    if confirm not in ['y', 'yes', '是', '确定']:
        print("❌ 操作已取消")
        return
    
    # 开始处理
    print(f"\n🚀 开始并行处理文件夹: {folder_path}")
    print(f"🔄 使用 {max_workers} 个线程同时处理")
    print("=" * 50)
    
    success = process_folder(
        folder_path=str(folder_path),
        output_folder=output_folder,
        parallel=True,
        max_workers=max_workers
    )
    
    if success:
        print("\n🎉 并行处理完成！")
        print("📄 SRT文件已生成")
        print("💡 提示：并行处理可以大幅提高效率，但请注意API调用限制")
    else:
        print("\n❌ 处理失败或被取消")
        print("💡 提示：如果遇到问题，可以尝试减少并行线程数量")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ 操作被用户中断")
    except Exception as e:
        print(f"\n❌ 程序发生错误: {e}")
        print("💡 提示：如果经常出错，建议使用顺序处理模式")
    
    input("\n按回车键退出...")
