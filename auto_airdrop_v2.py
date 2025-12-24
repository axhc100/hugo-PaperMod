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

# 2025年最推荐的 Flash 模型
MODEL_ID = 'gemini-2.0-flash' 

client = genai.Client(api_key=GEMINI_API_KEY)

def clean_html(raw_html):
    return re.sub(re.compile('<.*?>'), '', raw_html)

def get_safe_filename(title):
    safe_name = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '-')[:50]
    return f"{datetime.now().strftime('%Y%m%d')}-{safe_name}.md"

def get_latest_news():
    print("🔎 正在扫描 Web3 资讯源...")
    all_entries = []
    for url in RSS_URLS:
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                # 每个源只取 1 条，总量控制在 3 条以内
                entry = feed.entries[0]
                title = entry.get('title', '无标题')
                summary = clean_html(entry.get('summary', entry.get('description', '')))
                
                filename = get_safe_filename(title)
                if os.path.exists(os.path.join(OUTPUT_DIR, filename)):
                    print(f"⏭️  跳过已存在: {title[:15]}...")
                    continue
                
                all_entries.append({'title': title, 'summary': summary})
        except Exception as e:
            print(f"❌ 抓取源失败: {e}")
    return all_entries

def generate_article(news_title, news_content):
    prompt = f"""
    你是一个 Web3 研究员。请根据以下内容写一篇 Hugo 博客文章。
    要求：包含 YAML Frontmatter，内容涵盖项目介绍、融资详情、交互建议。
    新闻标题: {news_title}
    摘要内容: {news_content}
    注意：仅输出 Markdown 格式，不要包裹 ``` 代码块。
    """
    
    print(f"🚀 Gemini 2.0 Flash 正在处理: [{news_title[:15]}...]")
    
    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt
        )
        # 提取文本并清理
        text = response.text.strip()
        text = re.sub(r'^```markdown\n|^```\n|```$', '', text, flags=re.MULTILINE)
        return text
    except Exception as e:
        print(f"❌ API 调用出错: {e}")
        return None

def main():
    if not GEMINI_API_KEY:
        print("❌ 错误: 未设置 GEMINI_API_KEY")
        return

    news_list = get_latest_news()
    if not news_list:
        print("📭 暂无新资讯。")
        return

    success_count = 0
    for news in news_list:
        if success_count >= 3: # 严格限制单次运行产出，防止被封 Key
            break

        article_md = generate_article(news['title'], news['summary'])
        
        if article_md and article_md.startswith("---"):
            filename = get_safe_filename(news['title'])
            filepath = os.path.join(OUTPUT_DIR, filename)
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(article_md)
            print(f"✅ 成功生成: {filename}")
            success_count += 1
            
            # 关键：免费版必须等待，否则必报 429 错误
            print("⏳ 强制等待 60 秒 (避开 API 频率限制)...")
            time.sleep(60) 
        else:
            print("⚠️ 内容生成失败或格式错误，跳过。")
            time.sleep(10) # 失败也等一下

if __name__ == "__main__":
    main()
