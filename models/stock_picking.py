# -*- coding: utf-8 -*-

from odoo import models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        for picking in self.filtered(
            lambda p: p.state != 'done'
            and p.picking_type_code == 'incoming'
            and p.location_dest_id.complete_name == 'ENG/Stock'
        ):
            for move in picking.move_ids.filtered(
                lambda m: m.state != 'cancel'
            ):
                if not move.goods_condition:
                    raise UserError(_(
                        "Pilih Kondisi Barang untuk setiap produk "
                        "sebelum memvalidasi penerimaan Engineering."
                    ))

                if move.goods_condition == 'bad':
                    reject_location = (
                        move._get_engineering_reject_location()
                    )

                    if reject_location.company_id and (
                        reject_location.company_id != picking.company_id
                    ):
                        raise UserError(_(
                            "Lokasi reject tidak sesuai dengan perusahaan "
                            "pada dokumen penerimaan."
                        ))

                    move.location_dest_id = reject_location

        return super().button_validate()
