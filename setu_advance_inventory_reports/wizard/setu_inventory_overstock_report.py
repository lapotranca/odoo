from odoo import fields, models, api, _
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    from odoo.addons.setu_advance_inventory_reports.library import xlsxwriter
from . import setu_excel_formatter
import base64
from io import BytesIO

class SetuInventoryOverstockReport(models.TransientModel):

    _name = 'setu.inventory.overstock.report'
    _description = """
        Inventory Overtsock Report / Excess Inventory Report
        ===================================================================
        Excess Inventory Report is used to capture all products which are having overstock than needed.  
        
        Report will be downloaded in excel file, following data will be exported to excel file.
        -   Company
        -   Warehouse
        -   Product
        -   Product Category 
        -   Warehouse 
        -   Sales Qty,
        -   Average Daily Sale
        -   Available Stock
        -   Outgoing Stock
        -   Incoming Stock
        -   Forecasted Stock
        -   Demanded Qty
        -   Coverage Days
        -   Overstock Qty
        -   Overstock Value
        -   Last Purchase Date
        -   Last Purchase Qty
        -   Last Purchase Price
        -   Purchase Currency
        -   Vendor Name
        -   Warehouse Wise Overstock Qty Percentage
        -   Warehouse Wise Overstock Value Percentage
        -   Company Wise Overstock Qty Percentage
        -   Company Wise Overstock Value Percentage
    """

    advance_stock_days = fields.Integer("Analyse Inventory for Next X Days")
    stock_file_data = fields.Binary('Stock Movement File')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    company_ids = fields.Many2many("res.company", string="Companies")
    product_category_ids = fields.Many2many("product.category", string="Product Categories")
    product_ids = fields.Many2many("product.product", string="Products")
    warehouse_ids = fields.Many2many("stock.warehouse", string="Warehouses")

    @api.onchange('product_category_ids')
    def onchange_product_category_id(self):
        if self.product_category_ids:
            return {'domain' : { 'product_ids' : [('categ_id','child_of', self.product_category_ids.ids)] }}

    @api.onchange('company_ids')
    def onchange_company_id(self):
        if self.company_ids:
            return {'domain' : { 'warehouse_ids' : [('company_id','child_of', self.company_ids.ids)] }}

    def get_file_name(self):
        filename = "inventory_overstock_report.xlsx"
        return filename

    def create_excel_workbook(self, file_pointer):
        workbook = xlsxwriter.Workbook(file_pointer)
        return workbook

    def create_excel_worksheet(self, workbook, sheet_name):
        worksheet = workbook.add_worksheet(sheet_name)
        worksheet.set_default_row(20)
        # worksheet.set_border()
        return worksheet

    def set_column_width(self, workbook, worksheet):
        worksheet.set_column(0, 1, 20)
        worksheet.set_column(2, 19, 13)
        worksheet.set_column(20,20, 20)

    def set_format(self, workbook, wb_format):
        wb_new_format = workbook.add_format(wb_format)
        wb_new_format.set_border()
        return wb_new_format

    def set_report_title(self, workbook, worksheet):
        wb_format = self.set_format(workbook, setu_excel_formatter.FONT_TITLE_CENTER)
        worksheet.merge_range(0, 0, 1, 20, "Inventory Overstock Report", wb_format)
        wb_format_left = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)
        wb_format_center = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)

        report_string = ""

        report_string = "Inventory Analysis For Next"
        worksheet.merge_range(2, 0, 2, 1, report_string, wb_format_left)
        worksheet.write(2, 2, str(self.advance_stock_days) + " Days", wb_format_center)

        worksheet.merge_range(3, 0, 3, 1, "Sales History Taken From", wb_format_left)
        worksheet.merge_range(4, 0, 4, 1, "Sales History Taken Upto", wb_format_left)

        wb_format_center = self.set_format(workbook, {'num_format': 'dd/mm/yy', 'align' : 'center', 'bold':True ,'font_color' : 'red'})
        worksheet.write(3, 2, self.start_date, wb_format_center)
        worksheet.write(4, 2, self.end_date, wb_format_center)

    def get_overstock_report_data(self):
        """
        [
           {
              "company_id":1,
              "company_name":"Setu Consulting",
              "product_id":6,
              "product_name":"9seat_grey_sofa_cover",
              "product_category_id":5,
              "category_name":"All / Saleable / Hall Decoration",
              "warehouse_id":1,
              "warehouse_name":"Setu Main Warehouse",
              "sales":24.0,
              "ads":0.06,
              "qty_available":6.0,
              "outgoing":0.0,
              "incoming":0.0,
              "forecasted_stock":6.0,
              "demanded_qty":4.0,
              "coverage_days":100.0,
              "overstock_qty":2.0,
              "overstock_value":26000.0,
              "last_purchase_date":datetime.date(2020, 3, 29),
              "last_purchase_qty":15.0,
              "last_purchase_price":13000.0,
              "currency_name":"INR",
              "vendor_name":"Jessy Stefen",
              "wh_overstock_qty_per":0.018,
              "wh_overstock_value_per":1.0,
              "cmp_overstock_qty_per":0.018,
              "cmp_overstock_value_per":0.667
           },
   ]
        :return:
        """

        start_date = self.start_date
        end_date = self.end_date
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

        warehouses = self.warehouse_ids and set(self.warehouse_ids.ids) or {}

        # get_products_overstock_data(company_ids, product_ids, category_ids, warehouse_ids, start_date, end_date, advance_stock_days)
        query = """
                Select * from get_products_overstock_data('%s','%s','%s','%s','%s','%s', '%s')
            """%(company_ids, products, category_ids, warehouses, start_date, end_date, self.advance_stock_days)
        print(query)
        self._cr.execute(query)
        stock_data = self._cr.dictfetchall()
        return  stock_data

    def prepare_data_to_write(self, stock_data={}):
        """

        :param stock_data:
        :return:
        """
        warehouse_wise_data = {}
        for data in stock_data:
            key = (data.get('warehouse_id'), data.get('warehouse_name'))
            if not warehouse_wise_data.get(key,False):
                warehouse_wise_data[key] = {data.get('product_id') : data}
            else:
                warehouse_wise_data.get(key).update({data.get('product_id') : data})
        return warehouse_wise_data

    def download_report(self):
        file_name = self.get_file_name()
        file_pointer = BytesIO()
        stock_data = self.get_overstock_report_data()
        warehouse_wise_overstock_data = self.prepare_data_to_write(stock_data=stock_data)
        if not warehouse_wise_overstock_data:
            return False
        workbook = self.create_excel_workbook(file_pointer)
        for stock_data_key, stock_data_value in warehouse_wise_overstock_data.items():
            sheet_name = stock_data_key[1]
            wb_worksheet = self.create_excel_worksheet(workbook, sheet_name)
            row_no = 5
            self.write_report_data_header(workbook, wb_worksheet, row_no)
            for overstock_data_key, overstock_data_value in stock_data_value.items():
                row_no = row_no + 1
                self.write_data_to_worksheet(workbook, wb_worksheet, overstock_data_value, row=row_no)

        # workbook.save(file_name)
        workbook.close()
        file_pointer.seek(0)
        file_data = base64.encodestring(file_pointer.read())
        self.write({'stock_file_data' : file_data})
        file_pointer.close()

        return {
            'name' : 'Inventory Overstock Report',
            'type' : 'ir.actions.act_url',
            'url': '/web/binary/download_document?model=setu.inventory.overstock.report&field=stock_file_data&id=%s&filename=%s'%(self.id, file_name),
            'target': 'self',
        }

    def download_report_in_listview(self):
        stock_data = self.get_overstock_report_data()
        print (stock_data)
        for overstock_data_value in stock_data:
            overstock_data_value['wizard_id'] = self.id
            self.create_data(overstock_data_value)

        graph_view_id = self.env.ref('setu_advance_inventory_reports.setu_overstock_bi_report_graph').id
        tree_view_id = self.env.ref('setu_advance_inventory_reports.setu_inventory_overstock_bi_report_tree').id
        is_graph_first = self.env.context.get('graph_report',False)
        report_display_views = []
        viewmode = ''
        if is_graph_first:
            report_display_views.append((graph_view_id, 'graph'))
            report_display_views.append((tree_view_id, 'tree'))
            viewmode="graph,tree"
        else:
            report_display_views.append((tree_view_id, 'tree'))
            report_display_views.append((graph_view_id, 'graph'))
            viewmode="tree,graph"
        return {
            'name': _('Inventory Overstock Analysis'),
            'domain': [('wizard_id', '=', self.id)],
            'res_model': 'setu.inventory.overstock.bi.report',
            'view_mode': viewmode,
            'type': 'ir.actions.act_window',
            'views': report_display_views,
        }

    def create_data(self, data):
        del data['company_name']
        del data['product_name']
        del data['warehouse_name']
        del data['category_name']
        return self.env['setu.inventory.overstock.bi.report'].create(data)


    def write_report_data_header(self, workbook, worksheet, row):
        self.set_report_title(workbook,worksheet)
        self.set_column_width(workbook, worksheet)

        wb_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)
        wb_format.set_text_wrap()

        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_BOLD_RIGHT)
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_BOLD_RIGHT)
        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)
        normal_center_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)
        even_normal_left_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_BOLD_LEFT)
        odd_normal_left_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_BOLD_LEFT)

        worksheet.write(row, 0, 'Product Name', normal_left_format)
        worksheet.write(row, 1, 'Category', normal_left_format)
        worksheet.write(row, 2, 'Sales', odd_normal_right_format)
        worksheet.write(row, 3, 'ADS', even_normal_right_format)
        worksheet.write(row, 4, 'Current Stock', odd_normal_right_format)
        worksheet.write(row, 5, 'Outgoing', even_normal_right_format)
        worksheet.write(row, 6, 'Incoming', odd_normal_right_format)
        worksheet.write(row, 7, 'Virtual Stock', even_normal_right_format)
        worksheet.write(row, 8, 'Demanded Qty', odd_normal_right_format)
        worksheet.write(row, 9, 'Coverage Days', even_normal_right_format)
        worksheet.write(row, 10, 'Overstock Qty', odd_normal_right_format)
        worksheet.write(row, 11, 'Overstock Value', even_normal_right_format)
        worksheet.write(row, 12, 'Turnover Ratio', odd_normal_right_format)
        worksheet.write(row, 13, 'FSN Classification', even_normal_right_format)
        worksheet.write(row, 14, 'Overstock Qty (%)', odd_normal_right_format)
        worksheet.write(row, 15, 'Overstock Value (%)', even_normal_right_format)
        worksheet.write(row, 16, 'Last PO Date', odd_normal_right_format)
        worksheet.write(row, 17, 'Last PO Qty', even_normal_right_format)
        worksheet.write(row, 18, 'Last PO Price', odd_normal_right_format)
        worksheet.write(row, 19, 'Currency', even_normal_left_format)
        worksheet.write(row, 20, 'Vendor', odd_normal_left_format)
        return worksheet

    def write_data_to_worksheet(self, workbook, worksheet, data, row):
        # Start from the first cell. Rows and
        # columns are zero indexed.
        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_RIGHT)
        ODD_FONT_MEDIUM_NORMAL_RIGHT_WITH_DATE = setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_RIGHT.copy()
        ODD_FONT_MEDIUM_NORMAL_RIGHT_WITH_DATE.update({'num_format': 'dd/mm/yy', 'align' : 'center'})
        odd_normal_right_format_with_date = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_RIGHT_WITH_DATE)
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_NORMAL_RIGHT)
        even_normal_left_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_NORMAL_LEFT)
        even_normal_center_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_NORMAL_CENTER)
        odd_normal_left_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_LEFT)
        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_NORMAL_LEFT)

        worksheet.write(row, 0, data.get('product_name',''), normal_left_format)
        worksheet.write(row, 1, data.get('category_name',''), normal_left_format)
        worksheet.write(row, 2, data.get('sales',''), odd_normal_right_format)
        worksheet.write(row, 3, data.get('ads',''), even_normal_right_format)
        worksheet.write(row, 4, data.get('qty_available',''), odd_normal_right_format)
        worksheet.write(row, 5, data.get('outgoing',''), even_normal_right_format)
        worksheet.write(row, 6, data.get('incoming',''), odd_normal_right_format)
        worksheet.write(row, 7, data.get('forecasted_stock',''), even_normal_right_format)
        worksheet.write(row, 8, data.get('demanded_qty',''), odd_normal_right_format)
        worksheet.write(row, 9, data.get('coverage_days',''), even_normal_right_format)
        worksheet.write(row, 10, data.get('overstock_qty',''), odd_normal_right_format)
        worksheet.write(row, 11, data.get('overstock_value',''), even_normal_right_format)
        worksheet.write(row, 12, data.get('turnover_ratio',''), odd_normal_right_format)
        worksheet.write(row, 13, data.get('stock_movement',''), even_normal_center_format)
        worksheet.write(row, 14, data.get('wh_overstock_qty_per',''), odd_normal_right_format)
        worksheet.write(row, 15, data.get('wh_overstock_value_per',''), even_normal_right_format)
        worksheet.write(row, 16, data.get('last_purchase_date',''), odd_normal_right_format_with_date)
        worksheet.write(row, 17, data.get('last_purchase_qty',''), even_normal_right_format)
        worksheet.write(row, 18, data.get('last_purchase_price',''), odd_normal_right_format)
        worksheet.write(row, 19, data.get('currency_name',''), even_normal_left_format)
        worksheet.write(row, 20, data.get('vendor_name',''), odd_normal_left_format)
        return worksheet

class SetuInventoryOverstockBIReport(models.TransientModel):
    _name = 'setu.inventory.overstock.bi.report'

    product_id = fields.Many2one("product.product", "Product")
    product_category_id = fields.Many2one("product.category", "Category")
    warehouse_id = fields.Many2one("stock.warehouse")
    company_id = fields.Many2one("res.company", "Company")
    sales = fields.Float("Sales")
    ads = fields.Float("ADS")
    qty_available = fields.Float("Current Stock")
    incoming = fields.Float("Incoming")
    outgoing = fields.Float("Outgoing")
    forecasted_stock = fields.Float("Forecasted Stock")
    demanded_qty = fields.Float("Demand")
    coverage_days = fields.Float("Coverage Days")
    overstock_qty = fields.Float("Overstock Qty")
    overstock_value = fields.Float("Overstock Value")
    wh_overstock_qty_per = fields.Float("Overstock Qty (%)")
    wh_overstock_value_per = fields.Float("Overstock Value (%)")
    turnover_ratio = fields.Float("Turnover Ratio")
    stock_movement  = fields.Char("FSN Classification")
    last_purchase_date = fields.Date("Last PO Date")
    last_purchase_qty = fields.Float("Purchase Qty")
    last_purchase_price = fields.Float("Purchase Price")
    currency_name = fields.Char("Currency")
    vendor_name = fields.Char("Vendor")
    wizard_id = fields.Many2one("setu.inventory.overstock.report")