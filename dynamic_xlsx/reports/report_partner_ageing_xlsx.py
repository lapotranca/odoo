# _*_ coding: utf-8
from odoo import models, fields, api,_

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

class InsPartnerAgeingXlsx(models.AbstractModel):
    _name = 'report.dynamic_xlsx.ins_partner_ageing_xlsx'
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
            'font_size': 14,
            'font':'Arial'
        })
        self.format_header = workbook.add_format({
            'bold': True,
            'font_size': 11,
            'align': 'center',
            'font': 'Arial'
            #'border': True
        })
        self.format_header_period = workbook.add_format({
            'bold': True,
            'font_size': 11,
            'align': 'center',
            'font': 'Arial',
            'left': True,
            'right': True,
            # 'border': True
        })
        self.content_header = workbook.add_format({
            'bold': False,
            'font_size': 10,
            'align': 'center',
            'font': 'Arial'
        })
        self.content_header_date = workbook.add_format({
            'bold': False,
            'font_size': 10,
            'align': 'center',
            'font': 'Arial'
            #'num_format': 'dd/mm/yyyy',
        })
        self.line_header = workbook.add_format({
            'font_size': 11,
            'align': 'center',
            'bold': True,
            'left': True,
            'right': True,
            'font': 'Arial'
        })
        self.line_header_total = workbook.add_format({
            'font_size': 11,
            'align': 'center',
            'bold': True,
            'border': True,
            'font': 'Arial'
        })
        self.line_header_period = workbook.add_format({
            'font_size': 11,
            'align': 'center',
            'bold': True,
            'left': True,
            'right': True,
            'font': 'Arial'
        })
        self.line_header_light = workbook.add_format({
            'bold': False,
            'font_size': 10,
            'align': 'center',
            'border': False,
            'font': 'Arial',
            'text_wrap': True,
        })
        self.line_header_light_period = workbook.add_format({
            'bold': False,
            'font_size': 10,
            'align': 'center',
            'left': True,
            'right': True,
            'font': 'Arial',
            'text_wrap': True,
        })
        self.line_header_light_date = workbook.add_format({
            'bold': False,
            'font_size': 10,
            'border': False,
            'font': 'Arial',
            'align': 'center',
        })

    def prepare_report_filters(self, filter):
        """It is writing under second page"""
        self.row_pos_2 += 2
        if filter:
            # Date from
            self.sheet_2.write_string(self.row_pos_2, 0, _('As on Date'),
                                    self.format_header)
            self.sheet_2.write_datetime(self.row_pos_2, 1, self.convert_to_date(str(filter['as_on_date']) or ''),
                                        self.content_header_date)

            # Partners
            self.row_pos_2 += 1
            self.sheet_2.write_string(self.row_pos_2, 0, _('Partners'),
                                                 self.format_header)
            p_list = ', '.join([lt or '' for lt in filter.get('partners')])
            self.sheet_2.write_string(self.row_pos_2, 1, p_list,
                                      self.content_header)

            # Partner Tags
            self.row_pos_2 += 1
            self.sheet_2.write_string(self.row_pos_2, 0, _('Partner Tag'),
                                      self.format_header)
            p_list = ', '.join([lt or '' for lt in filter.get('categories')])
            self.sheet_2.write_string(self.row_pos_2, 1, p_list,
                                      self.content_header)

    def prepare_report_contents(self, data, period_dict, period_list, ageing_lines, filter):
        data = data[0]
        self.row_pos += 3

        if self.record.include_details:
            self.sheet.write_string(self.row_pos, 0,  _('Entry #'), self.format_header)
            self.sheet.write_string(self.row_pos, 1, _('Due Date'), self.format_header)
            self.sheet.write_string(self.row_pos, 2, _('Journal'), self.format_header)
            self.sheet.write_string(self.row_pos, 3, _('Account'), self.format_header)
        else:
            self.sheet.merge_range(self.row_pos, 0, self.row_pos, 3, _('Partner'),
                                   self.format_header)
        k = 4
        for period in period_list:
            self.sheet.write_string(self.row_pos, k, str(period),
                                    self.format_header_period)
            k += 1
        self.sheet.write_string(self.row_pos, k, _('Total'),
                                self.format_header_period)


        if ageing_lines:
            for line in ageing_lines:

                # Dummy vacant lines
                self.row_pos += 1
                self.sheet.write_string(self.row_pos, 4, '', self.line_header_light_period)
                self.sheet.write_string(self.row_pos, 5, '', self.line_header_light_period)
                self.sheet.write_string(self.row_pos, 6, '', self.line_header_light_period)
                self.sheet.write_string(self.row_pos, 7, '', self.line_header_light_period)
                self.sheet.write_string(self.row_pos, 8, '', self.line_header_light_period)
                self.sheet.write_string(self.row_pos, 9, '', self.line_header_light_period)
                self.sheet.write_string(self.row_pos, 10, '', self.line_header_light_period)
                self.sheet.write_string(self.row_pos, 11, '', self.line_header_light_period)

                self.row_pos += 1
                if line != 'Total':
                    self.sheet.merge_range(self.row_pos, 0, self.row_pos, 3, ageing_lines[line].get('partner_name'), self.line_header)
                else:
                    self.sheet.merge_range(self.row_pos, 0, self.row_pos, 3, _('Total'),self.line_header_total)
                k = 4

                for period in period_list:
                    if line != 'Total':
                        self.sheet.write_number(self.row_pos, k, ageing_lines[line][period],self.line_header)
                    else:
                        self.sheet.write_number(self.row_pos, k, ageing_lines[line][period], self.line_header_total)
                    k += 1
                if line != 'Total':
                    self.sheet.write_number(self.row_pos, k, ageing_lines[line]['total'], self.line_header)
                else:
                    self.sheet.write_number(self.row_pos, k, ageing_lines[line]['total'], self.line_header_total)

                if self.record.include_details:
                    if line != 'Total':
                        count, offset, sub_lines, period_list = self.record.process_detailed_data(partner=line, fetch_range=1000000)
                        for sub_line in sub_lines:
                            self.row_pos += 1
                            self.sheet.write_string(self.row_pos, 0, sub_line.get('move_name') or '',
                                                    self.line_header_light)
                            date = self.convert_to_date(sub_line.get('date_maturity') or sub_line.get('date'))
                            self.sheet.write_datetime(self.row_pos, 1, date,
                                                    self.line_header_light_date)
                            self.sheet.write_string(self.row_pos, 2, sub_line.get('journal_name'),
                                                    self.line_header_light)
                            self.sheet.write_string(self.row_pos, 3, sub_line.get('account_name') or '',
                                                    self.line_header_light)

                            self.sheet.write_number(self.row_pos, 4,
                                                    float(sub_line.get('range_0')), self.line_header_light_period)
                            self.sheet.write_number(self.row_pos, 5,
                                                    float(sub_line.get('range_1')), self.line_header_light_period)
                            self.sheet.write_number(self.row_pos, 6,
                                                    float(sub_line.get('range_2')), self.line_header_light_period)
                            self.sheet.write_number(self.row_pos, 7,
                                                    float(sub_line.get('range_3')), self.line_header_light_period)
                            self.sheet.write_number(self.row_pos, 8,
                                                    float(sub_line.get('range_4')), self.line_header_light_period)
                            self.sheet.write_number(self.row_pos, 9,
                                                    float(sub_line.get('range_5')), self.line_header_light_period)
                            self.sheet.write_number(self.row_pos, 10,
                                                    float(sub_line.get('range_6')), self.line_header_light_period)
                            self.sheet.write_string(self.row_pos, 11,
                                                    '', self.line_header_light_period)



            self.row_pos += 1
            k = 4

    def _format_float_and_dates(self, currency_id, lang_id):

        self.line_header.num_format = currency_id.excel_format
        self.line_header_light.num_format = currency_id.excel_format
        self.line_header_light_period.num_format = currency_id.excel_format
        self.line_header_total.num_format = currency_id.excel_format

        self.line_header_light_date.num_format = DATE_DICT.get(lang_id.date_format, 'dd/mm/yyyy')
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

        self.record = record # Wizard object

        self.sheet = workbook.add_worksheet('Partner Ageing')

        self.sheet_2 = workbook.add_worksheet('Filters')
        self.sheet.set_column(0, 0, 15)
        self.sheet.set_column(1, 1, 12)
        self.sheet.set_column(2, 3, 15)
        self.sheet.set_column(3, 3, 15)
        self.sheet.set_column(4, 4, 15)
        self.sheet.set_column(5, 5, 15)
        self.sheet.set_column(6, 6, 15)
        self.sheet.set_column(7, 7, 15)
        self.sheet.set_column(8, 8, 15)
        self.sheet.set_column(9, 9, 15)
        self.sheet.set_column(10, 10, 15)
        self.sheet.set_column(11, 11, 15)

        self.sheet_2.set_column(0, 0, 35)
        self.sheet_2.set_column(1, 1, 25)
        self.sheet_2.set_column(2, 2, 25)
        self.sheet_2.set_column(3, 3, 25)
        self.sheet_2.set_column(4, 4, 25)
        self.sheet_2.set_column(5, 5, 25)
        self.sheet_2.set_column(6, 6, 25)

        self.sheet.freeze_panes(4, 0)

        self.sheet.screen_gridlines = False
        self.sheet_2.screen_gridlines = False
        self.sheet_2.protect()
        self.record = record

        self.sheet.set_zoom(75)

        # For Formating purpose
        lang = self.env.user.lang
        self.language_id = self.env['res.lang'].search([('code','=',lang)])[0]
        self._format_float_and_dates(self.env.user.company_id.currency_id, self.language_id)

        if record:
            data = record.read()
            self.sheet.merge_range(0, 0, 0, 11, 'Partner Ageing'+' - '+data[0]['company_id'][1], self.format_title)
            self.dateformat = self.env.user.lang
            filters, ageing_lines, period_dict, period_list = record.get_report_datas()
            # Filter section
            self.prepare_report_filters(filters)
            # Content section
            self.prepare_report_contents(data, period_dict, period_list, ageing_lines, filters)
