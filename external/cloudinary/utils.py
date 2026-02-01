from cloudinary.uploader import upload, destroy
from cloudinary.utils import cloudinary_url
from urllib.parse import urlparse
from datetime import timedelta
from django.utils.timezone import now

class CloudinaryService:
    @staticmethod
    def upload_image(content, folder, public_id):
        response = upload(
            content, folder=folder,
            public_id=public_id,
            resource_type="image",
        )
        return response

    @staticmethod
    def destroy_image(url: str, public_id: str = None):
        if not public_id:
            public_id = CloudinaryService.extract_public_id(url)
        response = destroy(public_id)
        return response

    @staticmethod
    def upload_video(content, folder, public_id):
        response = upload(
            content,
            folder=folder,
            public_id=public_id,
            resource_type="video"
        )
        return response

    @staticmethod
    def upload_raw(content, folder, public_id):
        response = upload(
            content,
            folder=folder,
            public_id=public_id,
            resource_type="raw",   # ✅ This is the key
        )
        return response

    @staticmethod
    def generate_signed_pdf_url(public_id: str, expires_in_seconds: int = 1500):
        expires_at = int(
            (now() + timedelta(seconds=expires_in_seconds)).timestamp()
        )

        url, _ = cloudinary_url(
            public_id,
            resource_type="image", 
            type="private",
            sign_url=True,
            expires_at=expires_at,
            secure=True,
        )
        return url
    
    @staticmethod
    def extract_public_id(cloudinary_url: str) -> str:
        parsed = urlparse(cloudinary_url)
        path = parsed.path  

        try:
            upload_index = path.index("/upload/")
            public_part = path[upload_index + len("/upload/"):]
            public_part = public_part.split("/", 1)[1]  # remove version
            public_id = public_part.rsplit(".", 1)[0]   # remove extension
            return public_id
        except Exception:
            raise ValueError("Invalid Cloudinary URL format")
    