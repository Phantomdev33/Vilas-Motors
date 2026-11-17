import base64
import logging
import secrets
import uuid
from datetime import timedelta
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac

from .models import SMSChallenge, User

logger = logging.getLogger(__name__)


class SMSUnavailable(Exception):
    pass


def send_code(phone, code, purpose):
    action = 'ingresar' if purpose == 'login' else 'recuperar tu contraseña'
    message = f"Vila's Motor: código para {action}: {code}. Vence en 5 minutos."
    if settings.SMS_BACKEND == 'console' and settings.DEBUG:
        print(f'[SMS simulado] {phone}: {message}', flush=True)
        return

    sid, token, sender = settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_FROM
    if settings.SMS_BACKEND != 'twilio' or not all((sid, token, sender)):
        raise SMSUnavailable
    authorization = base64.b64encode(f'{sid}:{token}'.encode()).decode()
    request = Request(
        f'https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json',
        data=urlencode({'To': phone, 'From': sender, 'Body': message}).encode(),
        headers={'Authorization': f'Basic {authorization}'},
    )
    try:
        with urlopen(request, timeout=5):
            pass
    except (URLError, TimeoutError, OSError):
        logger.warning('No se pudo entregar un SMS mediante el proveedor configurado.')
        raise SMSUnavailable from None


def digest(challenge_id, purpose, user, code):
    return salted_hmac(
        'fleet.sms', f'{challenge_id}:{purpose}:{user.pk}:{user.access_version}:{user.password}:{code}',
        algorithm='sha256',
    ).hexdigest()


def start_challenge(user, purpose):
    """Caller holds the user row lock until the challenge is stored."""
    previous = SMSChallenge.objects.filter(user=user, purpose=purpose).first()
    if previous and previous.sent_at > timezone.now() - timedelta(minutes=1):
        return None
    challenge_id = uuid.uuid4()
    code = f'{secrets.randbelow(1_000_000):06d}'
    if previous:
        previous.delete()
    challenge = SMSChallenge.objects.create(
        id=challenge_id, user=user, purpose=purpose,
        digest=digest(challenge_id, purpose, user, code),
    )
    try:
        send_code(user.phone, code, purpose)
    except SMSUnavailable:
        challenge.used = True
        challenge.save(update_fields=['used'])
        raise
    return challenge_id


def check_challenge(challenge_id, purpose, code):
    """Verify under the user row lock, held until the caller consumes the code."""
    try:
        challenge_id = uuid.UUID(str(challenge_id))
    except (ValueError, TypeError):
        return None, None
    query = SMSChallenge.objects.filter(pk=challenge_id, purpose=purpose)
    user_id = query.values_list('user_id', flat=True).first()
    user = User.objects.select_for_update().filter(pk=user_id, is_active=True).first()
    challenge = query.first() if user else None
    if not challenge or challenge.used or challenge.attempts >= 5:
        return None, None
    if challenge.sent_at <= timezone.now() - timedelta(minutes=5):
        return None, None
    if not isinstance(code, str) or not constant_time_compare(
        challenge.digest, digest(challenge.id, purpose, user, code[:7]),
    ):
        challenge.attempts += 1
        challenge.save(update_fields=['attempts'])
        return None, None
    return user, challenge
