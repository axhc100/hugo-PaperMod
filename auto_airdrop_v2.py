import os
import feedparser
from google import genai # 使用最新的 google-genai 库
from datetime import datetime
import time

# --- 配置区 ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RSS_URLS = [
    "https://www.theblock.co/rss.xml",
    "https://cryptopanic.com/news/rss/",
    "https://blockchain.news/rss"
]
OUTPUT_DIR = "./content/posts"

# 初始化最新版 Client
client = genai.Client(api_key=GEMINI_API_KEY)

def get_latest_news():
    print("正在扫描 Web3 融资资讯源...")
    all_entries = []
    for url in RSS_URLS:
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                print(f"✅ 成功从源获取数据: {url[:30]}...")
                for entry in feed.entries[:2]:
                    title = entry.get('title', '无标题')
                    summary = entry.get('summary', entry.get('description', '点击查看详情'))
                    all_entries.append({'title': title, 'summary': summary})
        except Exception as e:
            print(f"❌ 抓取源失败 {url}: {e}")
    return all_entries

def generate_article_with_gemini(news_title, news_content):
    prompt = f"""
    你是一个 Web3 领域的 Alpha 猎人。请根据以下新闻内容，为我的 Hugo 博客撰写一篇高质量的交互指南。
    新闻标题: {news_title}
    新闻摘要: {news_content}
    要求：必须包含 YAML 头部，包含 title, date, tags, categories, tier(T0/T1/T2), status 字段。
    正文需包含项目简介、融资详情、交互建议、风险提示。
    仅输出 Markdown 内容，不要任何解释文字。
    """
    
    print(f"🚀 正在召唤 Gemini 2.5 Flash 处理: [{news_title[:15]}...]")
    # 按照你截图中的最新语法调用
    response = client.models.generate_content(
        model='gemini-2.5-flash', 
        contents=prompt
    )
    return response.text

def save_to_hugo(content, title):
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    safe_title = "".join(x for x in title if x.isalnum() or x==' ')[:30].strip().replace(' ', '-')
    filename = f"{datetime.now().strftime('%Y%m%d')}-{safe_title}.md"
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✨ 文章已生成: {filepath}")

def main():
    if not GEMINI_API_KEY:
        print("❌ 错误: 未找到 GEMINI_API_KEY 环境变量")
        return

    news_list = get_latest_news()
    for news in news_list:
        try:
            article = generate_article_with_gemini(news['title'], news['summary'])
            save_to_hugo(article, news['title'])
            time.sleep(1) # Gemini 2.5 响应极快
        except Exception as e:
            print(f"❌ Gemini 2.5 调用失败: {e}")

if __name__ == "__main__":
    main()
