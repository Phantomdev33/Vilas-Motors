"""Solo evidencias de lecturas: binarios de hasta 10 MB en MongoDB."""
import hashlib
import io
import uuid
from functools import lru_cache
from pathlib import PurePosixPath

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage, FileSystemStorage
from django.utils import timezone
from django.utils.deconstruct import deconstructible
from PIL import Image
from rest_framework.exceptions import APIException


class ImageStoreUnavailable(APIException):
    status_code = 503
    default_detail = 'El almacenamiento de fotos no está disponible. Intenta nuevamente; la lectura no se guardó.'


@lru_cache(maxsize=4)
def _client(uri):
    from pymongo import MongoClient
    return MongoClient(uri, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)


def image_collection():
    if not settings.MONGODB_URI:
        raise ImageStoreUnavailable('Configura MongoDB para adjuntar fotos. Puedes registrar la lectura sin imagen.')
    return _client(settings.MONGODB_URI)[settings.MONGODB_IMAGE_DATABASE]['reading_images']


@deconstructible
class ReadingImageStorage(Storage):
    def get_available_name(self, name, max_length=None):
        return f'mongo/{uuid.uuid4().hex}'

    def _save(self, name, content):
        from bson import Binary
        from pymongo.errors import PyMongoError
        data = content.read(10 * 1024 * 1024 + 1)
        if len(data) > 10 * 1024 * 1024:
            raise ValueError('La imagen no puede superar 10 MB.')
        with Image.open(io.BytesIO(data)) as image:
            mime = {'JPEG':'image/jpeg', 'PNG':'image/png', 'WEBP':'image/webp'}.get(image.format)
            image.verify()
        if not mime:
            raise ValueError('Formato de imagen no admitido.')
        try:
            image_collection().insert_one({'_id': name, 'data': Binary(data), 'content_type': mime,
                'filename': PurePosixPath(content.name or 'evidencia').name,
                'sha256': hashlib.sha256(data).hexdigest(), 'uploaded_at': timezone.now()})
        except PyMongoError:
            raise ImageStoreUnavailable() from None
        return name

    def _open(self, name, mode='rb'):
        # Las fotos antiguas continúan disponibles; todas las nuevas van a MongoDB.
        if not name.startswith('mongo/'):
            return FileSystemStorage().open(name, mode)
        from pymongo.errors import PyMongoError
        try:
            document = image_collection().find_one({'_id': name})
        except PyMongoError:
            raise ImageStoreUnavailable('No se pudo recuperar la foto. Intenta nuevamente.') from None
        if not document:
            raise FileNotFoundError(name)
        file = ContentFile(bytes(document['data']), name=document['filename'])
        file.content_type = document['content_type']
        return file

    def url(self, name):
        return settings.MEDIA_URL + name

    def exists(self, name):
        if not name.startswith('mongo/'):
            return FileSystemStorage().exists(name)
        return image_collection().find_one({'_id': name}, {'_id': 1}) is not None

    def delete(self, name):
        # Limpieza explícita de cargas fallidas; nunca borra archivos históricos locales.
        if name.startswith('mongo/'):
            image_collection().delete_one({'_id': name})

    def size(self, name):
        with self.open(name) as file:
            return file.size
