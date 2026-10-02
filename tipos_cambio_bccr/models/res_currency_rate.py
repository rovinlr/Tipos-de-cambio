from odoo import fields, models


class ResCurrencyRate(models.Model):
    _inherit = 'res.currency.rate'

    hacienda_buy_rate = fields.Float(
        string='Compra (Hacienda)',
        digits=(12, 5),
        help='Tipo de cambio de COMPRA publicado por Hacienda para esta '
             'fecha. Informativo: la tasa contable de Odoo es la de VENTA.',
    )
