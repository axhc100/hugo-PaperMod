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

# 模型 ID 设置
# 稳定生产建议用 'gemini-2.5-flash'
# 如果想尝试最新的，可改为 'gemini-3-flash-preview'
MODEL_ID = 'gemini-2.5-flash'

# 初始化 Client
client = genai.Client(api_key=GEMINI_API_KEY)

def clean_html(raw_html):
    """去除 RSS 摘要中的 HTML 标签，减少 Token 浪费"""
    return re.sub(re.compile('<.*?>'), '', raw_html)

def get_latest_news():
    print("🔎 正在扫描 Web3 融资及 Alpha 资讯...")
    all_entries = []
    for url in RSS_URLS:
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                for entry in feed.entries[:2]: # 每个源取最新的 2 条
                    title = entry.get('title', '无标题')
                    summary = clean_html(entry.get('summary', entry.get('description', '')))
                    all_entries.append({'title': title, 'summary': summary})
        except Exception as e:
            print(f"❌ 抓取源失败 {url}: {e}")
    return all_entries

def generate_article(news_title, news_content):
    """
    针对 Gemini 2.5 Flash 的 'Thinking' 特性优化提示词
    """
    prompt = f"""
    你是一位资深的 Web3 Alpha 猎人和 DeFi 研究员。请分析以下新闻并为 Hugo 博客撰写一篇深度交互指南。

    【新闻标题】: {news_title}
    【新闻摘要】: {news_content}

    【任务要求】:
    1. 输出内容必须以 YAML Frontmatter 开头，包含：
       title: (中文标题)
       date: {datetime.now().strftime('%Y-%m-%dT%H:%M:%S+08:00')}
       tags: [Web3, 融资, 交互]
       categories: [项目动态]
       tier: (T0-核心关注/T1-重点/T2-普通)
       status: "待交互"
    2. 正文结构：
       - ## 项目背景 (Gemini 请利用你的知识库简述该项目及其赛道意义)
       - ## 融资详情 (解析本轮金额、领投机构)
       - ## 交互策略 (这是重点：如果是融资消息，请给出撸空投或参与早期测试的具体建议)
       - ## 风险评估 (安全性、Gas成本等)
    3. 语言风格：专业、干练、具有煽动性。
    4. 纯净输出：仅返回 Markdown 内容，不要包裹 ```markdown 代码块，确保文件开头就是 ---。
    """
    
    print(f"🚀 Gemini 2.5 Flash 正在分析: [{news_title[:20]}...]")
    
    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt
        )
        content = response.text.strip()
        
        # 冗余清理：防止模型依然输出代码块标签
        content = re.sub(r'^```markdown\n', '', content)
        content = re.sub(r'^```\n', '', content)
        content = re.sub(r'\n```$', '', content)
        
        return content
    except Exception as e:
        print(f"❌ 调用 API 失败: {e}")
        return None

def save_article(content, title):
    if not content: return
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    # 文件名优化
    safe_name = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '-')[:50]
    filename = f"{datetime.now().strftime('%Y%m%d')}-{safe_name}.md"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ 生成成功: {filepath}")

def main():
    if not GEMINI_API_KEY:
        print("🔑 错误: 请先设置 GEMINI_API_KEY 环境变量")
        return

    news_list = get_latest_news()
    if not news_list:
        print("📭 暂无更新")
        return

    for news in news_list:
        article_md = generate_article(news['title'], news['summary'])
        if article_md and article_md.startswith("---"):
            save_article(article_md, news['title'])
        else:
            print(f"⚠️ 格式校验未通过，跳过文章")
        
        # Gemini 2.5 免费层级有 RPM 限制，建议保留小延迟
        time.sleep(2)

if __name__ == "__main__":
    main()
