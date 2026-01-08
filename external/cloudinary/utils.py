from cloudinary.uploader import upload, destroy
from urllib.parse import urlparse

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
    
