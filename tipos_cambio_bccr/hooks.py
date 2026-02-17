from odoo.exceptions import UserError


def pre_init_check(env):
    """Validate dependencies before module installation.

    Odoo calls ``pre_init_hook`` with an Environment in recent versions.
    """
    env.cr.execute(
        "SELECT 1 FROM ir_model WHERE model = %s LIMIT 1",
        ("res.currency.rate.provider",),
    )
    if env.cr.fetchone():
        return

    env.cr.execute(
        """
        SELECT state
          FROM ir_module_module
         WHERE name = %s
         LIMIT 1
        """,
        ("currency_rate_live",),
    )
    module_state = env.cr.fetchone()
    if not module_state:
        detail = (
            "No se encontró el módulo técnico 'currency_rate_live' en esta instalación. "
            "Verifique que su edición de Odoo incluya proveedores automáticos de tipo de cambio."
        )
    else:
        detail = (
            "El módulo técnico 'currency_rate_live' existe, pero el modelo "
            "'res.currency.rate.provider' no está disponible en la base de datos "
            "(estado: %s)."
        ) % module_state[0]

    raise UserError(
        "No es posible instalar 'Tipos de Cambio BCCR' porque faltan funcionalidades "
        "base de proveedores automáticos de tipo de cambio. "
        f"{detail}"
    )
