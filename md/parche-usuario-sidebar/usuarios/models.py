from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone

import pyotp


class UsuarioManager(BaseUserManager):
    def create_user(self, username, email, password=None, first_name='', last_name=''):
        if not email:
            raise ValueError("Debe tener email")

        user = self.model(
            username=username,
            email=self.normalize_email(email),
            first_name=first_name,
            last_name=last_name,
            is_active=True,
            password_cambiada_en=timezone.now(),
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password):
        user = self.create_user(username, email, password)
        user.is_staff = True
        user.is_superuser = True
        user.rol = 'superadmin'  # 🔥 importante
        user.save(using=self._db)
        return user




class Usuario(AbstractBaseUser, PermissionsMixin):

    ROLES = (
        ('superadmin', 'Super Administrador'),
        ('admin', 'Administrador'),
        ('secretaria', 'Secretaria'),
        ('docente', 'Docente'),
        ('estudiante', 'Estudiante'),
        ('director', 'Director'),
        ('cajero', 'Cajero'),
        ('tutor', 'Tutor'),
    )

    username = models.CharField(max_length=100, unique=True)
    email = models.EmailField(unique=True)

    foto = models.ImageField(
        'Foto',
        upload_to='usuarios/fotos/',
        blank=True,
        null=True
    )

    first_name = models.CharField("Nombres", max_length=150)
    last_name = models.CharField("Apellidos", max_length=150)

    rol = models.CharField(
        max_length=20,
        choices=ROLES
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    # --- Seguridad ---
    totp_secret = models.CharField(max_length=64, blank=True, null=True)
    totp_activo = models.BooleanField(default=False)
    password_cambiada_en = models.DateTimeField(null=True, blank=True)
    debe_cambiar_password = models.BooleanField(default=False)

    objects = UsuarioManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email", "first_name", "last_name"]

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def es_super(self):
        return self.is_superuser or self.rol == 'superadmin'

    # --- TOTP / 2FA ---
    def generar_totp(self):
        if not self.totp_secret:
            self.totp_secret = pyotp.random_base32()
            self.save(update_fields=['totp_secret'])
        return self.totp_secret

    def uri_totp(self):
        return pyotp.TOTP(self.generar_totp()).provisioning_uri(
            f"MiColegio:{self.username}", issuer_name="Mi Colegio",
        )

    def verificar_totp(self, codigo):
        if not self.totp_secret or not codigo:
            return False
        return pyotp.TOTP(self.totp_secret).verify(codigo, valid_window=1)

    def tiene_2fa_obligatorio(self):
        return self.rol in ('admin', 'superadmin')

    def requiere_2fa(self):
        return self.totp_activo or self.tiene_2fa_obligatorio()

    def password_vencida(self, dias_max=None):
        if dias_max is None:
            dias_max = getattr(settings, 'PASSWORD_MAX_DAYS', 90)
        if self.password_cambiada_en is None:
            return self.debe_cambiar_password
        return self.debe_cambiar_password or (
            timezone.now() - self.password_cambiada_en
        ).days >= dias_max
