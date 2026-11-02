# -*- coding: utf-8 -*-

from odoo import fields, models, tools
from odoo.tools.safe_eval import safe_eval


class EngineeringDashboard(models.Model):
    _name = 'engineering.stock.dashboard'
    _description = 'Engineering Stock Dashboard'
    _auto = False
    _rec_name = 'company_id'
    _order = 'company_id'

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        readonly=True,
    )

    qty_on_hand = fields.Float(
        string='Total On Hand',
        readonly=True,
        digits='Product Unit of Measure',
    )

    good_stock = fields.Float(
        string='Good Stock',
        readonly=True,
        digits='Product Unit of Measure',
    )

    bad_stock = fields.Float(
        string='Bad Stock',
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

    location_count = fields.Integer(
        string='Locations in Use',
        readonly=True,
    )

    product_count = fields.Integer(
        string='Products in Stock',
        readonly=True,
    )

    def action_open_stock_summary(self):
        return self.env.ref(
            'inventory_engineering_odoo19.action_engineering_stock_summary'
        ).read()[0]

    def action_open_good_stock(self):
        action = self.action_open_stock_summary()
        context = safe_eval(action.get('context') or '{}')
        context['search_default_good_stock'] = 1
        action['context'] = context
        return action

    def action_open_bad_stock(self):
        action = self.action_open_stock_summary()
        context = safe_eval(action.get('context') or '{}')
        context['search_default_bad_stock'] = 1
        action['context'] = context
        return action

    def action_open_stock_in(self):
        return self.env.ref(
            'inventory_engineering_odoo19.action_engineering_dashboard_incoming'
        ).read()[0]

    def action_open_stock_out(self):
        return self.env.ref(
            'inventory_engineering_odoo19.action_engineering_dashboard_outgoing'
        ).read()[0]

    def action_open_stock_on_hand(self):
        return self.env.ref(
            'inventory_engineering_odoo19.action_engineering_dashboard_on_hand'
        ).read()[0]

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE VIEW engineering_stock_dashboard AS
            SELECT
                company.id AS id,
                company.id AS company_id,
                COALESCE(SUM(summary.qty_on_hand), 0.0) AS qty_on_hand,
                COALESCE(SUM(summary.qty_on_hand) FILTER (
                    WHERE summary.goods_condition = 'good'
                ), 0.0) AS good_stock,
                COALESCE(SUM(summary.qty_on_hand) FILTER (
                    WHERE summary.goods_condition = 'bad'
                ), 0.0) AS bad_stock,
                COALESCE(SUM(summary.qty_in), 0.0) AS qty_in,
                COALESCE(SUM(summary.qty_out), 0.0) AS qty_out,
                COUNT(DISTINCT summary.location_id) FILTER (
                    WHERE summary.qty_on_hand > 0
                ) AS location_count,
                COUNT(DISTINCT summary.product_id) FILTER (
                    WHERE summary.qty_on_hand > 0
                ) AS product_count
            FROM res_company company
            LEFT JOIN engineering_stock_summary summary
                ON summary.company_id = company.id
            GROUP BY company.id
        """)
