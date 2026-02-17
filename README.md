# Tipos_de_cambio

Módulo para Odoo 19 que agrega el proveedor de tipos de cambio del **Banco Central de Costa Rica (BCCR)** sobre la arquitectura de `currency_rate_live` basada en `res.company`.

## Funcionalidad

- Agrega la opción **Banco Central de Costa Rica** en `res.company.currency_provider`.
- Consulta el web service del BCCR (suscripciones) enviando **token SDDE** y **correo electrónico** para obtener:
  - Tipo de cambio de **venta USD** (indicador por defecto `318`).
  - Tipo de cambio de **EUR** (indicador por defecto `333`).
- Expone los campos de configuración en `res.config.settings` como relacionados a la compañía.

## Instalación

1. Copie la carpeta `tipos_cambio_bccr` en su ruta de addons.
2. Actualice lista de apps.
3. Verifique que esté instalado **currency_rate_live**.
4. Instale **Tipos de Cambio BCCR**.

## Configuración

En **Contabilidad → Configuración → Tipos de cambio automáticos**:

- Seleccione proveedor: **Banco Central de Costa Rica**.
- Al seleccionar ese proveedor se muestran los campos:
  - Nombre BCCR (legado, opcional).
  - Correo BCCR (legado, opcional).
  - Token SDDE (obligatorio).
  - Indicador USD venta (por defecto `318`).
  - Indicador EUR venta (por defecto `333`).

El módulo consulta automáticamente los indicadores configurados para venta.

## Nota

Los valores de venta consultados (USD y EUR) se registran como `inverse_company_rate` en cada moneda correspondiente.


## Compatibilidad con el cambio del BCCR

El endpoint de suscripciones del BCCR requiere recibir los parámetros `Token` y `CorreoElectronico`.
Si falta alguno o es inválido, Odoo mostrará el detalle devuelto por el BCCR.


## Prueba manual de conectividad

Para validar rápidamente si su token/correo funcionan con el BCCR, puede ejecutar:

```bash
BCCR_EMAIL="su-correo@dominio.com" \
BCCR_TOKEN="su-token" \
python3 scripts/test_bccr_connection.py
```

Variables opcionales:
- `BCCR_INDICADOR` (default `318`).
- `BCCR_NOMBRE` (default `Odoo`).
- `BCCR_LOOKBACK_DAYS` (default `30`).
