# key_manager.py

import os
import queue
import sys
from dotenv import load_dotenv

# --- 配置 ---
# 这是我们约定好的，在 .env 文件中API Key变量的前缀
# 这样做的好处是，如果以后有其他类型的Key（比如用于上传的Key），可以定义不同的前缀
API_KEY_PREFIX = "API_KEY_"

# --- 模块初始化 ---

def _initialize_key_queue():
    """
    一个内部函数，用于加载环境变量并创建填充了API Key的队列。
    这个函数在模块第一次被导入时执行一次。
    """
    # 加载项目根目录下的 .env 文件
    # find_dotenv() 会自动从当前文件向上查找 .env 文件，非常可靠
    load_dotenv()

    print("正在从 .env 文件加载API Keys...")

    # 1. 从环境变量中加载所有以指定前缀开头的密钥
    keys = [
        value for key, value in os.environ.items() if key.startswith(API_KEY_PREFIX)
    ]

    # 2. 检查是否找到了任何Key
    if not keys:
        # 如果没有找到任何Key，打印错误信息并退出程序，防止后续代码出错
        print(f"错误：在 .env 文件中没有找到任何以 '{API_KEY_PREFIX}' 开头的API Key。", file=sys.stderr)
        print("请检查你的 .env 文件，并确保至少有一个Key，例如：API_KEY_1='your_key_here'", file=sys.stderr)
        sys.exit(1) # 退出程序，返回一个错误码

    print(f"✔️ 成功加载 {len(keys)} 个API Key。")

    # 3. 创建一个线程安全的队列
    key_q = queue.Queue()

    # 4. 将所有加载到的Key放入队列中
    for key in keys:
        key_q.put(key)
        
    return key_q

# --- 全局实例 ---

# 这是本模块的核心：创建一个全局的、唯一的密钥队列实例。
# 当其他任何 Python 文件 (如 批量处理.py) 执行 `from key_manager import api_key_queue` 时,
# 它们获取到的都是下面这同一个队列对象。
# 这种设计确保了整个应用程序共享同一个密钥池和状态。
api_key_queue = _initialize_key_queue()


# --- 使用说明 (注释) ---

# 如何在你的其他代码中使用这个模块？
#
# 1. 导入队列实例:
#    from key_manager import api_key_queue
#
# 2. 在需要API Key的地方，从队列中获取:
#    api_key = api_key_queue.get()
#
# 3. 使用这个 api_key 发起请求...
#
# 4. 请求结束后，无论成功或失败，务必将Key放回队列:
#    api_key_queue.put(api_key)
#
#    推荐使用 try...finally 结构来确保key一定会被放回:
#    api_key = None
#    try:
#        api_key = api_key_queue.get()
#        # ... 执行你的请求 ...
#    finally:
#        if api_key:
#            api_key_queue.put(api_key)