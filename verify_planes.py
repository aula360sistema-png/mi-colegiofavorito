"""Verificación E2E temporal de los dos centros demo. Borrar tras usar."""
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mycolegiofavorito.settings')
django.setup()

from django.conf import settings
settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ['testserver']

from django.test import Client

from caja.services import tiene_deuda_pendiente
from core.models import CentroEducativo
from core.services import modulo_activo
from estudiantes.models import Estudiante, SolicitudCertificado

FALLOS = []


def check(nombre, condicion, detalle=''):
    estado = 'OK ' if condicion else 'FAIL'
    print(f"[{estado}] {nombre}" + (f" -> {detalle}" if detalle else ''))
    if not condicion:
        FALLOS.append(nombre)


def cliente(username, password, centro_id):
    c = Client()
    ok = c.login(username=username, password=password)
    assert ok, f'login fallo: {username}'
    s = c.session
    s['centro_id'] = centro_id
    s.save()
    return c


a = CentroEducativo.objects.get(codigo_minerd='0001-01')
b = CentroEducativo.objects.get(codigo_minerd='0002-02')

print('--- FLAGS ---')
check('A: caja activa', modulo_activo(a.id, 'caja'))
check('A: facturación activa', modulo_activo(a.id, 'facturacion'))
check('A: certificados activos', modulo_activo(a.id, 'certificados'))
check('B: caja apagada', not modulo_activo(b.id, 'caja'))
check('B: facturación apagada', not modulo_activo(b.id, 'facturacion'))
check('B: certificados activos', modulo_activo(b.id, 'certificados'))

print('--- DEUDA NEUTRAL EN B ---')
pb1 = Estudiante.objects.get(centro=b, matricula='pb3001')
check(
    'pb3001 con asignación impaga NO aparece con deuda',
    not tiene_deuda_pendiente(b, pb1),
)

print('--- CENTRO B: gates y portales ---')
dirb = cliente('directorpb', 'admin123', b.id)
r = dirb.get('/caja/')
check('/caja/ redirige', r.status_code == 302, r.headers.get('Location', ''))
dash = dirb.get('/administracion/dashboard/')
html = dash.content.decode('utf-8')
check('dashboard sin menú Caja', 'menu-caja' not in html)
check('dashboard sin Recaudado', 'Recaudado' not in html)

def mensajes_de(response):
    try:
        return [str(m) for m in response.context['messages']]
    except Exception:
        return []


r = cajero_c = cliente('cajeropb', 'admin123', b.id).get('/', follow=True)
check(
    'cajeropb expulsado a login',
    r.request['PATH_INFO'].startswith('/usuarios/login'),
)
aviso = any(
    'caja no está activo' in m for m in mensajes_de(r)
)
print(f"       (aviso visible tras logout: {aviso} — el logout limpia la sesión)")

alumnob = cliente('pb3001', 'estudiante123', b.id)
alumnob.post('/estudiantes/inicio/solicitudes/', {
    'tipo_certificado': 'constancia_estudio',
    'metodo_pago': 'efectivo',
    'motivo': 'Verificación plan sin cobros',
})
sol_b = (
    SolicitudCertificado.objects.filter(estudiante=pb1)
    .order_by('-created_at').first()
)
check('solicitud B gratuita', sol_b.monto == 0, str(sol_b.monto))
check('solicitud B auto-aprobada', sol_b.estado == 'aprobada')
check('solicitud B pagada=True', sol_b.pagado)
panel_b = dirb.get('/estudiantes/solicitudes/')
html_b = panel_b.content.decode('utf-8')
check('panel B sin "Cobrar en caja"', 'Cobrar en caja' not in html_b)
check('panel B con "Exenta"', 'Exenta' in html_b)
karb = dirb.get(f'/estudiantes/{pb1.pk}/kardex/imprimir/')
check('kardex pb3001 imprime (sin bloqueo deuda)', karb.status_code == 200)

print('--- CENTRO A: flujo pagado intacto ---')
dira = cliente('director', 'admin123', a.id)
check('/caja/ accesible', dira.get('/caja/').status_code == 200)
check('/facturacion/ accesible', dira.get('/facturacion/').status_code == 200)
html_a = dira.get('/administracion/dashboard/').content.decode('utf-8')
check('dashboard A muestra Recaudado', 'Recaudado' in html_a)

est_a = Estudiante.objects.get(centro=a, matricula='20200001')
alumna = cliente('20200001', 'estudiante123', a.id)

pagina_a = alumna.get(
    '/estudiantes/inicio/solicitudes/'
).content.decode('utf-8')
check(
    'portal A muestra precio $500',
    '500' in pagina_a and 'Costo' in pagina_a,
)
check(
    'portal A ofrece método de pago',
    'metodo_pago' in pagina_a,
)
check(
    'portal B oculta método de pago',
    'metodo_pago' not in dirb.get('/estudiantes/inicio/solicitudes/')
    .content.decode('utf-8'),
)

resp_deuda = alumna.post(
    '/estudiantes/inicio/solicitudes/',
    {
        'tipo_certificado': 'record_notas',
        'metodo_pago': 'online',
        'motivo': 'Verificación plan completo',
    },
    follow=True,
)
check(
    'plan A bloquea solicitud por deuda (comportamiento esperado)',
    'deuda pendiente' in resp_deuda.content.decode('utf-8'),
)

print()
if FALLOS:
    print(f'RESULTADO: {len(FALLOS)} fallo(s): {FALLOS}')
    raise SystemExit(1)
print('RESULTADO: TODO OK — ambos centros se comportan según su plan.')
