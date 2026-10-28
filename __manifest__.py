{
    'name': 'Engineering',
    'version': '19.0.1.0.0',
    'summary': 'Integrated Engineering Inventory',
    'description': """
Inventory & Purchase Management for Engineering.

Features:
- Master Product
- Stock In and Stock Out
- Good Stock and Reject Stock tracking
- Stock Transfer
- Stock Card
- Equipment Register
- Minimum Stock Alerts
- Purchase Integration
- Monthly Stock Opname
- Weekly, Monthly, and Yearly Reports
""",
    'category': 'Inventory/Inventory',
    'author': 'Custom Development',
    'license': 'LGPL-3',

    'depends': [
        'stock',
        'purchase',
    ],

        'data': [
        'data/material_request_sequence.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/material_request_views.xml',
        'views/product_template_views.xml',
        'views/equipment_register_views.xml',
        'views/res_config_settings_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_card_views.xml',
        'views/menu_views.xml',
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
}