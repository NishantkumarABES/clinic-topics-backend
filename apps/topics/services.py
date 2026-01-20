import requests, uuid, nltk
import numpy as np
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from google import genai
from nltk.tokenize import sent_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer

try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt")
try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
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


# ============================================
# Video Transcription Services
# ============================================

def start_transcription(topic_id: str) -> dict:
    """
    Initiates a transcription job for a topic's video URL using Sonix API.
    Creates a TopicTranscription record to track the process.
    """
    from apps.topics.models import Topic, TopicTranscription
    from external.sonix.service import sonix_client, SonixAPIError
    
    topic = Topic.objects.get(id=topic_id)
    
    if not topic.video_url:
        raise ValueError("Topic does not have a video URL")
    
    # Check if transcription already exists
    if hasattr(topic, 'transcription'):
        raise ValueError("Transcription already exists for this topic")
    
    try:
        # Create transcription job via Sonix
        result = sonix_client.create_transcription_from_url(
            media_url=topic.video_url,
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
    """
    Checks the current status of a transcription job from Sonix.
    Updates the local database record with the latest status.
    """
    from apps.topics.models import Topic, TopicTranscription
    from external.sonix.service import sonix_client, SonixAPIError
    
    topic = Topic.objects.get(id=topic_id)
    
    if not hasattr(topic, 'transcription'):
        raise ValueError("No transcription exists for this topic")
    
    transcription = topic.transcription
    
    try:
        # Get status from Sonix
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
    """
    Retrieves completed transcript from Sonix and generates AI summary.
    Stores both transcript and summary in the database.
    """
    from apps.topics.models import Topic, TopicTranscription
    from external.sonix.service import sonix_client, SonixAPIError
    
    topic = Topic.objects.get(id=topic_id)
    
    if not hasattr(topic, 'transcription'):
        raise ValueError("No transcription exists for this topic")
    
    transcription = topic.transcription
    
    if transcription.status != 'completed':
        raise ValueError("Transcription is not completed yet")
    
    try:
        # Fetch transcript in multiple formats
        transcript_text = sonix_client.get_transcript_text(transcription.sonix_media_id)
        transcript_srt = sonix_client.get_transcript_srt(transcription.sonix_media_id)
        transcript_json = sonix_client.get_transcript_json(transcription.sonix_media_id)
        
        # Generate AI summary from transcript text
        summary = summarizer(transcript_text, word_limit=300)
        
        # Update transcription record
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
