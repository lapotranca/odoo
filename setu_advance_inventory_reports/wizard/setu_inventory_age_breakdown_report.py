from odoo import fields, models, api, _
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    from odoo.addons.setu_advance_inventory_reports.library import xlsxwriter
from . import  setu_excel_formatter
import base64
from io import BytesIO

class SetuInventoryAgeBreakdownReport(models.TransientModel):
    _name = 'setu.inventory.age.breakdown.report'
    _description = """
        Inventory age breakdown report is useful to determine how oldest your inventories are.
        It gives you detailed breakdown analysis products wise about oldest inventories at company level. 
    """

    stock_file_data = fields.Binary('Inventory Age Report File')
    company_ids = fields.Many2many("res.company", string="Companies")
    product_category_ids = fields.Many2many("product.category", string="Product Categories")
    product_ids = fields.Many2many("product.product", string="Products")
    breakdown_days = fields.Integer("Breakdown Days", default=30)

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
        worksheet.set_column(2, 17, 12)

    def set_format(self, workbook, wb_format):
        wb_new_format = workbook.add_format(wb_format)
        wb_new_format.set_border()
        return wb_new_format

    def set_report_title(self, workbook, worksheet):
        wb_format = self.set_format(workbook,setu_excel_formatter.FONT_TITLE_CENTER)
        worksheet.merge_range(0, 0, 1, 17, "Inventory Age Breakdown Report", wb_format)
        wb_format_left = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)
        wb_format_center = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)

    def get_inventory_age_breakdown_report_data(self):
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
                Select * from get_inventory_age_breakdown_data('%s','%s','%s', '%s')
            """%(company_ids, products, category_ids, self.breakdown_days)
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
        stock_data = self.get_inventory_age_breakdown_report_data()
        company_wise_analysis_data = self.prepare_data_to_write(stock_data=stock_data)
        if not company_wise_analysis_data:
            return False
        workbook = self.create_excel_workbook(file_pointer)
        for stock_data_key, stock_data_value in company_wise_analysis_data.items():
            sheet_name = stock_data_key[1]
            wb_worksheet = self.create_excel_worksheet(workbook, sheet_name)
            row_no = 4
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
            'name' : 'Inventory Age Breakdown Report',
            'type' : 'ir.actions.act_url',
            'url': '/web/binary/download_document?model=setu.inventory.age.breakdown.report&field=stock_file_data&id=%s&filename=%s'%(self.id, file_name),
            'target': 'self',
        }

    def get_column_header(self, counter):
        header = ""
        bbd = self.breakdown_days
        if counter == 1:
            header = "1 to " + str(bbd)
            return header

        if counter == 7:
            header = "Older than " + str(((counter - 1) * bbd) + 1)
            return header

        header = str(((counter - 1) * bbd) + 1) + " to " + str(counter * bbd)
        return header

    def set_breakdown_header(self, workbook, worksheet, row, col, title, wb_format):
        worksheet.merge_range(row, col, row, col + 1, title, wb_format)

    def write_report_data_header(self, workbook, worksheet, row):
        self.set_report_title(workbook,worksheet)
        self.set_column_width(workbook, worksheet)
        wb_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)
        wb_format.set_text_wrap()
        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_BOLD_RIGHT)
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_BOLD_RIGHT)

        odd_normal_center_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_BOLD_CENTER)
        even_normal_center_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_BOLD_CENTER)

        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)

        worksheet.write(row, 0, 'Product Name', normal_left_format)
        worksheet.write(row, 1, 'Category', normal_left_format)
        worksheet.write(row, 2, 'Total Stock', odd_normal_right_format)
        worksheet.write(row, 3, 'Stock Value', even_normal_right_format)

        self.set_breakdown_header(workbook, worksheet, row-1, 4, self.get_column_header(1), odd_normal_center_format)
        worksheet.write(row, 4, "Stock" ,odd_normal_right_format)
        worksheet.write(row, 5, "Value", odd_normal_right_format)

        self.set_breakdown_header(workbook, worksheet, row - 1, 6, self.get_column_header(2), even_normal_center_format)
        worksheet.write(row, 6, "Stock", even_normal_right_format)
        worksheet.write(row, 7, "Value", even_normal_right_format)

        self.set_breakdown_header(workbook, worksheet, row - 1, 8, self.get_column_header(3), odd_normal_center_format)
        worksheet.write(row, 8, "Stock", odd_normal_right_format)
        worksheet.write(row, 9, "Value", odd_normal_right_format)

        self.set_breakdown_header(workbook, worksheet, row - 1, 10, self.get_column_header(4), even_normal_center_format)
        worksheet.write(row, 10, "Stock", odd_normal_right_format)
        worksheet.write(row, 11, "Value", odd_normal_right_format)

        self.set_breakdown_header(workbook, worksheet, row - 1, 12, self.get_column_header(5), odd_normal_center_format)
        worksheet.write(row, 12, "Stock", odd_normal_right_format)
        worksheet.write(row, 13, "Value", odd_normal_right_format)

        self.set_breakdown_header(workbook, worksheet, row - 1, 14, self.get_column_header(6), even_normal_center_format)
        worksheet.write(row, 14, "Stock", odd_normal_right_format)
        worksheet.write(row, 15, "Value", odd_normal_right_format)

        self.set_breakdown_header(workbook, worksheet, row - 1, 16, self.get_column_header(7), odd_normal_center_format)
        worksheet.write(row, 16, "Stock", odd_normal_right_format)
        worksheet.write(row, 17, "Value", odd_normal_right_format)

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
        worksheet.write(row, 2, data.get('total_stock',''), odd_normal_right_format)
        worksheet.write(row, 3, data.get('total_stock_value',''), even_normal_right_format)
        worksheet.write(row, 4, data.get('breakdown1_qty',''), odd_normal_right_format)
        worksheet.write(row, 5, data.get('breckdown1_value',''), odd_normal_right_format)
        worksheet.write(row, 6, data.get('breakdown2_qty', ''), even_normal_right_format)
        worksheet.write(row, 7, data.get('breckdown2_value', ''), even_normal_right_format)
        worksheet.write(row, 8, data.get('breakdown3_qty', ''), odd_normal_right_format)
        worksheet.write(row, 9, data.get('breckdown3_value', ''), odd_normal_right_format)
        worksheet.write(row, 10, data.get('breakdown4_qty', ''), even_normal_right_format)
        worksheet.write(row, 11, data.get('breckdown4_value', ''), even_normal_right_format)
        worksheet.write(row, 12, data.get('breakdown5_qty', ''), odd_normal_right_format)
        worksheet.write(row, 13, data.get('breckdown5_value', ''), odd_normal_right_format)
        worksheet.write(row, 14, data.get('breakdown6_qty', ''), even_normal_right_format)
        worksheet.write(row, 15, data.get('breckdown6_value', ''), even_normal_right_format)
        worksheet.write(row, 16, data.get('breakdown7_qty', ''), odd_normal_right_format)
        worksheet.write(row, 17, data.get('breckdown7_value', ''), odd_normal_right_format)
        return worksheet
