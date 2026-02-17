#!/usr/bin/env python3
"""Prueba manual de conectividad contra el API de Hacienda.

Uso:
  python3 scripts/test_hacienda_connection.py

Opcionales:
  HACIENDA_TIMEOUT=20
"""

from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ENDPOINTS = {
    'USD': 'https://api.hacienda.go.cr/indicadores/tc/dolar',
    'EUR': 'https://api.hacienda.go.cr/indicadores/tc/euro',
}


def _extract_rate(currency_code: str, payload: dict) -> float:
    if currency_code == 'EUR':
        value = payload.get('colones')
        if value in (None, ''):
            raise ValueError('Hacienda no devolvió "colones" para EUR')
        return float(value)

    sale_info = payload.get('venta')
    if not isinstance(sale_info, dict) or sale_info.get('valor') in (None, ''):
        raise ValueError('Hacienda no devolvió "venta.valor" para USD')
    return float(sale_info['valor'])


def main() -> int:
    timeout = int(os.getenv('HACIENDA_TIMEOUT', '20'))

    for currency_code, endpoint in ENDPOINTS.items():
        request = Request(endpoint, headers={
            'Accept': 'application/json',
            'User-Agent': 'Odoo/19.0',
        })
        print(f'Consultando {currency_code} en {endpoint}...')

        try:
            with urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode('utf-8'))
        except HTTPError as exc:
            detail = exc.read().decode(errors='ignore').strip()
            print(f'HTTP ERROR {exc.code} ({currency_code}): {detail or exc.reason}', file=sys.stderr)
            return 1
        except URLError as exc:
            print(f'ERROR de red ({currency_code}): {exc}', file=sys.stderr)
            return 1
        except json.JSONDecodeError as exc:
            print(f'ERROR JSON inválido ({currency_code}): {exc}', file=sys.stderr)
            return 1

        if not isinstance(payload, dict):
            print(f'ERROR payload inesperado ({currency_code}): {payload!r}', file=sys.stderr)
            return 1

        try:
            rate = _extract_rate(currency_code, payload)
        except (TypeError, ValueError) as exc:
            print(f'ERROR al extraer tipo de cambio ({currency_code}): {exc}', file=sys.stderr)
            return 1

        print(f'OK {currency_code}: {rate}')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
