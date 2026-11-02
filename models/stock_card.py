# -*- coding: utf-8 -*-

import re
from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class EngineeringStockCardDocument(models.Model):
    _name = 'engineering.stock.card.document'
    _description = 'Engineering Stock Card Document'
    _order = 'posting_date desc, id desc'

    name = fields.Char(
        string='Nama Stock Card',
        required=True,
        default=lambda self: self.env['ir.sequence'].next_by_code(
            'engineering.stock.card.document'
        ) or _('New'),
        copy=False,
        index=True,
    )
    posting_date = fields.Date(
        string='Posting Date',
        required=True,
        default=fields.Date.context_today,
    )
    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    goods_condition = fields.Selection(
        [
            ('all', 'All Conditions'),
            ('good', 'Good Stock'),
            ('bad', 'Bad Stock'),
        ],
        string='Kondisi Barang',
        required=True,
        default='all',
    )
    product_ids = fields.Many2many(
        'product.product',
        'engineering_stock_card_document_product_rel',
        'document_id',
        'product_id',
        string='Produk',
    )
    line_ids = fields.One2many(
        'engineering.stock.card.document.line',
        'document_id',
        string='Detail Stock Card',
        copy=False,
    )
    line_count = fields.Integer(compute='_compute_line_count')
    company_id = fields.Many2one(
        'res.company',
        string='Perusahaan',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    @api.depends('line_ids')
    def _compute_line_count(self):
        for document in self:
            document.line_count = len(document.line_ids)

    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for document in self:
            if (
                document.date_from
                and document.date_to
                and document.date_from > document.date_to
            ):
                raise ValidationError(
                    _('Start Date must be on or before End Date.')
                )

    def _get_datetime_bounds(self):
        self.ensure_one()
        timezone = pytz.timezone(self.env.user.tz or 'UTC')
        start = timezone.localize(
            datetime.combine(self.date_from, time.min)
        ).astimezone(pytz.UTC).replace(tzinfo=None)
        end = timezone.localize(
            datetime.combine(self.date_to + timedelta(days=1), time.min)
        ).astimezone(pytz.UTC).replace(tzinfo=None)
        return start, end

    def _reload_document(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_add_all_stock_card(self):
        self.ensure_one()
        start, end = self._get_datetime_bounds()
        domain = [
            ('company_id', '=', self.company_id.id),
            ('date', '>=', start),
            ('date', '<', end),
        ]
        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))
        if self.goods_condition != 'all':
            domain.append(('goods_condition', '=', self.goods_condition))

        cards = self.env['engineering.stock.card'].search(
            domain,
            order='date asc, id asc',
        )
        existing_card_ids = set(self.line_ids.mapped('stock_card_id').ids)
        new_cards = cards.filtered(
            lambda card: card.id not in existing_card_ids
        )
        if new_cards:
            self.env['engineering.stock.card.document.line'].create([
                {
                    'document_id': self.id,
                    'stock_card_id': card.id,
                    'date': card.date,
                    'name': card.name,
                    'product_id': card.product_id.id,
                    'qty_in': card.qty_in,
                    'qty_out': card.qty_out,
                    'description': card.description,
                }
                for card in new_cards
            ])
        elif not cards:
            raise UserError(
                _('No Stock Card movements exist in the selected criteria.')
            )
        return self._reload_document()

    def action_clear_all_stock_card(self):
        self.ensure_one()
        self.line_ids.unlink()
        return self._reload_document()

    def action_print_excel(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(
                _('Add Stock Card movements before printing the Excel file.')
            )
        report = self.env['engineering.stock.card.report'].create({
            'document_id': self.id,
            'product_id': self.line_ids[0].product_id.id,
            'company_id': self.company_id.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
        })
        return report.action_export()


class EngineeringStockCardDocumentLine(models.Model):
    _name = 'engineering.stock.card.document.line'
    _description = 'Engineering Stock Card Document Line'
    _order = 'date, id'

    document_id = fields.Many2one(
        'engineering.stock.card.document',
        string='Stock Card',
        required=True,
        ondelete='cascade',
        index=True,
    )
    stock_card_id = fields.Many2one(
        'engineering.stock.card',
        string='Stock Card Movement',
        required=True,
        ondelete='restrict',
        index=True,
    )
    date = fields.Datetime(string='Tanggal', required=True, readonly=True)
    name = fields.Char(string='No. Dokumen', readonly=True)
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        readonly=True,
    )
    goods_condition = fields.Selection(
        selection=[
            ('good', 'Good Stock'),
            ('bad', 'Bad Stock'),
        ],
        string='Kondisi Barang',
        compute='_compute_goods_condition',
        store=True,
        readonly=True,
    )
    qty_in = fields.Float(
        string='QTY IN',
        digits='Product Unit of Measure',
        readonly=True,
    )
    qty_out = fields.Float(
        string='QTY OUT',
        digits='Product Unit of Measure',
        readonly=True,
    )
    description = fields.Char(string='Keterangan')

    @api.depends(
        'stock_card_id.goods_condition',
        'stock_card_id.location_id.complete_name',
        'stock_card_id.location_dest_id.complete_name',
        'qty_in',
    )
    def _compute_goods_condition(self):
        for line in self:
            direction = 'in' if line.qty_in else 'out'
            line.goods_condition = (
                line.stock_card_id._get_stock_card_condition(direction)
                if line.stock_card_id
                else False
            )

    _sql_constraints = [
        (
            'doc_card_unique',
            'unique(document_id, stock_card_id)',
            'A Stock Card movement can only be added once per document.',
        ),
    ]


class EngineeringStockCard(models.Model):
    _name = 'engineering.stock.card'
    _description = 'Engineering Stock Card'
    _order = 'date desc, id desc'

    name = fields.Char(
        string='No. Dokumen',
        required=True,
        index=True,
    )

    date = fields.Datetime(
        string='Tanggal Transaksi',
        required=True,
        index=True,
    )

    stock_move_id = fields.Many2one(
        'stock.move',
        string='Pergerakan Stok Sumber',
        readonly=True,
        index=True,
        ondelete='restrict',
        copy=False,
    )

    product_id = fields.Many2one(
        'product.product',
        string='Nama Barang',
        required=True,
        index=True,
    )

    part_number = fields.Char(
        string='Part Number',
        related='product_id.part_number',
        store=True,
    )

    picking_id = fields.Many2one(
        'stock.picking',
        string='Dokumen Stok',
        readonly=True,
    )

    location_id = fields.Many2one(
        'stock.location',
        string='Lokasi Asal',
    )

    location_dest_id = fields.Many2one(
        'stock.location',
        string='Lokasi Tujuan',
    )

    goods_condition = fields.Selection(
        [
            ('good', 'Good Stock'),
            ('bad', 'Bad Stock'),
        ],
        string='Kondisi Barang',
    )

    qty_in = fields.Float(
        string='QTY IN',
        digits='Product Unit of Measure',
        default=0.0,
    )

    qty_out = fields.Float(
        string='QTY OUT',
        digits='Product Unit of Measure',
        default=0.0,
    )

    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Satuan',
    )

    description = fields.Char(
        string='Keterangan',
    )

    company_id = fields.Many2one(
        'res.company',
        string='Perusahaan',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    _sql_constraints = [
        (
            'stock_move_unique',
            'unique(stock_move_id)',
            'Satu pergerakan stok hanya boleh memiliki satu catatan Stock Card.',
        ),
    ]

    def _get_stock_card_condition(self, direction):
        self.ensure_one()
        if self.goods_condition:
            return self.goods_condition
        location = (
            self.location_dest_id
            if direction == 'in'
            else self.location_id
        )
        return 'bad' if re.search(
            r'(^|/)ENG/REJECT(/|$)',
            location.complete_name or '',
        ) else 'good'
