from io import BytesIO
import uuid

from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from PIL import Image, ImageOps
from rest_framework import serializers
from rest_framework.exceptions import NotAuthenticated, ValidationError
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from .models import ProfilePhoto, User
from .permissions import MATRIX
from .serializers import UserSerializer, unique_user_email
from .services import audit
from .sms import SMSUnavailable, check_challenge, start_challenge


class ProfileSerializer(serializers.ModelSerializer):
    def validate_email(self, value):
        return unique_user_email(value, self.instance)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')
        extra_kwargs = {'email': {'validators': []}}


class ProfileSecurityThrottle(UserRateThrottle):
    scope = 'profile_security'
    rate = '10/min'

    def allow_request(self, request, view):
        return request.method in ('GET', 'HEAD', 'OPTIONS') or super().allow_request(request, view)


def profile_data(user):
    data = UserSerializer(user).data
    data['permissions'] = {module: roles.get(user.role, '') for module, roles in MATRIX.items()}
    revision = ProfilePhoto.objects.filter(user=user).values_list('revision', flat=True).first()
    data['photo_url'] = f'/api/auth/me/photo/?v={revision}' if revision else None
    return data


def locked_user(request):
    user = User.objects.select_for_update().filter(pk=request.user.pk, is_active=True).first()
    if not user or user.access_version != request.user.access_version or user.password != request.user.password:
        raise NotAuthenticated('Vuelve a iniciar sesión.')
    return user


def require_password(user, request):
    password = request.data.get('current_password')
    # Use the hasher directly so verification cannot change the session's password hash.
    if not isinstance(password, str) or len(password) > 1024 or not check_password(password, user.password):
        raise ValidationError({'current_password': 'La contraseña actual es incorrecta.'})


@method_decorator(never_cache, name='dispatch')
class MeView(APIView):
    throttle_classes = [ProfileSecurityThrottle]

    def get(self, request):
        return Response(profile_data(request.user))

    @transaction.atomic
    def patch(self, request):
        user = locked_user(request)
        serializer = ProfileSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        fields = serializer.validated_data
        if fields.get('email', user.email) != user.email:
            require_password(user, request)
        if fields:
            try:
                with transaction.atomic():
                    for field, value in fields.items():
                        setattr(user, field, value)
                    user.save(update_fields=fields.keys())
            except IntegrityError as exc:
                raise ValidationError({'email': 'Ya existe una cuenta con este correo.'}) from exc
            audit(user, 'profile_updated', user)
        return Response(profile_data(user))


@method_decorator(never_cache, name='dispatch')
class ProfilePhotoView(APIView):
    def get(self, request):
        image = ProfilePhoto.objects.filter(user=request.user).values_list('image', flat=True).first()
        if image is None:
            return Response(status=404)
        return HttpResponse(bytes(image), content_type='image/jpeg')

    @transaction.atomic
    def put(self, request):
        user = locked_user(request)
        file = request.FILES.get('photo')
        if not file or file.size > 2 * 1024 * 1024:
            raise ValidationError({'photo': 'Selecciona una imagen de hasta 2 MB.'})
        output = BytesIO()
        try:
            with Image.open(file, formats=['JPEG', 'PNG', 'WEBP']) as image:
                if image.width * image.height > 12_000_000:
                    raise ValueError('Imagen demasiado grande')
                resized = ImageOps.exif_transpose(image)
                resized.thumbnail((384, 384))
                resized.convert('RGB').save(output, format='JPEG', quality=85)
        except (OSError, ValueError, Image.DecompressionBombError) as exc:
            raise ValidationError({'photo': 'Usa una imagen JPG, PNG o WEBP de hasta 12 megapíxeles.'}) from exc
        ProfilePhoto.objects.update_or_create(user=user, defaults={'image': output.getvalue(), 'revision': uuid.uuid4()})
        audit(user, 'profile_photo_updated', user)
        return Response(profile_data(user))

    @transaction.atomic
    def delete(self, request):
        user = locked_user(request)
        if ProfilePhoto.objects.filter(user=user).delete()[0]:
            audit(user, 'profile_photo_removed', user)
        return Response(profile_data(user))


def new_phone(user, request):
    phone = request.data.get('phone')
    if not isinstance(phone, str) or not phone.strip():
        raise ValidationError({'phone': 'Ingresa un celular con prefijo internacional.'})
    try:
        value = User._meta.get_field('phone').clean(phone.strip(), user)
    except DjangoValidationError as exc:
        raise ValidationError({'phone': exc.messages}) from exc
    if value == user.phone:
        raise ValidationError({'phone': 'Este ya es tu celular registrado.'})
    return value


@method_decorator(never_cache, name='dispatch')
class ProfilePhoneView(APIView):
    throttle_classes = [ProfileSecurityThrottle]

    @transaction.atomic
    def post(self, request):
        user = locked_user(request)
        phone = new_phone(user, request)
        require_password(user, request)
        try:
            challenge_id = start_challenge(user, 'profile', destination=phone)
        except SMSUnavailable:
            return Response({'detail': 'El envío de SMS no está disponible. Intenta nuevamente.'}, status=503)
        if not challenge_id:
            return Response({'detail': 'Espera un minuto antes de solicitar otro código.'}, status=429)
        return Response({'challenge_id': challenge_id}, status=202)

    @transaction.atomic
    def put(self, request):
        user = locked_user(request)
        phone = new_phone(user, request)
        _, sms = check_challenge(
            request.data.get('challenge_id'), 'profile', request.data.get('code'),
            user=user, destination=phone,
        )
        if not sms:
            return Response({'detail': 'Código incorrecto, vencido o agotado.'}, status=400)
        user.phone = phone
        user.save(update_fields=['phone'])
        sms.used = True
        sms.save(update_fields=['used'])
        audit(user, 'profile_phone_updated', user)
        response = Response({'detail': 'Celular actualizado. Inicia sesión con tu nuevo número registrado.'})
        response.delete_cookie('access_token', samesite='Lax')
        return response
