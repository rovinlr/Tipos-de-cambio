from odoo.exceptions import UserError


def pre_init_check(env):
    """Validate dependencies before module installation.

    Odoo calls ``pre_init_hook`` with an Environment in recent versions.
    """
    required_model = "res.currency.rate.provider"

    env.cr.execute(
        "SELECT 1 FROM ir_model WHERE model = %s LIMIT 1",
        (required_model,),
    )
    if env.cr.fetchone():
        return

    env.cr.execute(
        """
        SELECT model
          FROM ir_model
         WHERE model IN (%s, %s)
         ORDER BY model
        """,
        ("res.currency.rate.source", "res.currency.rate.service"),
    )
    alternate_models = [row[0] for row in env.cr.fetchall()]

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
            f"'{required_model}' no está disponible en la base de datos "
            "(estado: %s)."
        ) % module_state[0]

    if alternate_models:
        alternates = ", ".join(alternate_models)
        detail = (
            f"{detail} Se detectaron modelos alternativos ({alternates}), "
            "lo que sugiere una variante de Odoo donde cambió la arquitectura "
            "de proveedores automáticos."
        )

    raise UserError(
        "No es posible instalar 'Tipos de Cambio BCCR' porque faltan funcionalidades "
        "base de proveedores automáticos de tipo de cambio. "
        f"{detail}"
    )
