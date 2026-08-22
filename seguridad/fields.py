from django.db import models

from seguridad.utils import cifrar_campo, descifrar_campo


class EncryptedTextField(models.TextField):

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return descifrar_campo(value)

    def get_prep_value(self, value):
        if value is None:
            return value
        return cifrar_campo(value)

    def value_to_string(self, obj):
        value = self.value_from_object(obj)
        return self.get_prep_value(value)


class EncryptedCharField(models.CharField):

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = kwargs.get('max_length', 512)
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return descifrar_campo(value)

    def get_prep_value(self, value):
        if value is None:
            return value
        return cifrar_campo(value)

    def value_to_string(self, obj):
        value = self.value_from_object(obj)
        return self.get_prep_value(value)
