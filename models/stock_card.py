# -*- coding: utf-8 -*-

from odoo import fields, models


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
