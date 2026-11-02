# -*- coding: utf-8 -*-

from odoo import fields, models


class InventoryDepartment(models.Model):
    _name = 'inventory.department'
    _description = 'Engineering Department'
    _order = 'name'

    name = fields.Char(
        string='Department',
        required=True,
        index=True,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    active = fields.Boolean(
        default=True,
    )

    _name_company_unique = models.Constraint(
        'UNIQUE(name, company_id)',
        'Department names must be unique per company.',
    )


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    department_id = fields.Many2one(
        'inventory.department',
        string='Department',
        ondelete='restrict',
        tracking=True,
    )
