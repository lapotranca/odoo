# -*- coding: utf-8 -*-

from odoo import fields, models, api


class AccountPartnerLedger(models.TransientModel):
    _inherit = "account.common.partner.report"
    _name = "account.report.partner.ledger"
    _description = "Account Partner Ledger"

    amount_currency = fields.Boolean("With Currency", help="It adds the currency column on report if the currency differs from the company currency.")
    reconciled = fields.Boolean('Reconciled Entries')
    partner_ids = fields.Many2many('res.partner', string='Partner')

    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update({'reconciled': self.reconciled, 'amount_currency': self.amount_currency})
        data['form'].update(self.read(['partner_ids'])[0])       
        return self.env.ref('skit_account_reports.action_report_partnerledger').with_context(landscape=True).report_action(self, data=data)
    
      
    @api.onchange('result_selection')
    def _display_partners(self):
        self.partner_ids = []
        if (self.result_selection == 'customers'):
            temp_partner_ids = self.env['res.partner'].search([('customers', '=', True)]).ids
            return {'domain': {'partner_ids': [('id', 'in', temp_partner_ids)]}}
        elif (self.result_selection == 'vendors'):
            temp_partner_ids = self.env['res.partner'].search([('vendors', '=', True)]).ids
            return {'domain': {'partner_ids': [('id', 'in', temp_partner_ids)]}}
        else:
            return {'domain': {'partner_ids': []}}