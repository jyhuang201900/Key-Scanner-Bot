import requests
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- 配置区 ---

# 包含待验证API密钥的输入文件
INPUT_FILE = "api.txt"

# 保存有效API密钥的输出文件
VALID_KEYS_FILE = "valid_gemini_keys.txt"

# 保存无效或已过期API密钥的输出文件
INVALID_KEYS_FILE = "invalid_keys.txt"

# 并发检查的线程数（可以根据你的网络情况调整，10-20是个不错的开始）
MAX_WORKERS = 15

# Gemini API的轻量级验证端点 (列出模型)
VALIDATION_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"

# --- 核心功能 ---

def check_key(api_key):
    """
    使用单个API密钥调用Gemini API以验证其有效性。
    
    返回: (状态字符串, api_key)
    状态可以是: 'valid', 'invalid', 'error'
    """
    url = f"{VALIDATION_ENDPOINT}?key={api_key}"
    try:
        # 设置一个合理的超时时间，防止单个请求卡住太久
        response = requests.get(url, timeout=10)
        
        # 状态码 200 OK，表示密钥有效
        if response.status_code == 200:
            # 进一步确认返回的内容是正确的模型列表
            if 'models' in response.json():
                print(f"✅ [有效] Key: {api_key[:8]}... ")
                return 'valid', api_key
            else:
                print(f"❌ [无效] Key: {api_key[:8]}... (响应异常)")
                return 'invalid', api_key

        # 状态码 400 Bad Request，通常是无效Key的标志
        elif response.status_code == 400:
            error_data = response.json()
            if 'error' in error_data and 'API key not valid' in error_data['error']['message']:
                print(f"❌ [无效] Key: {api_key[:8]}... (API明确拒绝)")
                return 'invalid', api_key
            else:
                print(f"❓ [未知错误 400] Key: {api_key[:8]}... - {error_data.get('error', {}).get('message', 'No message')}")
                return 'invalid', api_key # 其他400错误也视为无效
        
        # 其他所有错误码都视为无效
        else:
            print(f"❌ [无效] Key: {api_key[:8]}... (状态码: {response.status_code})")
            return 'invalid', api_key

    except requests.exceptions.RequestException as e:
        # 网络相关的错误
        print(f"🚨 [网络错误] Key: {api_key[:8]}... - {e.__class__.__name__}")
        return 'error', api_key

def main():
    """主函数，读取文件、并发验证并保存结果。"""
    
    # 检查输入文件是否存在
    if not os.path.exists(INPUT_FILE):
        print(f"错误: 输入文件 '{INPUT_FILE}' 未找到。请先运行搜索脚本。")
        return

    # 读取所有待检查的Keys，并去重
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        keys_to_check = {line.strip() for line in f if line.strip()}
    
    if not keys_to_check:
        print(f"'{INPUT_FILE}' 中没有找到任何API密钥。")
        return

    print(f"🔍 准备从 '{INPUT_FILE}' 中验证 {len(keys_to_check)} 个唯一的API密钥...")
    
    valid_keys = []
    invalid_keys = []
    
    start_time = time.time()

    # 使用线程池并发执行检查
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 提交所有任务
        future_to_key = {executor.submit(check_key, key): key for key in keys_to_check}
        
        # 获取已完成任务的结果
        for i, future in enumerate(as_completed(future_to_key), 1):
            try:
                status, key = future.result()
                if status == 'valid':
                    valid_keys.append(key)
                elif status == 'invalid':
                    invalid_keys.append(key)
                # 'error'状态的key我们暂时不处理，只打印日志
            except Exception as exc:
                print(f"处理一个Key时发生内部错误: {exc}")
            
            # 打印进度
            print(f"--- 进度: {i}/{len(keys_to_check)} ---")

    end_time = time.time()
    
    print("\n" + "="*40)
    print("✨ 验证完成！")
    print(f"总耗时: {end_time - start_time:.2f} 秒")
    print(f"总计找到 {len(valid_keys)} 个有效密钥。")
    print(f"另有 {len(invalid_keys)} 个无效密钥。")
    print("="*40 + "\n")

    # 将有效密钥写入文件
    if valid_keys:
        with open(VALID_KEYS_FILE, 'w', encoding='utf-8') as f:
            for key in sorted(valid_keys):
                f.write(f"{key}\n")
        print(f"所有有效密钥已保存到 '{VALID_KEYS_FILE}'")

    # 将无效密钥写入文件（可选，但有助于调试）
    if invalid_keys:
        with open(INVALID_KEYS_FILE, 'w', encoding='utf-8') as f:
            for key in sorted(invalid_keys):
                f.write(f"{key}\n")
        print(f"所有无效密钥已保存到 '{INVALID_KEYS_FILE}'")

if __name__ == "__main__":
    main()
