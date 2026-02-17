{
    'name': 'Tipos de Cambio BCCR',
    'version': '19.0.1.0.0',
    'summary': 'Proveedor de tipos de cambio usando Banco Central de Costa Rica',
    'category': 'Accounting',
    'author': 'FenixCR Solutions',
    'license': 'LGPL-3',
    'depends': ['account', 'account_accountant'],
    'data': [
        'views/res_currency_rate_provider_views.xml',
    ],
    'installable': True,
    'application': False,
}
