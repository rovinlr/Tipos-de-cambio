from odoo import fields, models


class ResCurrencyRateProvider(models.Model):
    _inherit = 'res.currency.rate.provider'

    service = fields.Selection(
        selection_add=[('hacienda_cr', 'Hacienda Costa Rica')],
        ondelete={'hacienda_cr': 'set default'},
    )
