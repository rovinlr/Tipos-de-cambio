from odoo.exceptions import UserError


def pre_init_check(cr):
    cr.execute("SELECT 1 FROM ir_model WHERE model = %s LIMIT 1", ('res.currency.rate.provider',))
    if not cr.fetchone():
        raise UserError(
            "El modelo 'res.currency.rate.provider' no está disponible en esta base de datos. "
            "Este módulo requiere la funcionalidad de proveedores automáticos de tipo de cambio "
            "(edición de Odoo que la incluya)."
        )
