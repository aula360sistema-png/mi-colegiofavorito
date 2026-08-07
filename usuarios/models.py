from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager


class UsuarioManager(BaseUserManager):
    def create_user(self, username, email, password=None):
        if not email:
            raise ValueError("Debe tener email")

        user = self.model(
            username=username,
            email=self.normalize_email(email),
            is_active=True
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
    )

    username = models.CharField(max_length=100, unique=True)
    email = models.EmailField(unique=True)

    first_name = models.CharField("Nombres", max_length=150)
    last_name = models.CharField("Apellidos", max_length=150)

    rol = models.CharField(
        max_length=20,
        choices=ROLES
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    fecha_creacion = models.DateTimeField(auto_now_add=True)

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
