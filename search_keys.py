import os
import requests
import time
import random
from datetime import datetime

# --- 配置区 ---

# 从环境变量中获取 GitHub 个人访问令牌 (PAT)
# GitHub Actions 会自动提供这个环境变量，确保了安全性
GITHUB_TOKEN = os.getenv('GH_PAT')
if not GITHUB_TOKEN:
    raise ValueError("未找到 GitHub PAT。请设置 'GH_PAT' 环境变量。")

# 要搜索的字符串前缀。你可以根据需要添加更多
SEARCH_QUERIES = [
    'AIzaSy'
]

# 保存结果的文件名
OUTPUT_FILE = "api.txt"

# GitHub API 请求头，包含认证信息
HEADERS = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3.text-match+json'
}

# --- 功能函数 ---

def check_rate_limit():
    """检查GitHub API的速率限制，如果接近限制则暂停等待。"""
    try:
        response = requests.get('https://api.github.com/rate_limit', headers=HEADERS)
        response.raise_for_status()
        rate_info = response.json().get('resources', {}).get('search', {})
        remaining = rate_info.get('remaining', 0)
        reset_time = rate_info.get('reset', 0)
        
        print(f"API速率限制: 剩余 {remaining} 次请求。重置时间: {datetime.fromtimestamp(reset_time).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 如果剩余请求次数小于5，就暂停直到重置时间
        if remaining < 5:
            sleep_time = max(0, reset_time - time.time()) + 5 # 增加5秒缓冲
            print(f"速率限制过低，程序将暂停 {sleep_time:.2f} 秒。")
            time.sleep(sleep_time)
            
    except requests.exceptions.RequestException as e:
        print(f"检查速率限制时出错: {e}")
        # 出错时，默认暂停60秒以保证安全
        time.sleep(60)

def search_github(query):
    """根据给定的查询字符串在 GitHub 上搜索代码。"""
    found_keys = set()
    base_url = 'https://api.github.com/search/code'
    
    # 构造更精确的查询，只查找旧代码，以过滤掉大量测试和示例Key
    # full_query = f'{query} pushed:<{datetime.now().year}-01-01'
    full_query = query # 为了最大化搜索结果，我们先用简单查询
    
    params = {
        'q': full_query,
        'per_page': 100, # 每页最多100个结果
        'page': 1
    }
    
    print(f"🚀 开始搜索: '{full_query}'")
    
    while True:
        check_rate_limit() # 每次请求前都检查速率限制
        try:
            response = requests.get(base_url, headers=HEADERS, params=params)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.HTTPError as e:
            # GitHub API对过于复杂的搜索会返回422，此时通常意味着搜索结束
            if e.response.status_code == 422:
                print("已达到此查询的可搜索结果末尾。")
                break
            print(f"HTTP请求错误: {e}")
            time.sleep(60)
            continue
        except requests.exceptions.RequestException as e:
            print(f"网络请求错误: {e}")
            time.sleep(60)
            continue
            
        items = data.get('items', [])
        
        # 如果当前页没有结果，说明搜索结束
        if not items:
            print("当前页无结果，结束搜索。")
            break

        for item in items:
            repo_name = item.get('repository', {}).get('full_name', '未知仓库')
            file_path = item.get('path', '未知路径')
            
            # 从返回的文本匹配中提取含有Key的整行内容
            for match in item.get('text_matches', []):
                line_content = match.get('fragment', '')
                
                # 简单提取逻辑：分割行内容，找到以查询开头的单词
                words = line_content.split()
                for word in words:
                    # 清理单词周围可能存在的引号、分号等字符
                    cleaned_word = word.strip('\'",;()[]{}<>') 
                    if cleaned_word.startswith(query) and len(cleaned_word) > len(query): # 确保不是只有前缀
                        print(f"  [+] 发现潜在Key: {cleaned_word} | 来源: {repo_name}/{file_path}")
                        
                        # --- 主要修改点在这里 ---
                        # 直接将清理后的单词（即API Key）添加到集合中
                        found_keys.add(cleaned_word)
                        # -----------------------

        # 翻页逻辑：检查响应头中是否有 'next' 链接
        if 'next' in response.links:
            params['page'] += 1
            time.sleep(random.uniform(2, 5)) # 随机暂停2-5秒，避免请求过于频繁
        else:
            print(f"✅ 查询 '{query}' 结束。")
            break
            
    return found_keys

def main():
    """主函数，负责整个流程的调度。"""
    all_found_keys = set()

    # 读取 api.txt 中已有的Key，避免重复添加
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                all_found_keys.add(line.strip())
        print(f"已从 {OUTPUT_FILE} 加载 {len(all_found_keys)} 条已有记录。")

    # 遍历所有查询条件
    for query in SEARCH_QUERIES:
        keys_from_query = search_github(query)
        all_found_keys.update(keys_from_query)
    
    print(f"\n搜索完成。共计 {len(all_found_keys)} 条不重复记录，将写入 {OUTPUT_FILE}...")

    # 将所有不重复的Key排序后写入文件
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        # 按字母顺序排序后写入文件
        for key in sorted(list(all_found_keys)):
            f.write(f"{key}\n")
    
    print("✨ 任务完成！")

if __name__ == '__main__':
    main()
