# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = 'stock.move'

    goods_condition = fields.Selection(
        selection=[
            ('good', 'Good Stock'),
            ('bad', 'Bad Stock'),
        ],
        string='Kondisi Barang',
        copy=True,
    )

    def _get_engineering_reject_location(self):
        """Cari lokasi internal Engineering untuk barang reject."""
        self.ensure_one()

        location = self.env['stock.location'].search([
        ('complete_name', '=', 'ENG/REJECT'),
        ('usage', '=', 'internal'),
        ('company_id', 'in', [False, self.company_id.id]),
    ], limit=1)

        if not location:
            raise UserError(_(
            "Lokasi ENG/REJECT tidak ditemukan atau bukan lokasi internal. "
            "Periksa konfigurasi lokasi stok Engineering."
        ))

        return location

    @api.onchange('goods_condition')
    def _onchange_goods_condition(self):
        for move in self:
            if (
                move.goods_condition == 'bad'
                and move.picking_type_id
                and move.picking_type_id.code == 'incoming'
            ):
                location = move._get_engineering_reject_location()
                move.location_dest_id = location

    def _action_done(self, cancel_backorder=False):
        """Buat Stock Card setelah pergerakan stok selesai."""
        result = super()._action_done(
            cancel_backorder=cancel_backorder
        )

        # Ambil pergerakan asli yang sudah selesai.
        done_moves = self.exists().filtered(
            lambda move: move.state == 'done'
        )

        StockCard = self.env['engineering.stock.card']

        for move in done_moves:
            if not move.product_id or move.quantity <= 0:
                continue

            source_name = move.location_id.complete_name or ''
            dest_name = move.location_dest_id.complete_name or ''

            source_is_eng = (
                source_name == 'ENG'
                or source_name.startswith('ENG/')
            )
            dest_is_eng = (
                dest_name == 'ENG'
                or dest_name.startswith('ENG/')
            )

            # Lewati pergerakan yang tidak menyentuh Engineering.
            if not source_is_eng and not dest_is_eng:
                continue

            qty = move.quantity
            qty_in = qty if dest_is_eng else 0.0
            qty_out = qty if source_is_eng else 0.0

            document_name = (
                move.reference
                or (
                    move.picking_id.name
                    if move.picking_id
                    else ''
                )
                or f'MOVE/{move.id}'
            )

            vals = {
                'name': document_name,
                'date': move.date,
                'stock_move_id': move.id,
                'product_id': move.product_id.id,
                'picking_id': move.picking_id.id or False,
                'location_id': move.location_id.id,
                'location_dest_id': move.location_dest_id.id,
                'goods_condition': move.goods_condition or False,
                'qty_in': qty_in,
                'qty_out': qty_out,
                'product_uom_id': move.product_uom.id,
                'description': document_name,
                'company_id': move.company_id.id,
            }

            card = StockCard.search(
                [('stock_move_id', '=', move.id)],
                limit=1,
            )

            if card:
                card.write(vals)
            else:
                StockCard.create(vals)

        # Harus berada di luar perulangan.
        return result