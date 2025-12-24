import os
import feedparser
import re
import time
from datetime import datetime
from google import genai

# --- 配置区 ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RSS_URLS = [
    "https://www.theblock.co/rss.xml",
    "https://cryptopanic.com/news/rss/",
    "https://blockchain.news/rss"
]
OUTPUT_DIR = "./content/posts"

# 模型选择：1.5-flash 免费额度最高且稳定。如果想试 2.5 可自行修改
MODEL_ID = 'gemini-1.5-flash' 

# 初始化 Client
client = genai.Client(api_key=GEMINI_API_KEY)

def clean_html(raw_html):
    """去除 RSS 中的 HTML 标签"""
    return re.sub(re.compile('<.*?>'), '', raw_html)

def get_safe_filename(title):
    """生成安全且唯一的文件名"""
    safe_name = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '-')[:50]
    return f"{datetime.now().strftime('%Y%m%d')}-{safe_name}.md"

def get_latest_news():
    print("🔎 正在扫描 Web3 资讯源...")
    all_entries = []
    for url in RSS_URLS:
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                # 每个源只取 1 条最新，避免超出免费额度
                entry = feed.entries[0]
                title = entry.get('title', '无标题')
                summary = clean_html(entry.get('summary', entry.get('description', '')))
                
                # 检查文件是否已存在，存在则跳过
                filename = get_safe_filename(title)
                if os.path.exists(os.path.join(OUTPUT_DIR, filename)):
                    print(f"⏭️  跳过已存在的文章: {title[:20]}")
                    continue
                    
                all_entries.append({'title': title, 'summary': summary})
        except Exception as e:
            print(f"❌ 抓取源失败 {url}: {e}")
    return all_entries

def generate_article(news_title, news_content):
    prompt = f"""
    你是一位资深的 Web3 Alpha 猎人。请根据以下内容撰写一篇 Hugo 博客文章。

    【新闻标题】: {news_title}
    【新闻摘要】: {news_content}

    【要求】:
    1. 必须包含 YAML Frontmatter (title, date, tags, categories, tier, status)。
    2. date 格式: {datetime.now().strftime('%Y-%m-%dT%H:%M:%S+08:00')}
    3. 内容包含：项目简介、融资详情、交互建议、风险提示。
    4. 仅输出 Markdown，不要包裹 ``` 标签，不要解释。
    """
    
    print(f"🚀 正在召唤 {MODEL_ID} 处理: [{news_title[:20]}...]")
    
    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt
        )
        content = response.text.strip()
        
        # 彻底清理可能存在的 Markdown 代码块标签
        content = re.sub(r'^```markdown\n', '', content)
        content = re.sub(r'^```\n', '', content)
        content = re.sub(r'```$', '', content)
        
        return content
    except Exception as e:
        if "429" in str(e):
            print("🛑 触发 API 频率限制 (429)，请稍后再试或检查配额。")
        else:
            print(f"❌ 调用失败: {e}")
        return None

def save_article(content, title):
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    filename = get_safe_filename(title)
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✨ 生成成功: {filepath}")

def main():
    if not GEMINI_API_KEY:
        print("🔑 错误: 未设置 GEMINI_API_KEY")
        return

    news_list = get_latest_news()
    if not news_list:
        print("📭 没有新资讯需要处理。")
        return

    # 计数器，限制单次任务处理总数
    processed_count = 0
    for news in news_list:
        if processed_count >= 3: # 每次运行最多处理 3 篇，保护 API
            print("✋ 已达到单次处理上限，停止。")
            break

        article_md = generate_article(news['title'], news['summary'])
        
        if article_md and article_md.startswith("---"):
            save_article(article_md, news['title'])
            processed_count += 1
            # 关键：每篇文章处理完强制等待 30 秒，防止 429 错误
            if processed_count < len(news_list):
                print("⏳ 等待 30 秒避开频率限制...")
                time.sleep(30)
        else:
            print(f"⚠️ 格式异常，跳过文章")

if __name__ == "__main__":
    main()
