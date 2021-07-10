# -*- coding: utf-8 -*-

from odoo import api, models, fields
import re

from datetime import datetime, timedelta, date
import calendar
from dateutil.relativedelta import relativedelta


class InsFinancialReport(models.TransientModel):
    _inherit = "ins.financial.report"
    _description = "Financial Reports"

    def action_xlsx(self):
        ''' Button function for Xlsx '''
        return self.env.ref(
            'dynamic_xlsx'
            '.action_ins_financial_report_xlsx').report_action(self)


class InsGeneralLedger(models.TransientModel):
    _inherit = "ins.general.ledger"
    _description = "General Ledger Reports"

    def action_xlsx(self):
        ''' Button function for Xlsx '''
        return self.env.ref(
            'dynamic_xlsx'
            '.action_ins_general_ledger_xlsx').report_action(self)


class InsPartnerLedger(models.TransientModel):
    _inherit = "ins.partner.ledger"
    _description = "Partner Ledger Reports"

    def action_xlsx(self):
        ''' Button function for Xlsx '''
        return self.env.ref(
            'dynamic_xlsx'
            '.action_ins_partner_ledger_xlsx').report_action(self)


class InsPartnerAgeing(models.TransientModel):
    _inherit = "ins.partner.ageing"
    _description = "Partner Ageing Reports"

    def action_xlsx(self):
        ''' Button function for Xlsx '''
        return self.env.ref(
            'dynamic_xlsx'
            '.action_ins_partner_ageing_xlsx').report_action(self)


class InsTrialBalance(models.TransientModel):
    _inherit = "ins.trial.balance"
    _description = "Trial Balance Reports"

    def action_xlsx(self):
        ''' Button function for Xlsx '''
        return self.env.ref(
            'dynamic_xlsx'
            '.action_ins_trial_balance_xlsx').report_action(self)