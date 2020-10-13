# -*- coding: utf-8 -*-

from odoo import tools
from odoo import models, fields


class PLReport(models.Model):
    _name = "account.profit.loss"
    _description = "Profit and Loss Statistics"
    _auto = False
    _rec_name = 'date'

    name = fields.Char(required=True, string="Label")
    report_name = fields.Char(string="Name")
    quantity = fields.Float(digits=(16, 2))
    product_id = fields.Many2one('product.product', string='Product')
    debit = fields.Monetary(default=0.0, currency_field='currency_id')
    credit = fields.Monetary(default=0.0, currency_field='currency_id')
    balance = fields.Monetary(compute='_store_balance', store=True,
                              currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency')
    account_id = fields.Many2one('account.account', string='Account')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', groups="analytic.group_analytic_accounting")
    move_id = fields.Many2one('account.move', string='Journal Entry')
    payment_id = fields.Many2one('account.payment',
                                 string="Payment")
    journal_id = fields.Many2one('account.journal',
                                 string='Journal')  # related is required
    date = fields.Date(string='Date')
    company_id = fields.Many2one('res.company',
                                 string='Company')
    partner_id = fields.Many2one('res.partner')
    cost_center_id = fields.Many2one('tf.cost.center', 'Cost Center')
    department_id = fields.Many2one('tf.department', string='Departments')

    def _compute_report_balance(self, reports):
        ''' '''
        res = {}
        query = ""
        for report in reports:
            if report.id in res:
                continue
            if report.type == 'accounts':
                # it's the sum of the linked accounts
                if query:
                    query = query+" union "
                
                if (report.account_ids != ""):
                    subquery = " select '"+(" "+report.name if report.name == "Income" else report.name)+"' as report_name, \
                    ml.journal_id,ml.payment_id,ml.quantity,\
                    ml.company_id,m.currency_id,ml.id as id, ml.move_id, ml.name, \
                    ml.date, ml.product_id,ml.partner_id,ml.account_id, ml.analytic_account_id, \
                    COALESCE((credit), 0) as credit, ((COALESCE((debit),0) - COALESCE((credit), 0)) * "+str(report.sign)+") as balance, COALESCE((debit), 0) as debit,ml.cost_center_id, ml.department_id \
                    from account_move m \
                    inner join account_move_line ml on m.id = ml.move_id \
                    where ml.account_id in ( "+report.account_ids+")"
                else: 
                    subquery = " SELECT '"+(" "+report.name if report.name == "Income" else report.name)+"' as report_name,0 as journal_id, \
                    0 as payment_id,0 as quantity,0 as company_id,0 as currency_id,0 as id,0 as move_id,null as name,null as date,0 as product_id, \
                    0 as partner_id,0 as account_id,0 as analytic_account_id,0 as credit,0 as balance,0 as debit"

                query = query + (subquery)

            elif report.type == 'account_type':
                # it's the sum the leaf accounts with such an account type
                accounts = self.env['account.account'].search([
                    ('user_type_id', 'in', report.account_type_ids.ids)
                    ])
                acc_ids = ""
                for account in accounts:
                    if not acc_ids:
                        acc_ids = str(account.id)
                    else:
                        acc_ids = acc_ids+", "+str(account.id)
                if query:
                    query = query+" union "

                if (acc_ids != ""):
                    subquery = " select '"+(" "+report.name if report.name == "Income" else report.name)+"' as report_name, \
                    ml.journal_id,ml.payment_id,ml.quantity,\
                    ml.company_id,m.currency_id,ml.id as id, ml.move_id, ml.name,\
                    ml.date, ml.product_id,ml.partner_id,ml.account_id, ml.analytic_account_id, \
                    COALESCE((credit), 0) as credit, ((COALESCE((debit),0) - COALESCE((credit), 0)) * "+str(report.sign)+") as balance, COALESCE((debit), 0) as debit,ml.cost_center_id, ml.department_id \
                    from account_move m \
                    inner join account_move_line ml on m.id = ml.move_id \
                    where ml.account_id in ( "+acc_ids+")"
                else: 
                    subquery = " SELECT '"+(" "+report.name if report.name == "Income" else report.name)+"' as report_name,0 as journal_id, \
                    0 as payment_id,0 as quantity,0 as company_id,0 as currency_id,0 as id,0 as move_id,null as name,null as date,0 as product_id, \
                    0 as partner_id,0 as account_id,0 as analytic_account_id,0 as credit,0 as balance,0 as debit"

                query = query + (subquery)

            elif report.type == 'account_report' and report.account_report_id:
                # it's the amount of the linked report
                res2 = self._compute_report_balance(report.account_report_id)
                if query and res2.strip():
                    query = query+" union "
                query = query + res2
            elif report.type == 'sum':
                continue

        return query

    def init(self):
        account_report = self.env['account.financial.report'].search([
            ('name', 'ilike', 'profit and loss')
            ])
        child_reports = account_report._get_children_by_order()
        res = self._compute_report_balance(child_reports)
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as ( %s )""" % (
                    self._table, res))

