# Inventario de Endpoints

Verificado al 2026-08-11: **443 URLs** en total (199 de app + 244 de admin). Todas resuelven con `reverse()` y apuntan a vistas existentes. `manage.py check` sin issues.

Convenciones:
- `(s/n)` = sin namespace (referencia con el nombre a secas: `{% url 'nombre' %}`).
- `(c/n)` = con namespace (referencia con prefijo: `{% url 'app:nombre' %}`).
- `RAIZ` = patrón vacío (listado principal de la app).
- `[AJAX]` = vista que devuelve `JsonResponse` (no página).

## Core — `/` (namespace `core`)

| URL | Nombre | Vista |
|---|---|---|
| `/` | `core:home` | `core.views.home` |
| `/seleccionar-centro/` | `core:seleccionar_centro` | `core.views.seleccionar_centro` |
| `/dashboard/` | `core:dashboard` | `core.views.dashboard` |
| `/centros/` | `core:centro_list` | `core.views.centro_list` |
| `/centros/crear/` | `core:centro_create` | `core.views.centro_create` |
| `/centros/<int:pk>/editar/` | `core:centro_update` | `core.views.centro_update` |
| `/centros/<int:pk>/eliminar/` | `core:centro_delete` | `core.views.centro_delete` |
| `/configuracion-centro/` | `core:configuracion_centro` | `core.views.configuracion_centro` |

## Docentes — `/docentes/` (s/n)

| URL | Nombre | Vista |
|---|---|---|
| `/docentes/` | `docente_list` | `docentes.views.docente_list` |
| `/docentes/crear/` | `docente_create` | `docentes.views.docente_create` |
| `/docentes/editar/<int:pk>/` | `docente_update` | `docentes.views.docente_update` |
| `/docentes/eliminar/<int:pk>/` | `docente_delete` | `docentes.views.docente_delete` |
| `/docentes/detalle/<int:pk>/` | `docente_detail` | `docentes.views.docente_detail` |
| `/docentes/dashboard/` | `dashboard_docente` | `docentes.views.dashboard_docente` |
| `/docentes/asignacion/<int:asignacion_id>/estudiantes/` | `docente_estudiantes` | `docentes.views.docente_estudiantes` |
| `/docentes/asignacion/<int:asignacion_id>/guardar-notas/` | `guardar_notas_ajax` | `docentes.views.guardar_notas_ajax` |
| `/docentes/asignacion/<int:asignacion_id>/calificar/` | `calificar_tabla` | `docentes.views.calificar_tabla` |

## Estudiantes — `/estudiantes/` (s/n)

| URL | Nombre | Vista |
|---|---|---|
| `/estudiantes/` | `estudiante_list` | `estudiantes.views.estudiante_list` |
| `/estudiantes/nuevo/` | `estudiante_create` | `estudiantes.views.estudiante_create` |
| `/estudiantes/<int:pk>/` | `estudiante_detail` | `estudiantes.views.estudiante_detail` |
| `/estudiantes/<int:pk>/editar/` | `estudiante_update` | `estudiantes.views.estudiante_update` |
| `/estudiantes/<int:pk>/eliminar/` | `estudiante_delete` | `estudiantes.views.estudiante_delete` |
| `/estudiantes/<int:pk>/cambiar-estado/` | `cambiar_estado_estudiante` | `estudiantes.views.cambiar_estado_estudiante` |
| `/estudiantes/<int:pk>/kardex/imprimir/` | `kardex_imprimir` | `estudiantes.views.kardex_imprimir` |
| `/estudiantes/<int:pk>/observaciones/agregar/` | `agregar_observacion_estudiante` | `estudiantes.views.agregar_observacion_estudiante` |
| `/estudiantes/inicio/` | `estudiante_inicio` | `estudiantes.views.estudiante_inicio` |
| `/estudiantes/<int:estudiante_id>/inscribir/` | `inscribir_estudiante` | `estudiantes.views.inscribir_estudiante_avanzado` |
| `/estudiantes/inscripcion/<int:inscripcion_id>/asignaturas/` | `inscripcion_asignaturas` | `estudiantes.views.inscripcion_asignaturas` |
| `/estudiantes/ajax/cargar-secciones/` | `ajax_cargar_secciones` | `estudiantes.views.ajax_cargar_secciones` |
| `/estudiantes/historial/` | `historial_estudiantes` | `estudiantes.views.historial_estudiantes` |
| `/estudiantes/constancias/` | `constancias` | `estudiantes.views.constancias` |
| `/estudiantes/constancia/<int:pk>/` | `constancia_estudiante` | `estudiantes.views.constancia_estudiante` |
| `/estudiantes/disciplina/` | `disciplina` | `estudiantes.views.disciplina` |
| `/estudiantes/disciplina/registrar/` | `disciplina_registrar` | `estudiantes.views.disciplina_registrar` |
| `/estudiantes/disciplina/<int:pk>/eliminar/` | `disciplina_eliminar` | `estudiantes.views.disciplina_eliminar` |
| `/estudiantes/inicio/solicitudes/` | `estudiante_solicitudes` | `estudiantes.views.estudiante_solicitudes` |
| `/estudiantes/inicio/solicitudes/<int:pk>/pagar/` | `estudiante_solicitud_pagar` | `estudiantes.views.estudiante_solicitud_pagar` |
| `/estudiantes/inicio/historial-clinico/` | `estudiante_historial_clinico` | `estudiantes.views.estudiante_historial_clinico` |
| `/estudiantes/historial-clinico/` | `historial_clinico_list` | `estudiantes.views.historial_clinico_list` |
| `/estudiantes/historial-clinico/<int:pk>/` | `historial_clinico_detalle` | `estudiantes.views.historial_clinico_detalle` |
| `/estudiantes/historial-clinico/<int:pk>/editar/` | `historial_clinico_editar` | `estudiantes.views.historial_clinico_editar` |
| `/estudiantes/historial-clinico/<int:pk>/registro/` | `registro_salud_crear` | `estudiantes.views.registro_salud_crear` |
| `/estudiantes/registro-salud/<int:pk>/eliminar/` | `registro_salud_eliminar` | `estudiantes.views.registro_salud_eliminar` |
| `/estudiantes/solicitudes/` | `solicitudes_certificados` | `estudiantes.views.solicitudes_certificados_list` |
| `/estudiantes/solicitudes/<int:pk>/aprobar/` | `solicitud_aprobar` | `estudiantes.views.solicitud_aprobar` |
| `/estudiantes/solicitudes/<int:pk>/rechazar/` | `solicitud_rechazar` | `estudiantes.views.solicitud_rechazar` |
| `/estudiantes/solicitudes/<int:pk>/cobrar/` | `solicitud_cobrar` | `estudiantes.views.solicitud_cobrar` |
| `/estudiantes/solicitudes/<int:pk>/entregar/` | `solicitud_entregar` | `estudiantes.views.solicitud_entregar` |
| `/estudiantes/solicitudes/<int:pk>/anular/` | `solicitud_anular` | `estudiantes.views.solicitud_anular` |

## Académico — `/academico/` (s/n)

| URL | Nombre | Vista |
|---|---|---|
| `/academico/curriculo/` | `curriculo` | `academico.views.curriculo` |
| `/academico/ajax/asignaturas-por-grado/<int:grado_id>/` | `ajax_asignaturas_por_grado` | `academico.views.ajax_asignaturas_por_grado` |
| `/academico/niveles/` | `nivel_list` | `academico.views.nivel_list` |
| `/academico/niveles/nuevo/` | `nivel_create` | `academico.views.nivel_create` |
| `/academico/niveles/<int:pk>/editar/` | `nivel_update` | `academico.views.nivel_update` |
| `/academico/niveles/<int:pk>/eliminar/` | `nivel_delete` | `academico.views.nivel_delete` [AJAX] |
| `/academico/niveles/estructura-minerd/` | `estructura_minerd` | `academico.views.estructura_minerd` |
| `/academico/grados/` | `grado_list` | `academico.views.grado_list` |
| `/academico/grados/nuevo/` | `grado_create` | `academico.views.grado_create` |
| `/academico/grados/<int:pk>/editar/` | `grado_update` | `academico.views.grado_update` |
| `/academico/grados/<int:pk>/eliminar/` | `grado_delete` | `academico.views.grado_delete` [AJAX] |
| `/academico/grados/<int:grado_id>/estudiantes/` | `grado_estudiantes` | `academico.views.grado_estudiantes` |
| `/academico/grados/<int:grado_id>/asignaturas/` | `grado_asignaturas` | `academico.views.grado_asignaturas` |
| `/academico/secciones/` | `seccion_list` | `academico.views.seccion_list` |
| `/academico/secciones/nueva/` | `seccion_create` | `academico.views.seccion_create` |
| `/academico/secciones/<int:pk>/editar/` | `seccion_update` | `academico.views.seccion_update` |
| `/academico/secciones/<int:pk>/eliminar/` | `seccion_delete` | `academico.views.seccion_delete` |
| `/academico/areas/` | `area_list` | `academico.views.area_list` |
| `/academico/areas/nueva/` | `area_create` | `academico.views.area_create` |
| `/academico/areas/<int:pk>/editar/` | `area_update` | `academico.views.area_update` |
| `/academico/areas/<int:pk>/eliminar/` | `area_delete` | `academico.views.area_delete` |
| `/academico/asignaturas/` | `asignatura_list` | `academico.views.asignatura_list` |
| `/academico/asignaturas/nueva/` | `asignatura_create` | `academico.views.asignatura_create` |
| `/academico/asignaturas/<int:pk>/editar/` | `asignatura_update` | `academico.views.asignatura_update` |
| `/academico/asignaturas/<int:pk>/eliminar/` | `asignatura_delete` | `academico.views.asignatura_delete` |
| `/academico/grado-asignaturas/` | `grado_asignatura_list` | `academico.views.grado_asignatura_list` |
| `/academico/grado-asignaturas/nueva/` | `grado_asignatura_create` | `academico.views.grado_asignatura_create` |
| `/academico/grado-asignaturas/<int:pk>/eliminar/` | `grado_asignatura_delete` | `academico.views.grado_asignatura_delete` |
| `/academico/competencias/` | `competencia_list` | `academico.views.competencia_list` |
| `/academico/competencias/nueva/` | `competencia_create` | `academico.views.competencia_create` |
| `/academico/competencias/<int:pk>/editar/` | `competencia_update` | `academico.views.competencia_update` |
| `/academico/competencias/<int:pk>/eliminar/` | `competencia_delete` | `academico.views.competencia_delete` |
| `/academico/periodos/` | `periodo_list` | `academico.views.periodo_list` |
| `/academico/periodos/nuevo/` | `periodo_create` | `academico.views.periodo_create` |
| `/academico/periodos/<int:pk>/editar/` | `periodo_update` | `academico.views.periodo_update` |
| `/academico/periodos/<int:pk>/eliminar/` | `periodo_delete` | `academico.views.periodo_delete` [AJAX] |
| `/academico/periodos/<int:pk>/alternar/` | `alternar_periodo_anio` | `academico.views.alternar_periodo_anio` |
| `/academico/periodos/cerrar-todos/` | `cerrar_todos_periodos` | `academico.views.cerrar_todos_los_periodos` |
| `/academico/docente-materia/` | `docentemateria_list` | `academico.views.docentemateria_list` |
| `/academico/docente-materia/nuevo/` | `docentemateria_create` | `academico.views.docentemateria_create` |
| `/academico/docente-materia/<int:pk>/editar/` | `docentemateria_update` | `academico.views.docentemateria_update` |
| `/academico/docente-materia/<int:pk>/eliminar/` | `docentemateria_delete` | `academico.views.docentemateria_delete` |
| `/academico/anio-escolar/` | `anio_escolar_list` | `administracion.views.anio_escolar_list` |
| `/academico/anio-escolar/crear/` | `anio_escolar_create` | `administracion.views.anio_escolar_create` |
| `/academico/anio-escolar/<int:pk>/editar/` | `anio_escolar_update` | `administracion.views.anio_escolar_update` |
| `/academico/anio-escolar/<int:pk>/cerrar/` | `cerrar_anio_escolar` | `academico.views.cerrar_anio_escolar` |
| `/academico/franjas/` | `franja_list` | `academico.views.franja_list` |
| `/academico/franjas/nueva/` | `franja_create` | `academico.views.franja_create` |
| `/academico/franjas/<int:pk>/editar/` | `franja_update` | `academico.views.franja_update` |
| `/academico/franjas/<int:pk>/eliminar/` | `franja_delete` | `academico.views.franja_delete` |
| `/academico/horario/` | `horario_list` | `academico.views.horario_list` |
| `/academico/horario/clase/nueva/` | `horario_clase_create` | `academico.views.horario_clase_create` |
| `/academico/horario/clase/<int:pk>/editar/` | `horario_clase_update` | `academico.views.horario_clase_update` |
| `/academico/horario/clase/<int:pk>/eliminar/` | `horario_clase_delete` | `academico.views.horario_clase_delete` |

## Usuarios — `/usuarios/` (namespace `usuarios`)

| URL | Nombre | Vista |
|---|---|---|
| `/usuarios/login/` | `usuarios:login` | `usuarios.views.login_view` |
| `/usuarios/logout/` | `usuarios:logout` | `usuarios.views.logout_view` |
| `/usuarios/crear/` | `usuarios:crear_miembro` | `usuarios.views.crear_miembro` |
| `/usuarios/password/` | `usuarios:cambiar_contrasena` | `usuarios.views.cambiar_contrasena` |
| `/usuarios/verificar-2fa/` | `usuarios:verificar_2fa` | `usuarios.views.verificar_2fa` |
| `/usuarios/configurar-2fa/` | `usuarios:configurar_2fa` | `usuarios.views.configurar_2fa` |
| `/usuarios/gestionar-2fa/` | `usuarios:gestionar_2fa` | `usuarios.views.gestionar_2fa` |

## Administración — `/administracion/` (namespace `administracion`)

| URL | Nombre | Vista |
|---|---|---|
| `/administracion/dashboard/` | `administracion:dashboard_admin` | `administracion.views.dashboard_admin` |
| `/administracion/crear-administrativo/` | `administracion:administrativo_create` | `administracion.views.administrativo_create` |
| `/administracion/personal/` | `administracion:listado_personal` | `administracion.views.listado_personal` |
| `/administracion/mantenimiento/` | `administracion:mantenimiento` | `administracion.views.mantenimiento_home` |
| `/reportes/` | `reportes:reportes` | `reportes.views.reportes` |
| `/reportes/asistencia/` | `reportes:reporte_asistencia` | `reportes.views.reporte_asistencia` |
| `/reportes/listado-seccion/imprimir/` | `reportes:print_listado_seccion` | `reportes.views.print_listado_seccion` |
| `/reportes/asistencia/imprimir/` | `reportes:print_asistencia` | `reportes.views.print_asistencia` |
| `/reportes/carga-academica/` | `reportes:reporte_carga_academica` | `reportes.views.reporte_carga_academica` |
| `/reportes/carga-academica/imprimir/` | `reportes:print_carga_academica` | `reportes.views.print_carga_academica` |
| `/administracion/boletines/generar/` | `administracion:generar_boletines` | `administracion.views.generar_boletines` |
| `/administracion/boletines/cerrar-completivo/` | `administracion:cerrar_completivo` | `administracion.views.cerrar_completivo` |
| `/administracion/boletines/` | `administracion:lista_boletines` | `administracion.views.lista_boletines` |
| `/administracion/boletines/<int:acta_id>/` | `administracion:ver_boletin` | `administracion.views.ver_boletin_estudiante` |
| `/administracion/boletines/imprimir/<int:acta_id>/` | `administracion:imprimir_boletin_acta` | `administracion.views.imprimir_boletin_acta` |
| `/administracion/seguimiento/estudiantes/` | `administracion:seguimiento_estudiantes` | `administracion.views.seguimiento_estudiantes` |
| `/administracion/seguimiento/estudiante/<int:estudiante_id>/` | `administracion:seguimiento_estudiante` | `administracion.views.seguimiento_estudiante` |

## Nómina — `/nomina/` (namespace `nomina`)

| URL | Nombre | Vista |
|---|---|---|
| `/nomina/` | `nomina:dashboard` | `nomina.views.dashboard` |
| `/nomina/afp/` | `nomina:afp_list` | `nomina.views.afp_list` |
| `/nomina/afp/crear/` | `nomina:afp_create` | `nomina.views.afp_create` |
| `/nomina/afp/<int:pk>/editar/` | `nomina:afp_edit` | `nomina.views.afp_edit` |
| `/nomina/afp/<int:pk>/alternar/` | `nomina:afp_toggle` | `nomina.views.afp_toggle` |
| `/nomina/ars/` | `nomina:ars_list` | `nomina.views.ars_list` |
| `/nomina/ars/crear/` | `nomina:ars_create` | `nomina.views.ars_create` |
| `/nomina/ars/<int:pk>/editar/` | `nomina:ars_edit` | `nomina.views.ars_edit` |
| `/nomina/ars/<int:pk>/alternar/` | `nomina:ars_toggle` | `nomina.views.ars_toggle` |
| `/nomina/cargos/` | `nomina:cargo_list` | `nomina.views.cargo_list` |
| `/nomina/cargos/crear/` | `nomina:cargo_create` | `nomina.views.cargo_create` |
| `/nomina/cargos/<int:pk>/editar/` | `nomina:cargo_edit` | `nomina.views.cargo_edit` |
| `/nomina/cargos/<int:pk>/alternar/` | `nomina:cargo_toggle` | `nomina.views.cargo_toggle` |
| `/nomina/tipos-ingreso/` | `nomina:tipo_ingreso_list` | `nomina.views.tipo_ingreso_list` |
| `/nomina/tipos-ingreso/crear/` | `nomina:tipo_ingreso_create` | `nomina.views.tipo_ingreso_create` |
| `/nomina/tipos-ingreso/<int:pk>/alternar/` | `nomina:tipo_ingreso_toggle` | `nomina.views.tipo_ingreso_toggle` |
| `/nomina/tipos-descuento/` | `nomina:tipo_descuento_list` | `nomina.views.tipo_descuento_list` |
| `/nomina/tipos-descuento/crear/` | `nomina:tipo_descuento_create` | `nomina.views.tipo_descuento_create` |
| `/nomina/tipos-descuento/<int:pk>/alternar/` | `nomina:tipo_descuento_toggle` | `nomina.views.tipo_descuento_toggle` |
| `/nomina/configuracion/` | `nomina:configuracion_nomina_list` | `nomina.views.configuracion_nomina_list` |
| `/nomina/configuracion/crear/` | `nomina:configuracion_nomina_create` | `nomina.views.configuracion_nomina_create` |
| `/nomina/configuracion/<int:pk>/editar/` | `nomina:configuracion_nomina_edit` | `nomina.views.configuracion_nomina_edit` |
| `/nomina/configuracion/<int:pk>/alternar/` | `nomina:configuracion_nomina_toggle` | `nomina.views.configuracion_nomina_toggle` |
| `/nomina/configuracion/<int:pk>/eliminar/` | `nomina:configuracion_nomina_delete` | `nomina.views.configuracion_nomina_delete` |
| `/nomina/empleado/<int:pk>/` | `nomina:empleado_detalle` | `nomina.views.empleado_detalle` |
| `/nomina/empleado/<int:pk>/ingreso/` | `nomina:ingreso_empleado_create` | `nomina.views.ingreso_empleado_create` |
| `/nomina/empleado/<int:pk>/ingreso/<int:ingreso_id>/eliminar/` | `nomina:ingreso_empleado_delete` | `nomina.views.ingreso_empleado_delete` |
| `/nomina/empleado/<int:pk>/descuento/` | `nomina:descuento_empleado_create` | `nomina.views.descuento_empleado_create` |
| `/nomina/empleado/<int:pk>/descuento/<int:descuento_id>/eliminar/` | `nomina:descuento_empleado_delete` | `nomina.views.descuento_empleado_delete` |
| `/nomina/periodos/` | `nomina:periodo_nomina_list` | `nomina.views.periodo_nomina_list` |
| `/nomina/periodos/<int:periodo_id>/` | `nomina:periodo_detalle` | `nomina.views.periodo_detalle` |
| `/nomina/generar/<int:periodo_id>/` | `nomina:generar_nomina` | `nomina.views.generar_nomina_view` |
| `/nomina/periodos/<int:periodo_id>/cerrar/` | `nomina:periodo_cerrar` | `nomina.views.periodo_cerrar` |
| `/nomina/periodos/<int:periodo_id>/anular/` | `nomina:periodo_anular` | `nomina.views.periodo_anular` |
| `/nomina/nomina/<int:nomina_id>/estado/` | `nomina:nomina_estado` | `nomina.views.nomina_estado` |
| `/nomina/nomina/<int:nomina_id>/boleta/` | `nomina:boleta_pago` | `nomina.views.boleta_pago` |
| `/nomina/historial/` | `nomina:historial_nomina` | `nomina.views.historial_nomina` |
| `/nomina/detalle/<int:periodo_id>/` | `nomina:detalle_nomina` | `nomina.views.detalle_nomina_view` |

## Asistencia — `/asistencia/` (namespace `asistencia`)

| URL | Nombre | Vista |
|---|---|---|
| `/asistencia/tomar/` | `asistencia:tomar_asistencia` | `asistencia.views.tomar_asistencia` |
| `/asistencia/estado-asistencia/` | `asistencia:estado_asistencia` | `asistencia.views.estado_asistencia` |
| `/asistencia/resumen/` | `asistencia:resumen_asistencia` | `asistencia.views.resumen_asistencia` |
| `/asistencia/dias-no-docencia/` | `asistencia:dias_no_docencia` | `asistencia.views.dias_no_docencia` |

## Caja — `/caja/` (namespace `caja`)

| URL | Nombre | Vista |
|---|---|---|
| `/caja/` | `caja:caja_inicio` | `caja.views.caja_inicio` |
| `/caja/cajas/` | `caja:lista_cajas` | `caja.views.lista_cajas` |
| `/caja/cajas/nueva/` | `caja:crear_caja` | `caja.views.crear_caja` |
| `/caja/cajas/<int:caja_id>/editar/` | `caja:editar_caja` | `caja.views.editar_caja` |
| `/caja/cajas/<int:caja_id>/alternar/` | `caja:alternar_caja` | `caja.views.alternar_caja` |
| `/caja/apertura/` | `caja:abrir_caja` | `caja.views.abrir_caja` |
| `/caja/cierre/` | `caja:cerrar_caja` | `caja.views.cerrar_caja` |
| `/caja/pagos/` | `caja:lista_pagos` | `caja.views.lista_pagos` |
| `/caja/pagos/nuevo/` | `caja:registrar_pago` | `caja.views.registrar_pago` |
| `/caja/pagos/nuevo/<int:estudiante_id>/` | `caja:registrar_pago_estudiante` | `caja.views.registrar_pago` |
| `/caja/pagos/nuevo/<int:estudiante_id>/<int:concepto_id>/` | `caja:registrar_pago_estudiante_concepto` | `caja.views.registrar_pago` |
| `/caja/pagos/<int:pago_id>/recibo/` | `caja:recibo_pago` | `caja.views.recibo_pago` |
| `/caja/pagos/balance/<int:estudiante_id>/` | `caja:api_balance_pago` | `caja.views.api_balance_pago` [AJAX] |
| `/caja/egresos/` | `caja:lista_egresos` | `caja.views.lista_egresos` |
| `/caja/egresos/nuevo/` | `caja:registrar_egreso` | `caja.views.registrar_egreso` |
| `/caja/conceptos/` | `caja:lista_conceptos` | `caja.views.lista_conceptos` |
| `/caja/conceptos/nuevo/` | `caja:crear_concepto` | `caja.views.crear_concepto` |
| `/caja/cuentas/` | `caja:cuentas_por_cobrar` | `caja.views.cuentas_por_cobrar` |
| `/caja/asignaciones/` | `caja:asignaciones_conceptos` | `caja.views.asignaciones_conceptos` |
| `/caja/reporte/` | `caja:reporte_diario` | `caja.views.reporte_diario` |
| `/caja/sesiones/` | `caja:historial_sesiones` | `caja.views.historial_sesiones` |
| `/caja/sesiones/<int:sesion_id>/` | `caja:detalle_sesion` | `caja.views.detalle_sesion` |

## Facturación — `/facturacion/` (namespace `facturacion`)

| URL | Nombre | Vista |
|---|---|---|
| `/facturacion/` | `facturacion:facturacion_inicio` | `facturacion.views.facturacion_inicio` |
| `/facturacion/facturas/` | `facturacion:lista_facturas` | `facturacion.views.lista_facturas` |
| `/facturacion/facturas/<int:factura_id>/` | `facturacion:detalle_factura` | `facturacion.views.detalle_factura` |
| `/facturacion/comprobantes/` | `facturacion:lista_comprobantes` | `facturacion.views.lista_comprobantes` |

## Tutores — `/tutores/` (namespace `tutores`)

| URL | Nombre | Vista |
|---|---|---|
| `/tutores/` | `tutores:tutor_list` | `tutores.views.tutor_list` |
| `/tutores/inicio/` | `tutores:tutor_inicio` | `tutores.views.tutor_inicio` |
| `/tutores/nuevo/` | `tutores:tutor_create` | `tutores.views.tutor_create` |
| `/tutores/inicio/solicitudes/` | `tutores:tutor_solicitudes` | `tutores.views.tutor_solicitudes` |
| `/tutores/inicio/historial-clinico/` | `tutores:tutor_historial_clinico` | `tutores.views.tutor_historial_clinico` |
| `/tutores/<int:pk>/` | `tutores:tutor_detail` | `tutores.views.tutor_detail` |
| `/tutores/<int:pk>/editar/` | `tutores:tutor_update` | `tutores.views.tutor_update` |
| `/tutores/<int:pk>/eliminar/` | `tutores:tutor_delete` | `tutores.views.tutor_delete` |

## Admin — `/admin/` (namespace `admin`)

Registro estándar de Django. 244 URLs (`admin:index`, `app_list`, y CRUD de los ~40 modelos registrados: `admin:auth_*`, `admin:usuarios_*`, `admin:core_*`, `admin:estudiantes_*`, `admin:docentes_*`, `admin:academico_*`, `admin:administracion_*`, `admin:auditoria_*`, `admin:nomina_*`, `admin:asistencia_*`, `admin:caja_*`, `admin:facturacion_*`, `admin:tutores_*`).

## Otros

| URL | Nombre | Vista | Nota |
|---|---|---|---|
| `/ia/prueba/` | *(sin nombre)* | `ia.views.prueba_ia` | No referenciable desde templates |

## Notas de verificación

- `python manage.py check` → sin issues.
- 443/443 URLs resuelven con `reverse()` (236 requieren argumentos de ruta, normal).
- 189 referencias `{% url %}` en templates → 188 OK, 1 rota que fue eliminada con el template huérfano `nomina/empleado_nomina_form.html` (`nomina:empleado_nomina_list` no existe).
- 11 templates huérfanos eliminados (los delete reales de académico son AJAX/redirect; los boletines imprimibles usan `boletin_imprimible_inicial/primaria/secundaria.html`).
