from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class PasswordStrengthValidator:
    """Exige mayúscula, minúscula, dígito y símbolo en la contraseña."""

    def __init__(self, minimo_mayusculas=1, minimo_minusculas=1,
                 minimo_digitos=1, minimo_simbolos=1):
        self.minimo_mayusculas = minimo_mayusculas
        self.minimo_minusculas = minimo_minusculas
        self.minimo_digitos = minimo_digitos
        self.minimo_simbolos = minimo_simbolos

    def validate(self, password, user=None):
        faltantes = []
        if sum(1 for c in password if c.isupper()) < self.minimo_mayusculas:
            faltantes.append('una mayúscula')
        if sum(1 for c in password if c.islower()) < self.minimo_minusculas:
            faltantes.append('una minúscula')
        if sum(1 for c in password if c.isdigit()) < self.minimo_digitos:
            faltantes.append('un número')
        if sum(1 for c in password if not c.isalnum()) < self.minimo_simbolos:
            faltantes.append('un símbolo')
        if faltantes:
            raise ValidationError(
                _('La contraseña debe contener al menos %(detalles)s.')
                % {'detalles': ', '.join(faltantes)},
                code='password_strength',
            )

    def get_help_text(self):
        return _(
            'La contraseña debe incluir al menos una mayúscula, una '
            'minúscula, un número y un símbolo.'
        )
