"""Siembra datos de demostración coherentes en TODAS las tablas del sistema.

Incluye: centro, años escolares (2017-2018 a 2025-2026), niveles/grados/
secciones, currículo MINERD con competencias, períodos, 3 docentes, personal
administrativo (director, secretaria, cajero), 9 estudiantes con historial
completo (calificaciones, asistencia, actas), caja (conceptos, cajas,
sesiones, pagos, egresos), nómina (AFP/ARS, cargos, configuraciones,
períodos y nóminas), días no docentes, documentos, proveedores y bitácora.

Idempotente: limpia y recrea únicamente los datos de demostración.

Uso:
    python manage.py seed_demo
"""

import calendar
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
import random

from django.apps import apps
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.utils import timezone

from academico.models import (
    AreaCurricular,
    Asignatura,
    Calificacion,
    Competencia,
    DocenteMateria,
    Grado,
    GradoAsignatura,
    Nivel,
    Periodo,
    PeriodoAnio,
    Seccion,
)
from academico.services.estructura_minerd import (
    COMPETENCIAS_FUNDAMENTALES_MINERD,
    crear_estructura_minerd,
)
from administracion.models import Acta, Administrativo
from administracion.services.boletin import construir_boletin_estudiante
from asistencia.models import AsistenciaEstudiante, DiaNoDocencia
from auditoria.models import Bitacora
from auditoria.signals import guardar_estado_anterior, registrar_eliminado, registrar_guardado
from caja.models import (
    AsignacionConcepto,
    Caja,
    ConceptoPago,
    Egreso,
    Pago,
    SesionCaja,
)
from core.models import (
    AnioEscolar,
    CentroEducativo,
    CentroProveedor,
    ConfiguracionCentro,
    Proveedor,
    RolCentro,
    UsuarioCentro,
)
from docentes.models import AsignacionDocente, Docente
from estudiantes.models import (
    DocumentoEstudiante,
    Estudiante,
    HistorialAcademico,
    Inscripcion,
    ObservacionEstudiante,
)
from nomina.models import (
    AFP,
    ARS,
    Cargo,
    ConfiguracionNomina,
    DescuentoEmpleado,
    DescuentoNomina,
    IngresoEmpleado,
    IngresoNomina,
    Nomina,
    PeriodoNomina,
    TipoDescuento,
    TipoIngreso,
)
from usuarios.models import Usuario

CENTRO_NOMBRE = "Colegio Demostrativo Juan Pablo Duarte"
CENTRO_CODIGO = "0001-01"

ANIOS = [(2017, 2018), (2018, 2019), (2019, 2020), (2020, 2021),
         (2021, 2022), (2022, 2023), (2023, 2024), (2024, 2025),
         (2025, 2026)]

# Año escolar activo (coherente con la fecha actual)
ANIO_ACTIVO = (2025, 2026)

# Meses del año académico activo para caja y nómina (sep - jun)
MESES_ACADEMICOS = [(2025, 9), (2025, 10), (2025, 11), (2025, 12),
                    (2026, 1), (2026, 2), (2026, 3), (2026, 4),
                    (2026, 5), (2026, 6)]

CURRICULO = [
    ("Lengua Española", "Lengua Española"),
    ("Lenguas Extranjeras", "Inglés"),
    ("Matemática", "Matemática"),
    ("Ciencias Sociales", "Ciencias Sociales"),
    ("Ciencias de la Naturaleza", "Ciencias de la Naturaleza"),
    ("Educación Artística", "Educación Artística"),
    ("Educación Física", "Educación Física"),
    ("Formación Integral Humana y Religiosa", "Formación Integral Humana y Religiosa"),
]

PASSWORD_ADMIN = "admin123"
PASSWORD_DOCENTE = "docente123"
PASSWORD_ESTUDIANTE = "estudiante123"

# Clave base32 para el 2FA del usuario admin (Google Authenticator, Authy, etc.)
ADMIN_TOTP_SECRET = "JBSWY3DPEHPK3PXP"

NOMBRES_GRADOS = ["1ro", "2do", "3ro", "4to", "5to", "6to"]

# Asignaturas que imparte cada docente
DOCENTES = [
    dict(username="docente", password=PASSWORD_DOCENTE,
         nombre="Carlos", apellido="Méndez", cedula="00100000001",
         codigo="000001", sexo="M", nacimiento=date(1985, 3, 10),
         area="Matemática", salario=32000,
         asignaturas=["Matemática", "Ciencias Sociales"]),
    dict(username="docente2", password=PASSWORD_DOCENTE,
         nombre="Laura", apellido="Fernández", cedula="00100000011",
         codigo="000002", sexo="F", nacimiento=date(1990, 7, 19),
         area="Lengua Española", salario=30000,
         asignaturas=["Lengua Española", "Inglés", "Educación Artística"]),
    dict(username="docente3", password=PASSWORD_DOCENTE,
         nombre="Felipe", apellido="Rojas", cedula="00100000012",
         codigo="000003", sexo="M", nacimiento=date(1988, 11, 5),
         area="Ciencias de la Naturaleza", salario=29000,
         asignaturas=["Ciencias de la Naturaleza", "Educación Física",
                      "Formación Integral Humana y Religiosa"]),
]

ADMINISTRATIVOS = [
    dict(username="director", password=PASSWORD_ADMIN, rol="director",
         nombre="Rosa", apellido="Ventura", cedula="00100000002",
         sexo="F", nacimiento=date(1978, 7, 22), salario=45000,
         fecha_ingreso=date(2010, 1, 15)),
    dict(username="secretaria", password=PASSWORD_ADMIN, rol="secretaria",
         nombre="María", apellido="Santana", cedula="00100000021",
         sexo="F", nacimiento=date(1985, 2, 14), salario=22000,
         fecha_ingreso=date(2015, 8, 1)),
    dict(username="cajero", password=PASSWORD_ADMIN, rol="cajero",
         nombre="Juan", apellido="Castillo", cedula="00100000022",
         sexo="M", nacimiento=date(1992, 9, 8), salario=18000,
         fecha_ingreso=date(2020, 8, 1)),
]

ESTUDIANTES = [
    dict(matricula="20170001", nombres="Ana María", apellidos="Pérez", sexo="F",
         nacimiento=date(2009, 3, 15), modalidad="ciencias_letras"),
    dict(matricula="20200001", nombres="Carmen Elena", apellidos="Duarte", sexo="F",
         nacimiento=date(2013, 9, 12)),
    dict(matricula="20210001", nombres="Luis Carlos", apellidos="Rodríguez", sexo="M",
         nacimiento=date(2014, 8, 10)),
    dict(matricula="20210002", nombres="Pedro Antonio", apellidos="Sánchez", sexo="M",
         nacimiento=date(2014, 2, 2)),
    dict(matricula="20220001", nombres="Juana Isabel", apellidos="Reyes", sexo="F",
         nacimiento=date(2015, 6, 24)),
    dict(matricula="20220002", nombres="José Miguel", apellidos="Santos", sexo="M",
         nacimiento=date(2015, 1, 30)),
    dict(matricula="20230001", nombres="María Fernanda", apellidos="Gómez", sexo="F",
         nacimiento=date(2016, 11, 20)),
    dict(matricula="20240001", nombres="Rosa Amelia", apellidos="Guzmán", sexo="F",
         nacimiento=date(2018, 4, 18)),
    dict(matricula="20240002", nombres="Miguel Ángel", apellidos="Peña", sexo="M",
         nacimiento=date(2010, 10, 5)),
]

# Trayectoria académica: (año_inicio, año_fin, nivel, grado)
TRAYECTORIAS = {
    "20170001": [  # Ana: primaria completa (egresa en 2023)
        (2017, 2018, "primaria", "1ro"),
        (2018, 2019, "primaria", "2do"),
        (2019, 2020, "primaria", "3ro"),
        (2020, 2021, "primaria", "4to"),
        (2021, 2022, "primaria", "5to"),
        (2022, 2023, "primaria", "6to"),
    ],
    "20200001": [  # Carmen
        (2020, 2021, "primaria", "1ro"),
        (2021, 2022, "primaria", "2do"),
        (2022, 2023, "primaria", "3ro"),
        (2023, 2024, "primaria", "4to"),
        (2024, 2025, "primaria", "5to"),
        (2025, 2026, "primaria", "6to"),
    ],
    "20210001": [  # Luis
        (2021, 2022, "primaria", "1ro"),
        (2022, 2023, "primaria", "2do"),
        (2023, 2024, "primaria", "3ro"),
        (2024, 2025, "primaria", "4to"),
        (2025, 2026, "primaria", "5to"),
    ],
    "20210002": [  # Pedro
        (2021, 2022, "primaria", "1ro"),
        (2022, 2023, "primaria", "2do"),
        (2023, 2024, "primaria", "3ro"),
        (2024, 2025, "primaria", "4to"),
        (2025, 2026, "primaria", "5to"),
    ],
    "20220001": [  # Juana
        (2022, 2023, "primaria", "1ro"),
        (2023, 2024, "primaria", "2do"),
        (2024, 2025, "primaria", "3ro"),
        (2025, 2026, "primaria", "4to"),
    ],
    "20220002": [  # José
        (2022, 2023, "primaria", "1ro"),
        (2023, 2024, "primaria", "2do"),
        (2024, 2025, "primaria", "3ro"),
        (2025, 2026, "primaria", "4to"),
    ],
    "20230001": [  # María
        (2023, 2024, "primaria", "1ro"),
        (2024, 2025, "primaria", "2do"),
        (2025, 2026, "primaria", "3ro"),
    ],
    "20240001": [  # Rosa (ingresa este año)
        (2025, 2026, "primaria", "1ro"),
    ],
    "20240002": [  # Miguel (ingresa este año)
        (2025, 2026, "primaria", "6to"),
    ],
}

# Conceptos de caja y cuántos meses pagó cada estudiante (para cuentas por cobrar)
CONCEPTOS_CAJA = [
    ("Inscripción", 5000, False),
    ("Mensualidad", 3000, True),
    ("Transporte", 1500, True),
    ("Merienda", 800, True),
    ("Uniforme", 2500, False),
]

# Estudiante -> {concepto: meses pagados} (los no listados pagan los 10)
PAGOS_INCOMPLETOS = {
    "20240001": {"Mensualidad": 4, "Transporte": 4, "Merienda": 4},
    "20240002": {"Mensualidad": 9},
    "20220001": {"Transporte": 8, "Merienda": 8},
}

DIAS_NO_DOCENCIA = [
    (2025, 11, 24, "Día de la No Violencia contra la Mujer"),
    (2026, 1, 6, "Día de los Santos Reyes"),
    (2026, 2, 27, "Día de la Independencia Nacional"),
    (2026, 4, 2, "Jueves Santo"),
    (2026, 4, 3, "Viernes Santo"),
    (2026, 5, 1, "Día del Trabajador"),
]

USUARIOS_DEMO = (["admin", "director", "secretaria", "cajero"]
                 + [d["username"] for d in DOCENTES]
                 + [e["matricula"] for e in ESTUDIANTES])


def _ultimo_dia(anio, mes):
    return date(anio, mes, calendar.monthrange(anio, mes)[1])


def _redondear(valor):
    return float(Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


class Command(BaseCommand):
    help = "Crea (o recrea) datos de demostración coherentes en todas las tablas"

    def _desconectar_auditoria(self):
        for model in apps.get_models():
            pre_save.disconnect(guardar_estado_anterior, sender=model)
            post_save.disconnect(registrar_guardado, sender=model)
            post_delete.disconnect(registrar_eliminado, sender=model)

    def _reconectar_auditoria(self):
        for model in apps.get_models():
            pre_save.connect(guardar_estado_anterior, sender=model)
            post_save.connect(registrar_guardado, sender=model)
            post_delete.connect(registrar_eliminado, sender=model)

    def _limpiar_centro(self, centro):
        # Detalles de nómina antes que sus padres (FK PROTECT)
        DescuentoNomina.objects.filter(nomina__periodo__centro=centro).delete()
        IngresoNomina.objects.filter(nomina__periodo__centro=centro).delete()
        Nomina.objects.filter(periodo__centro=centro).delete()
        IngresoEmpleado.objects.filter(configuracion__centro=centro).delete()
        DescuentoEmpleado.objects.filter(configuracion__centro=centro).delete()
        ConfiguracionNomina.objects.filter(centro=centro).delete()
        PeriodoNomina.objects.filter(centro=centro).delete()

        # Caja
        Pago.objects.filter(centro=centro).delete()
        Egreso.objects.filter(centro=centro).delete()
        SesionCaja.objects.filter(centro=centro).delete()
        AsignacionConcepto.objects.filter(centro=centro).delete()
        ConceptoPago.objects.filter(centro=centro).delete()
        Caja.objects.filter(centro=centro).delete()

        # Académico / estudiantes / asistencia
        Calificacion.objects.filter(inscripcion__centro=centro).delete()
        AsistenciaEstudiante.objects.filter(inscripcion__centro=centro).delete()
        DiaNoDocencia.objects.filter(centro=centro).delete()
        Acta.objects.filter(centro=centro).delete()
        HistorialAcademico.objects.filter(estudiante__centro=centro).delete()
        DocenteMateria.objects.filter(anio_escolar__centro=centro).delete()
        AsignacionDocente.objects.filter(centro=centro).delete()
        ObservacionEstudiante.objects.filter(estudiante__centro=centro).delete()
        Inscripcion.objects.filter(centro=centro).delete()
        for doc in DocumentoEstudiante.objects.filter(estudiante__centro=centro):
            if doc.archivo:
                doc.archivo.delete(save=False)
        DocumentoEstudiante.objects.filter(estudiante__centro=centro).delete()

        Estudiante.objects.filter(centro=centro).delete()
        Docente.objects.filter(centro=centro).delete()
        Administrativo.objects.filter(centro=centro).delete()
        UsuarioCentro.objects.filter(centro=centro).delete()

        GradoAsignatura.objects.filter(grado__nivel__centro=centro).delete()
        Seccion.objects.filter(centro=centro).delete()
        Grado.objects.filter(nivel__centro=centro).delete()
        Nivel.objects.filter(centro=centro).delete()
        Asignatura.objects.filter(centro=centro).delete()
        Competencia.objects.filter(nivel__centro=centro).delete()
        AreaCurricular.objects.filter(centro=centro).delete()
        PeriodoAnio.objects.filter(anio_escolar__centro=centro).delete()
        Periodo.objects.filter(centro=centro).delete()
        AnioEscolar.objects.filter(centro=centro).delete()
        CentroProveedor.objects.filter(centro=centro).delete()
        ConfiguracionCentro.objects.filter(centro=centro).delete()

        for nombre in ["AFP Crecer", "AFP Popular"]:
            AFP.objects.filter(nombre=nombre).delete()
        for nombre in ["ARS Humano", "ARS Senasa"]:
            ARS.objects.filter(nombre=nombre).delete()
        for nombre in ["Director", "Secretaria", "Cajero", "Docente", "Conserje"]:
            Cargo.objects.filter(nombre=nombre).delete()
        TipoIngreso.objects.filter(nombre__in=["Sueldo", "Bono transporte",
                                               "Horas extra", "Incentivo puntualidad"]).delete()
        TipoDescuento.objects.filter(nombre__in=["AFP", "ARS", "ISR",
                                                 "Préstamo", "Atrasos"]).delete()
        Proveedor.objects.filter(nombre__in=[
            "Papelería La Otra", "Distribuidora de Alimentos", "Servicios de Limpieza",
        ]).delete()

        centro.delete()

    def handle(self, *args, **options):
        self._desconectar_auditoria()
        try:
            self._run()
        finally:
            self._reconectar_auditoria()

    @transaction.atomic
    def _run(self):
        self.stdout.write("Limpiando datos demo previos...")
        for centro_demo in list(
            CentroEducativo.objects.filter(codigo_minerd=CENTRO_CODIGO)
        ):
            self._limpiar_centro(centro_demo)
        Usuario.objects.filter(username__in=USUARIOS_DEMO).delete()
        Bitacora.objects.filter(usuario__username__in=USUARIOS_DEMO).delete()

        # ===================== CORE =====================
        self.stdout.write("Creando centro, configuración y proveedores...")
        centro = CentroEducativo.objects.create(
            nombre=CENTRO_NOMBRE, codigo_minerd=CENTRO_CODIGO,
            direccion="Av. Principal #1", telefono="809-000-0000",
        )
        ConfiguracionCentro.objects.create(
            centro=centro, nota_minima_aprobacion=Decimal("70.00"),
            modulo_asistencia=True, modulo_caja=True, modulo_nomina=True,
            modulo_biblioteca=True, modulo_transporte=True, modulo_reportes=True,
        )
        roles = {}
        for nombre in ["Administrador", "Director", "Secretaria", "Cajero", "Docente"]:
            roles[nombre], _ = RolCentro.objects.get_or_create(nombre=nombre)

        proveedores = {}
        for nombre, contacto in [
            ("Papelería La Otra", "ventas@papeleria.com"),
            ("Distribuidora de Alimentos", "pedidos@distribuidora.com"),
            ("Servicios de Limpieza", "info@limpieza.com"),
        ]:
            proveedores[nombre] = Proveedor.objects.create(nombre=nombre, email=contacto)
            CentroProveedor.objects.create(proveedor=proveedores[nombre], centro=centro)

        # ===================== AÑOS ESCOLARES =====================
        self.stdout.write("Creando años escolares...")
        anios = {}
        for inicio, fin in ANIOS:
            anio = AnioEscolar.objects.create(
                centro=centro, nombre=f"{inicio}-{fin}",
                fecha_inicio=date(inicio, 8, 20), fecha_fin=date(fin, 6, 28),
            )
            anios[(inicio, fin)] = anio
        anio_activo = anios[ANIO_ACTIVO]
        anio_activo.activo = True
        anio_activo.save()

        # ===================== ACADÉMICO =====================
        self.stdout.write("Creando niveles, grados, secciones y currículo...")
        niveles = {}
        grados = {}
        secciones = {
            letra: Seccion.objects.create(centro=centro, nombre=letra)
            for letra in ("A", "B")
        }
        estructura = crear_estructura_minerd(
            centro, ("primaria",)
        )
        for nivel in estructura['niveles']:
            tipo = nivel.tipo
            niveles[tipo] = nivel
            for idx, grado in enumerate(nivel.grado_set.all().order_by('orden')):
                grado.secciones.add(*secciones.values())
                grados[(tipo, NOMBRES_GRADOS[idx])] = grado

        areas = {}
        asignaturas = {}
        for area_nombre, asig_nombre in CURRICULO:
            area = AreaCurricular.objects.create(centro=centro, nombre=area_nombre)
            asignatura = Asignatura.objects.create(centro=centro, nombre=asig_nombre, area=area)
            areas[asig_nombre] = area
            asignaturas[asig_nombre] = asignatura

        # Competencias Fundamentales MINERD por nivel: todas las asignaturas
        # del nivel se califican con las mismas competencias.
        competencias_por_nivel = {}
        for nivel in niveles.values():
            competencias_por_nivel[nivel.id] = [
                Competencia.objects.create(nivel=nivel, nombre=nombre)
                for nombre in COMPETENCIAS_FUNDAMENTALES_MINERD
            ]

        grado_asignaturas = []
        for tipo in ("primaria",):
            for g_nombre in NOMBRES_GRADOS:
                for asignatura in asignaturas.values():
                    grado_asignaturas.append(GradoAsignatura(
                        grado=grados[(tipo, g_nombre)], asignatura=asignatura,
                    ))
        GradoAsignatura.objects.bulk_create(grado_asignaturas)

        self.stdout.write("Creando períodos...")
        # Catálogo de períodos (reutilizable para todos los años)
        periodos_catalogo = [
            Periodo.objects.create(
                centro=centro, nombre=nombre, orden=orden,
            )
            for orden, nombre in enumerate(["P1", "P2", "P3", "P4"], start=1)
        ]
        # Estado por año escolar
        periodos_por_anio = {}
        for anio in anios.values():
            lista = []
            for p in periodos_catalogo:
                PeriodoAnio.objects.create(
                    periodo=p, anio_escolar=anio,
                    activo=anio.activo, cerrado=not anio.activo,
                    fecha_cierre=anio.fecha_fin if not anio.activo else None,
                )
                lista.append(p)
            periodos_por_anio[anio.id] = lista

        # ===================== USUARIOS / PERSONAL =====================
        self.stdout.write("Creando usuarios, docentes y administrativos...")
        admin = Usuario.objects.create_superuser("admin", "admin@demo.com", PASSWORD_ADMIN)
        admin.totp_secret = ADMIN_TOTP_SECRET
        admin.totp_activo = True
        admin.save(update_fields=['totp_secret', 'totp_activo'])
        UsuarioCentro.objects.create(usuario=admin, centro=centro, rol=roles["Administrador"])
        usuarios_demo = [admin]

        docentes = {}
        for datos in DOCENTES:
            usuario = Usuario.objects.create_user(
                datos["username"], f'{datos["username"]}@demo.com', datos["password"]
            )
            usuario.rol = "docente"
            usuario.first_name = datos["nombre"]
            usuario.last_name = datos["apellido"]
            usuario.save()
            docente = Docente.objects.create(
                usuario=usuario, centro=centro,
                primer_nombre=datos["nombre"], primer_apellido=datos["apellido"],
                cedula=datos["cedula"], sexo=datos["sexo"],
                fecha_nacimiento=datos["nacimiento"], nacionalidad="Dominicana",
                direccion=f"Calle {datos['apellido']} #5", telefono="809-555-0100",
                codigo_docente_minerd=datos["codigo"],
                area_especialidad=datos["area"], fecha_ingreso=date(2015, 8, 1),
                tipo_contrato="nombrado", tanda="matutina",
            )
            UsuarioCentro.objects.create(usuario=usuario, centro=centro, rol=roles["Docente"])
            docentes[datos["username"]] = docente
            usuarios_demo.append(usuario)

        docente_por_asignatura = {}
        for datos in DOCENTES:
            for asig in datos["asignaturas"]:
                docente_por_asignatura[asig] = docentes[datos["username"]]

        administrativos = {}
        for datos in ADMINISTRATIVOS:
            usuario = Usuario.objects.create_user(
                datos["username"], f'{datos["username"]}@demo.com', datos["password"]
            )
            usuario.rol = datos["rol"]
            usuario.first_name = datos["nombre"]
            usuario.last_name = datos["apellido"]
            usuario.save()
            adm = Administrativo.objects.create(
                usuario=usuario, centro=centro,
                primer_nombre=datos["nombre"], primer_apellido=datos["apellido"],
                cedula=datos["cedula"], sexo=datos["sexo"],
                fecha_nacimiento=datos["nacimiento"], nacionalidad="Dominicana",
                direccion="Calle Administrativa #3", telefono="809-555-0101",
                cargo=datos["rol"], fecha_ingreso=datos["fecha_ingreso"],
            )
            UsuarioCentro.objects.create(usuario=usuario, centro=centro, rol=roles[datos["rol"].title()])
            administrativos[datos["username"]] = adm
            usuarios_demo.append(usuario)

        secretaria = administrativos["secretaria"]
        cajero_user = administrativos["cajero"].usuario

        self.stdout.write("Creando estudiantes...")
        estudiantes = {}
        for datos in ESTUDIANTES:
            usuario = Usuario.objects.create_user(
                datos["matricula"], f'{datos["matricula"]}@demo.com', PASSWORD_ESTUDIANTE
            )
            usuario.rol = "estudiante"
            usuario.first_name = datos["nombres"].split()[0]
            usuario.last_name = datos["apellidos"].split()[0]
            usuario.save()
            estudiante = Estudiante.objects.create(
                usuario=usuario, centro=centro, matricula=datos["matricula"],
                primer_nombre=datos["nombres"], primer_apellido=datos["apellidos"],
                sexo=datos["sexo"], fecha_nacimiento=datos["nacimiento"],
                lugar_nacimiento="Santo Domingo", nacionalidad="Dominicana",
                direccion="Calle Los Estudiantes #10", telefono="809-555-0102",
                nombre_tutor="Tutor de Prueba", cedula_tutor="00100000003",
                telefono_tutor="809-555-0103", parentesco_tutor="Padre/Madre",
            )
            if datos.get("modalidad"):
                estudiante.modalidad_salida = datos["modalidad"]
                estudiante.save()
            estudiantes[datos["matricula"]] = estudiante
            usuarios_demo.append(usuario)

        # Usuarios demo: no fuerzan cambio de contraseña y su vigencia inicia hoy.
        for usuario_demo in usuarios_demo:
            usuario_demo.debe_cambiar_password = False
            usuario_demo.password_cambiada_en = timezone.now()
            usuario_demo.save(update_fields=['debe_cambiar_password', 'password_cambiada_en'])

        # ===================== NÓMINA: CATÁLOGO Y CONFIGURACIÓN =====================
        self.stdout.write("Creando nómina (catálogo y configuraciones)...")
        afp_crecer = AFP.objects.create(nombre="AFP Crecer")
        afp_popular = AFP.objects.create(nombre="AFP Popular")
        ars_humano = ARS.objects.create(nombre="ARS Humano")
        ars_senasa = ARS.objects.create(nombre="ARS Senasa")

        cargo_director = Cargo.objects.create(nombre="Director")
        Cargo.objects.create(nombre="Secretaria")
        Cargo.objects.create(nombre="Cajero")
        cargo_docente = Cargo.objects.create(nombre="Docente")
        Cargo.objects.create(nombre="Conserje")

        tipo_sueldo = TipoIngreso.objects.create(nombre="Sueldo", obligatorio=True)
        tipo_bono = TipoIngreso.objects.create(nombre="Bono transporte")
        TipoIngreso.objects.create(nombre="Horas extra")
        TipoIngreso.objects.create(nombre="Incentivo puntualidad")

        tipo_afp = TipoDescuento.objects.create(nombre="AFP", porcentaje=Decimal("2.87"),
                                                obligatorio=True)
        tipo_ars = TipoDescuento.objects.create(nombre="ARS", porcentaje=Decimal("3.04"),
                                                obligatorio=True)
        tipo_isr = TipoDescuento.objects.create(nombre="ISR", porcentaje=Decimal("15.00"))
        tipo_prestamo = TipoDescuento.objects.create(nombre="Préstamo", es_porcentaje=False)
        TipoDescuento.objects.create(nombre="Atrasos", es_porcentaje=False)

        empleados = []

        def _config_empleado(usuario, cargo, salario, afp, ars, bono, prestamo=0):
            config = ConfiguracionNomina.objects.create(
                usuario=usuario, centro=centro, cargo=cargo,
                salario_base=Decimal(str(salario)), afp=afp, ars=ars,
                tipo_pago="mensual", activo_nomina=True,
                cuenta_bancaria=f"880-000-00-{len(empleados) + 1:02d}",
                fecha_ingreso=date(2015, 8, 1),
            )
            if bono:
                IngresoEmpleado.objects.create(configuracion=config, tipo=tipo_bono,
                                               monto=Decimal(str(bono)))
            if prestamo:
                DescuentoEmpleado.objects.create(configuracion=config, tipo=tipo_prestamo,
                                                 monto=Decimal(str(prestamo)))
            empleados.append(config)
            return config

        _config_empleado(administrativos["director"].usuario, cargo_director, 45000,
                         afp_crecer, ars_humano, 3000, prestamo=5000)
        _config_empleado(administrativos["secretaria"].usuario, Cargo.objects.get(nombre="Secretaria"),
                         22000, afp_popular, ars_senasa, 1500)
        _config_empleado(administrativos["cajero"].usuario, Cargo.objects.get(nombre="Cajero"),
                         18000, afp_popular, ars_senasa, 1500)
        _config_empleado(docentes["docente"].usuario, cargo_docente, 32000,
                         afp_crecer, ars_humano, 2000, prestamo=2500)
        _config_empleado(docentes["docente2"].usuario, cargo_docente, 30000,
                         afp_popular, ars_humano, 2000)
        _config_empleado(docentes["docente3"].usuario, cargo_docente, 29000,
                         afp_crecer, ars_senasa, 2000)

        # ===================== INSCRIPCIONES Y RENDIMIENTO =====================
        self.stdout.write("Creando inscripciones, calificaciones y asistencia...")
        docentes_materia = []
        asignaciones_docente = []
        calificaciones = []
        asistencias = []
        inscripciones = []

        def _pfs_por_asignatura(inscripcion, anio, rng):
            resultado = {}
            comps = competencias_por_nivel[inscripcion.grado.nivel_id]
            for asig_nombre, area in areas.items():
                asignatura = asignaturas[asig_nombre]
                promedios_periodo = []
                for periodo in periodos_por_anio[anio.id]:
                    notas = [rng.randint(72, 99) for _ in comps]
                    promedios_periodo.append(sum(notas) / len(notas))
                    for comp, nota in zip(comps, notas):
                        calificaciones.append(Calificacion(
                            inscripcion=inscripcion, asignatura=asignatura,
                            competencia=comp, periodo=periodo, nota=Decimal(nota),
                        ))
                resultado[asig_nombre] = sum(promedios_periodo) / len(promedios_periodo)
            return resultado

        vistos_docente_materia = set()
        for matricula, trayecto in TRAYECTORIAS.items():
            estudiante = estudiantes[matricula]
            for idx, (a_i, a_f, tipo, grado_nombre) in enumerate(trayecto):
                anio = anios[(a_i, a_f)]
                grado = grados[(tipo, grado_nombre)]
                seccion = secciones["A" if idx % 2 else "B"]
                cerrado = not anio.activo

                inscripcion = Inscripcion.objects.create(
                    estudiante=estudiante, centro=centro, anio_escolar=anio,
                    grado=grado, seccion=seccion,
                    estado_final="pendiente", fecha_cierre=anio.fecha_fin if cerrado else None,
                )
                inscripciones.append(inscripcion)

                for asig_nombre in areas:
                    clave = (asig_nombre, grado.id, seccion.id, anio.id)
                    if clave in vistos_docente_materia:
                        continue
                    vistos_docente_materia.add(clave)
                    asignatura = asignaturas[asig_nombre]
                    docente = docente_por_asignatura[asig_nombre]
                    docentes_materia.append(DocenteMateria(
                        docente=docente, asignatura=asignatura,
                        grado=grado, seccion=seccion, anio_escolar=anio,
                    ))
                    asignaciones_docente.append(AsignacionDocente(
                        docente=docente, centro=centro, anio_escolar=anio,
                        area=areas[asig_nombre], grado=grado, seccion=seccion,
                    ))

                rng = random.Random(f"{matricula}-{a_i}-{a_f}")
                pfs = _pfs_por_asignatura(inscripcion, anio, rng)
                promedio = sum(pfs.values()) / len(pfs)
                inscripcion.promedio_final = Decimal(str(_redondear(promedio)))
                inscripcion.save()

                fecha_base = anio.fecha_inicio
                for i in range(20):
                    fecha = fecha_base + timedelta(days=5 * i + 1)
                    if fecha > anio.fecha_fin:
                        break
                    estado = "presente"
                    if i % 11 == 0:
                        estado = "justificado"
                    elif i % 9 == 0:
                        estado = "ausente"
                    elif i % 7 == 0:
                        estado = "tardanza"
                    asistencias.append(AsistenciaEstudiante(
                        inscripcion=inscripcion, fecha=fecha, estado=estado,
                        registrada_por=admin,
                    ))

        DocenteMateria.objects.bulk_create(docentes_materia)
        AsignacionDocente.objects.bulk_create(asignaciones_docente)
        Calificacion.objects.bulk_create(calificaciones)
        AsistenciaEstudiante.objects.bulk_create(asistencias)

        # ===================== ACTAS E HISTORIAL (años cerrados) =====================
        self.stdout.write("Generando actas e historial de años cerrados...")
        nota_minima = float(ConfiguracionCentro.objects.get(centro=centro).nota_minima_aprobacion)

        for inscripcion in inscripciones:
            if inscripcion.anio_escolar.activo:
                continue
            boletin = construir_boletin_estudiante(inscripcion, centro, inscripcion.anio_escolar)
            promedios = [a["pf"] for a in boletin.get("asignaturas", []) if a.get("pf") is not None]
            promedio = sum(promedios) / len(promedios) if promedios else None
            tiene_reprobada = any(
                (a.get("pf") or 0) < nota_minima
                for a in boletin.get("asignaturas", [])
                if a.get("pf") is not None
            )
            if not promedios:
                estado = "sin_calificacion"
            elif tiene_reprobada:
                estado = "recuperacion"
            elif promedio >= nota_minima:
                estado = "aprobado"
            else:
                estado = "reprobado"

            inscripcion.estado_final = estado
            if promedio is not None:
                inscripcion.promedio_final = Decimal(str(_redondear(promedio)))
            inscripcion.save()

            boletin["estado_final"] = estado
            boletin["promedio_general"] = promedio
            Acta.objects.update_or_create(
                centro=centro, anio_escolar=inscripcion.anio_escolar,
                estudiante=inscripcion.estudiante,
                defaults={
                    "grado": inscripcion.grado, "seccion": str(inscripcion.seccion),
                    "datos": boletin, "generado_por": admin,
                },
            )
            HistorialAcademico.objects.get_or_create(
                estudiante=inscripcion.estudiante,
                nivel=inscripcion.grado.nivel, grado=inscripcion.grado,
                seccion=inscripcion.seccion, anio_escolar=inscripcion.anio_escolar,
                defaults={"estado": estado, "cerrado": True},
            )

        # ===================== OBSERVACIONES Y DOCUMENTOS =====================
        ObservacionEstudiante.objects.create(
            estudiante=estudiantes["20170001"], tipo="merito", anio_escolar=anio_activo,
            fecha=date(2026, 5, 20),
            descripcion="Excelente rendimiento académico durante el año escolar.",
        )
        ObservacionEstudiante.objects.create(
            estudiante=estudiantes["20170001"], tipo="conducta", anio_escolar=None,
            fecha=date(2026, 5, 20),
            descripcion="Estudiante con excelente comportamiento y disciplina.",
        )
        ObservacionEstudiante.objects.create(
            estudiante=estudiantes["20210001"], tipo="amonestacion", anio_escolar=anio_activo,
            fecha=date(2026, 2, 10),
            descripcion="Retraso en la entrega de tareas durante el segundo período.",
        )

        documentos = [
            (estudiantes["20170001"], "Certificado de Nacimiento",
             "Documento de identidad de Ana María Pérez (copia)."),
            (estudiantes["20210001"], "Acta de Nacimiento",
             "Documento de identidad de Luis Carlos Rodríguez (copia)."),
        ]
        for estudiante, nombre, contenido in documentos:
            doc = DocumentoEstudiante(estudiante=estudiante, nombre=nombre)
            doc.archivo.save(f"documento_{estudiante.matricula}.txt",
                             ContentFile(contenido), save=True)

        # ===================== ASISTENCIA: DÍAS NO DOCENTES =====================
        for anio_d, mes, dia, motivo in DIAS_NO_DOCENCIA:
            DiaNoDocencia.objects.create(
                centro=centro, anio_escolar=anio_activo,
                fecha=date(anio_d, mes, dia), motivo=motivo, registrado_por=admin,
            )

        # ===================== CAJA =====================
        self.stdout.write("Creando caja (conceptos, sesiones, pagos y egresos)...")
        caja = Caja.objects.create(centro=centro, nombre="Caja Principal")

        conceptos = {}
        for nombre, monto, recurrente in CONCEPTOS_CAJA:
            conceptos[nombre] = ConceptoPago.objects.create(
                centro=centro, nombre=nombre, monto=Decimal(str(monto)),
                es_recurrente=recurrente,
            )

        sesiones = {}
        for idx, (a, m) in enumerate(MESES_ACADEMICOS):
            ultimo_abierto = (idx == len(MESES_ACADEMICOS) - 1)
            apertura = date(a, m, 1)
            cierre = _ultimo_dia(a, m)
            sesiones[(a, m)] = SesionCaja.objects.create(
                centro=centro, caja=caja, fecha_apertura=apertura,
                usuario_apertura=cajero_user, monto_inicial=Decimal("5000"),
                nota_apertura=f"Apertura {a}-{m:02d}",
                estado="abierta" if ultimo_abierto else "cerrada",
                fecha_cierre=None if ultimo_abierto else cierre,
                usuario_cierre=None if ultimo_abierto else cajero_user,
                nota_cierre="" if ultimo_abierto else f"Cierre {a}-{m:02d}",
            )

        # Asignación de conceptos recurrentes (año activo)
        primaria_ids = {
            e["matricula"] for e in ESTUDIANTES
            if TRAYECTORIAS[e["matricula"]][-1][2] == "primaria"
        }
        asignaciones = []
        for matricula, estudiante in estudiantes.items():
            es_primaria = matricula in primaria_ids
            for concepto_nombre, es_primaria_requerido in [
                ("Mensualidad", False), ("Transporte", True), ("Merienda", True),
            ]:
                if es_primaria_requerido and not es_primaria:
                    continue
                asignaciones.append(AsignacionConcepto(
                    centro=centro, estudiante=estudiante, concepto=conceptos[concepto_nombre],
                    anio_escolar=anio_activo,
                ))
        AsignacionConcepto.objects.bulk_create(asignaciones)

        # Pagos
        pagos = []
        recibo = 1
        for matricula, estudiante in estudiantes.items():
            es_primaria = matricula in primaria_ids
            incompletos = PAGOS_INCOMPLETOS.get(matricula, {})

            # Inscripción (única, en septiembre)
            pagos.append(Pago(
                centro=centro, sesion=sesiones[(2025, 9)], estudiante=estudiante,
                concepto=conceptos["Inscripción"], monto=conceptos["Inscripción"].monto,
                metodo_pago="efectivo", fecha=date(2025, 9, 5), recibo=recibo,
                creado_por=cajero_user,
            ))
            recibo += 1

            for concepto_nombre, es_primaria_requerido in [
                ("Mensualidad", False), ("Transporte", True), ("Merienda", True),
            ]:
                if es_primaria_requerido and not es_primaria:
                    continue
                pagados = incompletos.get(concepto_nombre, 10)
                for idx, (a, m) in enumerate(MESES_ACADEMICOS):
                    if idx >= pagados:
                        break
                    pagos.append(Pago(
                        centro=centro, sesion=sesiones[(a, m)], estudiante=estudiante,
                        concepto=conceptos[concepto_nombre],
                        monto=conceptos[concepto_nombre].monto,
                        metodo_pago="efectivo", fecha=date(a, m, 5), recibo=recibo,
                        creado_por=cajero_user,
                    ))
                    recibo += 1
        Pago.objects.bulk_create(pagos)

        # Egresos mensuales
        egresos = []
        recibo_e = 1
        egresos_mensuales = [
            (2025, 9, "Materiales de papelería", "Papelería La Otra", 2500),
            (2025, 10, "Servicio de limpieza", "Servicios de Limpieza", 1200),
            (2025, 11, "Factura de electricidad", "EDE Este", 4500),
            (2025, 12, "Mantenimiento de equipos", "Técnicos Rápidos", 6000),
            (2026, 1, "Factura de electricidad", "EDE Este", 4200),
            (2026, 2, "Materiales de papelería", "Papelería La Otra", 1800),
            (2026, 3, "Factura de electricidad", "EDE Este", 4400),
            (2026, 4, "Servicio de limpieza", "Servicios de Limpieza", 1500),
            (2026, 5, "Mantenimiento de equipos", "Técnicos Rápidos", 3500),
            (2026, 6, "Refrigerios para evaluación", "Distribuidora de Alimentos", 2000),
        ]
        for a, m, concepto, beneficiario, monto in egresos_mensuales:
            egresos.append(Egreso(
                centro=centro, sesion=sesiones[(a, m)], concepto=concepto,
                beneficiario=beneficiario, monto=Decimal(str(monto)),
                metodo_pago="cheque", fecha=date(a, m, 20), recibo=recibo_e,
                nota=f"Egreso de {a}-{m:02d}", creado_por=cajero_user,
            ))
            recibo_e += 1
        Egreso.objects.bulk_create(egresos)

        for (a, m), sesion in sesiones.items():
            if sesion.estado == "cerrada":
                sesion.arqueo = sesion.saldo_esperado()
                sesion.diferencia = Decimal("0")
                sesion.save(update_fields=["arqueo", "diferencia"])

        # ===================== NÓMINA: PERÍODOS Y NÓMINAS =====================
        self.stdout.write("Generando nóminas de los últimos meses...")
        periodos_nomina = []
        for idx, (a, m) in enumerate(MESES_ACADEMICOS):
            ultimo_abierto = (idx == len(MESES_ACADEMICOS) - 1)
            fin = _ultimo_dia(a, m)
            periodos_nomina.append(PeriodoNomina.objects.create(
                centro=centro, anio=a, mes=m, numero_periodo=1,
                descripcion=f"Nómina {m:02d}-{a}",
                fecha_inicio=date(a, m, 1), fecha_fin=fin, fecha_pago=fin,
                cerrado=not ultimo_abierto, nomina_generada=not ultimo_abierto,
            ))

        nominas = []
        ingresos_nomina = []
        descuentos_nomina = []
        for periodo in periodos_nomina:
            cerrado = periodo.cerrado
            for config in empleados:
                salario = float(config.salario_base)
                ingresos = [(tipo_sueldo, "Sueldo base", salario)]
                for fijo in config.ingresos_fijos.all():
                    ingresos.append((fijo.tipo, f"Bono: {fijo.tipo.nombre}", float(fijo.monto)))
                descuentos = [
                    (tipo_afp, "AFP", _redondear(salario * 2.87 / 100)),
                    (tipo_ars, "ARS", _redondear(salario * 3.04 / 100)),
                ]
                if salario > 34623:
                    descuentos.append((tipo_isr, "ISR", _redondear((salario - 34623) * 0.15)))
                for fijo in config.descuentos_fijos.all():
                    descuentos.append((fijo.tipo, f"Préstamo: {fijo.tipo.nombre}", float(fijo.monto)))

                total_i = _redondear(sum(m for _, _, m in ingresos))
                total_d = _redondear(sum(m for _, _, m in descuentos))
                nomina = Nomina.objects.create(
                    periodo=periodo, usuario=config.usuario, configuracion=config,
                    salario_base=config.salario_base, total_ingresos=Decimal(str(total_i)),
                    total_descuentos=Decimal(str(total_d)),
                    neto_pagar=Decimal(str(_redondear(total_i - total_d))),
                    estado="PAGADA" if cerrado else "GENERADA",
                    pagado=cerrado,
                    fecha_pago=periodo.fecha_pago if cerrado else None,
                    generado_por=admin,
                )
                nominas.append(nomina)
                for tipo, descripcion, monto in ingresos:
                    ingresos_nomina.append(IngresoNomina(
                        nomina=nomina, tipo=tipo, descripcion=descripcion,
                        monto=Decimal(str(monto)),
                    ))
                for tipo, descripcion, monto in descuentos:
                    descuentos_nomina.append(DescuentoNomina(
                        nomina=nomina, tipo=tipo, descripcion=descripcion,
                        monto=Decimal(str(monto)),
                    ))
        IngresoNomina.objects.bulk_create(ingresos_nomina)
        DescuentoNomina.objects.bulk_create(descuentos_nomina)

        # ===================== BITÁCORA =====================
        Bitacora.objects.create(usuario=admin, accion="LOGIN", modulo="AUTH",
                                descripcion="Inicio de sesión del superadmin",
                                modelo="USUARIO", objeto_id=str(admin.id),
                                ip="127.0.0.1", ruta="/", metodo="POST",
                                navegador="Datos demo", tipo_dispositivo="PC", riesgo="BAJO")
        Bitacora.objects.create(usuario=administrativos["director"].usuario, accion="LOGIN",
                                modulo="AUTH", descripcion="Inicio de sesión de la dirección",
                                modelo="USUARIO",
                                objeto_id=str(administrativos["director"].usuario.id),
                                ip="127.0.0.1", ruta="/", metodo="POST",
                                navegador="Datos demo", tipo_dispositivo="PC", riesgo="BAJO")
        Bitacora.objects.create(usuario=admin, accion="CREAR", modulo="ESTUDIANTES",
                                descripcion="Alta de estudiantes desde la carga inicial",
                                modelo="ESTUDIANTE",
                                objeto_id=str(estudiantes["20170001"].id),
                                ip="127.0.0.1", ruta="/estudiantes/crear/", metodo="POST",
                                navegador="Datos demo", tipo_dispositivo="PC", riesgo="MEDIO")
        Bitacora.objects.create(usuario=cajero_user, accion="CREAR", modulo="CAJA",
                                descripcion="Cobro de mensualidades de septiembre",
                                modelo="PAGO", objeto_id="1",
                                ip="127.0.0.1", ruta="/caja/registrar-pago/", metodo="POST",
                                navegador="Datos demo", tipo_dispositivo="PC", riesgo="MEDIO")
        Bitacora.objects.create(usuario=admin, accion="EXPORTAR", modulo="REPORTES",
                                descripcion="Exportación de matrícula por grado",
                                modelo=None, objeto_id=None,
                                ip="127.0.0.1", ruta="/administracion/reportes/", metodo="GET",
                                navegador="Datos demo", tipo_dispositivo="PC", riesgo="BAJO")

        # ===================== RESUMEN =====================
        self.stdout.write(self.style.SUCCESS("¡Datos demo creados!"))
        self.stdout.write(f"  Centro: {centro.nombre} ({centro.codigo_minerd})")
        self.stdout.write("  Usuarios: admin/admin123, director/admin123, "
                          "secretaria/admin123, cajero/admin123, docente/docente123, "
                          "docente2/docente123, docente3/docente123")
        self.stdout.write(f"  2FA admin: clave {ADMIN_TOTP_SECRET} "
                          "(agrégala en Google Authenticator / Authy)")
        for est in estudiantes.values():
            self.stdout.write(f"  Estudiante: {est.matricula}/{PASSWORD_ESTUDIANTE} "
                              f"({est.nombre_completo()}) id={est.id}")
        self.stdout.write(
            f"  Récord de Ana: /estudiantes/{estudiantes['20170001'].id}/kardex/imprimir/"
        )
        self.stdout.write("  Año activo: 2025-2026 · Caja: Caja Principal · "
                          "10 períodos de nómina generados")
