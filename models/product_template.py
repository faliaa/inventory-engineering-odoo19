# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    part_number = fields.Char(
        string='Part Number',
        index=True,
        copy=False,
    )

    brand = fields.Char(
        string='Brand',
    )

    specification = fields.Text(
        string='Specification',
    )

    minimum_stock = fields.Float(
        string='Minimum Stock',
        default=0.0,
        digits='Product Unit of Measure',
        help='Minimum stock level used to monitor inventory.',
    )

    maximum_stock = fields.Float(
        string='Maximum Stock',
        default=0.0,
        digits='Product Unit of Measure',
        help='Maximum desired stock level.',
    )

    @api.constrains('minimum_stock', 'maximum_stock')
    def _check_stock_limits(self):
        for product in self:
            if product.minimum_stock < 0:
                raise ValidationError(
                    _('Minimum Stock cannot be negative.')
                )

            if product.maximum_stock < 0:
                raise ValidationError(
                    _('Maximum Stock cannot be negative.')
                )

            if (
                product.maximum_stock > 0
                and product.maximum_stock < product.minimum_stock
            ):
                raise ValidationError(
                    _(
                        'Maximum Stock must be greater than or equal '
                        'to Minimum Stock.'
                    )
                )