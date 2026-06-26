import numpy as np
import os, requests, uuid, nltk, random
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from urllib.parse import urlparse, unquote
from google import genai
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from nltk.tokenize import sent_tokenize
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from sklearn.feature_extraction.text import TfidfVectorizer
from moviepy.editor import VideoFileClip

from apps.topics.models import Topic, TopicTranscription
from external.sonix.service import sonix_client, SonixAPIError

try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt")
try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab")

ext_mapping = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/webp": "webp",
    "image/gif": "gif",
    "image/svg+xml": "svg",
}

ua = UserAgent()
client = genai.Client()
SUMMARIZATION_PROMPT = """
You are an expert content summarizer.

Task:
Summarize the article below in a highly engaging way that encourages the reader to read the full article.

Strict Requirements:
1. The summary MUST NOT exceed {character_limit} characters (hard limit, including spaces).
2. If needed, prioritize clarity and key insights over completeness to stay within the limit.
3. The summary MUST be concise, compelling, and curiosity-driven.
4. Highlight the most important ideas, unique insights, or surprising elements.
5. End with a subtle hook or intrigue that motivates further reading.
6. Avoid repetition, filler, and generic phrases.

Output Rules:
- Output ONLY the summary.
- Do NOT explain anything.
- Do NOT exceed the character limit under any condition.

Article:
{text}
"""
SUMMARIZATION_PROMPT_TEMPLATE = PromptTemplate(
    input_variables=["text", "charater_limit"],
    template=SUMMARIZATION_PROMPT,
)

TITLE_REFINEMENT_PROMPT = """
You are an expert medical content editor and headline writer.

Task:
Rewrite the topic title below into a single, more engaging, catchy and click-worthy version
suitable for a medical/health education feed.

Strict Requirements:
1. The refined title MUST NOT exceed {character_limit} characters (hard limit, including spaces).
2. Keep the original medical meaning and factual accuracy. Do NOT invent facts or add clickbait that misleads.
3. Make it concise, compelling and curiosity-driven so a reader wants to open it.
4. Use Title Case. Do NOT wrap the result in quotes.
5. Do NOT use emojis or hashtags.

Output Rules:
- Output ONLY the refined title on a single line.
- Do NOT explain anything.
- Do NOT exceed the character limit under any condition.

Original title:
{title}
"""

DEBUG_MODE = False


class TopicImageService:
    @staticmethod
    def download_images_to_temp(image_urls: list[str]) -> list[str]:
        results = []
        for image_url in image_urls:
            if not image_url: continue
            if image_url.startswith("//"): image_url = "https:" + image_url
            try:
                resp = requests.get(image_url, timeout=20, headers={"User-Agent": ua.random})
                resp.raise_for_status()
                content_type = resp.headers.get("Content-Type", "").lower()
                ext = ext_mapping.get(content_type, "jpg")
                key = f"temp/topics/{uuid.uuid4()}.{ext}"
                file_path = default_storage.save(key, ContentFile(resp.content))
                results.append(file_path)
            except Exception as e:
                print(f"Image download failed: {image_url} -> {e}")
        return results
    
    @staticmethod
    def extract_image_path(image_url: str) -> str:
        if not image_url:
            raise ValueError("URL cannot be empty")
        # Remove leading slash
        path = urlparse(image_url).path.lstrip("/")
        # Decode URL-encoded characters (%20 etc.)
        key = unquote(path)
        return key
        
    
    @staticmethod
    def get_image_bytes(image_url: str) -> tuple[bytes, str]:
        """Return (content, content_type) for an image so the admin UI can edit it
        without hitting CORS. Our own bucket/CDN serves topic images without
        CORS headers, so the browser can display them but cannot read their pixels
        for cropping. Reading them server-side and re-serving them same-origin
        sidesteps that entirely.

        Prefers our own storage (no extra network hop); falls back to a plain
        server-side fetch for genuinely remote URLs (e.g. not-yet-promoted
        extracted images on another host).
        """
        if not image_url:
            raise ValueError("URL cannot be empty")
        if image_url.startswith("//"):
            image_url = "https:" + image_url

        key = TopicImageService.extract_image_path(image_url)
        if default_storage.exists(key):
            with default_storage.open(key, "rb") as f:
                content = f.read()
            ext = os.path.splitext(key)[1].lstrip(".").lower()
            content_type = next(
                (ct for ct, e in ext_mapping.items() if e == ext), "image/jpeg"
            )
            return content, content_type

        resp = requests.get(image_url, timeout=20, headers={"User-Agent": ua.random})
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
        if not content_type.startswith("image/"):
            raise ValueError("URL did not return an image")
        return resp.content, content_type

    @staticmethod
    def promote_image_to_topic(image_url: str) -> str:
        image_key = TopicImageService.extract_image_path(image_url)
        print(f"Promoting image from temp: {image_key}")
        if not default_storage.exists(image_key):
            raise FileNotFoundError(f"Temp image not found: {image_key}")
        file_name = os.path.basename(image_key)
        new_key = f"topics/images/{file_name}"
        with default_storage.open(image_key, "rb") as f:
            content = f.read()
            default_storage.save(new_key, ContentFile(content))
        default_storage.delete(image_key)
        return new_key

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

def summarizer(text: str, charater_limit: int = 500) -> str:
    prompt = SUMMARIZATION_PROMPT.format(text=text, charater_limit=charater_limit)
    response = client.models.generate_content(
        model="gemini-2.5-flash", contents=prompt
    )
    return response.text.strip()

def refine_title(title: str, character_limit: int = 150) -> str:
    """Use OpenAI to rewrite a topic title into a more engaging, catchy version.

    Keeps the medical meaning intact and respects the character limit. Falls back
    to the original title if the model returns nothing usable.
    """
    cleaned = (title or "").strip()
    if not cleaned:
        raise ValueError("Title cannot be empty")

    prompt = TITLE_REFINEMENT_PROMPT.format(title=cleaned, character_limit=character_limit)
    openai_llm = ChatOpenAI(
        model="gpt-4.1-mini-2025-04-14",
        api_key=os.environ.get("OPENAI_API_KEY"),
        temperature=0.6, max_tokens=256,
        max_retries=2, timeout=120,
    )
    refined = (openai_llm.invoke(prompt).content or "").strip().strip('"').strip()

    if not refined:
        return cleaned
    # Enforce the hard character limit defensively in case the model overshoots.
    if len(refined) > character_limit:
        refined = refined[:character_limit].rstrip()
    return refined

def summarize_tfidf(text: str, character_limit: int = 500) -> str:
    if not text or character_limit <= 0:
        return ""

    sentences = sent_tokenize(text)

    # Edge case: if text is already short enough
    if len(text) <= character_limit:
        return text

    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf = vectorizer.fit_transform(sentences)

    # Score sentences by TF-IDF weight
    scores = tfidf.sum(axis=1).A1
    ranked_indices = np.argsort(scores)[::-1]

    selected_sentences = []
    current_length = 0

    for idx in ranked_indices:
        sentence = sentences[idx]
        sentence_length = len(sentence) + 1  # +1 for space when joined

        if current_length + sentence_length > character_limit:
            continue

        selected_sentences.append((idx, sentence))
        current_length += sentence_length

        if current_length >= character_limit:
            break

    # Restore original order for readability
    selected_sentences.sort(key=lambda x: x[0])
    summary = " ".join(sentence for _, sentence in selected_sentences)
    return summary.strip()

def summarize_openai(text, character_limit=500):
    prompt = SUMMARIZATION_PROMPT_TEMPLATE.format(
        text=text, character_limit=character_limit
    )
    openai_llm = ChatOpenAI(
        model="gpt-4.1-mini-2025-04-14",
        api_key=os.environ.get("OPENAI_API_KEY"),  
        temperature=0.1, max_tokens=2048,
        max_retries=2, timeout=600
    )
    response = openai_llm.invoke(prompt).content
    return response.strip()

def inshort_generator(url: str) -> str:
    article_text, article_title, image_links = process_article(url)
    temp_image_urls = TopicImageService.download_images_to_temp(image_links)
    try:
        summary = summarize_openai(article_text)
    except Exception as e:
        print(e)
        summary = summarize_tfidf(article_text)
    return summary, article_title, temp_image_urls



# ---------------------------------------------------------------------
# Internal helpers for DEBUG dummy behavior
# ---------------------------------------------------------------------

def _dummy_sonix_create(topic: Topic):
    """Simulate Sonix transcription creation"""
    fake_id = f"debug-{uuid.uuid4()}"
    return {
        "id": fake_id,
        "status": "processing"
    }

def _dummy_sonix_status(sonix_media_id: str):
    """Simulate Sonix status progression"""
    # Randomly move to completed to simulate async processing
    status = random.choice(["processing", "completed"])
    return {"status": status}

def _dummy_sonix_transcript(sonix_media_id: str):
    """Return a fixed dummy transcript"""
    transcript_text = (
        "This is a dummy transcript generated in DEBUG mode. "
        "It simulates the transcription of a topic video without calling Sonix API. "
        "The purpose is to allow frontend and backend integration testing."
    )

    transcript_srt = """1
00:00:00,000 --> 00:00:04,000
This is a dummy transcript generated in DEBUG mode.
"""

    transcript_json = {
        "media_id": sonix_media_id,
        "segments": [
            {"start": 0.0, "end": 4.0, "text": "This is a dummy transcript generated in DEBUG mode."}
        ]
    }

    return transcript_text, transcript_srt, transcript_json




# ============================================
# Video Transcription Services
# ============================================

def start_transcription(topic_id: str) -> dict:
    topic = Topic.objects.get(id=topic_id)
    video_url = topic.video
    
    if not video_url:
        raise ValueError("Topic does not have a video URL")
    
    # Check if transcription already exists
    if hasattr(topic, 'transcription'):
        raise ValueError("Transcription already exists for this topic")
    
    try:
        # --- DEBUG MODE: Dummy Sonix call ---
        if DEBUG_MODE:
            result = _dummy_sonix_create(topic)
            
        else:
            print(video_url)
            # result = None
            result = sonix_client.create_transcription_from_url(
                media_url=video_url,
                language="en",
                name=topic.title
            )
        
        # Create transcription record
        transcription = TopicTranscription.objects.create(
            topic=topic,
            sonix_media_id=result['id'],
            status=result['status']
        )
        
        return {
            'success': True,
            'transcription_id': str(transcription.id),
            'sonix_media_id': result['id'],
            'status': result['status']
        }
        
    except SonixAPIError as e:
        raise Exception(f"Sonix API error: {str(e)}")
    except Exception as e:
        raise Exception(f"Failed to start transcription: {str(e)}")

def check_transcription_status(topic_id: str) -> dict:
    topic = Topic.objects.get(id=topic_id)
    
    if not hasattr(topic, 'transcription'):
        raise ValueError("No transcription exists for this topic")
    
    transcription = topic.transcription
    
    try:
        # Get status from Sonix
        if DEBUG_MODE:
            status_data = _dummy_sonix_status(transcription.sonix_media_id)
        else:
            # status_data = None
            status_data = sonix_client.get_media_status(transcription.sonix_media_id)
            
        # Update local record
        transcription.status = status_data['status']
        transcription.save()
        
        # If completed, trigger transcript retrieval
        if status_data['status'] == 'completed':
            retrieve_and_summarize_transcript(topic_id)
        
        return {
            'success': True,
            'status': status_data['status'],
            'transcription_id': str(transcription.id)
        }
        
    except SonixAPIError as e:
        transcription.status = 'failed'
        transcription.error_message = str(e)
        transcription.save()
        raise Exception(f"Sonix API error: {str(e)}")

def retrieve_and_summarize_transcript(topic_id: str) -> dict:
    topic = Topic.objects.get(id=topic_id)
    
    if not hasattr(topic, 'transcription'):
        raise ValueError("No transcription exists for this topic")
    
    transcription = topic.transcription
    
    if transcription.status != 'completed':
        raise ValueError("Transcription is not completed yet")
    
    try:
        # --- DEBUG MODE: Dummy transcript ---
        if DEBUG_MODE:
            transcript_text, transcript_srt, transcript_json = _dummy_sonix_transcript(transcription.sonix_media_id)
        else:
            # transcript_text, transcript_srt, transcript_json = None, None, None
            transcript_text = sonix_client.get_transcript_text(transcription.sonix_media_id)
            transcript_srt = sonix_client.get_transcript_srt(transcription.sonix_media_id)
            transcript_json = sonix_client.get_transcript_json(transcription.sonix_media_id)
        
        # Generate AI summary from transcript text
        if DEBUG_MODE:
            summary = summarize_tfidf(transcript_text)
        else:
            summary = summarize_openai(transcript_text)
        
        # Update transcription record
        transcription.status = 'completed'
        transcription.transcript_text = transcript_text
        transcription.transcript_srt = transcript_srt
        transcription.transcript_json = transcript_json
        transcription.summary_text = summary
        transcription.save()
        
        return {
            'success': True,
            'summary': summary,
            'transcript_length': len(transcript_text)
        }
        
    except SonixAPIError as e:
        transcription.status = 'failed'
        transcription.error_message = str(e)
        transcription.save()
        raise Exception(f"Failed to retrieve transcript: {str(e)}")

def get_transcription_data(topic_id: str) -> dict:
    """
    Returns the transcription data for a topic.
    """
    from apps.topics.models import Topic
    
    topic = Topic.objects.get(id=topic_id)
    
    if not hasattr(topic, 'transcription'):
        return None
    
    transcription = topic.transcription
    
    return {
        'id': str(transcription.id),
        'status': transcription.status,
        'sonix_media_id': transcription.sonix_media_id,
        'transcript_text': transcription.transcript_text,
        'transcript_srt': transcription.transcript_srt,
        'summary_text': transcription.summary_text,
        'error_message': transcription.error_message,
        'created_at': transcription.created_at,
        'updated_at': transcription.updated_at,
    }

def generate_thumbnail_moviepy(video_path, output_image_path, time_in_seconds=1.0):
    try:
        clip = VideoFileClip(video_path)
        duration = clip.duration
        clip.save_frame(output_image_path, t=time_in_seconds) 
        clip.close()
        return duration
    except Exception as e:
        print(f"An error occurred: {e}")

