from typing import BinaryIO

import cloudinary.uploader


class CloudinaryService:

    @staticmethod
    def upload_image(
        file: BinaryIO,
        folder: str,
        public_id: str | None = None,
    ) -> dict:

        options = {
            "folder": folder,
            "resource_type": "image",
            "overwrite": False,
        }

        if public_id:
            options["public_id"] = public_id

        result = cloudinary.uploader.upload(
            file,
            **options,
        )

        return {
            "url": result["secure_url"],
            "public_id": result["public_id"],
            "width": result.get("width"),
            "height": result.get("height"),
            "format": result.get("format"),
            "bytes": result.get("bytes"),
        }


    @staticmethod
    def delete_image(
        public_id: str,
    ) -> dict:

        return cloudinary.uploader.destroy(
            public_id,
            resource_type="image",
        )