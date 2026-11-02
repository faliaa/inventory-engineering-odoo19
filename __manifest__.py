{
    'name': 'Engineering',
    'version': '19.0.1.6.0',
    'summary': 'Engineering inventory dashboard and stock reports',
    'description': """
Engineering inventory and movement management.

Features:
- Tools & Equipment
- Engineering stock dashboard and summary
- Dashboard KPIs for stock balances, movements, and locations
- Good and bad stock condition reports
- Receipts, internal transfers, and returns
- Stock Card documents with multi-product Excel export
- Annual stock movement and stock opname reports
- Department assignment for internal transfers
- Equipment Register
- Minimum Stock Alerts
- Purchase Integration
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
        'views/department_views.xml',
        'views/res_config_settings_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_card_views.xml',
        'views/stock_card_report_views.xml',
        'views/engineering_dashboard_views.xml',
        'views/stock_summary_views.xml',
        'views/menu_views.xml',
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
}