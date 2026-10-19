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
        """Cari lokasi penampungan barang reject secara dinamis."""
        self.ensure_one()

        location = self.env['stock.location'].search([
            ('complete_name', '=', 'ENG/REJECT/Scrap'),
            ('usage', '=', 'internal'),
            ('company_id', 'in', [False, self.company_id.id]),
        ], limit=1)

        if not location:
            raise UserError(_(
                "Lokasi ENG/REJECT/Scrap tidak ditemukan atau "
                "bukan lokasi internal. Periksa konfigurasi lokasi stok."
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
