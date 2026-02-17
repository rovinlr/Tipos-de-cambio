# Tipos_de_cambio

Módulo para Odoo 19 que agrega el proveedor **Ministerio de Hacienda (Costa Rica)** sobre la arquitectura de `currency_rate_live` basada en `res.currency.rate.provider`.

> Nota: el nombre técnico del módulo (`tipos_cambio_bccr`) se mantiene por compatibilidad.

## Funcionalidad

- Agrega el servicio **Ministerio de Hacienda (Costa Rica)** en `res.currency.rate.provider.service`.
- Consulta el API de Hacienda para obtener:
  - **USD** desde `venta.valor`.
  - **EUR** desde `colones`.
- Actualiza exclusivamente USD y EUR para evitar conflictos con la moneda base CRC.
- Escribe los valores usando `inverse_company_rate` y respeta multi-compañía con `with_company(...)`.

## Instalación

1. Copie la carpeta `tipos_cambio_bccr` en su ruta de addons.
2. Actualice lista de apps.
3. Verifique que esté instalado **currency_rate_live**.
4. Instale **Tipos de Cambio BCCR**.

## Configuración

En **Contabilidad → Configuración → Tipos de cambio automáticos**:

- Cree/edite un proveedor con servicio **Ministerio de Hacienda (Costa Rica)**.
- Asigne la compañía correspondiente.
- Configure la ejecución automática según la frecuencia deseada.

## Prueba manual de conexión

Ejecute:

```bash
python3 scripts/test_hacienda_connection.py
```

## Nota

Los valores consultados (USD y EUR) se registran como `inverse_company_rate` en cada moneda correspondiente.
