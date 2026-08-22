import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from datetime import time as dtime
from django.db import transaction

from core.models import CentroEducativo, AnioEscolar, ConfiguracionCentro, RolCentro, UsuarioCentro
from usuarios.models import Usuario
from academico.models import (
    Nivel, Grado, Seccion, AreaCurricular, Asignatura, GradoAsignatura,
    Competencia, Periodo, PeriodoAnio, FranjaHoraria, DocenteMateria,
)
from docentes.models import Docente
from administracion.models import Administrativo
from tutores.models import Tutor
from estudiantes.models import Estudiante, Inscripcion, HistorialClinicoEstudiante
from entrenamiento.models import TramoEdad, DestrezaCognitiva, UnidadEntrenamiento, Ejercicio
from nomina.models import AFP, ARS, Cargo, TipoIngreso, TipoDescuento
from caja.models import Caja, ConceptoPago

NOMBRES_M = [
    "Carlos", "Miguel", "Juan", "Pedro", "Luis", "Jose", "Antonio",
    "Francisco", "Manuel", "Rafael", "Diego", "Andres", "Santiago",
    "Gabriel", "Daniel", "Sebastian", "Mateo", "Nicolas", "Alejandro",
    "Adrian", "Elias", "Isaac", "Samuel", "Daniel", "Matthew",
]
NOMBRES_F = [
    "Maria", "Ana", "Laura", "Carmen", "Rosa", "Isabel", "Teresa",
    "Patricia", "Claudia", "Lucia", "Sofia", "Valentina", "Camila",
    "Daniela", "Paula", "Gabriela", "Andrea", "Carolina", "Fernanda",
    "Ximena", "AnaMaria", "Liz", "Nathalie", "Katherine", "Yomaira",
]
APELLIDOS = [
    "Garcia", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Perez", "Sanchez", "Ramirez", "Torres", "Flores", "Rivera",
    "Gomez", "Diaz", "Cruz", "Morales", "Reyes", "Ortiz", "Gutierrez",
    "Chavez", "Ramos", "Ruiz", "Alvarez", "Mendoza", "Arias",
]


class Command(BaseCommand):
    help = "Genera datos iniciales de prueba para el colegio"

    def add_arguments(self, parser):
        parser.add_argument("--clean", action="store_true", help="Eliminar datos antes de crear")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["clean"]:
            self.stdout.write("Limpiando datos...")
            for m in [
                Inscripcion, Estudiante, HistorialClinicoEstudiante,
                Docente, Administrativo, Tutor,
                Ejercicio, UnidadEntrenamiento, DestrezaCognitiva, TramoEdad,
                GradoAsignatura, Competencia, PeriodoAnio, Periodo,
                FranjaHoraria, Seccion, Grado, Nivel,
                DocenteMateria, Asignatura, AreaCurricular,
                AnioEscolar, ConfiguracionCentro, CentroEducativo,
                Usuario,
                AFP, ARS, Cargo, TipoIngreso, TipoDescuento,
                Caja, ConceptoPago,
                RolCentro, UsuarioCentro,
            ]:
                m.objects.all().delete()
            self.stdout.write(self.style.WARNING("Datos eliminados."))

        self.stdout.write(self.style.SUCCESS("Creando datos iniciales..."))
        self._create_catalogs()
        self._create_users_and_staff()
        self._create_academic_structure()
        self._create_students()
        self._create_training()
        self._create_payroll_catalogs()
        self._create_caja_catalogs()
        self.stdout.write(self.style.SUCCESS("Datos iniciales creados correctamente."))

    # ─────────────────────── TIER 1: Catálogos puros ───────────────────────

    def _create_catalogs(self):
        self.centro, _ = CentroEducativo.objects.get_or_create(
            codigo_minerd="MIN-001",
            defaults={
                "nombre": "Colegio Favorito",
                "direccion": "Calle 1 #23, Santo Domingo",
                "telefono": "809-555-1234",
                "email": "info@colegiofavorito.edu.do",
                "activo": True,
            },
        )
        self.anio, _ = AnioEscolar.objects.get_or_create(
            centro=self.centro,
            nombre="2025-2026",
            defaults={
                "fecha_inicio": date(2025, 8, 25),
                "fecha_fin": date(2026, 6, 30),
                "activo": True,
            },
        )
        ConfiguracionCentro.objects.get_or_create(
            centro=self.centro,
            defaults={
                "nota_minima_aprobacion": Decimal("70.00"),
                "tipo_pago_nomina": "mensual",
                "modulo_caja": True,
                "modulo_nomina": True,
                "modulo_asistencia": True,
            },
        )
        self.rol_director, _ = RolCentro.objects.get_or_create(nombre="Director")
        self.rol_secretaria, _ = RolCentro.objects.get_or_create(nombre="Secretaria")
        self.rol_docente, _ = RolCentro.objects.get_or_create(nombre="Docente")
        self.rol_tutor, _ = RolCentro.objects.get_or_create(nombre="Tutor")
        self.stdout.write(f"  Centro: {self.centro.nombre} | Año: {self.anio.nombre}")

    # ─────────────────────── TIER 2: Usuarios y Personal ───────────────────────

    def _create_users_and_staff(self):
        self.usuarios = {}

        def make_user(username, email, nombre, apellido, rol, center=True, password="test1234"):
            if Usuario.objects.filter(username=username).exists():
                u = Usuario.objects.get(username=username)
            else:
                u = Usuario.objects.create_user(username=username, email=email, password=password)
                u.first_name = nombre
                u.last_name = apellido
                u.rol = rol
                u.save(update_fields=["first_name", "last_name", "rol"])
                if center:
                    rol_map = {
                        "director": self.rol_director,
                        "secretaria": self.rol_secretaria,
                        "docente": self.rol_docente,
                        "tutor": self.rol_tutor,
                    }
                    UsuarioCentro.objects.get_or_create(
                        usuario=u, centro=self.centro,
                        defaults={"rol": rol_map.get(rol, self.rol_director)},
                    )
            self.usuarios[username] = u
            return u

        make_user("director",    "director@colegio.edu.do",    "Roberto",  "Mendez",     "director")
        make_user("secretaria",  "secretaria@colegio.edu.do",  "Gloria",   "Santos",     "secretaria")
        make_user("admin",       "admin@colegio.edu.do",       "Teresa",   "Rios",       "admin", center=False)
        make_user("superadmin",  "super@colegio.edu.do",       "Manuel",   "Cruz",       "superadmin", center=False)

        # Configurar 2FA para admin/superadmin (coincide con USUARIOS.md)
        for username in ["admin", "superadmin"]:
            u = self.usuarios[username]
            u.totp_secret = "JBSWY3DPEHPK3PXP"
            u.totp_activo = True
            u.save(update_fields=["totp_secret", "totp_activo"])

        # Registros Administrativo para director y secretaria (requiere _asignar_centro_sesion)
        for username, cargo, ced in [("director","director","001-0501001-01"),("secretaria","secretaria","001-0501002-02")]:
            u = self.usuarios[username]
            Administrativo.objects.get_or_create(
                usuario=u,
                defaults={
                    "centro": self.centro,
                    "primer_nombre": u.first_name,
                    "primer_apellido": u.last_name,
                    "cedula": ced,
                    "sexo": "M",
                    "fecha_nacimiento": date(1980, 1, 1),
                    "nacionalidad": "Dominicana",
                    "direccion": "Calle Principal, Santo Domingo",
                    "telefono": "809-555-0001",
                    "cargo": cargo,
                    "fecha_ingreso": date(2020, 9, 1),
                    "estado": "activo",
                },
            )

        # Docentes
        datos_docentes = [
            ("Juan",  "Perez",    "docente1", "docente1@colegio.edu.do", "Matematica"),
            ("Laura", "Garcia",   "docente2", "docente2@colegio.edu.do", "Ciencias"),
            ("Pedro", "Rodriguez","docente3", "docente3@colegio.edu.do", "Ingles"),
            ("Ana",   "Lopez",    "docente4", "docente4@colegio.edu.do", "Espanol"),
            ("Luis",  "Martinez", "docente5", "docente5@colegio.edu.do", "Historia"),
        ]
        self.docentes = []
        for i, (nom, ape, user, email, esp) in enumerate(datos_docentes):
            u = make_user(user, email, nom, ape, "docente")
            doc, _ = Docente.objects.get_or_create(
                usuario=u,
                defaults={
                    "centro": self.centro,
                    "cedula": f"001-050{1000+i}-00{10+i}",
                    "primer_nombre": nom,
                    "primer_apellido": ape,
                    "sexo": "M" if nom in NOMBRES_M else "F",
                    "fecha_nacimiento": date(1980+i, 6, 15),
                    "nacionalidad": "Dominicana",
                    "direccion": f"Calle {10+i} # {20+i}, Santo Domingo",
                    "telefono": f"809-555-{1000+i}",
                    "correo_personal": email,
                    "codigo_docente_minerd": f"DOC-{100+i}",
                    "area_especialidad": esp,
                    "fecha_ingreso": date(2020, 9, 1),
                    "tipo_contrato": "nombrado",
                    "tanda": "matutina",
                    "estado": "activo",
                },
            )
            self.docentes.append(doc)
        self.stdout.write(f"  Usuarios: {Usuario.objects.count()} | Docentes: {len(self.docentes)}")

    # ─────────────────────── TIER 3: Estructura Académica ───────────────────────

    def _create_academic_structure(self):
        # Secciones
        self.secciones = []
        for letra in ["A", "B", "C"]:
            s, _ = Seccion.objects.get_or_create(centro=self.centro, nombre=letra)
            self.secciones.append(s)

        # Niveles y Grados (Primaria y Secundaria)
        self.grados = []
        for tipo, grados_info in [
            ("primaria", [("1ro Primaria",1,1),("2do Primaria",2,1),("3ro Primaria",3,1),("4to Primaria",4,1),("5to Primaria",5,1),("6to Primaria",6,1)]),
            ("secundaria", [("1ro Secundaria",7,1),("2do Secundaria",8,1),("3ro Secundaria",9,1),("4to Secundaria",10,1)]),
        ]:
            nivel, _ = Nivel.objects.get_or_create(centro=self.centro, tipo=tipo, defaults={"nombre": tipo.title()})
            for nombre, orden, ciclo in grados_info:
                g, _ = Grado.objects.get_or_create(nivel=nivel, nombre=nombre, defaults={"orden": orden, "ciclo": ciclo})
                g.secciones.set(self.secciones)
                self.grados.append(g)

        # Áreas y Asignaturas
        self.asignaturas = {}
        areas_data = {
            "Matematicas": ["Matematicas", "Algebra", "Geometria"],
            "Ciencias": ["Ciencias Naturales", "Biologia", "Fisica", "Quimica"],
            "Lenguaje": ["Espanol", "Literatura"],
            "Sociales": ["Historia", "Geografia", "Educacion Civic"],
            "Ingles": ["Ingles"],
            "Educacion Fisica": ["Educacion Fisica"],
            "Arte": ["Arte y Cultura"],
            "Tecnologia": ["Informatica"],
            "Religion": ["Religion"],
        }
        for area_nombre, asignaturas_nombres in areas_data.items():
            area, _ = AreaCurricular.objects.get_or_create(centro=self.centro, nombre=area_nombre)
            for asig_nombre in asignaturas_nombres:
                asig, _ = Asignatura.objects.get_or_create(centro=self.centro, nombre=asig_nombre, defaults={"area": area})
                self.asignaturas[asig_nombre] = asig

        # Asignar asignaturas a grados
        for g in self.grados:
            for asig in self.asignaturas.values():
                GradoAsignatura.objects.get_or_create(grado=g, asignatura=asig)

        # Competencias por nivel
        for nivel in Nivel.objects.filter(centro=self.centro):
            for i, comp_nombre in enumerate(["Lectura comprensiva", "Expresion oral", "Pensamiento critico", "Resolucion de problemas"], 1):
                Competencia.objects.get_or_create(
                    nivel=nivel, nombre=comp_nombre,
                    defaults={"orden": i, "activo": True},
                )

        # Periodos
        periodos_data = [
            ("1er Periodo", 1, False),
            ("2do Periodo", 2, False),
            ("3er Periodo", 3, False),
            ("4to Periodo", 4, True),  # completivo
        ]
        for nombre, orden, es_comp in periodos_data:
            p, _ = Periodo.objects.get_or_create(centro=self.centro, nombre=nombre, defaults={"orden": orden, "es_completivo": es_comp})
            PeriodoAnio.objects.get_or_create(periodo=p, anio_escolar=self.anio)

        # Franjas horarias
        self.franjas = []
        horas = [
            ("1ra hora",  7,0, 7,45,1), ("2da hora",  7,45, 8,30,2),
            ("3ra hora",  8,30, 9,15,3), ("4ta hora",  9,15,10,0,4),
            ("5ta hora", 10,0, 10,45,5), ("6ta hora", 10,45,11,30,6),
            ("7ma hora", 11,30,12,15,7), ("8va hora", 12,15,13,0,8),
        ]
        for nombre, h1,m1, h2,m2, orden in horas:
            fr, _ = FranjaHoraria.objects.get_or_create(
                centro=self.centro, nombre=nombre,
                defaults={"hora_inicio": dtime(h1,m1), "hora_fin": dtime(h2,m2), "orden": orden},
            )
            self.franjas.append(fr)

        # Asignar docentes a materias/grados/secciones (unique by asignatura+grado+seccion+anio)
        asig_list = list(self.asignaturas.values())
        combo_idx = 0
        for g in self.grados:
            for s in self.secciones:
                asig = asig_list[combo_idx % len(asig_list)]
                doc = self.docentes[combo_idx % len(self.docentes)]
                DocenteMateria.objects.get_or_create(
                    docente=doc, asignatura=asig, grado=g, seccion=s,
                    anio_escolar=self.anio,
                )
                combo_idx += 1

        self.stdout.write(f"  Secciones: {len(self.secciones)} | Grados: {len(self.grados)} | Asignaturas: {len(self.asignaturas)}")

    # ─────────────────────── TIER 4: Estudiantes ───────────────────────

    def _create_students(self):
        self.estudiantes = []
        for i in range(30):
            sexo = random.choice(["M", "F"])
            nombre = random.choice(NOMBRES_M if sexo == "M" else NOMBRES_F)
            apellido = random.choice(APELLIDOS)
            segundo_nombre = random.choice([""] + (NOMBRES_M if sexo == "M" else NOMBRES_F))
            segundo_apellido = random.choice([""] + APELLIDOS)
            matricula = f"EST-{2025}-{i+1:04d}"
            fecha_nac = date(random.randint(2012, 2018), random.randint(1,12), random.randint(1,28))

            nombre_completo = f"{nombre} {segundo_nombre}".strip()
            user, created = Usuario.objects.get_or_create(
                username=matricula,
                defaults={
                    "email": f"{matricula.lower()}@estudiante.edu.do",
                    "first_name": nombre_completo,
                    "last_name": apellido,
                    "rol": "estudiante",
                },
            )
            if created:
                user.set_password("test1234")
                user.save(update_fields=["password"])

            est, _ = Estudiante.objects.get_or_create(
                matricula=matricula,
                defaults={
                    "usuario": user,
                    "centro": self.centro,
                    "primer_nombre": nombre,
                    "segundo_nombre": segundo_nombre or None,
                    "primer_apellido": apellido,
                    "segundo_apellido": segundo_apellido or None,
                    "sexo": sexo,
                    "fecha_nacimiento": fecha_nac,
                    "lugar_nacimiento": "Santo Domingo",
                    "nacionalidad": "Dominicana",
                    "direccion": f"Calle {random.randint(1,200)} # {random.randint(1,100)}, Santo Domingo",
                    "nombre_tutor": f"{random.choice(NOMBRES_M if random.random()>0.5 else NOMBRES_F)} {random.choice(APELLIDOS)}",
                    "cedula_tutor": f"001-05{random.randint(10000,99999)}-{random.randint(10,99)}",
                    "telefono_tutor": f"809-555-{random.randint(1000,9999)}",
                    "parentesco_tutor": random.choice(["padre", "madre"]),
                    "estado": "activo",
                },
            )

            grado = random.choice(self.grados[:6])  # primaria
            seccion = random.choice(self.secciones)
            Inscripcion.objects.get_or_create(
                estudiante=est,
                anio_escolar=self.anio,
                defaults={
                    "centro": self.centro,
                    "grado": grado,
                    "seccion": seccion,
                    "estado_final": "pendiente",
                },
            )

            HistorialClinicoEstudiante.objects.get_or_create(
                estudiante=est,
                defaults={
                    "grupo_sanguineo": random.choice(["A+","A-","B+","B-","O+","O-","AB+","desconocido"]),
                    "alergias": random.choice(["", "Polen", "Penicilina", "Mariscos"]),
                    "condiciones_medicas": random.choice(["", "Asma", "Ninguna"]),
                    "observaciones": "",
                },
            )
            self.estudiantes.append(est)

        self.stdout.write(f"  Estudiantes: {len(self.estudiantes)} | Inscripciones: {Inscripcion.objects.filter(anio_escolar=self.anio).count()}")

    # ─────────────────────── TIER 5: Entrenamiento cognitivo ───────────────────────

    def _create_training(self):
        tramos_data = [
            ("Infantil", 5, 7, 1),
            ("Primario Bajo", 8, 9, 2),
            ("Primario Alto", 10, 11, 3),
            ("Secundario", 12, 15, 4),
        ]
        self.tramos = []
        for nombre, emin, emax, orden in tramos_data:
            t, _ = TramoEdad.objects.get_or_create(
                edad_min=emin, edad_max=emax,
                defaults={"nombre": nombre, "orden": orden, "activo": True},
            )
            self.tramos.append(t)

        destrezas_data = {
            "atencion":       ["Atencion sostenida", "Atencion selectiva", "Atencion dividida"],
            "memoria":        ["Memoria a corto plazo", "Memoria de trabajo", "Memoria visual"],
            "lectura":        ["Fluidez lectora", "Lectura en voz alta"],
            "logica":         ["Razonamiento logico", "Resolucion de problemas"],
            "comprension":    ["Comprension literal", "Comprension inferencial"],
            "metacognicion":  ["Autorregulacion", "Pensamiento critico"],
        }
        self.destrezas = {}
        for tramo in self.tramos:
            self.destrezas[tramo.nombre] = []
            for cat, nombres in destrezas_data.items():
                for nombre in nombres:
                    d, _ = DestrezaCognitiva.objects.get_or_create(
                        tramo=tramo, nombre=nombre,
                        defaults={"categoria": cat, "descripcion": f"Destreza de {cat} para tramo {tramo.nombre}", "orden": 1, "activo": True},
                    )
                    self.destrezas[tramo.nombre].append(d)

        self.unidades = []
        self.ejercicios = []
        for tramo in self.tramos:
            for num in range(1, 4):
                u, _ = UnidadEntrenamiento.objects.get_or_create(
                    tramo=tramo, numero=num,
                    defaults={"nombre": f"Unidad {num} - {tramo.nombre}", "activo": True},
                )
                u.destrezas.set(self.destrezas[tramo.nombre][:3])
                self.unidades.append(u)

                for d in self.destrezas[tramo.nombre][:3]:
                    for diff in [1, 2]:
                        tipo = random.choice(["seleccion","verdadero_falso","completar"])
                        ej, _ = Ejercicio.objects.get_or_create(
                            unidad=u, destreza=d,
                            defaults={
                                "tipo": tipo,
                                "dificultad": diff,
                                "enunciado": f"Ejercicio {tipo} - {d.nombre} (Dificultad {diff})",
                                "texto": f"Texto de ejemplo para {d.nombre}" if tipo == "comprension" else "",
                                "opciones": ["A) Opcion 1", "B) Opcion 2", "C) Opcion 3"],
                                "respuesta_correcta": "A) Opcion 1",
                                "tiempo_max_seg": 60,
                                "activo": True,
                            },
                        )
                        self.ejercicios.append(ej)

        self.stdout.write(f"  Tramos: {len(self.tramos)} | Unidades: {len(self.unidades)} | Ejercicios: {len(self.ejercicios)}")

    # ─────────────────────── TIER 6: Nómina catálogos ───────────────────────

    def _create_payroll_catalogs(self):
        for nombre, pe, emp in [
            ("AFP Confiamas", Decimal("2.87"), Decimal("7.10")),
            ("AFP Siembra",  Decimal("2.87"), Decimal("7.10")),
        ]:
            AFP.objects.get_or_create(nombre=nombre, defaults={"porcentaje_empleado": pe, "porcentaje_empresa": emp, "activo": True})

        for nombre, pe, emp in [
            ("ARS Universal",  Decimal("3.04"), Decimal("7.09")),
            ("ARS Palic",      Decimal("3.04"), Decimal("7.09")),
        ]:
            ARS.objects.get_or_create(nombre=nombre, defaults={"porcentaje_empleado": pe, "porcentaje_empresa": emp, "activo": True})

        for nombre in ["Director", "Secretaria", "Docente", "Cajero", "Tecnico de Sistemas"]:
            Cargo.objects.get_or_create(nombre=nombre, defaults={"activo": True})

        for nombre in ["Salario Base", "Bono Transporte", "Bono Alimentacion", "Horas Extras"]:
            TipoIngreso.objects.get_or_create(nombre=nombre, defaults={"activo": True})

        for nombre, porcentaje in [
            ("TSS (AFP)", Decimal("2.87")),
            ("SFS (ARS)", Decimal("3.04")),
            ("ISR", Decimal("0.00")),
        ]:
            TipoDescuento.objects.get_or_create(
                nombre=nombre,
                defaults={"porcentaje": porcentaje, "es_porcentaje": True, "obligatorio": True, "activo": True},
            )
        self.stdout.write(f"  AFP: {AFP.objects.count()} | ARS: {ARS.objects.count()} | Cargos: {Cargo.objects.count()}")

    # ─────────────────────── TIER 7: Caja catálogos ───────────────────────

    def _create_caja_catalogs(self):
        Caja.objects.get_or_create(
            centro=self.centro, nombre="Caja Principal",
            defaults={"activa": True},
        )
        for nombre, monto in [
            ("Mensualidad", Decimal("5500.00")),
            ("Matricula",   Decimal("3000.00")),
            ("Uniforme",    Decimal("1500.00")),
            ("Material Didactico", Decimal("800.00")),
            ("Transporte",  Decimal("1200.00")),
            ("Certificado", Decimal("500.00")),
        ]:
            ConceptoPago.objects.get_or_create(
                centro=self.centro, nombre=nombre,
                defaults={"monto": monto, "es_recurrente": nombre == "Mensualidad", "activo": True},
            )
        self.stdout.write(f"  Cajas: {Caja.objects.count()} | Conceptos: {ConceptoPago.objects.count()}")
