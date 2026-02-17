# Tipos_de_cambio

Módulo para Odoo 19 que actualiza los tipos de cambio de **USD** y **EUR** desde el API del **Ministerio de Hacienda (Costa Rica)**.

> Nota: el nombre técnico del módulo es `tipos_cambio_bccr` por compatibilidad.

## Funcionalidad

- Consulta el API de Hacienda para obtener:
  - **USD** desde `venta.valor`.
  - **EUR** desde `colones`.
- Actualiza exclusivamente USD y EUR para evitar conflictos con la moneda base CRC.
- Ejecuta una tarea programada (`ir.cron`) diaria para actualizar los tipos de cambio.

## Instalación

1. Copie la carpeta `tipos_cambio_bccr` en su ruta de addons.
2. Actualice la lista de aplicaciones en Odoo.
3. Instale el módulo **Tipo de Cambio Hacienda CR (Odoo 19)**.

## Configuración

El módulo crea automáticamente el cron **Hacienda CR: Actualizar Tipo de Cambio** con frecuencia diaria.

Si necesita cambiar la frecuencia:

- Vaya a **Ajustes → Técnico → Automatización → Acciones planificadas**.
- Busque el cron mencionado y ajuste intervalo, siguiente ejecución o estado activo.

## Nota técnica

Los valores consultados (USD y EUR) se escriben en `inverse_company_rate` de cada moneda.
