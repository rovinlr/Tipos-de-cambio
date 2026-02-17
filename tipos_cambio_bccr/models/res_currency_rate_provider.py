import requests

from odoo import _, fields, models
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = 'res.company'

    HACIENDA_ENDPOINTS = {
        'USD': 'https://api.hacienda.go.cr/indicadores/tc/dolar',
        'EUR': 'https://api.hacienda.go.cr/indicadores/tc/euro',
    }

    currency_provider = fields.Selection(
        selection_add=[('bccr', 'Hacienda CR')],
        ondelete={'bccr': 'set null'},
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
        self.ensure_one()

        supported_codes = {'CRC', 'USD', 'EUR'}
        company_code = (self.currency_id.name or '').strip().upper()
        if company_code:
            supported_codes.add(company_code)

        return sorted(supported_codes)

    def _get_supported_currencies_bccr(self):
        self.ensure_one()
        currency_codes = self._get_bccr_supported_currencies()
        return self.env['res.currency'].search([('name', 'in', currency_codes)])

    def _get_supported_currencies(self):
        self.ensure_one()

        if self.currency_provider == 'bccr':
            return self._get_supported_currencies_bccr()

        return super()._get_supported_currencies()

    def _hacienda_fetch_sale_rate(self, currency_code):
        self.ensure_one()

        endpoint = self.HACIENDA_ENDPOINTS.get(currency_code)
        if not endpoint:
            raise UserError(
                _(
                    'Hacienda no publica tipo de cambio para %s. '
                    'Solo están disponibles USD (dólar) y EUR (euro).'
                ) % currency_code
            )

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


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    bccr_skip_unavailable_currencies = fields.Boolean(
        related='company_id.bccr_skip_unavailable_currencies',
        readonly=False,
    )
