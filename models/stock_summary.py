# -*- coding: utf-8 -*-

from odoo import fields, models, tools


class EngineeringStockSummary(models.Model):
    _name = 'engineering.stock.summary'
    _description = 'Engineering Stock Summary'
    _auto = False
    _rec_name = 'product_id'
    _order = 'product_id, location_id'

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        readonly=True,
    )

    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        readonly=True,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        readonly=True,
    )

    goods_condition = fields.Selection(
        [
            ('good', 'Good Stock'),
            ('bad', 'Bad Stock'),
        ],
        string='Condition',
        readonly=True,
    )

    qty_on_hand = fields.Float(
        string='On Hand',
        readonly=True,
        digits='Product Unit of Measure',
    )

    qty_in = fields.Float(
        string='Total In',
        readonly=True,
        digits='Product Unit of Measure',
    )

    qty_out = fields.Float(
        string='Total Out',
        readonly=True,
        digits='Product Unit of Measure',
    )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE VIEW engineering_stock_summary AS
            WITH quant_balance AS (
                SELECT
                    MIN(quant.id) AS id,
                    quant.product_id,
                    quant.location_id,
                    quant.company_id,
                    CASE
                        WHEN location.complete_name ~ '(^|/)ENG/REJECT(/|$)'
                            THEN 'bad'
                        ELSE 'good'
                    END AS goods_condition,
                    SUM(quant.quantity) AS qty_on_hand
                FROM stock_quant quant
                JOIN stock_location location
                    ON location.id = quant.location_id
                WHERE location.usage = 'internal'
                    AND location.complete_name ~ '(^|/)ENG(/|$)'
                GROUP BY
                    quant.product_id,
                    quant.location_id,
                    quant.company_id,
                    CASE
                        WHEN location.complete_name ~ '(^|/)ENG/REJECT(/|$)'
                            THEN 'bad'
                        ELSE 'good'
                    END
            ),
            movement_rows AS (
                SELECT
                    card.id::bigint * 2 AS movement_key,
                    card.product_id,
                    card.location_dest_id AS location_id,
                    card.company_id,
                    CASE
                        WHEN card.goods_condition IS NOT NULL
                            THEN card.goods_condition
                        WHEN location.complete_name ~ '(^|/)ENG/REJECT(/|$)'
                            THEN 'bad'
                        ELSE 'good'
                    END AS goods_condition,
                    card.qty_in,
                    0.0 AS qty_out
                FROM engineering_stock_card card
                JOIN stock_location location
                    ON location.id = card.location_dest_id
                WHERE card.qty_in > 0
                    AND location.complete_name ~ '(^|/)ENG(/|$)'

                UNION ALL

                SELECT
                    card.id::bigint * 2 + 1 AS movement_key,
                    card.product_id,
                    card.location_id,
                    card.company_id,
                    CASE
                        WHEN card.goods_condition IS NOT NULL
                            THEN card.goods_condition
                        WHEN location.complete_name ~ '(^|/)ENG/REJECT(/|$)'
                            THEN 'bad'
                        ELSE 'good'
                    END AS goods_condition,
                    0.0 AS qty_in,
                    card.qty_out
                FROM engineering_stock_card card
                JOIN stock_location location
                    ON location.id = card.location_id
                WHERE card.qty_out > 0
                    AND location.complete_name ~ '(^|/)ENG(/|$)'
            ),
            movement_totals AS (
                SELECT
                    MIN(movement_key) AS id,
                    product_id,
                    location_id,
                    company_id,
                    goods_condition,
                    SUM(qty_in) AS qty_in,
                    SUM(qty_out) AS qty_out
                FROM movement_rows
                GROUP BY product_id, location_id, company_id, goods_condition
            ),
            dimensions AS (
                SELECT product_id, location_id, company_id, goods_condition
                FROM quant_balance
                UNION
                SELECT product_id, location_id, company_id, goods_condition
                FROM movement_totals
            )
            SELECT
                COALESCE(balance.id, -movement.id) AS id,
                dimension.product_id,
                dimension.location_id,
                dimension.company_id,
                dimension.goods_condition,
                COALESCE(balance.qty_on_hand, 0.0) AS qty_on_hand,
                COALESCE(movement.qty_in, 0.0) AS qty_in,
                COALESCE(movement.qty_out, 0.0) AS qty_out
            FROM dimensions dimension
            LEFT JOIN quant_balance balance
                ON balance.product_id = dimension.product_id
                AND balance.location_id = dimension.location_id
                AND balance.company_id IS NOT DISTINCT FROM dimension.company_id
                AND balance.goods_condition = dimension.goods_condition
            LEFT JOIN movement_totals movement
                ON movement.product_id = dimension.product_id
                AND movement.location_id = dimension.location_id
                AND movement.company_id IS NOT DISTINCT FROM dimension.company_id
                AND movement.goods_condition = dimension.goods_condition
        """)
