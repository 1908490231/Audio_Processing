#!/usr/bin/env python3
"""
管理失败文件记录
查看、清理、合并失败文件记录
"""

import json
from pathlib import Path
from datetime import datetime


def list_all_failed_records():
    """列出所有失败文件记录"""
    failed_dir = Path("failed_files")
    if not failed_dir.exists():
        print("❌ 没有找到失败文件记录目录")
        return []
    
    json_files = list(failed_dir.glob("failed_files_*.json"))
    if not json_files:
        print("❌ 没有找到失败文件记录")
        return []
    
    # 按时间排序
    json_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    print(f"📁 找到 {len(json_files)} 个失败文件记录:")
    print("=" * 60)
    
    total_failed = 0
    records = []
    
    for i, file in enumerate(json_files, 1):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 解析时间戳
            try:
                process_time = datetime.fromisoformat(data['processing_time'].replace('Z', '+00:00'))
                time_str = process_time.strftime('%Y-%m-%d %H:%M:%S')
            except:
                time_str = data.get('processing_time', '未知时间')
            
            failed_count = data['total_failed']
            total_failed += failed_count
            
            print(f"{i:2d}. {file.name}")
            print(f"    📅 处理时间: {time_str}")
            print(f"    📁 源文件夹: {data['source_folder']}")
            print(f"    ❌ 失败文件数: {failed_count}")
            print(f"    💾 文件大小: {file.stat().st_size / 1024:.1f} KB")
            print()
            
            records.append({
                'file': file,
                'data': data,
                'failed_count': failed_count,
                'time': time_str
            })
            
        except Exception as e:
            print(f"❌ 读取文件失败: {file.name} - {e}")
    
    print(f"📊 总计: {len(records)} 个记录, {total_failed} 个失败文件")
    return records


def show_failed_files_summary(records):
    """显示失败文件汇总"""
    if not records:
        return
    
    print(f"\n📋 失败文件汇总:")
    print("=" * 60)
    
    # 按源文件夹分组
    by_folder = {}
    all_failed_files = []
    
    for record in records:
        folder = record['data']['source_folder']
        if folder not in by_folder:
            by_folder[folder] = []
        by_folder[folder].extend(record['data']['failed_files'])
        all_failed_files.extend(record['data']['failed_files'])
    
    # 显示按文件夹分组的统计
    for folder, files in by_folder.items():
        print(f"📁 {folder}: {len(files)} 个失败文件")
    
    # 显示最常见的错误类型
    print(f"\n🔍 错误类型分析:")
    error_types = {}
    for failed_file in all_failed_files:
        error = failed_file.get('error', '未知错误')
        # 提取错误类型的关键词
        if 'ProxyError' in error:
            error_type = '代理连接错误'
        elif 'Max retries exceeded' in error:
            error_type = '重试次数耗尽'
        elif 'RemoteDisconnected' in error:
            error_type = '远程连接断开'
        elif 'timeout' in error.lower():
            error_type = '连接超时'
        else:
            error_type = '其他错误'
        
        error_types[error_type] = error_types.get(error_type, 0) + 1
    
    for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
        print(f"   {error_type}: {count} 次")


def clean_old_records():
    """清理旧的失败记录"""
    failed_dir = Path("failed_files")
    if not failed_dir.exists():
        print("❌ 没有找到失败文件记录目录")
        return
    
    all_files = list(failed_dir.glob("failed_*"))
    if not all_files:
        print("❌ 没有找到失败文件记录")
        return
    
    # 按修改时间排序
    all_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    print(f"📁 找到 {len(all_files)} 个失败记录文件")
    print("最新的5个记录将被保留，其余将被删除")
    
    # 保留最新的5个记录（JSON + TXT = 10个文件）
    files_to_keep = all_files[:10]
    files_to_delete = all_files[10:]
    
    if not files_to_delete:
        print("✅ 没有需要清理的旧记录")
        return
    
    print(f"\n将删除 {len(files_to_delete)} 个旧文件:")
    for file in files_to_delete:
        print(f"   - {file.name}")
    
    response = input(f"\n确认删除这些文件？(y/n): ").lower().strip()
    if response in ['y', 'yes', '是']:
        deleted_count = 0
        for file in files_to_delete:
            try:
                file.unlink()
                deleted_count += 1
            except Exception as e:
                print(f"❌ 删除失败: {file.name} - {e}")
        
        print(f"✅ 成功删除 {deleted_count} 个文件")
    else:
        print("操作已取消")


def merge_failed_files():
    """合并所有失败文件到一个记录中"""
    records = list_all_failed_records()
    if len(records) <= 1:
        print("❌ 没有足够的记录需要合并")
        return
    
    print(f"\n🔄 准备合并 {len(records)} 个失败记录")
    
    # 收集所有失败文件
    all_failed_files = []
    source_folders = set()
    
    for record in records:
        all_failed_files.extend(record['data']['failed_files'])
        source_folders.add(record['data']['source_folder'])
    
    # 去重（基于完整路径）
    unique_files = {}
    for failed_file in all_failed_files:
        full_path = failed_file['full_path']
        if full_path not in unique_files:
            unique_files[full_path] = failed_file
    
    unique_failed_files = list(unique_files.values())
    
    print(f"📊 合并结果:")
    print(f"   原始失败文件: {len(all_failed_files)} 个")
    print(f"   去重后文件: {len(unique_failed_files)} 个")
    print(f"   涉及文件夹: {', '.join(source_folders)}")
    
    response = input(f"\n确认合并？(y/n): ").lower().strip()
    if response not in ['y', 'yes', '是']:
        print("操作已取消")
        return
    
    # 创建合并后的记录
    merged_data = {
        "processing_time": datetime.now().isoformat(),
        "source_folder": f"合并记录({len(source_folders)}个文件夹)",
        "total_failed": len(unique_failed_files),
        "failed_files": unique_failed_files,
        "merged_from": [record['file'].name for record in records]
    }
    
    # 保存合并记录
    failed_dir = Path("failed_files")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    merged_file = failed_dir / f"merged_failed_files_{timestamp}.json"
    
    with open(merged_file, 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 合并记录已保存: {merged_file.name}")
    
    # 询问是否删除原始记录
    response = input(f"\n是否删除原始的 {len(records)} 个记录？(y/n): ").lower().strip()
    if response in ['y', 'yes', '是']:
        deleted_count = 0
        for record in records:
            try:
                record['file'].unlink()
                # 同时删除对应的txt文件
                txt_file = record['file'].with_name(record['file'].name.replace('failed_files_', 'failed_list_'))
                if txt_file.exists():
                    txt_file.unlink()
                deleted_count += 1
            except Exception as e:
                print(f"❌ 删除失败: {record['file'].name} - {e}")
        
        print(f"✅ 成功删除 {deleted_count} 个原始记录")


def main():
    """主函数"""
    print("🗂️  失败文件记录管理工具")
    print("=" * 50)
    
    while True:
        print(f"\n请选择操作:")
        print("1. 📋 查看所有失败记录")
        print("2. 📊 显示失败文件汇总")
        print("3. 🧹 清理旧记录（保留最新5个）")
        print("4. 🔄 合并所有失败记录")
        print("5. 🚪 退出")
        
        choice = input("\n请输入选择 (1-5): ").strip()
        
        if choice == '1':
            list_all_failed_records()
        elif choice == '2':
            records = list_all_failed_records()
            show_failed_files_summary(records)
        elif choice == '3':
            clean_old_records()
        elif choice == '4':
            merge_failed_files()
        elif choice == '5':
            print("👋 再见！")
            break
        else:
            print("❌ 无效选择，请重试")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ 操作被用户中断")
    except Exception as e:
        print(f"\n❌ 程序发生错误: {e}")
    
    input("\n按回车键退出...")
