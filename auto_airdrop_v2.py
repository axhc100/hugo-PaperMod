import os
import feedparser
import google.generativeai as genai  # 切换回更稳定的旧版库名，但功能一样
from datetime import datetime
import time
import re

# --- 配置区 ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RSS_URLS = [
    "https://www.theblock.co/rss.xml",
    "https://cryptopanic.com/news/rss/",
    "https://blockchain.news/rss"
]
OUTPUT_DIR = "./content/posts"

# 初始化 Gemini (使用最稳定的配置)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def get_latest_news():
    print("正在扫描 Web3 融资资讯源...")
    all_entries = []
    for url in RSS_URLS:
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                print(f"✅ 成功从源获取到数据: {url[:30]}...")
                for entry in feed.entries[:2]:
                    # 安全获取标题和摘要
                    title = entry.get('title', '无标题')
                    # 修复关键：兼容不同 RSS 的摘要字段
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

    要求：
    1. 必须包含 YAML 头部，包含 title, date, tags, categories, tier(T0/T1/T2), status 字段。
    2. 文章正文需包含项目简介、融资详情、交互建议、风险提示。
    3. 仅输出 Markdown 内容，不要任何解释。
    """
    
    print(f"🚀 正在为 [{news_title[:15]}...] 召唤 Gemini 生成文章...")
    # 修复关键：使用更稳健的调用方式
    response = model.generate_content(prompt)
    return response.text

def save_to_hugo(content, title):
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    # 处理文件名
    safe_title = "".join(x for x in title if x.isalnum() or x==' ')[:30].replace(' ', '-')
    filename = f"{datetime.now().strftime('%Y%m%d')}-{safe_title}.md"
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✨ 已生成文件: {filepath}")

def main():
    if not GEMINI_API_KEY:
        print("❌ 错误: 未找到 GEMINI_API_KEY 环境变量")
        return

    news_list = get_latest_news()
    for news in news_list:
        try:
            # 修复关键：使用字典取值
            article = generate_article_with_gemini(news['title'], news['summary'])
            save_to_hugo(article, news['title'])
            time.sleep(2)
        except Exception as e:
            print(f"❌ Gemini 生成失败: {e}")

if __name__ == "__main__":
    main()
