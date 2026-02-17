# Tipos_de_cambio

Módulo para Odoo 19 que agrega el proveedor de tipos de cambio del **Banco Central de Costa Rica (BCCR)** sobre la arquitectura de `currency_rate_live` basada en `res.company`.

## Funcionalidad

- Agrega la opción **Banco Central de Costa Rica** en `res.company.currency_provider`.
- Consulta el web service del BCCR para obtener:
  - Tipo de cambio de **venta USD** (indicador por defecto `318`).
  - Tipo de cambio de **EUR** (indicador por defecto `333`).
- Expone los campos de configuración en `res.config.settings` como relacionados a la compañía.

## Instalación

1. Copie la carpeta `tipos_cambio_bccr` en su ruta de addons.
2. Actualice lista de apps.
3. Verifique que esté instalado **currency_rate_live**.
4. Instale **Tipos de Cambio BCCR**.

## Configuración

En Ajustes de contabilidad / tipos de cambio automáticos:

- Seleccione proveedor: **Banco Central de Costa Rica**.
- Configure:
  - Nombre y correo para el servicio del BCCR.
  - Token (opcional, si su endpoint lo requiere).
  - Indicadores para USD y EUR.

## Nota

Los indicadores pueden cambiar con el tiempo. Si BCCR actualiza códigos, ajústelos en la configuración.
