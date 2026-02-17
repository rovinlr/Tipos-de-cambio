# Tipos_de_cambio

Módulo para Odoo 19 que agrega un proveedor de tipos de cambio para Costa Rica usando **Hacienda** sobre la arquitectura de `currency_rate_live` basada en `res.company`.

> Nota: el nombre técnico del módulo (`tipos_cambio_bccr`) se mantiene por compatibilidad, pero la consulta activa es a Hacienda.

## Funcionalidad

- Agrega la opción **Hacienda CR** en `res.company.currency_provider`.
- Consulta el API de Hacienda para obtener:
  - Tipo de cambio de **venta USD**.
  - Tipo de cambio en **colones EUR**.
- Permite omitir monedas sin dato disponible para no bloquear la actualización automática.

## Instalación

1. Copie la carpeta `tipos_cambio_bccr` en su ruta de addons.
2. Actualice lista de apps.
3. Verifique que esté instalado **currency_rate_live**.
4. Instale **Tipos de Cambio BCCR**.

## Configuración

En **Contabilidad → Configuración → Tipos de cambio automáticos**:

- Seleccione proveedor: **Hacienda CR**.
- Active/desactive la opción de omitir monedas no disponibles según su operación.

## Prueba manual de conexión

Ejecute:

```bash
python3 scripts/test_hacienda_connection.py
```

## Nota

Los valores consultados (USD y EUR) se registran como `inverse_company_rate` en cada moneda correspondiente.
