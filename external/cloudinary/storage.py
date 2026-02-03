from cloudinary_storage.storage import MediaCloudinaryStorage

class PrivateCloudinaryStorage(MediaCloudinaryStorage):
    def _save(self, name, content):
        self.resource_type = "image"
        self.type = "private"   # 🔒 THIS is the key
        return super()._save(name, content)