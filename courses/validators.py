from django.core.exceptions import ValidationError
from urllib.parse import urlparse


def validate_youtube(value):
    """Проверяет, что ссылка ведет только на YouTube"""
    if value:
        parsed_url = urlparse(value)
        allowed_domains = ['youtube.com', 'www.youtube.com', 'youtu.be']


        if parsed_url.netloc not in allowed_domains:
            raise ValidationError('Разрешены только ссылки на YouTube')

        # Дополнительная проверка для youtu.be
        if parsed_url.netloc == 'youtu.be' and not parsed_url.path.strip('/'):
            raise ValidationError('Некорректная ссылка YouTube Short')