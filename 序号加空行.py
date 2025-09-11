import re
import os

def add_extra_newlines(file_path):
    """
    读取指定文件，并根据以下规则处理换行：
    1. 序号行后跟一个换行符。
    2. 每个序号下的内容行后跟一个换行符。
    3. 每个序号下的所有内容结束后，添加一个空行。
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_lines = f.readlines()

        # Step 1: Clean up the input by removing all existing empty lines
        cleaned_lines = [line.strip() for line in raw_lines if line.strip() != '']

        blocks = []
        current_block_number = None
        current_block_content = []

        for line in cleaned_lines: # Iterate over cleaned lines
            if re.fullmatch(r'\d+', line):
                if current_block_number is not None:
                    blocks.append((current_block_number, current_block_content))
                current_block_number = line
                current_block_content = []
            else: # All remaining lines are content lines
                current_block_content.append(line)
        
        if current_block_number is not None: # Add the last block
            blocks.append((current_block_number, current_block_content))

        processed_output_parts = []
        for number, content_lines in blocks:
            processed_output_parts.append(number)
            processed_output_parts.append('\r\n') # 序号后跟一个换行符 (Windows style)

            for content_line in content_lines:
                processed_output_parts.append(content_line)
                processed_output_parts.append('\r\n') # 内容行后跟一个换行符 (Windows style)
            
            processed_output_parts.append('\r\n') # 在所有内容结束后添加一个空行 (即两个换行符, Windows style)

        final_content = "".join(processed_output_parts)
        
        # For debugging: print the content that will be written
        print("--- Content to be written ---")
        print(repr(final_content)) # Use repr to show actual newlines
        print("-----------------------------")

        with open(file_path, 'w', encoding='utf-8', newline='') as f: # Use newline='' to prevent universal newlines mode
            f.write(final_content)
        print(f"文件 '{file_path}' 已成功处理。")
    except FileNotFoundError:
        print(f"错误：文件 '{file_path}' 未找到。")
    except Exception as e:
        print(f"处理文件时发生错误：{e}")

if __name__ == "__main__":
    user_input_path = input("请输入文件路径或文件夹路径： ")
    
    if os.path.isfile(user_input_path):
        if user_input_path.lower().endswith('.srt'):
            add_extra_newlines(user_input_path)
        else:
            print(f"错误：指定文件 '{user_input_path}' 不是 .srt 文件。")
    elif os.path.isdir(user_input_path):
        print(f"正在处理文件夹 '{user_input_path}' 中的所有 .srt 文件...")
        for root, _, files in os.walk(user_input_path):
            for file in files:
                if file.lower().endswith('.srt'):
                    file_path = os.path.join(root, file)
                    add_extra_newlines(file_path)
    else:
        print(f"错误：路径 '{user_input_path}' 无效或不存在。请提供有效的文件或文件夹路径。")
