# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class EquipmentRegister(models.Model):
    _name = 'inventory.equipment.register'
    _description = 'Equipment Register'
    _order = 'name, asset_id'

    name = fields.Char(
        string='Equipment Name',
        required=True,
        index=True,
    )

    asset_id = fields.Char(
        string='Internal Asset ID',
        required=True,
        copy=False,
        index=True,
    )

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        ondelete='restrict',
    )

    serial_number = fields.Char(
        string='Serial Number',
        index=True,
    )

    supplier_id = fields.Many2one(
        'res.partner',
        string='Supplier',
        domain=[('supplier_rank', '>', 0)],
    )

    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        domain=[('usage', '=', 'internal')],
    )

    status = fields.Selection(
        [
            ('available', 'Available'),
            ('in_use', 'In Use'),
            ('maintenance', 'Maintenance'),
            ('retired', 'Retired'),
        ],
        string='Status',
        required=True,
        default='available',
    )

    notes = fields.Text(
        string='Notes',
    )

    active = fields.Boolean(
        string='Active',
        default=True,
    )

    _asset_id_unique = models.Constraint(
        'UNIQUE(asset_id)',
        'Internal Asset ID must be unique.',
    )