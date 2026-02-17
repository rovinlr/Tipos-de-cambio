#!/usr/bin/env python3
"""Prueba manual de conectividad contra el WS de indicadores del BCCR.

Uso:
  BCCR_EMAIL="correo@dominio.com" BCCR_TOKEN="..." python3 scripts/test_bccr_connection.py

Opcionales:
  BCCR_INDICADOR=318        # por defecto 318 (USD venta)
  BCCR_NOMBRE=Odoo          # por defecto Odoo
  BCCR_LOOKBACK_DAYS=30     # rango de búsqueda hacia atrás
"""

from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

ENDPOINT = (
    "https://gee.bccr.fi.cr/Indicadores/Suscripciones/WS/"
    "wsindicadoreseconomicos.asmx/ObtenerIndicadoresEconomicosXML"
)


def _get_latest_num_valor(payload: bytes):
    root = ET.fromstring(payload)
    latest = None
    for node in root.iter():
        tag = node.tag.rsplit("}", 1)[-1].upper()
        if tag == "NUM_VALOR" and node.text:
            latest = node.text.strip()
    return latest


def _extract_message(payload: bytes):
    try:
        root = ET.fromstring(payload)
    except ET.ParseError:
        return payload.decode(errors="ignore").strip() or None

    for node in root.iter():
        tag = node.tag.rsplit("}", 1)[-1].upper()
        if tag in {"MENSAJE", "ERROR", "MESSAGE", "DETAIL"} and node.text:
            detail = node.text.strip()
            if detail:
                return detail
    return None


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
        "FechaInicio": fecha_inicio.strftime("%d/%m/%Y"),
        "FechaFinal": fecha_final.strftime("%d/%m/%Y"),
        "Nombre": nombre,
        "CorreoElectronico": email,
        "SubNiveles": "N",
        "Token": token,
    }

    url = f"{ENDPOINT}?{urlencode(params)}"
    print(f"Consultando indicador {indicador} para rango {params['FechaInicio']} - {params['FechaFinal']}...")

    try:
        with urlopen(url, timeout=30) as response:
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
        print(f"Sin NUM_VALOR. Detalle: {_extract_message(payload) or 'sin detalle'}", file=sys.stderr)
        return 1

    print(f"OK: conexión exitosa. Último valor recibido: {latest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
