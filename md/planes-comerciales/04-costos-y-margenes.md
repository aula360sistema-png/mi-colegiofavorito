# 4. Costos de operación y márgenes (RD$)

> Modelo de costos para decidir precios y saber el punto de equilibrio al
> escalar. Los planes ya contemplan margen bruto sano incluso en el plan
> Esencial.

## 4.1 Costo de hosting por cliente

Hoy el proyecto corre en **Render** (o equivalente). Para producción real de
clientes el plan **gratis no sirve**; se paga infraestructura compartida:

| Concepto | Costo/mes |
|---|---|
| Web service (2 workers, 512 MB-1 GB) | ~US$7-25 (~RD$400-1,450) |
| PostgreSQL administrado (1-2 GB, respaldos) | ~US$19-25 (~RD$1,100-1,450) |
| Redis (caché) | ~US$0-15 (~RD$0-870) |
| Dominio/subdominio + email transaccional | ~US$1-5 (~RD$60-290) |
| **Total estimado por centro activo (alojado por separado)** | **~US$27-70 ≈ RD$1,600-4,100/mes** |

> **Clave de escalabilidad:** no se aloja un "servidor" por colegio. En un solo
> clúster corren MUCHOS centros (la arquitectura ya es multi-centro y separa
> datos por cliente). Es decir, el costo por cliente **cae** al crecer:
> infraestructura de 10 centros ≈ igual que la de 1, salvo base de datos.

## 4.2 Margen bruto por plan (estimado)

Suponiendo hosting compartido ≈ RD$1,200/mes por el primer centro en el clúster
(se diluye con más clientes):

| Plan | Precio/mes | Costo infra aprox. | Margen bruto |
|---|---|---|---|
| Esencial | RD$2,490 | RD$1,200-1,500 | ~40-50% |
| Escolar | RD$4,990 | RD$1,200-1,800 | ~64-76% |
| Integral Pro | RD$9,990 | RD$1,500-2,500 | ~75-85% |
| Red (3 centros) | RD$14,900 | RD$3,000-5,000 | ~66-80% |

## 4.3 Punto de equilibrio del negocio

Costos fijos mínimos (técnico + ventas + herramientas):

| Concepto | /mes |
|---|---|
| Hosting clúster inicial | RD$5,000 |
| Correo transaccional / WhatsApp | RD$2,000 |
| Dominio + herramientas | RD$1,500 |
| Soporte (part-time) | RD$15,000 |
| **Total fijos aprox.** | **RD$23,500/mes** |

Punto de equilibrio con mezcla (2 Esencial + 4 Escolar + 2 Pro ≈ RD$44,930/mes)
→ flojo antes de los **8-10 clientes**, incluso cubriendo implementación.
Con 25 clientes la operación es claramente rentable.

## 4.4 Caja por implementaciones (entrada de capital)

La implementación se cobra **única** y se reconoce al inicio del contrato.
Ese dinero financia el setup del primer ciclo sin tocar la caja mensual:

| Plan | Implementación |
|---|---|
| Esencial | RD$4,990 |
| Escolar | RD$9,990 |
| Integral Pro | desde RD$19,990 |
| Red | RD$9,990/centro |

> En lanzamiento (primeros 15 clientes) se regala la implementación **solo con
> contrato anual**: convierte setup → flujo anual seguro y baja el churn.

## 4.5 Recomendaciones de costos

1. Comenzar con **1 clúster** de producción (ej. Render) + ambiente de demo.
2. Respaldo: backups automáticos + descarga mensual a un storage externo.
3. Cobrar en **moneda local RD$** (los colegios presupuestan en peso).
4. Escalar a un plan superior de infraestructura al pasar de ~20 clientes.