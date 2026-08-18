import time
from datetime import timedelta

import pyotp
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from auditoria.models import Bitacora
from usuarios.models import Usuario


class BaseSeguridadTests(TestCase):
    def setUp(self):
        cache.clear()
        self.usuario = Usuario.objects.create_user(
            username="prueba", email="prueba@demo.com", password="ClaveSegura123!",
        )
        self.usuario.rol = "docente"
        self.usuario.first_name = "Prueba"
        self.usuario.last_name = "Demo"
        self.usuario.debe_cambiar_password = False
        self.usuario.save()


class LoginSecurityTests(BaseSeguridadTests):
    def test_login_exitoso_redirige_y_registra_bitacora(self):
        resp = self.client.post(reverse("usuarios:login"), {
            "username": "prueba",
            "password": "ClaveSegura123!",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Bitacora.objects.filter(accion="LOGIN", usuario=self.usuario).exists())

    def test_bloqueo_tras_5_intentos_fallidos(self):
        url = reverse("usuarios:login")
        for i in range(5):
            resp = self.client.post(url, {"username": "prueba", "password": "incorrecta"})
            if i < 4:
                self.assertContains(resp, "Usuario o contraseña incorrectos")
            else:
                self.assertContains(resp, "bloqueada")

        resp = self.client.post(url, {
            "username": "prueba",
            "password": "ClaveSegura123!",
        })
        self.assertContains(resp, "bloqueada")
        self.assertTrue(
            Bitacora.objects.filter(accion="ACCESO_DENEGADO", riesgo="CRITICO").count() >= 2
        )

    def test_login_correcto_resetea_contador_de_fallos(self):
        url = reverse("usuarios:login")
        for _ in range(3):
            self.client.post(url, {"username": "prueba", "password": "incorrecta"})
        resp = self.client.post(url, {
            "username": "prueba",
            "password": "ClaveSegura123!",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(self.client.session.get("_auth_user_id"))


class TwoFactorTests(BaseSeguridadTests):
    def setUp(self):
        super().setUp()
        self.usuario.rol = "docente"
        self.usuario.totp_secret = pyotp.random_base32()
        self.usuario.totp_activo = True
        self.usuario.save()

    def test_login_2fa_redirige_a_verificacion(self):
        resp = self.client.post(reverse("usuarios:login"), {
            "username": "prueba",
            "password": "ClaveSegura123!",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].endswith(reverse("usuarios:verificar_2fa")))
        self.assertFalse(self.client.session.get("_auth_user_id"))

    def test_codigo_incorrecto_rechazado(self):
        self.client.post(reverse("usuarios:login"), {
            "username": "prueba", "password": "ClaveSegura123!",
        })
        resp = self.client.post(reverse("usuarios:verificar_2fa"), {"codigo": "000000"})
        self.assertContains(resp, "El código no es válido")
        self.assertFalse(self.client.session.get("_auth_user_id"))

    def test_codigo_correcto_inicia_sesion(self):
        self.client.post(reverse("usuarios:login"), {
            "username": "prueba", "password": "ClaveSegura123!",
        })
        codigo = pyotp.TOTP(self.usuario.totp_secret).now()
        resp = self.client.post(reverse("usuarios:verificar_2fa"), {"codigo": codigo})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(self.client.session.get("_auth_user_id"))
        self.assertTrue(Bitacora.objects.filter(accion="LOGIN", usuario=self.usuario).exists())

    def test_admin_sin_2fa_configurada_va_a_configurar(self):
        admin = Usuario.objects.create_user(
            username="boss", email="boss@demo.com", password="ClaveSegura123!",
        )
        admin.rol = "admin"
        admin.debe_cambiar_password = False
        admin.save()
        resp = self.client.post(reverse("usuarios:login"), {
            "username": "boss", "password": "ClaveSegura123!",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].endswith(reverse("usuarios:configurar_2fa")))
        self.assertFalse(self.client.session.get("_auth_user_id"))


class HoneypotTests(BaseSeguridadTests):
    def test_bot_detectado_por_honeypot(self):
        resp = self.client.post(reverse("usuarios:login"), {
            "username": "prueba",
            "password": "ClaveSegura123!",
            "website": "spam",
        })
        self.assertContains(resp, "Usuario o contraseña incorrectos")
        self.assertFalse(self.client.session.get("_auth_user_id"))
        self.assertTrue(
            Bitacora.objects.filter(
                accion="ACCESO_DENEGADO", descripcion__icontains="honeypot"
            ).exists()
        )


class IdleTimeoutTests(BaseSeguridadTests):
    def test_cierra_sesion_tras_inactividad(self):
        self.client.force_login(self.usuario)
        s = self.client.session
        s["ultima_actividad"] = time.time() - 3600
        s.save()
        resp = self.client.get(reverse("core:home"))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].endswith(reverse("usuarios:login")))
        self.assertFalse(self.client.session.get("_auth_user_id"))


class PasswordExpiryTests(BaseSeguridadTests):
    def test_primer_inicio_obliga_cambio(self):
        self.usuario.debe_cambiar_password = True
        self.usuario.save()
        self.client.force_login(self.usuario)
        resp = self.client.get(reverse("core:home"))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].endswith(reverse("usuarios:cambiar_contrasena")))

    def test_password_vencida_obliga_cambio(self):
        self.usuario.debe_cambiar_password = False
        self.usuario.password_cambiada_en = timezone.now() - timedelta(days=91)
        self.usuario.save()
        self.client.force_login(self.usuario)
        resp = self.client.get(reverse("core:home"))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].endswith(reverse("usuarios:cambiar_contrasena")))


class PasswordChangeTests(BaseSeguridadTests):
    def test_cambia_contrasena_y_registra_bitacora(self):
        self.client.force_login(self.usuario)
        url = reverse("usuarios:cambiar_contrasena")
        resp = self.client.post(url, {
            "password_actual": "ClaveSegura123!",
            "password_nueva": "NuevaClaveSegura456!",
            "password_confirmacion": "NuevaClaveSegura456!",
        })
        self.assertEqual(resp.status_code, 302)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password("NuevaClaveSegura456!"))
        self.assertFalse(self.usuario.debe_cambiar_password)
        self.assertTrue(Bitacora.objects.filter(accion="PASSWORD_CHANGE").exists())

    def test_requiere_contrasena_actual_correcta(self):
        self.client.force_login(self.usuario)
        resp = self.client.post(reverse("usuarios:cambiar_contrasena"), {
            "password_actual": "incorrecta",
            "password_nueva": "NuevaClaveSegura456!",
            "password_confirmacion": "NuevaClaveSegura456!",
        })
        self.assertContains(resp, "La contraseña actual no es correcta.")

    def test_rechaza_contrasena_debil(self):
        self.client.force_login(self.usuario)
        resp = self.client.post(reverse("usuarios:cambiar_contrasena"), {
            "password_actual": "ClaveSegura123!",
            "password_nueva": "12345678",
            "password_confirmacion": "12345678",
        })
        self.assertContains(resp, "completamente numérica")


class PasswordValidatorsTests(BaseSeguridadTests):
    def test_rechaza_contraseña_sin_símbolo(self):
        with self.assertRaises(ValidationError):
            validate_password("Abcdefghij1", user=self.usuario)

    def test_acepta_contraseña_fuerte(self):
        validate_password("Abcdefghi1!", user=self.usuario)


class SecurityHeadersTests(BaseSeguridadTests):
    def test_cabeceras_de_seguridad_presentes(self):
        resp = self.client.get(reverse("usuarios:login"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get("Permissions-Policy"), "geolocation=(), microphone=(), camera=()")
        self.assertEqual(resp.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(resp.get("X-Frame-Options"), "DENY")
        self.assertEqual(resp.get("Referrer-Policy"), "same-origin")
        self.assertEqual(resp.get("Cross-Origin-Opener-Policy"), "same-origin")
