import os
import requests
import time
import random
from datetime import datetime, timedelta
from tqdm import tqdm # ✨ 引入tqdm库，用于显示总体进度

# --- 配置区 (保持不变) ---
GITHUB_TOKEN = os.getenv('GH_PAT')
if not GITHUB_TOKEN:
    raise ValueError("未找到 GitHub PAT。请设置 'GH_PAT' 环境变量。")

BASE_SEARCH_PREFIX = 'AIzaSy'
OUTPUT_FILE = "api.txt"
HEADERS = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3.text-match+json'
}

# --- 功能函数 (check_rate_limit, search_github, generate_search_queries 均保持不变) ---
def check_rate_limit():
    """检查GitHub API的速率限制，如果接近限制则暂停等待。"""
    try:
        response = requests.get('https://api.github.com/rate_limit', headers=HEADERS)
        response.raise_for_status()
        rate_info = response.json().get('resources', {}).get('search', {})
        remaining = rate_info.get('remaining', 0)
        reset_time = rate_info.get('reset', 0)
        
        # 减少不必要的打印，只在接近限制时提示
        if remaining < 10:
            print(f"API速率限制: 剩余 {remaining} 次请求。重置时间: {datetime.fromtimestamp(reset_time).strftime('%Y-%m-%d %H:%M:%S')}")
        
        if remaining < 5:
            sleep_time = max(0, reset_time - time.time()) + 5
            print(f"速率限制过低，程序将暂停 {sleep_time:.2f} 秒。")
            time.sleep(sleep_time)
            
    except requests.exceptions.RequestException as e:
        print(f"检查速率限制时出错: {e}")
        time.sleep(60)

def search_github(query, existing_keys):
    """
    根据单个精确的查询在 GitHub 上搜索代码。
    返回一个包含新发现的Key的集合。
    """
    found_keys = set()
    base_url = 'https://api.github.com/search/code'
    params = {'q': query, 'per_page': 100, 'page': 1}
    
    # print(f"🚀 开始搜索: '{query}'") # 在主循环中打印，减少冗余信息
    
    try:
        while True:
            check_rate_limit()
            response = requests.get(base_url, headers=HEADERS, params=params)
            
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
                time.sleep(random.uniform(3, 6))
            else:
                break
                
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 422:
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
    """
    queries = []
    current_year = datetime.now().year
    for year in range(current_year, 2014, -1):
        for month in range(1, 13):
            start_date = f"{year}-{month:02d}-01"
            end_date_dt = (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            end_date = end_date_dt.strftime("%Y-%m-%d")
            queries.append(f'"{BASE_SEARCH_PREFIX}" created:{start_date}..{end_date}')

    characters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_'
    for char1 in characters:
        queries.append(f'"{BASE_SEARCH_PREFIX}{char1}"')
    
    print(f"🎉 已生成 {len(queries)} 个精细化搜索查询。")
    return queries


# --- ✨ 主函数 (核心修改区) ---
def main():
    """主函数，负责整个流程的调度。"""
    
    # 步骤 1: 读取所有已存在的key到内存中的集合，用于去重检查
    all_found_keys = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            # 兼容旧的文件格式，即使有'|'也能正确读取
            all_found_keys = {line.split('|')[0].strip() for line in f if line.strip()}
        print(f"✅ 已从 {OUTPUT_FILE} 加载 {len(all_found_keys)} 条已有记录。")
    else:
        print(f"📋 未找到 {OUTPUT_FILE}，将创建一个新文件。")

    # 步骤 2: 生成所有要执行的搜索查询
    queries_to_run = generate_search_queries()
    
    # 步骤 3: 遍历执行所有查询，并使用tqdm显示总体进度
    total_new_keys_this_run = 0
    
    # 使用tqdm来包装查询列表，提供一个美观且信息丰富的进度条
    for query in tqdm(queries_to_run, desc="🔍 总体搜索进度"):
        
        # 在进度条上显示当前正在执行的查询
        tqdm.write(f"🚀 开始搜索: '{query}'")
        
        # 传入内存中所有的key，避免重复搜索和记录
        newly_found_set = search_github(query, all_found_keys)
        
        if newly_found_set:
            count = len(newly_found_set)
            total_new_keys_this_run += count
            
            # ✨ 核心修改点: 使用 'a' (append) 模式来追加新内容 ✨
            # 这样既不会覆盖旧数据，也能保证程序中断时数据不丢失。
            with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
                for key in newly_found_set:
                    f.write(f"{key}\n")
            
            # 更新内存中的集合，确保后续的查询不会把刚找到的key当作新的
            all_found_keys.update(newly_found_set)
            
            tqdm.write(f"  [✅] 查询结束，发现 {count} 个新Key。已追加到 {OUTPUT_FILE}。")
        else:
            # 如果没有新发现，静默处理或只在进度条上更新，避免刷屏
            pass
            
    print("\n" + "="*50)
    print("✨ 全部搜索任务完成！")
    print(f"本次运行共发现 {total_new_keys_this_run} 个新Key。")
    print(f"文件中总计 {len(all_found_keys)} 条不重复记录。")
    print("="*50)


if __name__ == '__main__':
    # 建议在使用tqdm时，如果可能，安装colorama库以获得更好的显示效果
    # pip install colorama
    main()
