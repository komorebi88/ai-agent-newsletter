import requests
from bs4 import BeautifulSoup
import feedparser
import openai
from datetime import datetime
from typing import List, Dict
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

class AIAgentNewsletterGenerator:
    def __init__(self, openai_api_key: str):
        self.client = openai.Client(api_key=openai_api_key)
        self.agent_keywords = [
            "AI agent", "AIエージェント", "autonomous agent", "自律エージェント",
            "LLM agent", "AI assistant", "AI workflow",
            "AutoGPT", "AgentGPT", "BabyAGI", "agent GPT",
            "AI automation", "AI bot", "intelligent agent"
        ]
    
    def _is_agent_related(self, text: str) -> bool:
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in self.agent_keywords)

    def fetch_news(self) -> List[Dict]:
        news_items = []
        
        # HackerNews APIからの取得
        try:
            hn_top = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json")
            story_ids = hn_top.json()[:30]
            
            for story_id in story_ids:
                story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                story = requests.get(story_url).json()
                if story.get('title') and self._is_agent_related(story.get('title', '')):
                    news_items.append({
                        'title': story['title'],
                        'url': story.get('url', f"https://news.ycombinator.com/item?id={story_id}"),
                        'source': 'Hacker News',
                        'date': datetime.now().strftime('%Y-%m-%d')
                    })
        except Exception as e:
            print(f"Error fetching from Hacker News: {str(e)}")

        # Reddit JSON APIからの取得
        subreddits = ['artificial', 'MachineLearning', 'technews']
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        for subreddit in subreddits:
            try:
                response = requests.get(
                    f"https://www.reddit.com/r/{subreddit}/search.json?q=AI%20agent&restrict_sr=1&sort=new",
                    headers=headers
                )
                if response.status_code == 200:
                    posts = response.json()['data']['children']
                    for post in posts:
                        title = post['data']['title']
                        if self._is_agent_related(title):
                            news_items.append({
                                'title': title,
                                'url': f"https://reddit.com{post['data']['permalink']}",
                                'source': f'Reddit r/{subreddit}',
                                'date': datetime.now().strftime('%Y-%m-%d')
                            })
            except Exception as e:
                print(f"Error fetching from Reddit r/{subreddit}: {str(e)}")

        # DEV.to RSSフィードからの取得
        try:
            dev_feed = feedparser.parse('https://dev.to/feed/tag/ai')
            for entry in dev_feed.entries[:10]:
                if self._is_agent_related(entry.title) or self._is_agent_related(entry.summary):
                    news_items.append({
                        'title': entry.title,
                        'url': entry.link,
                        'source': 'DEV.to',
                        'date': datetime.now().strftime('%Y-%m-%d')
                    })
        except Exception as e:
            print(f"Error fetching from DEV.to: {str(e)}")

        return news_items

    def generate_newsletter(self, news_items: List[Dict]) -> str:
        if not news_items:
            return "本日のAIエージェント関連のニュースは見つかりませんでした。"

        prompt = f"""
以下のAIエージェント関連ニュースから、技術者向けのニュースレターを作成してください：

本日のニュース：
{[f"- {item['title']} (Source: {item['source']}, URL: {item['url']})" for item in news_items]}

要件：
1. 冒頭にAIエージェント分野の最新トレンドの要約（100字程度）
2. 重要なニュース3つを選んで技術的な観点から解説（各200字程度）
3. 実装や開発に関する具体的な示唆を含める
4. 各ニュースの参考URLを含める
"""

        response = self.client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "あなたはAIエージェント開発の専門家で、最新の技術トレンドを解説するテックライターです。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        return response.choices[0].message.content

class NewsletterAutomation:
    def __init__(self):
        self.gmail_address = os.getenv('GMAIL_ADDRESS')
        self.gmail_app_password = os.getenv('GMAIL_APP_PASSWORD')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.recipient_email = self.gmail_address
        
        # デバッグ用に環境変数の値を確認（パスワードは最初の4文字のみ表示）
        print(f"Gmail Address: {self.gmail_address}")
        print(f"App Password (first 4 chars): {self.gmail_app_password[:4] if self.gmail_app_password else 'None'}")
        print(f"OpenAI API Key (first 4 chars): {self.openai_api_key[:4] if self.openai_api_key else 'None'}")

    def send_email(self, subject: str, body: str):
        print(f"送信先メールアドレス: {self.recipient_email}")
        
        msg = MIMEMultipart()
        msg['From'] = self.gmail_address
        msg['To'] = self.recipient_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        try:
            print("SMTPサーバーに接続を開始します")
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            print("ログインを試みます")
            server.login(self.gmail_address, self.gmail_app_password)
            print("メール送信を試みます")
            server.send_message(msg)
            server.quit()
            print("メール送信完了")
        except Exception as e:
            print(f"メール送信エラーの詳細: {str(e)}")
            raise

    def run_daily_newsletter(self):
        try:
            print("ニュースレター生成を開始します")
            generator = AIAgentNewsletterGenerator(self.openai_api_key)
            print("ニュース記事の取得を開始します")
            news_items = generator.fetch_news()
            print(f"取得したニュース数: {len(news_items)}")
            newsletter = generator.generate_newsletter(news_items)

            today = datetime.now().strftime('%Y-%m-%d')
            subject = f"AI Agent ニュースレター - {today}"
            
            self.send_email(subject, newsletter)
            print(f"ニュースレター生成完了: {today}")

        except Exception as e:
            error_msg = f"ニュースレター生成エラー: {str(e)}"
            print(error_msg)
            self.send_email("AI Agent ニュースレター エラー通知", error_msg)

def main():
    print("プログラムを開始します")
    automation = NewsletterAutomation()
    automation.run_daily_newsletter()

if __name__ == "__main__":
    main()
