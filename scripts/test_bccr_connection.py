#!/usr/bin/env python3
"""Prueba manual de conectividad contra el API REST de indicadores del BCCR.

Uso:
  BCCR_EMAIL="correo@dominio.com" BCCR_TOKEN="..." python3 scripts/test_bccr_connection.py

Opcionales:
  BCCR_INDICADOR=318        # por defecto 318 (USD venta)
  BCCR_NOMBRE=Odoo          # por defecto Odoo
  BCCR_LOOKBACK_DAYS=30     # rango de búsqueda hacia atrás
"""

from __future__ import annotations

import base64
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ENDPOINT = "https://gee.bccr.fi.cr/indicadoreseconomicos/api/Indicador/ObtenerIndicador"


def _parse_number(raw_value):
    value = str(raw_value).strip().replace(' ', '')
    if ',' in value and '.' in value:
        value = value.replace(',', '')
    else:
        value = value.replace(',', '.')
    return float(value)


def _get_latest_num_valor(payload: bytes):
    try:
        parsed = json.loads(payload.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None

    if not isinstance(parsed, list):
        return None

    latest = None
    for row in parsed:
        if not isinstance(row, dict):
            continue
        value = row.get('NumValor')
        if value in (None, ''):
            continue
        latest = _parse_number(value)
    return latest


def _extract_message(payload: bytes):
    try:
        parsed = json.loads(payload.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return payload.decode(errors='ignore').strip() or None

    if isinstance(parsed, dict):
        for key in ('message', 'error', 'detail', 'Message', 'Error', 'Detail'):
            value = parsed.get(key)
            if value:
                return str(value).strip()
        if parsed:
            return json.dumps(parsed, ensure_ascii=False)

    if isinstance(parsed, list) and not parsed:
        return 'respuesta vacía'

    return None


def _token_diagnostics(token: str, configured_email: str):
    if token.count('.') != 2:
        return None

    payload_segment = token.split('.')[1]
    payload_segment += '=' * (-len(payload_segment) % 4)

    try:
        claims = json.loads(base64.urlsafe_b64decode(payload_segment.encode('utf-8')).decode('utf-8'))
    except Exception:
        return None

    warnings = []
    token_email = (claims.get('email') or claims.get('sub') or '').strip().lower()
    email = (configured_email or '').strip().lower()
    if token_email and email and token_email != email:
        warnings.append(f'email en token ({token_email}) distinto al configurado ({email})')

    nbf = claims.get('nbf')
    if isinstance(nbf, (int, float)):
        valid_from = datetime.fromtimestamp(nbf, timezone.utc)
        if valid_from > datetime.now(timezone.utc):
            warnings.append(f'token no vigente aún (nbf={valid_from.isoformat()})')

    aud = claims.get('aud')
    if aud and aud != 'SDDE-SitioExterno':
        warnings.append(f'aud inesperado: {aud}')

    return '; '.join(warnings) if warnings else None


def main() -> int:
    email = os.getenv("BCCR_EMAIL")
    token = os.getenv("BCCR_TOKEN")

    if not email or not token:
        print("ERROR: Debe definir BCCR_EMAIL y BCCR_TOKEN.", file=sys.stderr)
        return 2

    indicador = os.getenv("BCCR_INDICADOR", "318")
    nombre = os.getenv("BCCR_NOMBRE", "Odoo")
    lookback_days = int(os.getenv("BCCR_LOOKBACK_DAYS", "30"))

    fecha_final = date.today()
    fecha_inicio = fecha_final - timedelta(days=lookback_days)

    params = {
        "Indicador": indicador,
        "FechaInicio": fecha_inicio.strftime("%Y-%m-%d"),
        "FechaFinal": fecha_final.strftime("%Y-%m-%d"),
        "Nombre": nombre,
        "CorreoElectronico": email,
        "SubNiveles": "N",
        "Token": token,
    }

    url = f"{ENDPOINT}?{urlencode(params)}"
    request = Request(url, headers={
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Odoo/19.0",
        "Authorization": f"Bearer {token}",
    })
    print(f"Consultando indicador {indicador} para rango {params['FechaInicio']} - {params['FechaFinal']}...")

    try:
        with urlopen(request, timeout=30) as response:
            payload = response.read()
    except HTTPError as exc:
        detail = _extract_message(exc.read())
        print(f"HTTP ERROR {exc.code}: {detail or exc.reason}", file=sys.stderr)
        return 1
    except URLError as exc:
        print(f"ERROR de red: {exc}", file=sys.stderr)
        return 1

    latest = _get_latest_num_valor(payload)
    if latest is None:
        detail = _extract_message(payload) or 'sin detalle'
        print(f"Sin NumValor. Detalle: {detail}", file=sys.stderr)
        if 'suscripción' in detail.lower() or 'token' in detail.lower():
            diagnostics = _token_diagnostics(token, email)
            if diagnostics:
                print(f"Diagnóstico local JWT: {diagnostics}", file=sys.stderr)
        return 1

    print(f"OK: conexión exitosa. Último valor recibido: {latest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
