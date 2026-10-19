{
    'name': 'Inventory & Purchase Management',
    'version': '19.0.1.0.0',
    'summary': 'Integrated Inventory and Purchase Management',
    'description': """
Inventory & Purchase Management for Engineering.

Features:
- Consumables, spare parts, tools and equipment
- Stock in and stock out management
- Storage location tracking
- Minimum stock alerts
- Purchase integration
- Monthly stock opname
- Weekly, monthly and yearly reports
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
    'security/ir.model.access.csv',
    'views/material_request_views.xml',
    'views/product_template_views.xml',
    'views/equipment_register_views.xml',
    'views/res_config_settings_views.xml',
    'views/stock_picking_views.xml',
    'views/menu_views.xml',
],
    'installable': True,
    'application': True,
    'auto_install': False,
}
