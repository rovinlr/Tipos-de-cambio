import logging

import requests

from odoo import models

_logger = logging.getLogger(__name__)


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    def _update_hacienda_rates(self):
        """Consulta Hacienda y actualiza USD/EUR para todas las compañías."""
        companies = self.env['res.company'].sudo().search([])
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

        for code, conf in target_currencies.items():
            try:
                response = requests.get(conf['url'], timeout=10)
                response.raise_for_status()
                value = conf['extract'](response.json())

                currency = self.search([('name', '=', code)], limit=1)
                if not currency or not value:
                    _logger.warning('Hacienda: no se encontró valor válido para %s', code)
                    continue

                rate_value = float(value)
                for company in companies:
                    currency.with_company(company).sudo().write({'inverse_company_rate': rate_value})

                _logger.info('Hacienda: %s actualizado a %s en %s compañías', code, rate_value, len(companies))
            except Exception as exc:
                _logger.error('Hacienda: error actualizando %s: %s', code, exc)

        return True
