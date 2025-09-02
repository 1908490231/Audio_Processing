import os
import queue
import sys
import requests
import threading
import time
from dotenv import load_dotenv
import contextlib # 导入 contextlib

API_KEY_PREFIX = "API_KEY_"

class ApiKeyManager:
    """
    一个健壮的API密钥管理器和请求调度器。
    它封装了密钥轮询和重试逻辑，并为临时的API错误引入了“冷静期”策略，
    以适应不稳定的API行为，在高并发下也能稳健运行。
    """
    def __init__(self):
        self._load_keys_from_env()

    def _load_keys_from_env(self):
        """从.env加载API Keys到内部队列。"""
        load_dotenv()
        print("正在初始化API密钥管理器...")
        
        keys = [v for k, v in os.environ.items() if k.startswith(API_KEY_PREFIX)]
        
        if not keys:
            print(f"错误：在 .env 文件中未找到任何以 '{API_KEY_PREFIX}' 开头的API Key。", file=sys.stderr)
            sys.exit(1)
            
        self.key_queue = queue.Queue()
        self.initial_key_count = len(keys)
        for key in keys:
            self.key_queue.put(key)
            
        print(f"✔️ 成功加载 {self.initial_key_count} 个API Key。")

    @contextlib.contextmanager
    def get_key_for_session(self):
        """
        为一系列相关的API调用提供一个固定的API Key。
        这是一个上下文管理器，确保Key在使用后被安全地放回队列。
        """
        api_key = None
        try:
            # 从队列获取一个Key，如果队列为空，会等待，这在高并发下是安全的
            api_key = self.key_queue.get(timeout=self.initial_key_count * 5) # 增加超时以应对高负载
            yield api_key
        finally:
            if api_key:
                # 无论会话成功还是失败，都将Key放回队列
                self.key_queue.put(api_key)

    def execute_request(self, api_key, method, url, **kwargs):
        """
        【已修改】使用一个 *指定的* API Key 执行HTTP请求。
        此方法现在只处理单次请求的重试和错误，不再负责从队列取Key。
        """
        if not api_key:
            raise ValueError("execute_request 必须提供一个 api_key。")

        # 对于单个请求，我们可以进行小范围的重试（例如，应对瞬时网络问题）
        max_attempts = 3 # 对同一个key的请求最多重试3次
        last_exception = None

        for attempt in range(max_attempts):
            try:
                current_kwargs = kwargs.copy()
                headers = current_kwargs.get('headers', {}).copy()
                headers['X-goog-api-key'] = api_key
                current_kwargs['headers'] = headers

                print(f"    (使用Key: ...{api_key[-4:]}，尝试 #{attempt + 1}/{max_attempts})")
                response = requests.request(method, url, **current_kwargs)

                # 如果请求成功，直接返回
                if response.ok:
                    return response

                # 如果是已知的临时错误 (如速率限制)
                if response.status_code in [429, 500, 503]:
                    error_message = f"Key ...{api_key[-4:]} 遇到临时错误 (状态码: {response.status_code})。等待后重试..."
                    print(f"    ⚠️ {error_message}")
                    last_exception = Exception(f"{error_message} - Response: {response.text}")
                    time.sleep(2 * (attempt + 1)) # 递增等待时间
                    continue

                # 如果是权限或无效参数等错误，不应重试，直接抛出异常
                if response.status_code in [400, 403, 404]:
                    # 添加更详细的调试信息
                    error_details = response.text
                    try:
                        error_json = response.json()
                        error_details = error_json.get('error', {}).get('message', response.text)
                    except Exception:
                        pass # 如果响应不是json，就用原始文本
                    
                    print(f"    ❌ Key ...{api_key[-4:]} 遇到永久性错误 (状态码: {response.status_code})。错误详情: {error_details}")
                    response.raise_for_status() # 这会中断循环并抛出HTTPError

                # 其他客户端或服务器错误
                response.raise_for_status()

            except requests.exceptions.RequestException as e:
                print(f"    ❌ Key ...{api_key[-4:]} 发生网络错误: {e}。等待后重试...")
                last_exception = e
                time.sleep(2 * (attempt + 1))
                continue
        
        # 如果循环了所有次数都未能成功
        raise Exception(f"使用Key ...{api_key[-4:]} 尝试了 {max_attempts} 次后仍无法完成请求。最后错误: {last_exception}")


# 全局单例
api_manager = ApiKeyManager()