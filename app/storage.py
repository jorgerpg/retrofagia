import os
import uuid
from typing import Optional

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def _ensure_upload_folder() -> str:
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def save_image(file_storage: Optional[FileStorage]) -> str:
    """Save a FileStorage image into the static uploads directory."""
    if not file_storage or not file_storage.filename:
        return ""

    filename = secure_filename(file_storage.filename)
    if "." not in filename:
        raise ValueError("Arquivo sem extensão.")

    ext = filename.rsplit(".", 1)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("Formato de imagem não suportado. Use PNG/JPG/GIF/WEBP.")

    unique_name = f"{uuid.uuid4().hex}.{ext}"
    upload_dir = _ensure_upload_folder()
    file_path = os.path.join(upload_dir, unique_name)
    file_storage.save(file_path)

    static_dir = os.path.join(current_app.root_path, "static")
    relative_path = os.path.relpath(file_path, static_dir)
    return relative_path.replace("\\", "/")


def delete_image(relative_path: str) -> None:
    if not relative_path:
        return
    if relative_path.startswith("http://") or relative_path.startswith("https://"):
        return
    static_dir = os.path.join(current_app.root_path, "static")
    file_path = os.path.join(static_dir, relative_path)
    if os.path.isfile(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass
