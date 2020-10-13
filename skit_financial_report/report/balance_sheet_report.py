# -*- coding: utf-8 -*-

from odoo import tools
from odoo import models, fields, api
from datetime import datetime, date

class BalanceSheetReport(models.Model):
    _name = "account.balance.sheet"
    _description = "Balance Sheet Statistics"
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
    account_code = fields.Char(string="Por Codigo Cuenta", compute="_store_balance_code", store=True)
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
    initial_balance = fields.Float('Initial Balance')

    def _store_balance_code(self):
        if self.account_id:
            self.account_code= self.account_id.code

    def _compute_report_balance(self, reports, report_name):
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
                if report_name == 'Balance Sheet':
                    report_name = report.name
                #removed the ml.user_type_id,ml. 
                if (report.account_ids != ""):
                    subquery = " select '"+(report_name if report_name else report.name)+"' as report_name, \
                    ml.journal_id,ml.payment_id,ml.quantity,\
                    ml.company_id ,m.currency_id,ml.id as id, ml.move_id, ml.name,\
                    ml.date, ml.product_id,ml.partner_id,ml.account_id, ml.analytic_account_id,\
                    COALESCE((credit), 0) as credit,\
                    COALESCE((debit),0) - COALESCE((credit), 0) as balance,CONCAT(aa.code,' ',aa.name) as account_code,\
                    CASE WHEN    ml.date < \'" + str(date(date.today().year, 1, 1)) + "\'  THEN COALESCE((debit),0) - COALESCE((credit), 0) ELSE 0 END AS initial_balance,\
                    COALESCE((debit), 0) as debit, ml.cost_center_id, ml.department_id from account_move m inner join \
                    account_move_line ml on m.id = ml.move_id \
                    inner join account_account aa on aa.id = ml.account_id\
                    where ml.account_id \
                    in ( "+report.account_ids+")"
                else:        
                    subquery = " SELECT '"+(" "+report.name if report.name == "Balance Sheet" else report.name)+"' as report_name,0 as journal_id, \
                    0 as payment_id,0 as quantity,0 as company_id,0 as currency_id,0 as id,0 as move_id,null as name,null as date,0 as product_id, \
                    0 as partner_id,0 as account_id,0 as analytic_account_id,0 as credit,0 as balance,0 as debit"
                query = query + (subquery)

            elif report.type == 'account_type':
                # it's the sum the leaf accounts with such an account type
                accounts = self.env['account.account'].search(
                    [('user_type_id', 'in', report.account_type_ids.ids)])
                acc_ids = ""
                for account in accounts:
                    if not acc_ids:
                        acc_ids = str(account.id)
                    else:
                        acc_ids = acc_ids+", "+str(account.id)
                if query:
                    query = query+" union "
                if report_name == 'Balance Sheet':
                    report_name = report.name
                if (acc_ids != ""):
                    subquery = " select '"+(report_name if report_name else report.name)+"' as report_name, \
                    ml.journal_id,ml.payment_id,ml.quantity,\
                    ml.company_id,m.currency_id,ml.id as id, ml.move_id, ml.name,\
                    ml.date, ml.product_id,ml.partner_id,ml.account_id,ml.analytic_account_id, \
                    COALESCE((credit), 0) as credit,\
                    COALESCE((debit),0) - COALESCE((credit), 0) as balance,CONCAT(aa.code,' ',aa.name) as account_code,\
                    CASE WHEN    ml.date < \'" + str(date(date.today().year, 1, 1)) + "\'  THEN COALESCE((debit),0) - COALESCE((credit), 0) ELSE 0 END AS initial_balance,\
                    COALESCE((debit), 0) as debit, ml.cost_center_id, ml.department_id from account_move m  inner join \
                    account_move_line ml on m.id = ml.move_id \
                    inner join account_account aa on aa.id = ml.account_id\
                    where ml.account_id \
                    in ( "+acc_ids+")"                
                else:        
                    subquery = " SELECT '"+(" "+report.name if report.name == "Balance Sheet" else report.name)+"' as report_name,0 as journal_id, \
                    0 as payment_id,0 as quantity,0 as company_id,0 as currency_id,0 as id,0 as move_id,null as name,null as date,0 as product_id, \
                    0 as partner_id,0 as account_id,0 as analytic_account_id,0 as credit,0 as balance,0 as debit"

                query = query + (subquery)

            elif report.type == 'account_report' and report.account_report_id:
                # it's the amount of the linked report
                res2 = self._compute_report_balance(
                    report.account_report_id, report.account_report_id.name)
                if query and res2.strip():
                    query = query+" union "
                query = query + res2
            elif report.type == 'sum':
                # continue
                res2 = self._compute_report_balance(report.children_ids,
                                                    report.name)
                if query and res2.strip():
                    query = query+" union "
                query = query + res2
        return query
     
   
    def init(self):
        account_report = self.env['account.financial.report'].search(
                                                [('name', 'ilike',
                                                  'balance sheet')])
        child_reports = account_report._get_children_by_order()
        res = self._compute_report_balance(child_reports, '')
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as ( %s )""" % (
                    self._table, res))

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super(BalanceSheetReport, self).read_group(domain=domain, fields=fields, groupby=groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

        updatable_rec = [x for x in res if x.get('account_id')]
        compare_date = str(date(date.today().year, 1, 1))
        if domain:
            comp_date = [x for x in domain if x[0] == 'date' and x[1] in ['>', '=', '>=']]
            if comp_date:
                compare_date = comp_date[0][2]
                if not compare_date:
                    compare_date = str(date(date.today().year, 1, 1))

        for bal in updatable_rec:
            compare_sql_string = ""
            if bal.get('account_id'):
                if compare_sql_string:
                    compare_sql_string += " and "
                compare_sql_string += "account_id = "+str(bal['account_id'][0])
            if bal.get('cost_center_id'):
                if compare_sql_string:
                    compare_sql_string += " and "
                compare_sql_string += "cost_center_id = " + str(bal['cost_center_id'][0])
            if bal.get('department_id'):
                if compare_sql_string:
                    compare_sql_string += " and "
                compare_sql_string += "department_id = " + str(bal['department_id'][0])

            self.env.cr.execute("select sum(debit) as debit, sum(credit) as credit \
                                 from account_move_line \
                                 where "+compare_sql_string+" and date < \' "+str(compare_date)+" \'")
            ml_id = self.env.cr.dictfetchall()
            # ml_id = self.env['account.move.line'].search([('account_id', '=', bal['account_id']), ('date', '<', str(compare_date))])
            if 'initial_balance' in bal.keys():
                if ml_id:
                    for ml in ml_id:
                        debit = 0
                        credit = 0
                        if ml.get('debit'):
                            debit = ml.get('debit')
                        if ml.get('credit'):
                            credit = ml.get('credit')
                        if debit or credit:
                            bal['initial_balance'] = debit - credit
                else:
                    bal['initial_balance'] = 0


        # if updatable_rec:
        #     records = [x for x in self.env['account.balance.sheet'].search([]) if str(x.date) < compare_date]
        #     for rec in records:
        #         # move_line_id = self.env['account.move.line'].browse()
        #         for updte in updatable_rec:
        #             if updte.get('account_id')[0] == rec.account_id.id:
        #                 updte['initial_balance'] = updte['debit'] - updte['credit']
        #             # else:
        #             #     updte['initial_balance'] = 0
        for updte in res:
            if 'balance' in updte.keys() and updte.get('initial_balance') and updte.get('debit') or updte.get('credit'):
                updte['balance'] = (updte.get('initial_balance') or 0) + (updte.get('debit') or 0) - (updte.get('credit') or 0)

        return res

class ReportWizard(models.TransientModel):
    _name = "tf.report.wizard"

    date_from = fields.Date('Date From')
    date_to = fields.Date('Date To')

    def create_odoo_report(self):
        result = {
            'name': 'Balance Sheet',
            'view_type': 'pivot',
            'view_mode': 'pivot',
            'view_id': self.env.ref('skit_financial_report.view_balance_sheet_report_pivot').id,
            'res_model': 'account.balance.sheet',
            'type': 'ir.actions.act_window',
            # "target": "new",
            "context": {'search_default_current':1,
				'search_default_customer':1, 'group_by':[], 'group_by_no_leaf':1,
				'search_default_year': 1},
        }
        domain = []
        if self.date_from:
            self.env.cr.execute("drop rule IF EXISTS account_balance_sheet_rule_tf on account_balance_sheet")
            self.env.cr.execute("CREATE or REPLACE RULE account_balance_sheet_rule_tf AS ON UPDATE TO account_balance_sheet \
                                             DO INSTEAD UPDATE account_balance_sheet SET initial_balance = \
                                             (select COALESCE((debit),0) - COALESCE((credit), 0) as initial_balance from account_move_line ml \
                                             WHERE date < \'" + str(self.date_from) + "\' and ml.id = id)")
            self.env.cr.execute("CREATE or REPLACE RULE account_balance_sheet_rule_tf AS ON UPDATE TO account_balance_sheet \
                                             DO INSTEAD UPDATE account_balance_sheet SET balance = (initial_balance + debit - credit)")
            # self.env.cr.execute("UPDATE account_balance_sheet SET initial_balance = balance WHERE date = \'"+str(self.date_from)+"\' ")

            # self.env['account.balance.sheet'].with_context(tf_from_date=self.date_from).init()
            # bal_ids = [x for x in self.env['account.balance.sheet'].search([]) if x.date < self.date_from]
            #
            # for rec in bal_ids:
            #     rec.initial_balance = rec.balance

            domain.append(('date', '>', str(self.date_from)))
        if self.date_to:
            domain.append(('date', '<', str(self.date_to)))
        if domain:
            result['domain'] = domain
        return result
