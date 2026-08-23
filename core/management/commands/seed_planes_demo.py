"""Semilla de DOS centros demo para verificar planes de venta:

  A) Centro COMPLETO (vía seed_demo) con caja + facturación +
     certificados pagados activos.
  B) Centro SIN módulos de cobro (caja/facturación/nómina apagados)
     pero operativo: certificados gratuitos, sin deudas aunque existan
     conceptos/asignaciones, portales y dashboard sin secciones de dinero.

Idempotente: puede ejecutarse varias veces.
Uso:  python manage.py seed_planes_demo
"""

from datetime import date
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from academico.models import Seccion
from academico.services.estructura_minerd import crear_estructura_minerd
from administracion.models import Administrativo
from auditoria.models import Bitacora
from caja.models import AsignacionConcepto, ConceptoPago
from core.cache_utils import borrar
from core.models import (
    AnioEscolar,
    CentroEducativo,
    ConfiguracionCentro,
    RolCentro,
    UsuarioCentro,
)
from estudiantes.models import Estudiante, Inscripcion
from usuarios.models import Usuario

# ------------------------------------------------------------------
# Centro B: sin módulos de cobro (plan "público / básico")
# ------------------------------------------------------------------
CENTRO_B_NOMBRE = "Centro Educativo Público Los Próceres"
CENTRO_B_CODIGO = "0002-02"

PASSWORD_STAFF = "admin123"
PASSWORD_ESTUDIANTE = "estudiante123"

USUARIOS_B = ["directorpb", "secretariapb", "cajeropb"]

ANIO_ACTUAL = (2025, 2026)
ANIO_ANTERIOR = (2024, 2025)

ESTUDIANTES_B = [
    dict(matricula="pb3001", nombres="Carla", apellidos="Jiménez",
         sexo="F", nacimiento=date(2014, 4, 2), grado="3ro"),
    dict(matricula="pb3002", nombres="Diego", apellidos="Cruz",
         sexo="M", nacimiento=date(2013, 9, 15), grado="4to"),
    dict(matricula="pb3003", nombres="Valeria", apellidos="Núñez",
         sexo="F", nacimiento=date(2012, 1, 28), grado="4to"),
    dict(matricula="pb3004", nombres="Mateo", apellidos="Herrera",
         sexo="M", nacimiento=date(2011, 7, 9), grado="5to"),
]

STAFF_B = [
    dict(username="directorpb", rol="director", nombre="Gloria",
         apellido="Báez", cedula="00200000001", sexo="F",
         nacimiento=date(1980, 3, 12)),
    dict(username="secretariapb", rol="secretaria", nombre="Otto",
         apellido="Reyes", cedula="00200000002", sexo="M",
         nacimiento=date(1990, 6, 25)),
    dict(username="cajeropb", rol="cajero", nombre="Iris",
         apellido="Peralta", cedula="00200000003", sexo="F",
         nacimiento=date(1995, 11, 3)),
]


class Command(BaseCommand):
    help = (
        "Crea dos centros demo: uno completo (con cobros) y otro sin "
        "módulos de pago, para verificar la independencia de módulos."
    )

    def handle(self, *args, **options):
        from core.management.commands.seed_demo import Command as DemoCommand

        demo = DemoCommand()
        demo._desconectar_auditoria()
        try:
            with transaction.atomic():
                self._centro_completo(demo)
                self._centro_sin_cobros(demo)
        finally:
            demo._reconectar_auditoria()

        self._resumen()

    # ------------------------------------------------------------------
    # A) Centro completo (seed_demo) + plan de cobros encendido
    # ------------------------------------------------------------------

    def _centro_completo(self, demo=None):
        self.stdout.write("== Centro A: completo (seed_demo) ==")
        call_command('seed_demo', verbosity=0)

        centro = CentroEducativo.objects.get(codigo_minerd="0001-01")
        ConfiguracionCentro.objects.filter(centro=centro).update(
            permitir_facturacion=True,
            facturacion_itbis=True,
            permitir_pago_online=True,
            modulo_certificados=True,
            precio_certificado=Decimal("500.00"),
        )
        borrar(f'config:{centro.id}')

    # ------------------------------------------------------------------
    # B) Centro sin cobros
    # ------------------------------------------------------------------

    @transaction.atomic
    def _centro_sin_cobros(self, demo):
        self.stdout.write("== Centro B: sin módulos de cobro ==")

        for centro_previo in CentroEducativo.objects.filter(
            codigo_minerd=CENTRO_B_CODIGO
        ):
            demo._limpiar_centro(centro_previo)

        Usuario.objects.filter(username__in=USUARIOS_B).delete()
        Bitacora.objects.filter(
            usuario__username__in=USUARIOS_B
        ).delete()

        centro = CentroEducativo.objects.create(
            nombre=CENTRO_B_NOMBRE,
            codigo_minerd=CENTRO_B_CODIGO,
            direccion="Calle del Parque #10",
            telefono="809-200-0002",
        )
        ConfiguracionCentro.objects.create(
            centro=centro,
            nota_minima_aprobacion=Decimal("70.00"),
            modulo_asistencia=True,
            modulo_reportes=True,
            modulo_certificados=True,
            precio_certificado=Decimal("500.00"),
            permitir_pago_online=True,
            # Plan SIN cobros:
            modulo_caja=False,
            permitir_facturacion=False,
            modulo_nomina=False,
            modulo_biblioteca=False,
            modulo_transporte=False,
        )
        self.stdout.write("  Centro, configuración (sin caja/facturación)...")

        roles = {}
        for nombre in ["admin", "director", "secretaria", "cajero", "docente"]:
            roles[nombre], _ = RolCentro.objects.get_or_create(nombre=nombre)

        # ---- Años escolares ----
        anios = {}
        for inicio, fin in (ANIO_ANTERIOR, ANIO_ACTUAL):
            anio = AnioEscolar.objects.create(
                centro=centro, nombre=f"{inicio}-{fin}",
                fecha_inicio=date(inicio, 8, 20),
                fecha_fin=date(fin, 6, 28),
            )
            anios[(inicio, fin)] = anio
        anio_activo = anios[ANIO_ACTUAL]
        anio_activo.activo = True
        anio_activo.save()

        # ---- Estructura académica mínima ----
        secciones = {
            letra: Seccion.objects.create(centro=centro, nombre=letra)
            for letra in ("A",)
        }
        estructura = crear_estructura_minerd(centro, ("primaria",))
        nivel_primaria = estructura['niveles'][0]
        grados_por_nombre = {
            grado.nombre.split()[0]: grado
            for grado in nivel_primaria.grado_set.all().order_by('orden')
        }
        for grado in nivel_primaria.grado_set.all():
            grado.secciones.add(*secciones.values())

        # ---- Usuarios staff + administrativos ----
        usuarios_creados = []
        admin = Usuario.objects.filter(
            username="admin", is_superuser=True
        ).first()
        if admin:
            UsuarioCentro.objects.get_or_create(
                usuario=admin, centro=centro,
                defaults={'rol': roles["admin"]},
            )

        for datos in STAFF_B:
            usuario = Usuario.objects.create_user(
                datos["username"],
                f'{datos["username"]}@demo.com',
                PASSWORD_STAFF,
            )
            usuario.rol = datos["rol"]
            usuario.first_name = datos["nombre"]
            usuario.last_name = datos["apellido"]
            usuario.save()

            Administrativo.objects.create(
                usuario=usuario, centro=centro,
                primer_nombre=datos["nombre"],
                primer_apellido=datos["apellido"],
                cedula=datos["cedula"], sexo=datos["sexo"],
                fecha_nacimiento=datos["nacimiento"],
                nacionalidad="Dominicana",
                direccion="Calle Pública #2",
                telefono="809-555-0200",
                cargo=datos["rol"],
                fecha_ingreso=date(2018, 8, 1),
            )
            UsuarioCentro.objects.create(
                usuario=usuario, centro=centro, rol=roles[datos["rol"]]
            )
            usuario.debe_cambiar_password = False
            usuario.password_cambiada_en = timezone.now()
            usuario.save(update_fields=[
                'debe_cambiar_password', 'password_cambiada_en'
            ])
            usuarios_creados.append(usuario)

        # ---- Estudiantes con trayectoria de 2 años ----
        self.stdout.write("  Estudiantes e inscripciones...")
        for datos in ESTUDIANTES_B:
            usuario = Usuario.objects.create_user(
                datos["matricula"],
                f'{datos["matricula"]}@demo.com',
                PASSWORD_ESTUDIANTE,
            )
            usuario.rol = "estudiante"
            usuario.first_name = datos["nombres"]
            usuario.last_name = datos["apellidos"]
            usuario.save()

            estudiante = Estudiante.objects.create(
                usuario=usuario, centro=centro,
                matricula=datos["matricula"],
                primer_nombre=datos["nombres"],
                primer_apellido=datos["apellidos"],
                sexo=datos["sexo"],
                fecha_nacimiento=datos["nacimiento"],
                lugar_nacimiento="Santo Domingo",
                nacionalidad="Dominicana",
                direccion="Calle Los Próceres #5",
                telefono="809-555-0300",
                nombre_tutor="Tutor de Prueba",
                cedula_tutor="00200000099",
                telefono_tutor="809-555-0301",
                parentesco_tutor="Padre/Madre",
            )
            usuario.debe_cambiar_password = False
            usuario.password_cambiada_en = timezone.now()
            usuario.save(update_fields=[
                'debe_cambiar_password', 'password_cambiada_en'
            ])

            Inscripcion.objects.create(
                estudiante=estudiante, centro=centro,
                anio_escolar=anios[ANIO_ANTERIOR],
                grado=grados_por_nombre[self._grado_anterior(datos["grado"])],
                seccion=secciones["A"],
                estado_final="aprobado",
                fecha_cierre=anios[ANIO_ANTERIOR].fecha_fin,
            )
            Inscripcion.objects.create(
                estudiante=estudiante, centro=centro,
                anio_escolar=anio_activo,
                grado=grados_por_nombre[datos["grado"]],
                seccion=secciones["A"],
                estado_final="pendiente",
            )

        # ---- Concepto/asignación impaga: prueba de deuda neutral ----
        concepto = ConceptoPago.objects.create(
            centro=centro, nombre="Inscripción",
            monto=Decimal("3000.00"), es_recurrente=False, activo=True,
        )
        AsignacionConcepto.objects.create(
            centro=centro, concepto=concepto,
            estudiante=Estudiante.objects.get(
                centro=centro, matricula="pb3001"
            ),
            anio_escolar=anio_activo, activo=True,
        )
        self.stdout.write(
            "  Asignación impaga creada (la deuda debe ser invisible)."
        )

    @staticmethod
    def _grado_anterior(grado_actual):
        orden = ["1ro", "2do", "3ro", "4to", "5to", "6to"]
        idx = max(orden.index(grado_actual) - 1, 0)
        return orden[idx]

    # ------------------------------------------------------------------

    def _resumen(self):
        linea = "=" * 62
        self.stdout.write("")
        self.stdout.write(linea)
        self.stdout.write("SEMILLA DE PLANES LISTA")
        self.stdout.write(linea)
        self.stdout.write(
            "\nCENTRO A — Colegio Demostrativo Juan Pablo Duarte "
            "(CON cobros)\n"
            "  director / admin123      secretaria / admin123\n"
            "  cajero / admin123        20200001 / estudiante123\n"
            "  Módulos: caja+facturación+certificados pagados ($500)\n"
        )
        self.stdout.write(
            "\nCENTRO B — Centro Educativo Público Los Próceres "
            "(SIN cobros)\n"
            "  directorpb / admin123    secretariapb / admin123\n"
            "  cajeropb / admin123      pb3001 / estudiante123\n"
            "  Módulos: certificados GRATIS; caja/facturación/nómina OFF\n"
            "  pb3001 tiene asignación impaga: NO debe verse como deuda\n"
        )
        self.stdout.write(
            "\nQUÉ VERIFICAR:\n"
            "  En A: sidebar con Caja/Facturación; certificado pide pago;\n"
            "        dashboard muestra Recaudado.\n"
            "  En B: sin menú Caja/Facturación; /caja/ redirige con aviso;\n"
            "        certificado queda Exenta/aprobada al instante;\n"
            "        kardex/constancias imprimen sin bloqueo de deuda;\n"
            "        cajeropb no puede entrar (módulo inactivo).\n"
            "  Superadmin admin/admin123 (2FA: JBSWY3DPEHPK3PXP) para\n"
            "  alternar centros desde 'Seleccionar centro'.\n"
        )
