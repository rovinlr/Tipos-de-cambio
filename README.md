# Tipos_de_cambio

Módulo para Odoo 19 que agrega un proveedor de tipos de cambio del **Banco Central de Costa Rica (BCCR)**.

## Funcionalidad

- Agrega la opción **Banco Central de Costa Rica** en `res.currency.rate.provider`.
- Consulta el web service del BCCR para obtener:
  - Tipo de cambio de **venta USD** (indicador por defecto `318`).
  - Tipo de cambio de **EUR** (indicador por defecto `333`).
- Compatible con Odoo 19, donde la tasa se guarda como `inverse_company_rate`.

## Instalación

1. Copie la carpeta `tipos_cambio_bccr` en su ruta de addons.
2. Actualice lista de apps.
3. Verifique que esté instalado **currency_rate_live** (proveedores automáticos de tipo de cambio).
4. Instale **Tipos de Cambio BCCR**.

## Configuración

En el proveedor de tipo de cambio:

- Seleccione servicio: **Banco Central de Costa Rica**.
- Configure:
  - Nombre y correo para el servicio del BCCR.
  - Token (opcional, si su endpoint lo requiere).
  - Indicadores para USD y EUR.

## Nota

Los indicadores pueden cambiar con el tiempo. Si BCCR actualiza códigos, ajústelos en la configuración del proveedor.
