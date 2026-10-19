# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    minimum_stock_alert = fields.Boolean(
        string='Minimum Stock Alert',
        config_parameter='inventory_purchase_management.minimum_stock_alert',
        default=True,
    )

    stock_out_approval = fields.Boolean(
        string='Stock Out Approval',
        config_parameter='inventory_purchase_management.stock_out_approval',
        default=False,
    )

    equipment_tracking = fields.Boolean(
        string='Equipment Tracking',
        config_parameter='inventory_purchase_management.equipment_tracking',
        default=True,
    )

    inventory_default_stock_location_id = fields.Many2one(
        comodel_name='stock.location',
        string='Default Stock Location',
        domain=[('usage', '=', 'internal')],
        config_parameter='inventory_purchase_management.default_stock_location_id',
    )
