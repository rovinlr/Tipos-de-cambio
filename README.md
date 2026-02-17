# Tipos_de_cambio

Módulo para Odoo 19 que agrega un proveedor de tipos de cambio para Costa Rica usando **Hacienda** sobre la arquitectura de `currency_rate_live` basada en `res.company`.

## Funcionalidad

- Agrega la opción **Hacienda CR** en `res.company.currency_provider`.
- Consulta primero el API de Hacienda para obtener:
  - Tipo de cambio de **venta USD**.
  - Tipo de cambio de **venta EUR**.

## Instalación

1. Copie la carpeta `tipos_cambio_bccr` en su ruta de addons.
2. Actualice lista de apps.
3. Verifique que esté instalado **currency_rate_live**.
4. Instale **Tipos de Cambio BCCR**.

## Configuración

En **Contabilidad → Configuración → Tipos de cambio automáticos**:

- Seleccione proveedor: **Hacienda CR**.
- El proveedor obtiene tipos de cambio de **venta** para **USD** y **EUR** desde Hacienda.

## Nota

Los valores de venta consultados (USD y EUR) se registran como `inverse_company_rate` en cada moneda correspondiente.
