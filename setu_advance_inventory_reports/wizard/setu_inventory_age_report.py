from odoo import fields, models, api, _
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    from odoo.addons.setu_advance_inventory_reports.library import xlsxwriter
    # from ..library import xlsxwriter
from . import  setu_excel_formatter
import base64
from io import BytesIO

class SetuInventoryAgeReport(models.TransientModel):
    _name = 'setu.inventory.age.report'
    _description = """
        Inventory age report is useful to determine how oldest your inventories are.
        It gives you detailed analysis products wise about oldest inventories at company level. 
    """

    stock_file_data = fields.Binary('Inventory Age Report File')
    company_ids = fields.Many2many("res.company", string="Companies")
    product_category_ids = fields.Many2many("product.category", string="Product Categories")
    product_ids = fields.Many2many("product.product", string="Products")

    @api.onchange('product_category_ids')
    def onchange_product_category_id(self):
        if self.product_category_ids:
            return {'domain' : { 'product_ids' : [('categ_id','child_of', self.product_category_ids.ids)] }}

    def get_file_name(self):
        filename = "inventory_age_report.xlsx"
        return filename

    def create_excel_workbook(self, file_pointer):
        workbook = xlsxwriter.Workbook(file_pointer)
        return workbook

    def create_excel_worksheet(self, workbook, sheet_name):
        worksheet = workbook.add_worksheet(sheet_name)
        worksheet.set_default_row(22)
        # worksheet.set_border()
        return worksheet

    def set_column_width(self, workbook, worksheet):
        worksheet.set_column(0, 1, 25)
        worksheet.set_column(2, 8, 14)

    def set_format(self, workbook, wb_format):
        wb_new_format = workbook.add_format(wb_format)
        wb_new_format.set_border()
        return wb_new_format

    def set_report_title(self, workbook, worksheet):
        wb_format = self.set_format(workbook,setu_excel_formatter.FONT_TITLE_CENTER)
        worksheet.merge_range(0, 0, 1, 8, "Inventory Age Report", wb_format)
        wb_format_left = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)
        wb_format_center = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)

    def get_inventory_age_report_data(self):
        """
        :return:
        """
        category_ids = company_ids = {}
        if self.product_category_ids:
            categories = self.env['product.category'].search([('id','child_of',self.product_category_ids.ids)])
            category_ids = set(categories.ids) or {}
        products = self.product_ids and set(self.product_ids.ids) or {}

        if self.company_ids:
            companies = self.env['res.company'].search([('id','child_of',self.company_ids.ids)])
            company_ids = set(companies.ids) or {}
        else:
            company_ids = set(self.env.context.get('allowed_company_ids',False) or self.env.user.company_ids.ids) or {}

        # warehouses = self.warehouse_ids and set(self.warehouse_ids.ids) or {}

        # get_products_overstock_data(company_ids, product_ids, category_ids, warehouse_ids, start_date, end_date, advance_stock_days)
        query = """
                Select * from inventory_stock_age_report('%s','%s','%s')
            """%(company_ids, products, category_ids)
        print(query)
        self._cr.execute(query)
        stock_data = self._cr.dictfetchall()
        return  stock_data

    def prepare_data_to_write(self, stock_data={}):
        """

        :param stock_data:
        :return:
        """
        company_wise_data = {}
        for data in stock_data:
            key = (data.get('company_id'), data.get('company_name'))
            if not company_wise_data.get(key,False):
                company_wise_data[key] = {data.get('product_id') : data}
            else:
                company_wise_data.get(key).update({data.get('product_id') : data})
        return company_wise_data

    def download_report(self):
        file_name = self.get_file_name()
        file_pointer = BytesIO()
        stock_data = self.get_inventory_age_report_data()
        company_wise_analysis_data = self.prepare_data_to_write(stock_data=stock_data)
        if not company_wise_analysis_data:
            return False
        workbook = self.create_excel_workbook(file_pointer)
        for stock_data_key, stock_data_value in company_wise_analysis_data.items():
            sheet_name = stock_data_key[1]
            wb_worksheet = self.create_excel_worksheet(workbook, sheet_name)
            row_no = 3
            self.write_report_data_header(workbook, wb_worksheet, row_no)
            for age_data_key, age_data_value in stock_data_value.items():
                row_no = row_no + 1
                self.write_data_to_worksheet(workbook, wb_worksheet, age_data_value, row=row_no)

        # workbook.save(file_name)
        workbook.close()
        file_pointer.seek(0)
        file_data = base64.encodestring(file_pointer.read())
        self.write({'stock_file_data' : file_data})
        file_pointer.close()

        return {
            'name' : 'Inventory Age Report',
            'type' : 'ir.actions.act_url',
            'url': '/web/binary/download_document?model=setu.inventory.age.report&field=stock_file_data&id=%s&filename=%s'%(self.id, file_name),
            'target': 'self',
        }

    def download_report_in_listview(self):
        stock_data = self.get_inventory_age_report_data()
        print (stock_data)
        for fsn_data_value in stock_data:
            fsn_data_value['wizard_id'] = self.id
            self.create_data(fsn_data_value)
        graph_view_id = self.env.ref('setu_advance_inventory_reports.setu_inventory_age_bi_report_graph').id
        tree_view_id = self.env.ref('setu_advance_inventory_reports.setu_inventory_age_bi_report_tree').id
        is_graph_first = self.env.context.get('graph_report',False)
        report_display_views = []
        viewmode= ''
        if is_graph_first:
            report_display_views.append((graph_view_id, 'graph'))
            report_display_views.append((tree_view_id, 'tree'))
            viewmode = "graph,tree"
        else:
            report_display_views.append((tree_view_id, 'tree'))
            report_display_views.append((graph_view_id, 'graph'))
            viewmode="tree,graph"
        return {
            'name': _('Inventory Age Analysis'),
            'domain': [('wizard_id', '=', self.id)],
            'res_model': 'setu.inventory.age.bi.report',
            'view_mode': viewmode,
            'type': 'ir.actions.act_window',
            'views': report_display_views,
        }

    def create_data(self, data):
        del data['company_name']
        del data['product_name']
        del data['category_name']
        return self.env['setu.inventory.age.bi.report'].create(data)

    def write_report_data_header(self, workbook, worksheet, row):
        self.set_report_title(workbook,worksheet)
        self.set_column_width(workbook, worksheet)
        wb_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)
        wb_format.set_text_wrap()
        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_BOLD_RIGHT)
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_BOLD_RIGHT)
        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)

        worksheet.write(row, 0, 'Product Name', normal_left_format)
        worksheet.write(row, 1, 'Category', normal_left_format)
        worksheet.write(row, 2, 'Current Stock', odd_normal_right_format)
        worksheet.write(row, 3, 'Stock Value', even_normal_right_format)
        worksheet.write(row, 4, 'Stock Qty (%)', odd_normal_right_format)
        worksheet.write(row, 5, 'Stock Value (%)', even_normal_right_format)
        worksheet.write(row, 6, "Oldest Stock Age", odd_normal_right_format)
        worksheet.write(row, 7, "Oldest Qty", even_normal_right_format)
        worksheet.write(row, 8, "Oldest Stock Value", odd_normal_right_format)

        return worksheet

    def write_data_to_worksheet(self, workbook, worksheet, data, row):
        # Start from the first cell. Rows and
        # columns are zero indexed.
        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_RIGHT)
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_NORMAL_RIGHT)
        odoo_normal_center_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_CENTER)
        # odd_normal_left_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_LEFT)
        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_NORMAL_LEFT)

        worksheet.write(row, 0, data.get('product_name',''), normal_left_format)
        worksheet.write(row, 1, data.get('category_name',''), normal_left_format)
        worksheet.write(row, 2, data.get('current_stock',''), odd_normal_right_format)
        worksheet.write(row, 3, data.get('current_stock_value',''), even_normal_right_format)
        worksheet.write(row, 4, data.get('stock_qty_ratio',''), odd_normal_right_format)
        worksheet.write(row, 5, data.get('stock_value_ratio',''), even_normal_right_format)
        worksheet.write(row, 6, data.get('days_old',''), odd_normal_right_format)
        worksheet.write(row, 7, data.get('oldest_stock_qty', ''), even_normal_right_format)
        worksheet.write(row, 8, data.get('oldest_stock_value', ''), odd_normal_right_format)
        return worksheet

class SetuInventoryAgeBIReport(models.TransientModel):
    _name = 'setu.inventory.age.bi.report'

    product_id = fields.Many2one("product.product", "Product")
    product_category_id = fields.Many2one("product.category", "Category")
    company_id = fields.Many2one("res.company", "Company")
    current_stock = fields.Float("Current Stock")
    current_stock_value = fields.Float("Stock Value")
    oldest_date = fields.Date("Oldest Date")
    days_old = fields.Integer("Oldest Stock Age")
    oldest_stock_qty = fields.Float("Oldest Stock Qty")
    oldest_stock_value  = fields.Float("Oldest Stock Value")
    stock_qty_ratio = fields.Float("Stock Qty (%)")
    stock_value_ratio = fields.Float("Stock Value (%)")
    wizard_id = fields.Many2one("setu.inventory.age.report")
