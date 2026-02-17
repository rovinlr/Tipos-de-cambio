from datetime import date, datetime, timedelta, timezone
import base64
import json
import xml.etree.ElementTree as ET
import requests

from odoo import _, fields, models
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = 'res.company'

    BCCR_DEFAULT_USD_SALE_INDICATOR = '318'
    BCCR_DEFAULT_EUR_SALE_INDICATOR = '333'
    BCCR_LOOKBACK_DAYS = 30
    BCCR_DATE_FORMATS = ('%d/%m/%Y', '%Y-%m-%d')
    BCCR_ENDPOINTS = (
        'https://gee.bccr.fi.cr/indicadoreseconomicos/api/Indicador/ObtenerIndicador',
        'https://gee.bccr.fi.cr/Indicadores/Suscripciones/WS/wsindicadoreseconomicos.asmx/ObtenerIndicadoresEconomicos',
        'https://gee.bccr.fi.cr/Indicadores/Suscripciones/WS/wsindicadoreseconomicos.asmx/ObtenerIndicadoresEconomicosXML',
    )
    HACIENDA_ENDPOINTS = {
        'USD': 'https://api.hacienda.go.cr/indicadores/tc/dolar',
        'EUR': 'https://api.hacienda.go.cr/indicadores/tc/euro',
    }

    currency_provider = fields.Selection(
        selection_add=[('bccr', 'Hacienda CR')],
        ondelete={'bccr': 'set null'},
    )
    bccr_name = fields.Char(
        string='Nombre BCCR (legado)',
        compute='_compute_bccr_settings',
        inverse='_inverse_bccr_name',
        help='Campo legado del proveedor anterior del BCCR.',
    )
    bccr_email = fields.Char(
        string='Correo BCCR (legado)',
        compute='_compute_bccr_settings',
        inverse='_inverse_bccr_email',
        help='Campo legado del proveedor anterior del BCCR.',
    )
    bccr_token = fields.Char(
        string='Token SDDE (legado)',
        compute='_compute_bccr_settings',
        inverse='_inverse_bccr_token',
        help='Token requerido por el servicio web del BCCR.',
    )
    bccr_usd_sale_indicator = fields.Char(
        string='Indicador USD venta',
        compute='_compute_bccr_settings',
        inverse='_inverse_bccr_usd_sale_indicator',
        help='Código de indicador BCCR para tipo de cambio de venta USD.',
    )
    bccr_eur_sale_indicator = fields.Char(
        string='Indicador EUR venta',
        compute='_compute_bccr_settings',
        inverse='_inverse_bccr_eur_sale_indicator',
        help='Código de indicador BCCR para tipo de cambio de venta EUR.',
    )
    bccr_skip_unavailable_currencies = fields.Boolean(
        string='Omitir monedas sin tipo de cambio disponible',
        compute='_compute_bccr_settings',
        inverse='_inverse_bccr_skip_unavailable_currencies',
        help='Si está activo, se omiten monedas sin valor disponible en Hacienda en lugar de fallar.',
    )

    def _bccr_param_key(self, field_name):
        self.ensure_one()
        return f'tipos_cambio_bccr.{field_name}.{self.id}'

    def _compute_bccr_settings(self):
        params = self.env['ir.config_parameter'].sudo()
        for company in self:
            company.bccr_name = params.get_param(company._bccr_param_key('bccr_name'), 'Odoo')
            company.bccr_email = params.get_param(company._bccr_param_key('bccr_email'), 'noreply@example.com')
            company.bccr_token = params.get_param(company._bccr_param_key('bccr_token'), False)
            company.bccr_usd_sale_indicator = params.get_param(
                company._bccr_param_key('bccr_usd_sale_indicator'),
                company.BCCR_DEFAULT_USD_SALE_INDICATOR,
            )
            company.bccr_eur_sale_indicator = params.get_param(
                company._bccr_param_key('bccr_eur_sale_indicator'),
                company.BCCR_DEFAULT_EUR_SALE_INDICATOR,
            )
            company.bccr_skip_unavailable_currencies = (
                params.get_param(
                    company._bccr_param_key('bccr_skip_unavailable_currencies'),
                    'True',
                )
                == 'True'
            )

    def _bccr_inverse_field(self, field_name, default=False):
        params = self.env['ir.config_parameter'].sudo()
        for company in self:
            value = company[field_name]
            params.set_param(company._bccr_param_key(field_name), value or default)

    def _inverse_bccr_name(self):
        self._bccr_inverse_field('bccr_name', 'Odoo')

    def _inverse_bccr_email(self):
        self._bccr_inverse_field('bccr_email', 'noreply@example.com')

    def _inverse_bccr_token(self):
        self._bccr_inverse_field('bccr_token', False)

    def _inverse_bccr_usd_sale_indicator(self):
        self._bccr_inverse_field('bccr_usd_sale_indicator', self.BCCR_DEFAULT_USD_SALE_INDICATOR)

    def _inverse_bccr_eur_sale_indicator(self):
        self._bccr_inverse_field('bccr_eur_sale_indicator', self.BCCR_DEFAULT_EUR_SALE_INDICATOR)

    def _inverse_bccr_skip_unavailable_currencies(self):
        self._bccr_inverse_field('bccr_skip_unavailable_currencies', True)

    def _parse_bccr_data(self, available_currencies):
        self.ensure_one()

        rates = {}
        currencies_to_fetch = [currency.name for currency in available_currencies if currency.active]
        for currency_name in ('USD', 'EUR'):
            if currency_name not in currencies_to_fetch:
                continue

            try:
                rates[currency_name] = self._hacienda_fetch_sale_rate(currency_name)
            except UserError:
                if self.bccr_skip_unavailable_currencies:
                    continue
                raise

        return rates

    def _get_bccr_supported_currencies(self):
        """Proveedor Hacienda CR: moneda base CRC y tasas de venta USD/EUR."""
        return self.env['res.currency'].search([('name', 'in', ['CRC', 'USD', 'EUR'])])

    def _get_supported_currencies_bccr(self):
        """Compatibilidad con variantes del hook de `currency_rate_live`."""
        return self._get_bccr_supported_currencies()

    def _get_rate_with_hacienda_fallback(self, currency_code, indicator):
        self.ensure_one()

        try:
            return self._hacienda_fetch_sale_rate(currency_code)
        except UserError as hacienda_error:
            if not self.bccr_token:
                raise UserError(
                    _(
                        'No se pudo consultar Hacienda para %s y no hay token SDDE configurado '
                        'para usar respaldo con BCCR. Detalle: %s'
                    ) % (currency_code, hacienda_error)
                ) from hacienda_error

            today = fields.Date.context_today(self)
            target_date = today if isinstance(today, date) else fields.Date.to_date(today)
            return self._bccr_fetch_indicator(indicator, target_date)

    def _hacienda_fetch_sale_rate(self, currency_code):
        self.ensure_one()

        endpoint = self.HACIENDA_ENDPOINTS.get(currency_code)
        if not endpoint:
            raise UserError(_('No hay endpoint de Hacienda configurado para %s.') % currency_code)

        try:
            response = requests.get(
                endpoint,
                headers={'Accept': 'application/json', 'User-Agent': 'Odoo/19.0'},
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.exceptions.RequestException as exc:
            raise UserError(_('No se pudo consultar Hacienda: %s') % exc) from exc
        except ValueError as exc:
            raise UserError(_('La respuesta de Hacienda no es JSON válido.')) from exc

        if not isinstance(payload, dict):
            raise UserError(_('Respuesta inesperada de Hacienda para %s.') % currency_code)

        if currency_code == 'EUR':
            eur_value = payload.get('colones')
            if eur_value in (None, ''):
                raise UserError(_('Hacienda no devolvió tipo de cambio colones para %s.') % currency_code)
            return float(eur_value)

        sale_info = payload.get('venta')
        if not isinstance(sale_info, dict) or sale_info.get('valor') in (None, ''):
            raise UserError(_('Hacienda no devolvió tipo de cambio de venta para %s.') % currency_code)

        return float(sale_info['valor'])

    def _bccr_fetch_indicator(self, indicator, requested_date):
        self.ensure_one()

        if not self.bccr_token:
            raise UserError(_('Debe configurar el token SDDE del BCCR.'))

        date_end = requested_date
        date_start = requested_date - timedelta(days=self.BCCR_LOOKBACK_DAYS)
        date_start_display = date_start.strftime('%Y-%m-%d')
        date_end_display = date_end.strftime('%Y-%m-%d')

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Odoo/19.0',
            'Authorization': f"Bearer {self.bccr_token.strip()}",
        }

        payload = None
        last_http_error = None
        attempted_endpoints = []
        for endpoint in self.BCCR_ENDPOINTS:
            for date_format in self.BCCR_DATE_FORMATS:
                params = {
                    'Indicador': indicator,
                    'FechaInicio': date_start.strftime(date_format),
                    'FechaFinal': date_end.strftime(date_format),
                    'Nombre': self.bccr_name or 'Odoo',
                    'CorreoElectronico': (self.bccr_email or 'noreply@example.com').strip(),
                    'SubNiveles': 'N',
                    'Token': self.bccr_token.strip(),
                }

                try:
                    response = requests.get(endpoint, params=params, headers=headers, timeout=20)
                    response.raise_for_status()
                    payload = response.content
                    break
                except requests.exceptions.HTTPError as exc:
                    last_http_error = exc
                    attempted_endpoints.append(endpoint)
                    detail = self._bccr_extract_error(
                        exc.response.content if exc.response is not None else None
                    )
                    if detail and self._bccr_is_auth_error(detail):
                        self._bccr_raise_auth_error(detail)
                    continue
                except requests.exceptions.RequestException as exc:
                    raise UserError(_('No se pudo consultar el BCCR: %s') % exc) from exc
                except Exception as exc:
                    raise UserError(_('No se pudo consultar el BCCR: %s') % exc) from exc

            if payload is not None:
                break

        if payload is None:
            detail = self._bccr_extract_error(
                (
                    last_http_error.response.content
                    if last_http_error is not None and last_http_error.response is not None
                    else None
                )
            )
            if detail:
                raise UserError(_('No se pudo consultar el BCCR: %s') % detail) from last_http_error

            status_code = (
                last_http_error.response.status_code
                if last_http_error is not None and last_http_error.response is not None
                else 'desconocido'
            )
            endpoints_info = ', '.join(sorted(set(attempted_endpoints))) or ', '.join(self.BCCR_ENDPOINTS)
            raise UserError(
                _('No se pudo consultar el BCCR: HTTP %s (endpoints: %s)') % (status_code, endpoints_info)
            ) from last_http_error

        value = self._bccr_extract_latest_value(payload)
        if value is None:
            detail = self._bccr_extract_error(payload)
            if detail:
                if self._bccr_is_auth_error(detail):
                    self._bccr_raise_auth_error(detail)
                raise UserError(
                    _(
                        'No se encontró valor para el indicador %s en el rango %s - %s. '
                        'Detalle BCCR: %s'
                    ) % (indicator, date_start_display, date_end_display, detail)
                )
            raise UserError(
                _(
                    'No se encontró valor para el indicador %s en el rango %s - %s.'
                ) % (indicator, date_start_display, date_end_display)
            )

        return value

    @staticmethod
    def _bccr_extract_latest_value(payload):
        if not payload:
            return None

        try:
            parsed_payload = json.loads(payload.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            parsed_payload = None

        if isinstance(parsed_payload, list):
            latest_value = None
            for row in parsed_payload:
                if not isinstance(row, dict):
                    continue
                row_value = row.get('NumValor')
                if row_value in (None, ''):
                    continue
                latest_value = ResCompany._parse_bccr_number(str(row_value))
            if latest_value is not None:
                return latest_value

        root = ResCompany._bccr_normalize_payload(payload)

        latest_value = None
        for node in root.iter():
            tag_name = node.tag.rsplit('}', 1)[-1].upper()
            if tag_name != 'NUM_VALOR' or not node.text:
                continue
            latest_value = ResCompany._parse_bccr_number(node.text)

        return latest_value

    @staticmethod
    def _parse_bccr_number(raw_text):
        raw_value = raw_text.strip().replace(' ', '')
        if ',' in raw_value and '.' in raw_value:
            normalized = raw_value.replace(',', '')
        else:
            normalized = raw_value.replace(',', '.')
        return float(normalized)

    @staticmethod
    def _bccr_normalize_payload(payload):
        """Normaliza respuestas del BCCR a un XML iterable.

        El BCCR expone dos variantes comunes:
          - `ObtenerIndicadoresEconomicosXML`: retorna XML directo.
          - `ObtenerIndicadoresEconomicos`: retorna un nodo `<string>` con XML serializado.
        """
        root = ET.fromstring(payload)

        inner_xml = (root.text or '').strip()
        if inner_xml.startswith('<') and inner_xml.endswith('>'):
            try:
                return ET.fromstring(inner_xml)
            except ET.ParseError:
                return root

        return root

    @staticmethod
    def _bccr_extract_error(payload):
        if not payload:
            return None

        try:
            parsed_payload = json.loads(payload.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            parsed_payload = None

        if isinstance(parsed_payload, dict):
            for key in ('message', 'error', 'detail', 'Message', 'Error', 'Detail'):
                value = parsed_payload.get(key)
                if value:
                    return str(value).strip()
            if parsed_payload:
                return json.dumps(parsed_payload, ensure_ascii=False)

        if isinstance(parsed_payload, list) and not parsed_payload:
            return _('Respuesta vacía del servicio REST del BCCR.')

        try:
            root = ResCompany._bccr_normalize_payload(payload)
        except ET.ParseError:
            return payload.decode(errors='ignore').strip() or None

        for node in root.iter():
            tag_name = node.tag.rsplit('}', 1)[-1].upper()
            if tag_name in {'MENSAJE', 'ERROR', 'DETAIL', 'MESSAGE'} and node.text:
                detail = node.text.strip()
                if detail:
                    return detail

        return root.text.strip() if root.text else None

    @staticmethod
    def _bccr_is_auth_error(detail):
        detail_text = detail.lower()
        return (
            'token' in detail_text
            and (
                'suscripción' in detail_text
                or 'autentic' in detail_text
                or 'inválid' in detail_text
                or 'no válida' in detail_text
            )
        )

    def _bccr_token_diagnostics(self):
        """Valida localmente claims comunes del JWT SDDE para mensajes de soporte."""
        self.ensure_one()

        token = (self.bccr_token or '').strip()
        if not token or token.count('.') != 2:
            return None

        payload_segment = token.split('.')[1]
        payload_segment += '=' * (-len(payload_segment) % 4)

        try:
            decoded_payload = base64.urlsafe_b64decode(payload_segment.encode('utf-8'))
            claims = json.loads(decoded_payload.decode('utf-8'))
        except Exception:
            return None

        warnings = []

        token_email = (claims.get('email') or claims.get('sub') or '').strip().lower()
        configured_email = (self.bccr_email or '').strip().lower()
        if token_email and configured_email and token_email != configured_email:
            warnings.append(
                _('el correo del token (%s) no coincide con el correo configurado (%s)')
                % (token_email, configured_email)
            )

        now_utc = datetime.now(timezone.utc)
        not_before = claims.get('nbf')
        if isinstance(not_before, (int, float)):
            valid_from = datetime.fromtimestamp(not_before, timezone.utc)
            if valid_from > now_utc:
                warnings.append(
                    _('el token todavía no está vigente (nbf=%s UTC)')
                    % valid_from.strftime('%Y-%m-%d %H:%M:%S')
                )

        audience = claims.get('aud')
        if audience and audience != 'SDDE-SitioExterno':
            warnings.append(
                _('el claim aud esperado es "SDDE-SitioExterno" y se recibió "%s"') % audience
            )

        return '; '.join(warnings) if warnings else None

    def _bccr_raise_auth_error(self, detail):
        self.ensure_one()

        token_diagnostics = self._bccr_token_diagnostics()
        diagnostics_note = ''
        if token_diagnostics:
            diagnostics_note = _(' Diagnóstico local: %s') % token_diagnostics

        raise UserError(
            _(
                'No se pudo autenticar con el BCCR. Verifique el token SDDE configurado '
                'en la compañía. Correo configurado: %s. Token configurado: %s. '
                'Detalle BCCR: %s%s'
            ) % (
                (self.bccr_email or 'noreply@example.com').strip(),
                self._bccr_mask_token(),
                detail,
                diagnostics_note,
            )
        )

    def _bccr_mask_token(self):
        """Devuelve el token parcialmente oculto para evitar exponer secretos en errores."""
        self.ensure_one()

        token = (self.bccr_token or '').strip()
        if not token:
            return _('(vacío)')

        if len(token) <= 10:
            return '*' * len(token)

        return '%s...%s' % (token[:6], token[-4:])


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    bccr_name = fields.Char(related='company_id.bccr_name', readonly=False)
    bccr_email = fields.Char(related='company_id.bccr_email', readonly=False)
    bccr_token = fields.Char(related='company_id.bccr_token', readonly=False)
    bccr_usd_sale_indicator = fields.Char(related='company_id.bccr_usd_sale_indicator', readonly=False)
    bccr_eur_sale_indicator = fields.Char(related='company_id.bccr_eur_sale_indicator', readonly=False)
    bccr_skip_unavailable_currencies = fields.Boolean(
        related='company_id.bccr_skip_unavailable_currencies',
        readonly=False,
    )
