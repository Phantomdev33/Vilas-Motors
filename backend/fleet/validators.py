import re
from django.core.exceptions import ValidationError

class MixedPasswordValidator:
    def validate(self, password, user=None):
        if not all(re.search(pattern, password) for pattern in ['[a-z]', '[A-Z]', '[0-9]']):
            raise ValidationError('La contraseña debe incluir mayúsculas, minúsculas y números.')
    def get_help_text(self):
        return 'Incluye mayúsculas, minúsculas y números.'
