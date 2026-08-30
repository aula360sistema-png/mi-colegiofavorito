from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from core.decorators import centro_required, role_required
from core.utils.anio import obtener_anio_activo
from tutores.models import Tutor

from .models import NotificacionAutomatica
from .services import GRUPOS_ALERTA, generar_tablero

ROLES_AUTOMATIZACIONES = ('director', 'secretaria', 'admin', 'superadmin')

MENSAJE_POR_REGLA = {
    'inasistencias': (
        "Estimado(a) {{tutor}}: le informamos que {{estudiante}} acumula "
        "ausencias consecutivas en el colegio. Le solicitamos comunicarse "
        "con la coordinación académica para regularizar su asistencia."
    ),
    'notas_rojas': (
        "Estimado(a) {{tutor}}: en el período actual {{estudiante}} presenta "
        "notas por debajo del mínimo esperado. Es importante reforzar esos "
        "contenidos desde casa."
    ),
    'pagos_vencidos': (
        "Estimado(a) {{tutor}}: no se ha registrado un pago reciente de "
        "{{estudiante}}. Por favor, regularice la mensualidad pendiente para "
        "mantener su inscripción al día."
    ),
    'cumpleanos': (
        "Estimado(a) {{tutor}}: hoy {{estudiante}} celebra su cumpleaños. "
        "¡Felicitaciones y que tenga un gran día!"
    ),
}


@login_required
@centro_required
@role_required(*ROLES_AUTOMATIZACIONES)
def tablero(request):
    centro = request.centro
    anio = obtener_anio_activo(centro)
    tablero = generar_tablero(centro, anio)

    return render(request, 'automatizaciones/tablero.html', {
        'centro': centro,
        'anio': anio,
        'grupos': tablero['grupos'],
        'recientes': NotificacionAutomatica.objects.filter(
            centro=centro,
        ).select_related('campania').order_by('-created_at')[:5],
    })


@login_required
@centro_required
@role_required(*ROLES_AUTOMATIZACIONES)
def crear_campania(request):
    centro = request.centro
    regla = request.POST.get('regla', '').strip()

    claves_validas = {clave for clave, *_ in GRUPOS_ALERTA}
    if regla not in claves_validas:
        messages.error(request, 'Regla de alerta no válida.')
        return redirect('automatizaciones:tablero')

    if request.method != 'POST':
        return redirect('automatizaciones:tablero')

    anio = obtener_anio_activo(centro)
    if anio is None:
        messages.error(request, 'No hay un año escolar activo para este centro.')
        return redirect('automatizaciones:tablero')

    tablero = generar_tablero(centro, anio)
    grupo = next((g for g in tablero['grupos'] if g['clave'] == regla), None)

    if not grupo or not grupo['items']:
        messages.warning(request, 'No hay estudiantes afectados para esta alerta.')
        return redirect('automatizaciones:tablero')

    tutor_ids = set()
    for item in grupo['items']:
        tutor_ids.update(item['tutor_ids'])

    tutores = Tutor.objects.filter(pk__in=tutor_ids, centro=centro)

    from comunicaciones.models import Campania
    from comunicaciones.services import construir_destinatarios

    campania = Campania.objects.create(
        centro=centro,
        asunto=f'[Alerta] {grupo["titulo"]}',
        mensaje=MENSAJE_POR_REGLA[regla],
        canal='email',
        alcance='seleccion',
        estado='borrador',
        enviado_por=request.user,
    )
    campania.tutores.set(tutores)

    destinatarios = construir_destinatarios(campania)
    total_destinatarios = campania.destinatarios.count()

    NotificacionAutomatica.objects.create(
        centro=centro,
        tipo=regla,
        titulo=grupo['titulo'],
        campania=campania,
        canal='email',
        total_destinatarios=total_destinatarios,
        creado_por=request.user,
    )

    messages.success(
        request,
        f'Campaña creada para {destinatarios} tutor(es) con contacto '
        f'({total_destinatarios} en total). '
        'Revísala y envíala cuando quieras desde Comunicaciones.'
    )
    return redirect('comunicaciones:campania_detail', pk=campania.pk)