import os
import feedparser
import re
from google import genai 
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
# 建议检查模型名称，目前主流为 'gemini-2.0-flash' 或 'gemini-1.5-flash'
MODEL_ID = 'gemini-2.5-flash' 

client = genai.Client(api_key=GEMINI_API_KEY)

def clean_summary(raw_html):
    """去除 RSS 摘要中的 HTML 标签"""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', raw_html)

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
                    summary = clean_summary(entry.get('summary', entry.get('description', '')))
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
    2. date 格式必须为: {datetime.now().strftime('%Y-%m-%dT%H:%M:%S+08:00')}
    3. 正文需包含项目简介、融资详情、交互建议、风险提示。
    4. 仅输出 Markdown 原始内容，不要包含 ```markdown 这样的包裹代码块，也不要任何解释文字。
    """
    
    print(f"🚀 正在调用 {MODEL_ID} 处理: [{news_title[:15]}...]")
    
    response = client.models.generate_content(
        model=MODEL_ID, 
        contents=prompt
    )
    
    content = response.text
    
    # 核心优化：剥离可能存在的 Markdown 代码块包裹
    if content.startswith("```"):
        content = re.sub(r'^```[^\n]*\n', '', content) # 去掉开头的 ```markdown
        content = re.sub(r'\n```$', '', content)     # 去掉结尾的 ```
        
    return content.strip()

def save_to_hugo(content, title):
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    # 优化文件名生成：过滤非法字符并防止过长
    safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '-')
    filename = f"{datetime.now().strftime('%Y%m%d')}-{safe_title[:50]}.md"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✨ 文章已生成: {filepath}")

def main():
    if not GEMINI_API_KEY:
        print("❌ 错误: 未找到 GEMINI_API_KEY 环境变量")
        return

    news_list = get_latest_news()
    if not news_list:
        print("📭 没有发现新资讯")
        return

    for news in news_list:
        try:
            article = generate_article_with_gemini(news['title'], news['summary'])
            # 简单验证是否包含 Hugo 头部
            if article.startswith("---"):
                save_to_hugo(article, news['title'])
            else:
                print(f"⚠️ 生成内容格式不符(缺少 YAML 头部)，跳过: {news['title'][:15]}")
            
            # 免费版 API 建议增加延迟避免频率限制 (RPM)
            time.sleep(2) 
        except Exception as e:
            print(f"❌ Gemini 调用失败: {e}")

if __name__ == "__main__":
    main()
