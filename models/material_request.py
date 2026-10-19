# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class InventoryMaterialRequest(models.Model):
    _name = 'inventory.material.request'
    _description = 'Material Request'
    _order = 'request_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Request Number',
        required=True,
        copy=False,
        readonly=True,
        default='New',
        tracking=True,
    )

    request_date = fields.Date(
        string='Request Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )

    requester_id = fields.Many2one(
        'res.users',
        string='Requester',
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
    )

    department = fields.Char(
        string='Department',
    )

    source_location_id = fields.Many2one(
        'stock.location',
        string='Source Location',
        required=True,
        domain=[('usage', '=', 'internal')],
        tracking=True,
    )

    destination_location_id = fields.Many2one(
        'stock.location',
        string='Destination Location',
        required=True,
        tracking=True,
    )

    line_ids = fields.One2many(
        'inventory.material.request.line',
        'request_id',
        string='Requested Materials',
        copy=True,
    )

    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('waiting_approval', 'Waiting Approval'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('ready', 'Ready'),
            ('done', 'Done'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        required=True,
        copy=False,
        tracking=True,
    )

    approval_user_id = fields.Many2one(
        'res.users',
        string='Approved By',
        readonly=True,
        copy=False,
        tracking=True,
    )

    approval_date = fields.Datetime(
        string='Approval Date',
        readonly=True,
        copy=False,
        tracking=True,
    )

    rejection_reason = fields.Text(
        string='Rejection Reason',
        copy=False,
    )

    picking_id = fields.Many2one(
        'stock.picking',
        string='Stock Transfer',
        readonly=True,
        copy=False,
        tracking=True,
    )

    notes = fields.Text(
        string='Notes',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'inventory.material.request'
                ) or 'New'
        return super().create(vals_list)

    @api.constrains('line_ids', 'source_location_id', 'destination_location_id')
    def _check_request_data(self):
        for request in self:
            if (
                request.source_location_id
                and request.destination_location_id
                and request.source_location_id == request.destination_location_id
            ):
                raise ValidationError(
                    _('Source and destination locations must be different.')
                )

            for line in request.line_ids:
                if line.product_qty <= 0:
                    raise ValidationError(
                        _('Requested quantity must be greater than zero.')
                    )

    def action_submit(self):
        for request in self:
            if request.state != 'draft':
                raise UserError(_('Only draft requests can be submitted.'))

            if not request.line_ids:
                raise UserError(_('Add at least one material before submitting.'))

            request.write({'state': 'waiting_approval'})

    def action_approve(self):
        if not self.env.user.has_group('stock.group_stock_manager'):
            raise UserError(_('Only Inventory Managers can approve requests.'))

        for request in self:
            if request.state != 'waiting_approval':
                raise UserError(
                    _('Only requests waiting for approval can be approved.')
                )

            request.write({
                'state': 'approved',
                'approval_user_id': self.env.user.id,
                'approval_date': fields.Datetime.now(),
                'rejection_reason': False,
            })

    def action_reject(self):
        if not self.env.user.has_group('stock.group_stock_manager'):
            raise UserError(_('Only Inventory Managers can reject requests.'))

        for request in self:
            if request.state != 'waiting_approval':
                raise UserError(
                    _('Only requests waiting for approval can be rejected.')
                )

            if not request.rejection_reason:
                raise UserError(_('Enter a rejection reason first.'))

            request.write({'state': 'rejected'})

    def action_reset_to_draft(self):
        for request in self:
            if request.state not in ('rejected', 'cancelled'):
                raise UserError(
                    _('Only rejected or cancelled requests can be reset to draft.')
                )

            request.write({
                'state': 'draft',
                'approval_user_id': False,
                'approval_date': False,
                'rejection_reason': False,
            })

    def action_cancel(self):
        for request in self:
            if request.state in ('done', 'cancelled'):
                raise UserError(
                    _('Completed or cancelled requests cannot be cancelled again.')
                )

            if request.picking_id and request.picking_id.state == 'done':
                raise UserError(
                    _('The stock transfer is already completed.')
                )

            request.write({'state': 'cancelled'})


class InventoryMaterialRequestLine(models.Model):
    _name = 'inventory.material.request.line'
    _description = 'Material Request Line'
    _order = 'id'

    request_id = fields.Many2one(
        'inventory.material.request',
        string='Material Request',
        required=True,
        ondelete='cascade',
    )

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        domain=[('is_storable', '=', True)],
    )

    product_qty = fields.Float(
        string='Requested Quantity',
        required=True,
        default=1.0,
        digits='Product Unit of Measure',
    )

    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        related='product_id.uom_id',
        readonly=True,
    )

    notes = fields.Char(
        string='Notes',
    )

    @api.constrains('product_qty')
    def _check_product_qty(self):
        for line in self:
            if line.product_qty <= 0:
                raise ValidationError(
                    _('Requested quantity must be greater than zero.')
                )
