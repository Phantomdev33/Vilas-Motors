from io import BytesIO
from unittest.mock import patch

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from rest_framework.test import APIClient

from .models import User


class ProfileTests(TestCase):
    def setUp(self):
        self.password = 'ProfileDemo2026!'
        self.user = User.objects.create_user(
            username='profile', email='original@example.cl', password=self.password,
            role='helper', phone='+56912345678',
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.addCleanup(cache.clear)

    def test_profile_fields_and_email_reauthentication(self):
        response = self.client.patch('/api/auth/me/', {'first_name': 'Ana', 'role': 'admin', 'is_active': False, 'phone': '+56998765432'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['first_name'], 'Ana')
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, 'helper')
        self.assertEqual(self.user.phone, '+56912345678')
        self.assertTrue(self.user.is_active)
        request = {'email': 'NEW@example.cl'}
        self.assertEqual(self.client.patch('/api/auth/me/', request, format='json').status_code, 400)
        request['current_password'] = self.password
        response = self.client.patch('/api/auth/me/', request, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['email'], 'new@example.cl')
        self.assertNotIn('current_password', response.data)

    def test_upload_get_and_remove_profile_photo(self):
        url = '/api/auth/me/photo/'
        self.assertEqual(self.client.get(url).status_code, 404)
        image = BytesIO()
        Image.new('RGB', (500, 250), color='red').save(image, 'PNG')
        response = self.client.put(url, {'photo': SimpleUploadedFile('photo.png', image.getvalue(), 'image/png')})
        self.assertEqual(response.status_code, 200)
        photo_url = response.data['photo_url']
        photo = self.client.get(photo_url)
        self.assertEqual(photo['Content-Type'], 'image/jpeg')
        with Image.open(BytesIO(photo.content)) as resized:
            self.assertEqual(resized.size, (384, 192))
        self.assertIn(APIClient().get(photo_url).status_code, (401, 403))
        self.assertIsNone(self.client.delete(url).data['photo_url'])
        self.assertEqual(self.client.get(photo_url).status_code, 404)

    def test_phone_change_requires_password_and_code_bound_to_new_phone(self):
        url = '/api/auth/me/phone/'
        phone = '+56998765432'
        original_version = self.user.access_version
        with patch('fleet.sms.send_code') as send_code:
            self.assertEqual(self.client.post(url, {'phone': phone}, format='json').status_code, 400)
            send_code.assert_not_called()
            response = self.client.post(url, {'phone': phone, 'current_password': self.password}, format='json')
        self.assertEqual(response.status_code, 202)
        sent_phone, code, purpose = send_code.call_args.args
        self.assertEqual((sent_phone, purpose), (phone, 'profile'))
        payload = {'challenge_id': str(response.data['challenge_id']), 'code': code, 'phone': '+56999999999'}
        self.assertEqual(self.client.put(url, payload, format='json').status_code, 400)
        payload['phone'] = phone
        response = self.client.put(url, payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.cookies['access_token']['max-age'], 0)
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, phone)
        self.assertNotEqual(self.user.access_version, original_version)
