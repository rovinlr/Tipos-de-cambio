from datetime import date
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import HTTPError
import xml.etree.ElementTree as ET

from odoo import _, fields, models
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = 'res.company'

    currency_provider = fields.Selection(
        selection_add=[('bccr', 'Banco Central de Costa Rica')],
        ondelete={'bccr': 'set null'},
    )
    bccr_name = fields.Char(
        string='Nombre BCCR',
        default='Odoo',
        help='Nombre requerido por el servicio web del BCCR.',
    )
    bccr_email = fields.Char(
        string='Correo BCCR',
        default='noreply@example.com',
        help='Correo requerido por el servicio web del BCCR.',
    )
    bccr_token = fields.Char(
        string='Token BCCR',
        help='Token requerido por el servicio web del BCCR.',
    )
    bccr_usd_indicator = fields.Char(
        string='Indicador USD venta',
        default='318',
        help='Código de indicador del tipo de cambio de venta USD en BCCR.',
    )
    bccr_eur_indicator = fields.Char(
        string='Indicador EUR venta',
        default='333',
        help='Código de indicador del tipo de cambio de venta EUR en BCCR.',
    )

    def _parse_bccr_data(self, available_currencies):
        self.ensure_one()

        rates = {}
        today = fields.Date.context_today(self)
        target_date = today if isinstance(today, date) else fields.Date.to_date(today)

        currency_names = {currency.name for currency in available_currencies}
        if 'USD' in currency_names:
            rates['USD'] = self._bccr_fetch_indicator(self.bccr_usd_indicator, target_date)

        if 'EUR' in currency_names:
            rates['EUR'] = self._bccr_fetch_indicator(self.bccr_eur_indicator, target_date)

        return rates

    def _bccr_fetch_indicator(self, indicator, requested_date):
        self.ensure_one()

        if not indicator:
            raise UserError(_('Debe configurar el indicador BCCR para esta moneda.'))

        if not self.bccr_email:
            raise UserError(_('Debe configurar el correo BCCR.'))
        if not self.bccr_token:
            raise UserError(_('Debe configurar el token BCCR.'))

        date_str = requested_date.strftime('%d/%m/%Y')
        params = {
            'Indicador': indicator,
            'FechaInicio': date_str,
            'FechaFinal': date_str,
            'Nombre': self.bccr_name or 'Odoo',
            'SubNiveles': 'N',
            'CorreoElectronico': self.bccr_email,
            'Token': self.bccr_token,
        }

        endpoint = 'https://gee.bccr.fi.cr/Indicadores/Suscripciones/WS/wsindicadoreseconomicos.asmx/ObtenerIndicadoresEconomicosXML'
        url = f"{endpoint}?{urlencode(params)}"

        try:
            with urlopen(url, timeout=20) as response:
                payload = response.read()
        except HTTPError as exc:
            detail = self._bccr_extract_error(exc.read())
            if detail:
                raise UserError(_('No se pudo consultar el BCCR: %s') % detail) from exc
            raise UserError(_('No se pudo consultar el BCCR: HTTP %s') % exc.code) from exc
        except Exception as exc:
            raise UserError(_('No se pudo consultar el BCCR: %s') % exc) from exc

        value = self._bccr_extract_value(payload)
        if value is None:
            raise UserError(
                _('No se encontró valor para el indicador %s en la fecha %s.') % (indicator, date_str)
            )

        return value

    @staticmethod
    def _bccr_extract_value(payload):
        root = ET.fromstring(payload)

        for node in root.iter():
            tag_name = node.tag.rsplit('}', 1)[-1].upper()
            if tag_name != 'NUM_VALOR' or not node.text:
                continue

            raw_value = node.text.strip().replace(' ', '')
            if ',' in raw_value and '.' in raw_value:
                normalized = raw_value.replace(',', '')
            else:
                normalized = raw_value.replace(',', '.')

            return float(normalized)

        return None

    @staticmethod
    def _bccr_extract_error(payload):
        if not payload:
            return None

        try:
            root = ET.fromstring(payload)
        except ET.ParseError:
            return payload.decode(errors='ignore').strip() or None

        for node in root.iter():
            tag_name = node.tag.rsplit('}', 1)[-1].upper()
            if tag_name in {'MENSAJE', 'ERROR', 'DETAIL', 'MESSAGE'} and node.text:
                detail = node.text.strip()
                if detail:
                    return detail

        return root.text.strip() if root.text else None


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    bccr_name = fields.Char(related='company_id.bccr_name', readonly=False)
    bccr_email = fields.Char(related='company_id.bccr_email', readonly=False)
    bccr_token = fields.Char(related='company_id.bccr_token', readonly=False)
    bccr_usd_indicator = fields.Char(related='company_id.bccr_usd_indicator', readonly=False)
    bccr_eur_indicator = fields.Char(related='company_id.bccr_eur_indicator', readonly=False)
