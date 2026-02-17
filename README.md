# Tipos_de_cambio

Módulo para Odoo 19 que agrega el proveedor de tipos de cambio del **Banco Central de Costa Rica (BCCR)** sobre la arquitectura de `currency_rate_live` basada en `res.company`.

## Funcionalidad

- Agrega la opción **Banco Central de Costa Rica** en `res.company.currency_provider`.
- Consulta el API REST del BCCR enviando **token SDDE** y **correo electrónico** para obtener:
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
  - Nombre BCCR (identificador del cliente, opcional).
  - Correo BCCR (legado, opcional).
  - Token SDDE (obligatorio).
  - Indicador USD venta (por defecto `318`).
  - Indicador EUR venta (por defecto `333`).

El módulo consulta automáticamente los indicadores configurados para venta.

## Nota

Los valores de venta consultados (USD y EUR) se registran como `inverse_company_rate` en cada moneda correspondiente.


## Compatibilidad con el cambio del BCCR

El endpoint REST del BCCR `api/Indicador/ObtenerIndicador` requiere recibir los parámetros `Token` y `CorreoElectronico`, además del header `Authorization: Bearer <token>`.
Si falta alguno o es inválido, Odoo mostrará el detalle devuelto por el BCCR.

Este módulo procesa respuestas JSON del API REST y mantiene tolerancia con respuestas XML heredadas para escenarios de compatibilidad.


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


## Consulta directa al BCCR con correo y token

Si desea probar la consulta sin usar el script, puede llamar el endpoint del BCCR enviando
los parámetros obligatorios `CorreoElectronico` y `Token`:

```bash
curl -sS "https://gee.bccr.fi.cr/indicadoreseconomicos/api/Indicador/ObtenerIndicador" \
  --get \
  --data-urlencode "Indicador=318" \
  --data-urlencode "FechaInicio=$(date -d '30 days ago' +%Y-%m-%d)" \
  --data-urlencode "FechaFinal=$(date +%Y-%m-%d)" \
  --data-urlencode "Nombre=Odoo" \
  --data-urlencode "SubNiveles=N" \
  --data-urlencode "CorreoElectronico=su-correo@dominio.com" \
  --data-urlencode "Token=su-token" \
  -H "Authorization: Bearer su-token"
```



## Formato de fechas del API SDDE

Según la especificación técnica del SDDE del BCCR, los parámetros `FechaInicio` y `FechaFinal` suelen enviarse en formato `dd/MM/yyyy`.

Este módulo intenta primero ese formato (`dd/MM/yyyy`) y, por compatibilidad, también reintenta con `yyyy-MM-dd` si el servicio devuelve error HTTP.

## Diagnóstico técnico de autenticación (BCCR SDDE)

Si el BCCR responde: `No se encontró una suscripción para el correo electrónico y el token ingresados`,
el problema **no está en Odoo**, sino en el par `CorreoElectronico` + `Token` registrado en el BCCR.

Validaciones recomendadas:
- El correo configurado en Odoo debe coincidir **exactamente** con el correo del token (claim `email` o `sub`), incluyendo mayúsculas/minúsculas y espacios extra (se recomienda guardar sin espacios).
- El token debe estar vigente para la fecha/hora actual (`nbf` <= ahora).
- El claim `aud` esperado para SDDE externo es `SDDE-SitioExterno`.
- La suscripción debe estar activa en el portal del BCCR para ese mismo correo y token.

Este módulo ahora agrega un diagnóstico local adicional cuando detecta errores de autenticación para facilitar soporte.

