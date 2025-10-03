import os
import requests
import time
import random
from datetime import datetime, timedelta

# --- 配置区 ---
GITHUB_TOKEN = os.getenv('GH_PAT')
if not GITHUB_TOKEN:
    raise ValueError("未找到 GitHub PAT。请设置 'GH_PAT' 环境变量。")

# 基础搜索前缀
BASE_SEARCH_PREFIX = 'AIzaSy'

OUTPUT_FILE = "api.txt"
HEADERS = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3.text-match+json'
}

# --- 功能函数 (check_rate_limit 函数保持不变) ---
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

# --- 核心搜索逻辑 (已重构) ---
def search_github(query, existing_keys):
    """
    根据单个精确的查询在 GitHub 上搜索代码。
    返回一个包含新发现的Key的集合。
    """
    found_keys = set()
    base_url = 'https://api.github.com/search/code'
    params = {'q': query, 'per_page': 100, 'page': 1}
    
    print(f"🚀 开始搜索: '{query}'")
    
    try:
        while True:
            check_rate_limit()
            response = requests.get(base_url, headers=HEADERS, params=params)
            
            # 如果触发了滥用限制，则长时间休眠
            if response.status_code == 403 and 'abuse detection' in response.text.lower():
                print("🚨 触发滥用检测机制，暂停5分钟...")
                time.sleep(300)
                continue

            response.raise_for_status()
            data = response.json()
            
            items = data.get('items', [])
            if not items:
                break

            for item in items:
                for match in item.get('text_matches', []):
                    line_content = match.get('fragment', '')
                    words = line_content.replace(':', ' ').replace('=', ' ').split()
                    for word in words:
                        cleaned_word = word.strip('\'",;()[]{}<>`').rstrip('.')
                        if cleaned_word.startswith(BASE_SEARCH_PREFIX) and len(cleaned_word) >= 39:
                            if cleaned_word not in existing_keys and cleaned_word not in found_keys:
                                repo_name = item.get('repository', {}).get('full_name', '未知')
                                print(f"  [+] 发现新Key: {cleaned_word} (来自: {repo_name})")
                                found_keys.add(cleaned_word)

            if 'next' in response.links:
                params['page'] += 1
                time.sleep(random.uniform(3, 6)) # 增加翻页间隔
            else:
                break
                
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 422: # 查询无法处理，正常情况
            pass
        else:
            print(f"HTTP请求错误: {e}")
            time.sleep(60)
    except requests.exceptions.RequestException as e:
        print(f"网络请求错误: {e}")
        time.sleep(60)
            
    return found_keys


def generate_search_queries():
    """
    生成一系列精细化的搜索查询来绕过1000个结果的限制。
    策略：按年份 + 附加字符
    """
    queries = []
    
    # 策略1: 按年份搜索
    # 从今年到2015年
    current_year = datetime.now().year
    for year in range(current_year, 2014, -1):
        # 完整的年份
        queries.append(f'"{BASE_SEARCH_PREFIX}" created:{year}-01-01..{year}-12-31')
        # 年份内的每个月
        for month in range(1, 13):
            start_date = f"{year}-{month:02d}-01"
            end_date_dt = (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            end_date = end_date_dt.strftime("%Y-%m-%d")
            queries.append(f'"{BASE_SEARCH_PREFIX}" created:{start_date}..{end_date}')

    # 策略2: 增加后续字符进行细分 (这是最有效的方法)
    # 包含字母、数字、下划线、中划线
    characters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_'
    for char1 in characters:
        queries.append(f'"{BASE_SEARCH_PREFIX}{char1}"')
        # 如果需要更精细的搜索，可以开启第二层循环
        # for char2 in characters:
        #     queries.append(f'"{BASE_SEARCH_PREFIX}{char1}{char2}"')

    print(f"🎉 已生成 {len(queries)} 个精细化搜索查询。")
    return queries


def main():
    """主函数，负责整个流程的调度。"""
    
    # 1. 读取已有记录
    all_found_keys = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                clean_key = line.split('|')[0].strip()
                if clean_key:
                    all_found_keys.add(clean_key)
        print(f"已从 {OUTPUT_FILE} 加载并清洗了 {len(all_found_keys)} 条已有记录。")

    # 2. 生成所有要执行的搜索查询
    queries_to_run = generate_search_queries()
    
    # 3. 遍历执行所有查询
    total_new_keys = 0
    for query in queries_to_run:
        newly_found = search_github(query, all_found_keys)
        if newly_found:
            count = len(newly_found)
            total_new_keys += count
            all_found_keys.update(newly_found)
            
            # 每次发现新key后立即写入文件，防止中途中断丢失数据
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                for key in sorted(list(all_found_keys)):
                    f.write(f"{key}\n")
            print(f"✅ 查询 '{query}' 结束，发现 {count} 个新Key。已更新 {OUTPUT_FILE}。")
        else:
            print(f"✅ 查询 '{query}' 结束，无新发现。")
    
    print("\n" + "="*40)
    print("✨ 全部搜索任务完成！")
    print(f"本次运行共发现 {total_new_keys} 个新Key。")
    print(f"文件中总计 {len(all_found_keys)} 条不重复记录。")
    print("="*40)


if __name__ == '__main__':
    main()
