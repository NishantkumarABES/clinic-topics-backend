import requests, uuid, nltk
import numpy as np
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from google import genai
from nltk.tokenize import sent_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer

if not nltk.data.find("tokenizers/punkt"):
    nltk.download("punkt")
if not nltk.data.find("tokenizers/punkt_tab"):
    nltk.download("punkt_tab")


from external.cloudinary.utils import CloudinaryService
cloudinary = CloudinaryService()

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

def extract_article_title(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    title = soup.find("h1").text.strip()
    if title:
        return title
    return ""

def process_article(url: str):
    article_html = get_html_from_url(url)
    soup = BeautifulSoup(article_html, "html.parser")
    article_text = soup.get_text(separator=" ", strip=True)
    article_title = extract_article_title(article_html)
    all_image_links = [img.get("src") for img in soup.find_all("img")]
    return article_text, article_title, all_image_links

def download_images(image_links: list[str]) -> list[str]:
    uploaded_image_urls: list[str] = []

    for link in image_links:
        if not link: continue
        try:
            if link.startswith("//"):
                link = "https:" + link

            response = requests.get(
                link, timeout=15,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            response.raise_for_status()

            upload_result = cloudinary.upload_image(
                response.content,
                folder="media/topics/",
                public_id=f"article_{uuid.uuid4()}",
            )
            uploaded_image_urls.append(upload_result["secure_url"])

        except Exception as exc:
            pass

    return uploaded_image_urls

def summarizer(text: str, word_limit: int = 300) -> str:
    prompt = SUMMARIZATION_PROMPT.format(text=text, word_limit=word_limit)
    response = client.models.generate_content(
        model="gemini-2.5-flash", contents=prompt
    )
    return response.text.strip()

def summarize_tfidf(text, word_limit=300):
    sentences = sent_tokenize(text)
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf = vectorizer.fit_transform(sentences)

    scores = tfidf.sum(axis=1).A1
    ranked_sentences = np.argsort(scores)[::-1]
    summary = []
    count = 0
    for idx in ranked_sentences:
        words = sentences[idx].split()
        if count + len(words) > word_limit:
            continue
        summary.append(sentences[idx])
        count += len(words)

        if count >= word_limit:
            break
    return " ".join(summary)

def inshort_generator(url: str) -> str:
    article_text, article_title, image_links = process_article(url)
    image_paths = download_images(image_links)
    summary = summarize_tfidf(article_text)
    return summary, article_title, image_paths

