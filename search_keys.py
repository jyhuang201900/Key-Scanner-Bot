import os
import requests
import time
import random
import string
from datetime import datetime

# --- 配置区 ---
GITHUB_TOKEN = os.getenv('GH_PAT')
if not GITHUB_TOKEN:
    raise ValueError("未找到 GitHub PAT。请设置 'GH_PAT' 环境变量。")

# 基础搜索前缀
BASE_QUERY_PREFIX = 'AIzaSy'

# 保存结果的文件名
OUTPUT_FILE = "api.txt"

# GitHub API 请求头
HEADERS = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3.text-match+json'
}

# --- 功能函数 ---

def generate_search_queries(prefix):
    """
    【核心增强】生成更精细的搜索查询列表。
    将 'AIzaSy' 扩展为 ['AIzaSyA', 'AIzaSyB', ..., 'AIzaSy9', 'AIzaSy-', 'AIzaSy_']
    """
    # 包含所有字母（大小写）、数字，以及API Key中常见的'-'和'_'
    characters_to_try = string.ascii_letters + string.digits + '-_'
    queries = [f'"{prefix}{char}"' for char in characters_to_try]
    print(f"已生成 {len(queries)} 个精细化搜索查询，例如：{queries[0]}, {queries[10]}, {queries[-1]}")
    return queries

def check_rate_limit():
    """检查GitHub API的速率限制，如果接近限制则暂停等待。"""
    try:
        response = requests.get('https://api.github.com/rate_limit', headers=HEADERS)
        response.raise_for_status()
        rate_info = response.json().get('resources', {}).get('search', {})
        remaining = rate_info.get('remaining', 0)
        reset_time = rate_info.get('reset', 0)
        
        print(f"API速率限制: 剩余 {remaining} 次请求。重置时间: {datetime.fromtimestamp(reset_time).strftime('%Y-%m-%d %H:%M:%S')}")
        
        if remaining < 5:
            sleep_time = max(0, reset_time - time.time()) + 5
            print(f"速率限制过低，程序将暂停 {sleep_time:.2f} 秒。")
            time.sleep(sleep_time)
            
    except requests.exceptions.RequestException as e:
        print(f"检查速率限制时出错: {e}")
        time.sleep(60)

def search_github(query):
    """根据单个精细化的查询字符串在 GitHub 上搜索代码。"""
    found_keys = set()
    base_url = 'https://api.github.com/search/code'
    params = {'q': query, 'per_page': 100, 'page': 1}
    
    print(f"🚀 开始精细搜索: {query}")
    
    page_count = 0
    while True:
        # GitHub API限制每个查询最多只能访问10页（1000个结果）
        if page_count >= 10:
            print(f"已达到查询 '{query}' 的10页（1000个结果）上限，继续下一个查询。")
            break

        check_rate_limit()
        try:
            response = requests.get(base_url, headers=HEADERS, params=params)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in [422, 403]:
                print(f"查询 '{query}' 遇到API限制或无效查询，跳过。错误: {e}")
                break
            print(f"HTTP请求错误: {e}")
            time.sleep(60)
            continue
        except requests.exceptions.RequestException as e:
            print(f"网络请求错误: {e}")
            time.sleep(60)
            continue
            
        items = data.get('items', [])
        if not items:
            print(f"查询 '{query}' 在第 {params['page']} 页无结果，结束此查询。")
            break

        for item in items:
            repo_name = item.get('repository', {}).get('full_name', '未知仓库')
            file_path = item.get('path', '未知路径')
            
            for match in item.get('text_matches', []):
                line_content = match.get('fragment', '')
                words = line_content.replace(':', ' ').replace('=', ' ').split() # 分割更多可能的分隔符
                for word in words:
                    cleaned_word = word.strip('\'",;()[]{}<>`')
                    # 我们查询的是 "AIzaSyA"，所以要确保找到的词以它开头
                    if cleaned_word.startswith(query.strip('"')) and len(cleaned_word) > len(BASE_QUERY_PREFIX):
                        # print(f"  [+] 发现潜在Key: {cleaned_word} | 来源: {repo_name}/{file_path}")
                        found_keys.add(cleaned_word)

        if 'next' in response.links:
            params['page'] += 1
            page_count += 1
            time.sleep(random.uniform(2, 4)) # 随机暂停，避免请求过于频繁
        else:
            print(f"✅ 查询 '{query}' 完成。")
            break
            
    return found_keys

def main():
    """主函数，负责整个流程的调度。"""
    all_found_keys = set()

    # 读取 api.txt 中已有的Key，并在读取时进行清洗
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                clean_key = line.split('|')[0].strip()
                if clean_key:
                    all_found_keys.add(clean_key)
        print(f"已从 {OUTPUT_FILE} 加载并清洗了 {len(all_found_keys)} 条已有记录。")

    # 【核心修改】生成精细化的查询列表
    SEARCH_QUERIES = generate_search_queries(BASE_QUERY_PREFIX)

    # 遍历所有精细化的查询条件
    for i, query in enumerate(SEARCH_QUERIES):
        print(f"\n--- 正在执行第 {i+1}/{len(SEARCH_QUERIES)} 个主查询系列 ---")
        keys_from_query = search_github(query)
        new_keys_count = len(keys_from_query - all_found_keys)
        if new_keys_count > 0:
            print(f"🎉 查询 '{query}' 发现 {new_keys_count} 个新Key！")
            all_found_keys.update(keys_from_query)
        else:
            print(f"查询 '{query}' 未发现新Key。")
    
    print(f"\n搜索完成。共计 {len(all_found_keys)} 条不重复记录，将写入 {OUTPUT_FILE}...")

    # 将所有不重复的Key排序后写入文件
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for key in sorted(list(all_found_keys)):
            f.write(f"{key}\n")
    
    print("✨ 任务完成！")

if __name__ == '__main__':
    main()
