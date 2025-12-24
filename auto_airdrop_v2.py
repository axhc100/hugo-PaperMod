import os
import feedparser
from google import genai  # 注意：这里需要安装 google-genai 库
from datetime import datetime
import time
import re

# --- 你刚才截图的内容 ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RSS_URLS = [
    "https://rsshub.app/foresightnews/column/7",
    "https://rsshub.app/odaily/news/33",
    "https://rsshub.app/theblockbeats/news"
]
OUTPUT_DIR = "./content/posts"

client = genai.Client(api_key=GEMINI_API_KEY)
# ... 后面接之前的函数定义 (get_latest_news, generate_article_with_gemini, save_to_hugo, main)

def get_latest_news():
    print("正在扫描 Web3 融资资讯源...")
    all_entries = []
    for url in RSS_URLS:
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                print(f"✅ 成功从 {url[:30]}... 获取到 {len(feed.entries)} 条资讯")
                all_entries.extend(feed.entries[:3])
        except Exception as e:
            print(f"❌ 抓取源失败: {url[:30]}...")
    return all_entries

def generate_article_with_gemini(news_title, news_content):
    prompt = f"""
    你是一个 Web3 领域的 Alpha 猎人。请根据以下新闻内容，为我的 Hugo 博客撰写一篇高质量的交互指南。
    新闻标题: {news_title}
    新闻摘要: {news_content}
    要求：必须包含 YAML 头部，包含 title, date, tags, categories, tier(T0/T1/T2), status 字段。
    正文需包含项目简介、融资详情、交互建议、风险提示。仅输出内容，不带解释。
    """
    
    print(f"🚀 正在为 [{news_title[:15]}...] 召唤 Gemini 生成文章...")
    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=prompt
    )
    return response.text

def save_to_hugo(content, title):
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    safe_title = "".join(x for x in title if x.isalnum())[:30]
    filename = f"{datetime.now().strftime('%Y%m%d')}-{safe_title}.md"
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✨ 已生成文件: {filepath}")

def main():
    news_list = get_latest_news()
    if not news_list:
        print("💡 依然没拿到消息？尝试以下测试步骤：")
        print("1. 检查电脑是否能打开 https://rsshub.app")
        print("2. 确认 RSS_URLS 里的链接在浏览器里能否看到文字内容")
        return

    for news in news_list:
        try:
            article = generate_article_with_gemini(news.title, news.summary)
            save_to_hugo(article, news.title)
            time.sleep(2)
        except Exception as e:
            print(f"❌ Gemini 生成失败: {e}")

if __name__ == "__main__":
    main()