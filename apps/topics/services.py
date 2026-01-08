import requests, dotenv, uuid
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from google import genai
ua = UserAgent()
client = genai.Client()

SUMMARIZATION_PROMPT = """
Summarize the following article in approximately {word_limit} words.
Focus on key ideas, arguments, and conclusions.
Avoid repetition and filler.

Article:
{text}
"""

def get_html_from_url(url: str) -> str:
    resp = requests.get(
        url, timeout=30,
        headers={"User-Agent": ua.random},
    )
    resp.raise_for_status()
    return resp.text

def extract_article_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    return text

def process_article(url: str):
    article_html = get_html_from_url(url)
    soup = BeautifulSoup(article_html, "html.parser")
    article_text = soup.get_text(separator=" ", strip=True)
    all_image_links = [img.get("src") for img in soup.find_all("img")]
    return article_text, all_image_links

def download_images(image_links: list[str]):
    image_paths = []
    for i, link in enumerate(image_links):
        try:
            response = requests.get(link)
            image_path = f"media/temp/image_{uuid.uuid4()}.jpg"
            with open(image_path, "wb") as f:
                f.write(response.content)
            image_paths.append(image_path)
        except Exception as e:
            print(f"Error downloading image {link}: {e}")
    return image_paths

def summarizer(text: str, word_limit: int = 300) -> str:
    prompt = SUMMARIZATION_PROMPT.format(text=text, word_limit=word_limit)
    response = client.models.generate_content(
        model="gemini-2.5-flash", contents=prompt
    )
    return response.text.strip()

def inshort_generator(url: str) -> str:
    article_text, image_links = process_article(url)
    image_paths = download_images(image_links)
    summary = summarizer(article_text)
    return summary, image_paths

