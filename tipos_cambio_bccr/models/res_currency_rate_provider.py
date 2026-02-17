import logging

import requests

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResCurrencyRateProviderHacienda(models.Model):
    _inherit = 'res.currency.rate.provider'

    HACIENDA_ENDPOINTS = {
        'USD': 'https://api.hacienda.go.cr/indicadores/tc/dolar',
        'EUR': 'https://api.hacienda.go.cr/indicadores/tc/euro',
    }

    service = fields.Selection(
        selection_add=[('hacienda_cr', 'Ministerio de Hacienda (Costa Rica)')],
        ondelete={'hacienda_cr': 'set default'},
    )

    def _hacienda_extract_rate(self, currency_code, payload):
        if not isinstance(payload, dict):
            raise UserError(_('Respuesta inesperada de Hacienda para %s.') % currency_code)

        if currency_code == 'EUR':
            eur_value = payload.get('colones')
            if eur_value in (None, ''):
                raise UserError(_('Hacienda no devolvió "colones" para %s.') % currency_code)
            return float(eur_value)

        sale_info = payload.get('venta')
        if not isinstance(sale_info, dict) or sale_info.get('valor') in (None, ''):
            raise UserError(_('Hacienda no devolvió "venta.valor" para %s.') % currency_code)

        return float(sale_info['valor'])

    def _get_hacienda_cr_rates(self):
        """Consulta Hacienda y devuelve solo los valores para USD y EUR."""
        self.ensure_one()

        rates = {}
        for currency_code, endpoint in self.HACIENDA_ENDPOINTS.items():
            try:
                response = requests.get(
                    endpoint,
                    headers={'Accept': 'application/json', 'User-Agent': 'Odoo/19.0'},
                    timeout=20,
                )
                response.raise_for_status()
                payload = response.json()
                rates[currency_code] = self._hacienda_extract_rate(currency_code, payload)
            except requests.exceptions.RequestException as exc:
                _logger.error('Error consultando %s en Hacienda: %s', currency_code, exc)
            except (TypeError, ValueError, UserError) as exc:
                _logger.error('Error procesando %s en Hacienda: %s', currency_code, exc)

        return rates

    def _update_all_rates(self):
        """Actualiza únicamente USD y EUR usando inverse_company_rate por compañía."""
        providers = self.search([('service', '=', 'hacienda_cr')])
        for provider in providers:
            external_rates = provider._get_hacienda_cr_rates()
            if not external_rates:
                _logger.warning('No se obtuvieron tipos de cambio desde Hacienda para %s.', provider.company_id.display_name)
                continue

            currencies = self.env['res.currency'].search([
                ('name', 'in', ['USD', 'EUR']),
                ('active', '=', True),
            ])

            for currency in currencies:
                rate_value = external_rates.get(currency.name)
                if not rate_value:
                    continue

                currency.with_company(provider.company_id).write({
                    'inverse_company_rate': rate_value,
                })
                _logger.info(
                    'Tipo de cambio actualizado para %s (%s): %s',
                    currency.name,
                    provider.company_id.display_name,
                    rate_value,
                )

        return True
