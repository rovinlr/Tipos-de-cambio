import logging

import requests

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    def _upsert_company_inverse_rate(self, currency, company, inverse_rate, buy_rate=None):
        """Crea o actualiza la tasa de la fecha de hoy para una compañía.

        ``inverse_rate`` es la VENTA (la tasa contable); ``buy_rate`` es la
        COMPRA informativa de Hacienda, guardada junto a la tasa para
        conservar el histórico y alimentar el indicador de la barra
        superior sin volver a consultar el API.
        """
        company_currency = self.env['res.currency.rate'].sudo().search(
            [
                ('currency_id', '=', currency.id),
                ('company_id', '=', company.id),
                ('name', '=', fields.Date.context_today(self)),
            ],
            limit=1,
        )

        values = {
            'currency_id': currency.id,
            'company_id': company.id,
            'name': fields.Date.context_today(self),
            'inverse_company_rate': inverse_rate,
        }
        if buy_rate:
            values['hacienda_buy_rate'] = buy_rate
        if company_currency:
            company_currency.write({
                key: value for key, value in values.items()
                if key in ('inverse_company_rate', 'hacienda_buy_rate')
            })
            return company_currency

        return self.env['res.currency.rate'].sudo().create(values)

    def _update_hacienda_rates(self):
        """Consulta Hacienda y actualiza USD/EUR para compañías habilitadas."""
        params = self.env['ir.config_parameter'].sudo()
        auto_update = params.get_param('tipos_cambio_bccr.hacienda_rate_auto_update', 'True') == 'True'
        if not auto_update:
            _logger.info('Hacienda: actualización automática desactivada en configuración')
            return True

        companies = self.env['res.company'].sudo().search([])
        if not companies:
            _logger.info('Hacienda: no hay compañías disponibles para actualizar')
            return True

        target_currencies = {
            'USD': {
                'url': 'https://api.hacienda.go.cr/indicadores/tc/dolar',
                'extract': lambda payload: payload.get('venta', {}).get('valor'),
                # La compra es informativa (indicador en barra superior e
                # histórico); la contable sigue siendo la venta.
                'extract_buy': lambda payload: payload.get('compra', {}).get('valor'),
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
                payload = response.json()
                value = conf['extract'](payload)
                if not value:
                    _logger.warning('Hacienda: no se encontró valor válido para %s', code)
                    continue
                buy_extract = conf.get('extract_buy')
                buy_value = buy_extract(payload) if buy_extract else None
                rates[code] = (float(value), float(buy_value) if buy_value else None)
            except Exception as exc:
                _logger.error('Hacienda: error consultando %s: %s', code, exc)

        if not rates:
            return True

        now = fields.Datetime.now()
        for code, (rate_value, buy_value) in rates.items():
            currency = self.search([('name', '=', code)], limit=1)
            if not currency:
                _logger.warning('Hacienda: no existe la moneda %s en esta base', code)
                continue

            for company in companies:
                self._upsert_company_inverse_rate(currency, company, rate_value, buy_rate=buy_value)

            _logger.info('Hacienda: %s actualizado a %s en %s compañías', code, rate_value, len(companies))

        params.set_param('tipos_cambio_bccr.hacienda_rate_last_sync', fields.Datetime.to_string(now))
        return True

    @api.model
    def get_hacienda_systray_info(self):
        """Datos del indicador de la barra superior (USD compra/venta).

        Lee la última tasa guardada en BD — nunca consulta el API en vivo:
        cada carga de página de cada usuario pasa por aquí. Devuelve False
        cuando no aplica (compañía no CRC o sin tasa USD) y el widget no
        se muestra.
        """
        company = self.env.company
        if (company.currency_id.name or '') != 'CRC':
            return False
        usd = self.with_context(active_test=False).search([('name', '=', 'USD')], limit=1)
        if not usd or not usd.active:
            return False
        Rate = self.env['res.currency.rate'].sudo()
        rate = Rate.search(
            [('currency_id', '=', usd.id), ('company_id', '=', company.id)],
            order='name desc', limit=1,
        ) or Rate.search(
            [('currency_id', '=', usd.id), ('company_id', '=', False)],
            order='name desc', limit=1,
        )
        if not rate or not rate.inverse_company_rate:
            return False
        return {
            'sell': rate.inverse_company_rate,
            'buy': rate.hacienda_buy_rate or False,
            'date': fields.Date.to_string(rate.name),
            'last_sync': self.env['ir.config_parameter'].sudo().get_param(
                'tipos_cambio_bccr.hacienda_rate_last_sync', ''),
        }
