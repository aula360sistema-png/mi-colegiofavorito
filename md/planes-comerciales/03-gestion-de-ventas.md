# 3. Guía para vender (gestión comercial)

> Cómo conseguir, calificar y cerrar colegios. Con el `seed_demo` del proyecto
> ya hay un entorno de demostración listo con usuarios por rol.

## 3.1 A quién vender (segmentos priorizados)

1. **Colegios privados medianos (200-600 estudiantes)** — el "sweet spot":
   duelen con las notas/boletines, la morosidad y los reportes al MINERD.
   → Plan Escolar.
2. **Cadenas y franquicias de colegios (2-10 centros)** — nadie local les vende
   centralización → Plan Red (nuestro diferenciador más fuerte).
3. **Colegios pequeños (hasta 200)** → Plan Esencial, vendido por "salir de
   Excel y WhatsApp".
4. **Centros grandes/bilingües (600+)**: venta más larga, más valor →
   Integral Pro.
5. **Público (MINERD)** → piloto de posicionamiento (ver sección 1.6 de
   `01-planes-y-precios.md`).

Priorizar por densidad: **Santo Domingo (1,096 colegios privados)** y
**Distrito Nacional (506)** primero; luego Santiago, La Vega, San Cristóbal,
La Altagracia (clientes turísticos/bilingües).

## 3.2 Fuente de prospectos

- Directorio MINERD de centros privados por distrito (más bases como EnRankeo).
- Ferias de colegios y asociaciones de centros educativos (ASBISE, COPRAC, etc.).
- Colegios que ya salen en Google con mala calificación administrativa.
- **Referidos**: el segmento educativo es de confianza; lançar un incentivo de
  1 mes gratis por cliente referido.

## 3.3 El demo de 20 minutos (usando el `seed_demo`)

Preparar 3 pantallas por rol (2 min cada una) + cierre:

1. **Dirección (5 min):** Dashboard → un estudiante con su **kardex** → una
   boleta/planilla imprimible → **cuentas por cobrar** (mostrar la morosidad).
2. **Secretaría (5 min):** matrícula/inscripción en 2 clics → constancia →
   solicitud de certificado.
3. **Docente (5 min):** entrar calificar una asignación → guardar notas →
   planilla. 
4. **Padres/estudiantes (2 min):** portal con notas, deuda y comunicados.
5. **Cierre (3 min):** "en 5 días hábiles su colegio opera así", con el plan
   sugerido y la promoción de lanzamiento (implementación gratis).

> Tip: preparar la demo **con los nombres de las secciones del colegio**
> (crear su centro rápido en la consola demo) hace que se proyecten en ella.

## 3.4 Objeciones típicas y respuestas

| Objeción | Respuesta |
|---|---|
| "Es caro / ya uso Excel" | "Hoy usted pierde horas cuadrando notas y persiguiendo mora. Este sistema cuesta ~RD$4,990/mes para 300-600 estudiantes = menos de RD$17 por alumno. Un solo pago recuperado lo paga." |
| "¿Y la DGII?" | "Facturación con **NCF** integrada; la emisión de comprobantes electrónicos (e-CF) está en nuestro plan de entrega certificado por DGII para 2026" (ver roadmap). |
| "¿Y si mañana nos vamos?" | "Al terminar le entregamos **toda su data en CSV** en 7 días. Los datos son suyos." |
| "¿Seguridad de la información?" | "Base de datos separada por cliente, cifrado de cédulas/contactos, **2FA** y bitácora de auditoría; respaldos automáticos." |
| "Mi secretaria no sabe de computadoras" | "La capacitamos por rol con manuales en PDF y la acompañamos la primera semana por WhatsApp." |
| "¿Y un solo maestro puede usarlo?" | "Sí: notas del maestro y reportes al director en el mismo día. El docente solo ve **sus secciones**." |
| "Ya estamos viendo a [competidor]" | (EscoLink/WisEdu/MiColegioRD): "Ellos son muy buenos en **un solo colegio**. ¿Tienen varias sedes o piensan crecer? Nuestra plataforma es **multi-centro** desde ya, con panel de red y consolidados." |
| "Necesito pagarlo por estudiante" | "Tenemos costeo por alumno: RD$45-65/estudiante/mes con mínimo mensual." |

## 3.5 Embudo y tiempos

1. Contacto por WhatsApp (director/administrador) → 1 semana.
2. Demo de 20 min → que apruebe el consejo/director → 1-2 semanas.
3. Piloto 15 días (grado de prueba o el equipo admin) → 2 semanas.
4. Contrato anual + implementación en 5 días hábiles → 1 semana.
5. **Onboarding:** crear centro → migrar data (Excel → sistema) → capacitar por
   rol → manuales PDF → alta en producción.

**Meta realista del año 1:** 1 contrato EA al mes. con 15 clientes +
referidos, el negocio es viable (ver `04-costos-y-margenes.md`).

## 3.6 Kit de venta mínimo (checklist)

- [ ] Propuesta de 1 página personalizada (`02-propuesta-comercial.md`).
- [ ] Link de demo funcional (deploy de prueba con `seed_demo`).
- [ ] Manuales por rol en PDF (carpeta `md/manual-proyecto/pdf/`).
- [ ] Contrato / términos y condiciones (modelo impreso).
- [ ] Lista de precios con descuentos vigentes.

## 3.7 KPI para medir ventas

- Prospectos por semana (≥ 15).
- Demos agendadas (≥ 25% de contacto).
- Pilotos activos (≥ 50% de demos).
- Cierre (≥ 50% de pilotos).
- **Churn** mensual objetivo: < 2% (renovaciones anuales).