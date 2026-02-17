from datetime import date
from urllib.parse import urlencode
from urllib.request import urlopen
import xml.etree.ElementTree as ET

from odoo import _, fields, models
from odoo.exceptions import UserError


class ResCurrencyRateProvider(models.Model):
    _inherit = 'res.currency.rate.provider'

    service = fields.Selection(
        selection_add=[('bccr', 'Banco Central de Costa Rica')],
        ondelete={'bccr': 'set default'},
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
        help='Token opcional para servicios del BCCR que lo requieran.',
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

    def _obtain_rates(self, base_currency, currencies, date_from, date_to):
        if self.service != 'bccr':
            return super()._obtain_rates(base_currency, currencies, date_from, date_to)

        if not currencies:
            return {}

        target_date = date_from if isinstance(date_from, date) else fields.Date.to_date(date_from)
        rates = {}
        currency_map = {currency.name: currency for currency in currencies}

        if 'USD' in currency_map:
            rates[currency_map['USD']] = self._bccr_fetch_indicator(
                self.bccr_usd_indicator,
                target_date,
            )

        if 'EUR' in currency_map:
            rates[currency_map['EUR']] = self._bccr_fetch_indicator(
                self.bccr_eur_indicator,
                target_date,
            )

        return rates

    def _bccr_fetch_indicator(self, indicator, requested_date):
        if not indicator:
            raise UserError(_('Debe configurar el indicador BCCR para esta moneda.'))

        date_str = requested_date.strftime('%d/%m/%Y')
        params = {
            'Indicador': indicator,
            'FechaInicio': date_str,
            'FechaFinal': date_str,
            'Nombre': self.bccr_name or 'Odoo',
            'SubNiveles': 'N',
            'CorreoElectronico': self.bccr_email or 'noreply@example.com',
        }
        if self.bccr_token:
            params['Token'] = self.bccr_token

        endpoint = 'https://gee.bccr.fi.cr/Indicadores/Suscripciones/WS/wsindicadoreseconomicos.asmx/ObtenerIndicadoresEconomicosXML'
        url = f"{endpoint}?{urlencode(params)}"

        try:
            with urlopen(url, timeout=20) as response:
                payload = response.read()
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
            # BCCR puede devolver coma decimal ("534,12") o punto decimal
            # con separador de miles en coma ("1,234.56").
            if ',' in raw_value and '.' in raw_value:
                normalized = raw_value.replace(',', '')
            else:
                normalized = raw_value.replace(',', '.')

            return float(normalized)

        return None
