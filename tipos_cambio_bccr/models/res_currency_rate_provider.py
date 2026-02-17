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

    currency_provider = fields.Selection(
        selection_add=[('bccr', 'Banco Central de Costa Rica')],
        ondelete={'bccr': 'set null'},
    )
    bccr_name = fields.Char(
        string='Nombre BCCR (legado)',
        compute='_compute_bccr_settings',
        inverse='_inverse_bccr_name',
        help='Nombre requerido por el servicio web del BCCR.',
    )
    bccr_email = fields.Char(
        string='Correo BCCR (legado)',
        compute='_compute_bccr_settings',
        inverse='_inverse_bccr_email',
        help='Correo requerido por el servicio web del BCCR.',
    )
    bccr_token = fields.Char(
        string='Token BCCR',
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

    def _parse_bccr_data(self, available_currencies):
        self.ensure_one()

        rates = {}
        today = fields.Date.context_today(self)
        target_date = today if isinstance(today, date) else fields.Date.to_date(today)

        currency_names = {currency.name for currency in available_currencies}
        if 'USD' in currency_names:
            usd_indicator = self.bccr_usd_sale_indicator or self.BCCR_DEFAULT_USD_SALE_INDICATOR
            rates['USD'] = self._bccr_fetch_indicator(usd_indicator, target_date)

        if 'EUR' in currency_names:
            eur_indicator = self.bccr_eur_sale_indicator or self.BCCR_DEFAULT_EUR_SALE_INDICATOR
            rates['EUR'] = self._bccr_fetch_indicator(eur_indicator, target_date)

        return rates

    def _bccr_fetch_indicator(self, indicator, requested_date):
        self.ensure_one()

        if not self.bccr_token:
            raise UserError(_('Debe configurar el token SDDE del BCCR.'))

        date_end = requested_date
        date_start = requested_date - timedelta(days=self.BCCR_LOOKBACK_DAYS)
        date_start_display = date_start.strftime('%Y-%m-%d')
        date_end_display = date_end.strftime('%Y-%m-%d')

        endpoint = 'https://gee.bccr.fi.cr/indicadoreseconomicos/api/Indicador/ObtenerIndicador'
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Odoo/19.0',
            'Authorization': f"Bearer {self.bccr_token.strip()}",
        }

        payload = None
        last_http_error = None
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
            raise UserError(
                _('No se pudo consultar el BCCR: HTTP %s (%s)') % (status_code, endpoint)
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
