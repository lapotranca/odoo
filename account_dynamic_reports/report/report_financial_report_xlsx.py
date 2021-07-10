# _*_ coding: utf-8
from odoo import models, fields, api, _

from datetime import datetime
try:
    from odoo.addons.report_xlsx.report.report_xlsx import ReportXlsx
    from xlsxwriter.utility import xl_rowcol_to_cell
except ImportError:
    ReportXlsx = object

DATE_DICT = {
    '%m/%d/%Y' : 'mm/dd/yyyy',
    '%Y/%m/%d' : 'yyyy/mm/dd',
    '%m/%d/%y' : 'mm/dd/yy',
    '%d/%m/%Y' : 'dd/mm/yyyy',
    '%d/%m/%y' : 'dd/mm/yy',
    '%d-%m-%Y' : 'dd-mm-yyyy',
    '%d-%m-%y' : 'dd-mm-yy',
    '%m-%d-%Y' : 'mm-dd-yyyy',
    '%m-%d-%y' : 'mm-dd-yy',
    '%Y-%m-%d' : 'yyyy-mm-dd',
    '%f/%e/%Y' : 'm/d/yyyy',
    '%f/%e/%y' : 'm/d/yy',
    '%e/%f/%Y' : 'd/m/yyyy',
    '%e/%f/%y' : 'd/m/yy',
    '%f-%e-%Y' : 'm-d-yyyy',
    '%f-%e-%y' : 'm-d-yy',
    '%e-%f-%Y' : 'd-m-yyyy',
    '%e-%f-%y' : 'd-m-yy'
}

class InsFinancialReportXlsx(models.AbstractModel):
    _name = 'report.account_dynamic_reports.ins_financial_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def _define_formats(self, workbook):
        """ Add cell formats to current workbook.
        Available formats:
         * format_title
         * format_header
        """
        self.format_title = workbook.add_format({
            'bold': True,
            'align': 'center',
            'font_size': 12,
            'border': False,
            'font': 'Arial',
        })
        self.format_header = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'center',
            'font': 'Arial',
            'bottom': False
        })
        self.content_header = workbook.add_format({
            'bold': False,
            'font_size': 10,
            'align': 'center',
            'font': 'Arial',
        })
        self.content_header_date = workbook.add_format({
            'bold': False,
            'font_size': 10,
            'align': 'center',
            'font': 'Arial',
            #'num_format': 'dd/mm/yyyy',
        })
        self.line_header = workbook.add_format({
            'bold': False,
            'font_size': 10,
            'align': 'right',
            'font': 'Arial',
            'bottom': True
        })
        self.line_header_bold = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'right',
            'font': 'Arial',
            'bottom': True
        })
        self.line_header_string = workbook.add_format({
            'bold': False,
            'font_size': 10,
            'align': 'left',
            'font': 'Arial',
            'bottom': True
        })
        self.line_header_string_bold = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'left',
            'font': 'Arial',
            'bottom': True
        })

    def prepare_report_filters(self, filter):
        """It is writing under second page"""
        self.row_pos_2 += 2
        if filter:
            # Date from
            self.sheet_2.write_string(self.row_pos_2, 0, _('Date from'),
                                    self.format_header)
            date = self.convert_to_date(
                filter['form']['date_from'] and filter['form']['date_from'].strftime('%Y-%m-%d'))
            if filter['form'].get('date_from'):
                self.sheet_2.write_datetime(self.row_pos_2, 1, date,
                                        self.content_header_date)
            self.row_pos_2 += 1
            # Date to
            self.sheet_2.write_string(self.row_pos_2, 0, _('Date to'),
                                    self.format_header)
            date = self.convert_to_date(
                filter['form']['date_to'] and filter['form']['date_to'].strftime('%Y-%m-%d'))
            if filter['form'].get('date_to'):
                self.sheet_2.write_datetime(self.row_pos_2, 1, date,
                                        self.content_header_date)
            self.row_pos_2 += 1
            if filter['form']['enable_filter']:

                # Compariosn Date from
                self.sheet_2.write_string(self.row_pos_2, 0, _('Comparison Date from'),
                                          self.format_header)
                date = self.convert_to_date(
                    filter['form']['comparison_context']['date_from'] and filter['form']['comparison_context']['date_from'].strftime('%Y-%m-%d'))
                if filter['form']['comparison_context'].get('date_from'):
                    self.sheet_2.write_datetime(self.row_pos_2, 1, date,
                                                self.content_header_date)
                self.row_pos_2 += 1
                # Compariosn Date to
                self.sheet_2.write_string(self.row_pos_2, 0, _('Comparison Date to'),
                                          self.format_header)
                date = self.convert_to_date(
                    filter['form']['comparison_context']['date_to'] and filter['form']['comparison_context']['date_to'].strftime('%Y-%m-%d'))
                if filter['form']['comparison_context'].get('date_to'):
                    self.sheet_2.write_datetime(self.row_pos_2, 1, date,
                                                self.content_header_date)

    def prepare_report_contents(self, data):
        self.row_pos += 3

        if data['form']['debit_credit'] == 1:

            self.sheet.set_column(0, 0, 90)
            self.sheet.set_column(1, 1, 15)
            self.sheet.set_column(2, 3, 15)
            self.sheet.set_column(3, 3, 15)

            self.sheet.write_string(self.row_pos, 0, _('Name'),
                                    self.format_header)
            self.sheet.write_string(self.row_pos, 1, _('Debit'),
                                    self.format_header)
            self.sheet.write_string(self.row_pos, 2, _('Credit'),
                                    self.format_header)
            self.sheet.write_string(self.row_pos, 3, _('Balance'),
                                    self.format_header)

            for a in data['report_lines']:
                if a['level'] == 2:
                    self.row_pos += 1
                self.row_pos += 1
                if a.get('account', False):
                    tmp_style_str = self.line_header_string
                    tmp_style_num = self.line_header
                else:
                    tmp_style_str = self.line_header_string_bold
                    tmp_style_num = self.line_header_bold
                self.sheet.write_string(self.row_pos, 0, '   ' * len(a.get('list_len', [])) + a.get('name'),
                                        tmp_style_str)
                self.sheet.write_number(self.row_pos, 1, float(a.get('debit')), tmp_style_num)
                self.sheet.write_number(self.row_pos, 2, float(a.get('credit')), tmp_style_num)
                self.sheet.write_number(self.row_pos, 3, float(a.get('balance')), tmp_style_num)

        if data['form']['debit_credit'] != 1:

            self.sheet.set_column(0, 0, 105)
            self.sheet.set_column(1, 1, 15)
            self.sheet.set_column(2, 2, 15)

            self.sheet.write_string(self.row_pos, 0, _('Name'),
                                    self.format_header)
            if data['form']['enable_filter']:
                self.sheet.write_string(self.row_pos, 1, data['form']['label_filter'],
                                        self.format_header)
                self.sheet.write_string(self.row_pos, 2, _('Balance'),
                                        self.format_header)
            else:
                self.sheet.write_string(self.row_pos, 1, _('Balance'),
                                        self.format_header)

            for a in data['report_lines']:
                if a['level'] == 2:
                    self.row_pos += 1
                self.row_pos += 1
                if a.get('account', False):
                    tmp_style_str = self.line_header_string
                    tmp_style_num = self.line_header
                else:
                    tmp_style_str = self.line_header_string_bold
                    tmp_style_num = self.line_header_bold
                self.sheet.write_string(self.row_pos, 0, '   ' * len(a.get('list_len', [])) + a.get('name'),
                                        tmp_style_str)
                if data['form']['enable_filter']:
                    self.sheet.write_number(self.row_pos, 1, float(a.get('balance_cmp')), tmp_style_num)
                    self.sheet.write_number(self.row_pos, 2, float(a.get('balance')), tmp_style_num)
                else:
                    self.sheet.write_number(self.row_pos, 1, float(a.get('balance')), tmp_style_num)



    def _format_float_and_dates(self, currency_id, lang_id):

        self.line_header.num_format = currency_id.excel_format
        self.line_header_bold.num_format = currency_id.excel_format

        self.content_header_date.num_format = DATE_DICT.get(lang_id.date_format, 'dd/mm/yyyy')

    def convert_to_date(self, datestring=False):
        if datestring:
            datestring = fields.Date.from_string(datestring).strftime(self.language_id.date_format)
            return datetime.strptime(datestring, self.language_id.date_format)
        else:
            return False

    def generate_xlsx_report(self, workbook, data, record):

        self._define_formats(workbook)
        self.row_pos = 0
        self.row_pos_2 = 0

        if not record:
            return False
        data = record.get_report_values()

        self.record = record # Wizard object

        self.sheet = workbook.add_worksheet(data['form']['account_report_id'][1])
        self.sheet_2 = workbook.add_worksheet('Filters')

        self.sheet_2.set_column(0, 0, 25)
        self.sheet_2.set_column(1, 1, 25)
        self.sheet_2.set_column(2, 2, 25)
        self.sheet_2.set_column(3, 3, 25)
        self.sheet_2.set_column(4, 4, 25)
        self.sheet_2.set_column(5, 5, 25)
        self.sheet_2.set_column(6, 6, 25)

        self.sheet.freeze_panes(4, 0)

        self.sheet.screen_gridlines = False
        self.sheet_2.screen_gridlines = False
        #self.sheet.protect()
        self.sheet_2.protect()

        # For Formating purpose
        lang = self.env.user.lang
        self.language_id = self.env['res.lang'].search([('code','=',lang)])[0]
        self._format_float_and_dates(self.env.user.company_id.currency_id, self.language_id)

        self.sheet.merge_range(0, 0, 0, 3, data['form']['account_report_id'][1] +' - '+data['form']['company_id'][1], self.format_title)
        self.dateformat = self.env.user.lang

        #Filter section
        self.prepare_report_filters(data)
        # Content section
        self.prepare_report_contents(data)
