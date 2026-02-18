import logging

import requests

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    def _update_hacienda_rates(self):
        """Consulta Hacienda y actualiza USD/EUR para compañías habilitadas."""
        companies = self.env['res.company'].sudo().search([('hacienda_rate_auto_update', '=', True)])
        if not companies:
            _logger.info('Hacienda: no hay compañías con actualización automática activa')
            return True

        target_currencies = {
            'USD': {
                'url': 'https://api.hacienda.go.cr/indicadores/tc/dolar',
                'extract': lambda payload: payload.get('venta', {}).get('valor'),
            },
            'EUR': {
                'url': 'https://api.hacienda.go.cr/indicadores/tc/euro',
                'extract': lambda payload: payload.get('colones'),
            },
        }

        rates = {}
        for code, conf in target_currencies.items():
            try:
                response = requests.get(conf['url'], timeout=10)
                response.raise_for_status()
                value = conf['extract'](response.json())
                if not value:
                    _logger.warning('Hacienda: no se encontró valor válido para %s', code)
                    continue
                rates[code] = float(value)
            except Exception as exc:
                _logger.error('Hacienda: error consultando %s: %s', code, exc)

        if not rates:
            return True

        now = fields.Datetime.now()
        for code, rate_value in rates.items():
            currency = self.search([('name', '=', code)], limit=1)
            if not currency:
                _logger.warning('Hacienda: no existe la moneda %s en esta base', code)
                continue

            for company in companies:
                currency.with_company(company).sudo().write({'inverse_company_rate': rate_value})

            _logger.info('Hacienda: %s actualizado a %s en %s compañías', code, rate_value, len(companies))

        companies.sudo().write({'hacienda_rate_last_sync': now})
        return True
