{
    'name': 'Tipo de Cambio Hacienda CR (Odoo 19)',
    'version': '19.0.2.2.0',
    'summary': 'Actualización de tipos de cambio USD y EUR desde Hacienda de Costa Rica',
    'category': 'Accounting',
    'author': 'FenixCR Solutions',
    'license': 'LGPL-3',
    'depends': ['account'],
    'external_dependencies': {'python': ['requests']},
    'data': [
        'data/ir_cron.xml',
    ],
    'installable': True,
    'application': False,
}
