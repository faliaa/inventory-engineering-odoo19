# -*- coding: utf-8 -*-

import base64
import binascii
import io
import logging
import re
from datetime import datetime, time, timedelta
from urllib.parse import quote

import pytz
import xlsxwriter
from PIL import Image, UnidentifiedImageError, WebPImagePlugin

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class EngineeringStockCardReport(models.TransientModel):
    _name = 'engineering.stock.card.report'
    _description = 'Engineering Stock Card Excel Report'

    document_id = fields.Many2one(
        'engineering.stock.card.document',
        string='Stock Card',
    )
    product_id = fields.Many2one(
        'product.product',
        string='Produk',
        required=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Perusahaan',
        required=True,
        default=lambda self: self.env.company,
    )
    date_from = fields.Date(string='Tanggal Mulai')
    date_to = fields.Date(string='Tanggal Akhir')

    def action_export(self):
        self.ensure_one()
        if self.document_id:
            workbook_data = self._generate_document_workbook()
            safe_name = re.sub(
                r'[^A-Za-z0-9._-]+',
                '_',
                self.document_id.name or str(self.document_id.id),
            )
            file_name = f'Stock_Card_{safe_name}.xlsx'
            self.write({
                'file_data': base64.b64encode(workbook_data),
                'file_name': file_name,
            })
            return {
                'type': 'ir.actions.act_url',
                'url': (
                    '/web/content?model=engineering.stock.card.report'
                    f'&id={self.id}&field=file_data'
                    f'&filename={quote(file_name)}&download=true'
                ),
                'target': 'download',
            }

        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValidationError(_('Start Date must be on or before End Date.'))

        workbook_data = self._generate_workbook()
        product_code = self.product_id.default_code or self.product_id.part_number
        safe_code = re.sub(r'[^A-Za-z0-9._-]+', '_', product_code or str(self.product_id.id))
        file_name = f'Stock_Card_{safe_code}.xlsx'
        self.write({
            'file_data': base64.b64encode(workbook_data),
            'file_name': file_name,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': (
                '/web/content?model=engineering.stock.card.report'
                f'&id={self.id}&field=file_data&filename={quote(file_name)}'
                '&download=true'
            ),
            'target': 'download',
        }

    def _generate_document_workbook(self):
        self.ensure_one()
        document = self.document_id
        if not document.line_ids:
            raise UserError(
                _('Add Stock Card movements before printing the Excel file.')
            )

        lines_by_product = {}
        for line in document.line_ids.sorted(
            key=lambda item: (item.product_id.display_name, item.date, item.id)
        ):
            product_id = line.product_id.id
            if product_id not in lines_by_product:
                lines_by_product[product_id] = (
                    line.product_id,
                    self.env['engineering.stock.card.document.line'],
                )
            product, product_lines = lines_by_product[product_id]
            lines_by_product[product_id] = (
                product,
                product_lines | line,
            )

        start = self._local_datetime_boundary(document.date_from)
        end = self._local_datetime_boundary(
            document.date_to + timedelta(days=1)
        )
        stock_cards = self.env['engineering.stock.card']
        product_sections = []
        for product, lines in lines_by_product.values():
            lines = lines.filtered(
                lambda line: start <= line.date < end
            )
            if not lines:
                continue
            opening_cards = stock_cards.search(
                [
                    ('company_id', '=', document.company_id.id),
                    ('product_id', '=', product.id),
                    ('date', '<', start),
                ],
                order='date asc, id asc',
            )
            opening = {'good': 0.0, 'bad': 0.0}
            for card in opening_cards:
                self._apply_card(opening, card, product=product)

            balances = opening.copy()
            movements = []
            for line in lines:
                card = line.stock_card_id
                quantity_in = self._quantity_in_product_uom(
                    card,
                    line.qty_in,
                    product=product,
                )
                quantity_out = self._quantity_in_product_uom(
                    card,
                    line.qty_out,
                    product=product,
                )
                if quantity_in:
                    condition = line.goods_condition or self._card_condition(
                        card,
                        'in',
                    )
                    balances[condition] += quantity_in
                if quantity_out:
                    condition = line.goods_condition or self._card_condition(
                        card,
                        'out',
                    )
                    balances[condition] -= quantity_out
                transaction_date = fields.Datetime.context_timestamp(
                    self,
                    line.date,
                )
                movements.append({
                    'date': transaction_date.strftime('%d/%m/%y'),
                    'quantity_in': quantity_in,
                    'quantity_out': quantity_out,
                    'good': balances['good'],
                    'bad': balances['bad'],
                    'total': balances['good'] + balances['bad'],
                    'description': line.description or '',
                })

            product_sections.append({
                'product': product,
                'opening': opening,
                'movements': movements,
            })

        if not product_sections:
            raise UserError(
                _('No Stock Card movements exist in the selected date range.')
            )

        return self._generate_workbook(
            product_sections=product_sections,
            document_name=document.name,
            period_from=document.date_from,
            period_to=document.date_to,
        )

    file_data = fields.Binary(attachment=False)
    file_name = fields.Char()

    def _local_datetime_boundary(self, report_date):
        local_datetime = datetime.combine(report_date, time.min)
        timezone = pytz.timezone(self.env.user.tz or 'UTC')
        return timezone.localize(local_datetime).astimezone(pytz.UTC).replace(tzinfo=None)

    def _get_report_cards(self, product=None):
        self.ensure_one()
        product = product or self.product_id
        domain = [
            ('product_id', '=', product.id),
            ('company_id', '=', self.company_id.id),
        ]
        cards = self.env['engineering.stock.card'].search(
            domain,
            order='date asc, id asc',
        )
        if not cards:
            raise UserError(_('No Stock Card movements exist for this product and company.'))

        start = self._local_datetime_boundary(self.date_from) if self.date_from else None
        end = (
            self._local_datetime_boundary(self.date_to + timedelta(days=1))
            if self.date_to
            else None
        )
        opening_cards = cards.filtered(lambda card: start and card.date < start)
        period_cards = cards.filtered(
            lambda card: (not start or card.date >= start)
            and (not end or card.date < end)
        )
        if self.date_from or self.date_to:
            if not period_cards and not opening_cards:
                raise UserError(_('No Stock Card movements exist in the selected date range.'))
        return opening_cards, period_cards

    def _card_condition(self, card, direction):
        if card.goods_condition:
            return card.goods_condition
        location = card.location_dest_id if direction == 'in' else card.location_id
        complete_name = location.complete_name or ''
        return 'bad' if re.search(
            r'(^|/)ENG/REJECT(/|$)',
            complete_name,
        ) else 'good'

    def _quantity_in_product_uom(self, card, quantity, product=None):
        product = product or self.product_id
        if card.product_uom_id and card.product_uom_id != product.uom_id:
            return card.product_uom_id._compute_quantity(
                quantity,
                product.uom_id,
            )
        return quantity

    def _apply_card(self, balances, card, product=None):
        quantity_in = self._quantity_in_product_uom(
            card,
            card.qty_in,
            product=product,
        )
        quantity_out = self._quantity_in_product_uom(
            card,
            card.qty_out,
            product=product,
        )
        if quantity_in:
            condition = self._card_condition(card, 'in')
            balances[condition] += quantity_in
        if quantity_out:
            condition = self._card_condition(card, 'out')
            balances[condition] -= quantity_out
        return quantity_in, quantity_out

    def _fit_image(self, image_value, max_size):
        if not image_value:
            return None
        try:
            raw_image = base64.b64decode(image_value)
            image_stream = io.BytesIO(raw_image)
            try:
                image = Image.open(image_stream)
            except UnidentifiedImageError:
                if raw_image[:4] != b'RIFF' or raw_image[8:12] != b'WEBP':
                    raise
                image = WebPImagePlugin.WebPImageFile(io.BytesIO(raw_image))
            with image:
                image.thumbnail(max_size)
                output = io.BytesIO()
                image.convert('RGBA').save(output, format='PNG')
            output.seek(0)
            return output
        except (binascii.Error, OSError, ValueError) as error:
            _logger.warning(
                'Skipping invalid image in Stock Card Excel report: %s',
                error,
            )
            return None

    def _generate_workbook(
        self,
        product=None,
        opening_cards=None,
        movements=None,
        product_sections=None,
        document_name=None,
        period_from=None,
        period_to=None,
    ):
        self.ensure_one()
        product = product or self.product_id
        if product_sections is None:
            if opening_cards is None:
                opening_cards, period_cards = self._get_report_cards(
                    product=product,
                )
            else:
                period_cards = None
        else:
            opening_cards = self.env['engineering.stock.card']
            period_cards = self.env['engineering.stock.card']
        if opening_cards is None:
            opening_cards, period_cards = self._get_report_cards(product=product)
        company = self.company_id
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Stock Card')
        worksheet.hide_gridlines(2)
        worksheet.set_landscape()
        worksheet.fit_to_pages(1, 1)
        worksheet.set_margins(0.25, 0.25, 0.3, 0.3)
        worksheet.repeat_rows(4, 7)
        worksheet.set_column('A:A', 12)
        worksheet.set_column('B:B', 24)
        worksheet.set_column('C:C', 25)
        worksheet.set_column('D:D', 18)
        worksheet.set_column('E:E', 13)
        worksheet.set_column('F:F', 14)
        worksheet.set_column('G:G', 10)
        worksheet.set_column('H:H', 14)
        worksheet.set_column('I:I', 10)
        worksheet.set_column('J:K', 10)
        worksheet.set_column('L:L', 12)
        worksheet.set_column('M:M', 26)

        border = {'border': 1, 'border_color': '#000000', 'valign': 'vcenter'}
        formats = {
            'title': workbook.add_format({
                **border, 'bold': True, 'font_size': 20, 'align': 'center',
            }),
            'document': workbook.add_format({
                **border, 'font_size': 10, 'align': 'left',
            }),
            'period': workbook.add_format({
                **border, 'bold': True, 'font_size': 10, 'align': 'center',
            }),
            'yellow': workbook.add_format({
                **border, 'bold': True, 'font_size': 14, 'align': 'center',
                'bg_color': '#FFFF00',
            }),
            'header': workbook.add_format({
                **border, 'bold': True, 'align': 'center', 'text_wrap': True,
                'bg_color': '#F4B183',
            }),
            'cell': workbook.add_format({
                **border, 'align': 'center', 'text_wrap': True,
            }),
            'number': workbook.add_format({
                **border, 'align': 'center', 'num_format': '[$-409]0.###',
            }),
            'metadata': workbook.add_format({
                **border, 'bold': True, 'font_size': 12, 'align': 'center',
                'text_wrap': True,
            }),
            'total_label': workbook.add_format({
                **border, 'bold': True, 'align': 'center',
            }),
            'total_number': workbook.add_format({
                **border, 'bold': True, 'align': 'center',
                'num_format': '[$-409]0.###',
            }),
        }

        for row, height in ((0, 27), (1, 27), (2, 27), (3, 12)):
            worksheet.set_row(row, height)
        worksheet.merge_range('A1:C4', '', formats['document'])
        worksheet.merge_range('D1:H4', 'STOCK CARD', formats['title'])
        worksheet.merge_range(
            'I1:M1',
            f'No Doc     : {document_name or "FR.SOP.GAS.ENG.002.02"}',
            formats['document'],
        )
        worksheet.merge_range('I2:M2', 'Rev         :', formats['document'])
        worksheet.merge_range('I3:M4', '', formats['document'])
        logo = self._fit_image(company.logo, (220, 75))
        if logo:
            worksheet.insert_image(
                'A1',
                'company_logo.png',
                {
                    'image_data': logo,
                    'x_offset': 28,
                    'y_offset': 8,
                    'object_position': 1,
                },
            )
        else:
            worksheet.write('A1', company.name, formats['title'])

        worksheet.set_row(4, 25)
        worksheet.merge_range(
            'A5:M5',
            'Stock Card Tools & Equipment Engineering',
            formats['yellow'],
        )
        worksheet.set_row(5, 20)
        worksheet.merge_range(
            'A6:M6',
            (
                f'Periode: {fields.Date.to_string(period_from)} - '
                f'{fields.Date.to_string(period_to)}'
                if period_from and period_to
                else ''
            ),
            formats['period'],
        )
        worksheet.set_row(6, 24)
        worksheet.set_row(7, 24)
        for cell_range in (
            'A7:A8', 'B7:B8', 'C7:C8', 'D7:D8', 'E7:E8',
            'F7:G7', 'H7:I7', 'J7:K7', 'L7:L8', 'M7:M8',
        ):
            worksheet.merge_range(cell_range, '', formats['header'])
        for cell, label in (
            ('A7', 'No ID'), ('B7', 'Nama Barang'), ('C7', 'Foto'),
            ('D7', 'Supplier'), ('E7', 'Stock awal'), ('F7', 'In'),
            ('H7', 'Out'), ('J7', 'Status'), ('L7', 'Total Qty'),
            ('M7', 'Keterangan'), ('F8', 'Tanggal'), ('G8', 'Qty'),
            ('H8', 'Tanggal'), ('I8', 'Qty'), ('J8', 'GS'), ('K8', 'BS'),
        ):
            worksheet.write(cell, label, formats['header'])

        if product_sections is None:
            opening = {'good': 0.0, 'bad': 0.0}
            for card in opening_cards:
                self._apply_card(opening, card, product=product)
            balances = opening.copy()
            movements = movements or []
            if not movements:
                for card in period_cards:
                    quantity_in, quantity_out = self._apply_card(
                        balances,
                        card,
                        product=product,
                    )
                    transaction_date = fields.Datetime.context_timestamp(
                        self,
                        card.date,
                    )
                    description = (
                        card.description
                        or (card.picking_id.name if card.picking_id else False)
                        or card.name
                    )
                    movements.append({
                        'date': transaction_date.strftime('%d/%m/%y'),
                        'quantity_in': quantity_in,
                        'quantity_out': quantity_out,
                        'good': balances['good'],
                        'bad': balances['bad'],
                        'total': balances['good'] + balances['bad'],
                        'description': description or '',
                    })
            product_sections = [{
                'product': product,
                'opening': opening,
                'movements': movements,
            }]

        next_detail_row = 8
        for section in product_sections:
            last_total_row = self._write_product_section(
                worksheet,
                section,
                next_detail_row,
                formats,
            )
            next_detail_row = last_total_row + 2
        worksheet.print_area(0, 0, last_total_row, 12)
        workbook.close()
        output.seek(0)
        return output.getvalue()

    def _write_product_section(
        self,
        worksheet,
        section,
        first_detail_row,
        formats,
    ):
        product = section['product']
        opening = section['opening']
        movements = section['movements']
        balances = (
            {
                'good': movements[-1]['good'],
                'bad': movements[-1]['bad'],
            }
            if movements
            else opening.copy()
        )
        total_in = sum(item['quantity_in'] for item in movements)
        total_out = sum(item['quantity_out'] for item in movements)
        movement_slots = max(14, len(movements))
        last_detail_row = first_detail_row + movement_slots - 1
        opening_total = opening['good'] + opening['bad']

        for offset in range(movement_slots):
            row = first_detail_row + offset
            worksheet.set_row(row, 22)
            if offset < len(movements):
                movement = movements[offset]
                worksheet.write_blank(row, 5, None, formats['cell'])
                worksheet.write_blank(row, 6, None, formats['number'])
                worksheet.write_blank(row, 7, None, formats['cell'])
                worksheet.write_blank(row, 8, None, formats['number'])
                if movement['quantity_in']:
                    worksheet.write(row, 5, movement['date'], formats['cell'])
                    worksheet.write_number(
                        row, 6, movement['quantity_in'], formats['number'],
                    )
                if movement['quantity_out']:
                    worksheet.write(row, 7, movement['date'], formats['cell'])
                    worksheet.write_number(
                        row, 8, movement['quantity_out'], formats['number'],
                    )
                worksheet.write_number(row, 9, movement['good'], formats['number'])
                worksheet.write_number(row, 10, movement['bad'], formats['number'])
                worksheet.write_number(row, 11, movement['total'], formats['number'])
                worksheet.write(row, 12, movement['description'], formats['cell'])
            else:
                for column in range(5, 13):
                    worksheet.write_blank(
                        row,
                        column,
                        None,
                        formats['cell'],
                    )

        product_code = product.part_number or product.default_code or ''
        supplier = product.seller_ids.sorted('sequence')[:1].partner_id.display_name
        metadata_values = (
            (0, product_code),
            (1, product.name),
            (3, supplier or ''),
            (4, opening_total),
        )
        for column, value in metadata_values:
            cell_format = formats['metadata'] if column != 4 else formats['number']
            worksheet.merge_range(
                first_detail_row,
                column,
                last_detail_row,
                column,
                value,
                cell_format,
            )

        worksheet.merge_range(
            first_detail_row,
            2,
            last_detail_row,
            2,
            '',
            formats['document'],
        )
        template_image = product.product_tmpl_id.image_1920
        photo = self._fit_image(template_image, (150, 300))
        if photo:
            worksheet.insert_image(
                first_detail_row,
                2,
                f'product_template_{product.product_tmpl_id.id}.png',
                {
                    'image_data': photo,
                    'x_offset': 8,
                    'y_offset': 8,
                    'object_position': 1,
                },
            )

        total_row = last_detail_row + 1
        worksheet.set_row(total_row, 24)
        for column in range(13):
            worksheet.write_blank(total_row, column, None, formats['total_label'])
        worksheet.write(total_row, 5, 'Total', formats['total_label'])
        worksheet.write_number(total_row, 6, total_in, formats['total_number'])
        worksheet.write_number(total_row, 8, total_out, formats['total_number'])
        worksheet.write_number(total_row, 9, balances['good'], formats['total_number'])
        worksheet.write_number(total_row, 10, balances['bad'], formats['total_number'])
        worksheet.write_number(
            total_row,
            11,
            balances['good'] + balances['bad'],
            formats['total_number'],
        )
        return total_row

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        if self.env.context.get('active_model') == 'engineering.stock.card':
            cards = self.env['engineering.stock.card'].browse(
                self.env.context.get('active_ids') or []
            ).exists()
            products = cards.mapped('product_id')
            if len(products) == 1:
                values['product_id'] = products.id
        return values
