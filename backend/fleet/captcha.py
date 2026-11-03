import base64
import hashlib
import io
import secrets
from datetime import timedelta

from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError
from PIL import Image, ImageDraw, ImageFont
from .models import CaptchaChallenge


def challenge():
    CaptchaChallenge.objects.filter(expires_at__lt=timezone.now()).delete()
    answer = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(6))
    item = CaptchaChallenge.objects.create(
        answer_hash=hashlib.sha256(answer.encode()).hexdigest(),
        expires_at=timezone.now() + timedelta(minutes=5))
    image = Image.new('RGB', (240, 72), '#f1f5f9')
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=32)
    for i, letter in enumerate(answer):
        draw.text((15 + i * 36, 14 + secrets.randbelow(9)), letter, font=font, fill='#173b52')
    for _ in range(6):
        draw.line([(secrets.randbelow(240), secrets.randbelow(72)), (secrets.randbelow(240), secrets.randbelow(72))], fill='#8da6b4', width=1)
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    return {'id': str(item.pk), 'image': 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode()}


def verify(request):
    try:
        item = CaptchaChallenge.objects.select_for_update().filter(pk=request.data.get('captcha_id')).first()
    except (ValueError, DjangoValidationError):
        item = None
    if item:
        valid = item.expires_at > timezone.now() and secrets.compare_digest(
            item.answer_hash, hashlib.sha256(str(request.data.get('captcha_answer', '')).strip().upper().encode()).hexdigest())
        item.delete()
        if valid:
            return
    return 'Código incorrecto o vencido. Solicita un nuevo CAPTCHA.'
