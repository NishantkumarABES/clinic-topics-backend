import os, requests, time
from urllib.parse import urlparse


class SonixAPIError(Exception):
    pass

class SonixClient:
    BASE_URL = "https://api.sonix.ai/v1"

    def __init__(self, api_key: str, timeout: int = 15):
        self.api_key = api_key
        self.timeout = timeout
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    # -------------------------
    # Internal utilities
    # -------------------------

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        try:
            parsed = urlparse(url)
            return parsed.scheme in ("http", "https") and bool(parsed.netloc)
        except Exception:
            return False

    def _request(self, method: str, endpoint: str, **kwargs):
        """Internal unified request handler."""
        url = f"{self.BASE_URL}{endpoint}"
        try:
            response = requests.request(
                method,
                url,
                headers=self.headers,
                timeout=self.timeout,
                **kwargs
            )
        except requests.RequestException as e:
            raise SonixAPIError(f"Network error: {str(e)}")

        return response

    # -------------------------
    # Authentication
    # -------------------------

    def verify_api_key(self) -> bool:
        """Non-billable API key verification."""
        response = self._request("GET", "/users")

        if response.status_code == 200:
            print("✅ API key is valid.")
            return True

        elif response.status_code == 401:
            raise SonixAPIError("❌ Invalid API Key.")

        elif response.status_code == 403:
            raise SonixAPIError("❌ No API access — account not subscribed.")

        else:
            raise SonixAPIError(
                f"Unexpected verification error: {response.status_code} {response.text}"
            )

    # -------------------------
    # Media Submission
    # -------------------------

    def create_transcription_from_url(self, media_url: str, language="en", name=None) -> dict:
        """Creates a transcription job from a public media URL (billable)."""

        if not self._is_valid_url(media_url):
            raise ValueError("Provided media_url is not a valid http/https URL.")

        data = {
            "file_url": media_url,
            "language": language
        }

        if name:
            data["name"] = name

        print("Submitting transcription job to Sonix...")

        response = self._request("POST", "/media", data=data)

        if response.status_code in (200, 201):
            result = response.json()
            print("✅ Transcription job created successfully.")
            print("Media ID:", result["id"])
            print("Status:", result["status"])
            return result

        elif response.status_code == 400:
            raise SonixAPIError("Invalid request — check parameters carefully.")

        elif response.status_code == 402:
            raise SonixAPIError("Payment issue — billing problem on account.")

        else:
            raise SonixAPIError(
                f"Error creating transcription: {response.status_code} {response.text}"
            )

    # -------------------------
    # Media Status
    # -------------------------

    def get_media_status(self, media_id: str) -> dict:
        response = self._request("GET", f"/media/{media_id}")

        if response.status_code == 200:
            return response.json()

        elif response.status_code == 404:
            raise SonixAPIError("Media ID not found.")

        elif response.status_code == 401:
            raise SonixAPIError("Invalid API Key.")

        else:
            raise SonixAPIError(
                f"Status check failed: {response.status_code} {response.text}"
            )

    def wait_until_completed(self, media_id: str, poll_interval=15, timeout_seconds=1800):
        """Polls until transcription completes or fails."""
        start = time.time()

        while True:
            status_data = self.get_media_status(media_id)
            status = status_data["status"]

            print("Current Status:", status)

            if status == "completed":
                print("✅ Transcription completed.")
                return status_data

            if status in ("failed", "blocked"):
                raise SonixAPIError(f"Transcription failed with status: {status}")

            if time.time() - start > timeout_seconds:
                raise SonixAPIError("Timeout waiting for transcription completion.")

            time.sleep(poll_interval)

    # -------------------------
    # Transcript Fetching
    # -------------------------

    def get_transcript_text(self, media_id: str) -> str:
        response = self._request("GET", f"/media/{media_id}/transcript")

        if response.status_code == 200:
            return response.text

        elif response.status_code == 409:
            raise SonixAPIError("Transcription still in progress.")

        else:
            raise SonixAPIError(
                f"Failed to fetch transcript text: {response.status_code} {response.text}"
            )

    def get_transcript_srt(self, media_id: str) -> str:
        response = self._request("GET", f"/media/{media_id}/transcript.srt")

        if response.status_code == 200:
            return response.text

        elif response.status_code == 409:
            raise SonixAPIError("Transcription still in progress.")

        else:
            raise SonixAPIError(
                f"Failed to fetch transcript SRT: {response.status_code} {response.text}"
            )

    def get_transcript_json(self, media_id: str) -> dict:
        response = self._request("GET", f"/media/{media_id}/transcript.json")

        if response.status_code == 200:
            return response.json()

        elif response.status_code == 409:
            raise SonixAPIError("Transcription still in progress.")

        else:
            raise SonixAPIError(
                f"Failed to fetch transcript JSON: {response.status_code} {response.text}"
            )
        

sonix_client = SonixClient(os.getenv("SONIX_API_KEY"))
# sonix_client.verify_api_key()