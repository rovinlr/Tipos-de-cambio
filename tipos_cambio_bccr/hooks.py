from odoo.exceptions import UserError


def pre_init_check(env):
    """Validate dependencies before module installation.

    Odoo calls ``pre_init_hook`` with an Environment in recent versions.
    """
    env.cr.execute(
        "SELECT 1 FROM ir_model WHERE model = %s LIMIT 1",
        ("res.currency.rate.provider",),
    )
    if not env.cr.fetchone():
        raise UserError(
            "El modelo 'res.currency.rate.provider' no está disponible en esta base de datos. "
            "Este módulo requiere la funcionalidad de proveedores automáticos de tipo de cambio "
            "(edición de Odoo que la incluya)."
        )
