from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta, date
import calendar
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

FETCH_RANGE = 2000

class InsGeneralLedger(models.TransientModel):
    _inherit = "ins.general.ledger"

    as_account_start = fields.Many2one('account.account', string='Cuenta Inicio')
    as_account_end = fields.Many2one('account.account', string='Cuenta Fin')

    def get_filters(self, default_filters={}):
        ret = super(InsGeneralLedger, self).get_filters(default_filters)
        ret['as_account_start'] = self.as_account_start
        ret['as_account_end'] = self.as_account_end
        return ret

    def process_filters(self):
        filters = super(InsGeneralLedger, self).process_filters()
        data = self.get_filters(default_filters={})
        if data.get('as_account_start', False) and data.get('as_account_end', False):
            as_inicio = data.get('as_account_start', False)
            as_fin = data.get('as_account_end', False)
            accounts = self.env['account.account'].search([('code','>=',as_inicio.code),('code','<=',as_fin.code)])
            filters['accounts'] = self.env['account.account'].browse(accounts.ids).mapped('code')
        # else:
        #     filters['accounts'] = ['All']
        return filters

    def process_data(self):
        '''
        It is the method for showing summary details of each accounts. Just basic details to show up
        Three sections,
        1. Initial Balance
        2. Current Balance
        3. Final Balance
        :return:
        '''
        cr = self.env.cr

        data = self.get_filters(default_filters={})

        WHERE = self.build_where_clause(data)

        account_company_domain = [('company_id','=', self.env.context.get('company_id') or self.env.company.id)]

        if data.get('account_tag_ids', []):
            account_company_domain.append(('tag_ids','in', data.get('account_tag_ids', [])))

        if data.get('account_ids', []):
            account_company_domain.append(('id','in', data.get('account_ids', [])))

        if data.get('as_account_start', False) and data.get('as_account_end', False):
            as_inicio = data.get('as_account_start', False)
            as_fin = data.get('as_account_end', False)
            accounts = self.env['account.account'].search([('code','>=',as_inicio.code),('code','<=',as_fin.code)])
            account_company_domain.append(('id','in', accounts.ids))

        account_ids = self.env['account.account'].search(account_company_domain)

        move_lines = {
            x.code: {
                'name': x.name,
                'code': x.code,
                'company_currency_id': 0,
                'company_currency_symbol': 'AED',
                'company_currency_precision': 0.0100,
                'company_currency_position': 'after',
                'id': x.id,
                'lines': []
            } for x in sorted(account_ids, key=lambda a:a.code)
        }
        for account in account_ids:

            currency = account.company_id.currency_id or self.env.company.currency_id
            symbol = currency.symbol
            rounding = currency.rounding
            position = currency.position

            opening_balance = 0

            WHERE_INIT = WHERE + " AND l.date < '%s'" % data.get('date_from')
            WHERE_INIT += " AND l.account_id = %s" % account.id
            if data.get('sort_accounts_by') == 'date':
                ORDER_BY_CURRENT = 'l.date, l.move_id'
            else:
                ORDER_BY_CURRENT = 'j.code, p.name, l.move_id'
            if data.get('initial_balance'):
                sql = ('''
                    SELECT 
                        COALESCE(SUM(l.debit),0) AS debit, 
                        COALESCE(SUM(l.credit),0) AS credit, 
                        COALESCE(SUM(l.debit - l.credit),0) AS balance
                    FROM account_move_line l
                    JOIN account_move m ON (l.move_id=m.id)
                    JOIN account_account a ON (l.account_id=a.id)
                    LEFT JOIN account_analytic_account anl ON (l.analytic_account_id=anl.id)
                    LEFT JOIN account_analytic_tag_account_move_line_rel analtag ON analtag.account_move_line_id = l.id
                    LEFT JOIN res_currency c ON (l.currency_id=c.id)
                    LEFT JOIN res_partner p ON (l.partner_id=p.id)
                    JOIN account_journal j ON (l.journal_id=j.id)
                    WHERE %s
                ''') % WHERE_INIT
                cr.execute(sql)
                for row in cr.dictfetchall():
                    row['move_name'] = 'Initial Balance'
                    row['account_id'] = account.id
                    row['initial_bal'] = True
                    row['ending_bal'] = False
                    opening_balance += row['balance']
                    move_lines[account.code]['lines'].append(row)
            WHERE_CURRENT = WHERE + " AND l.date >= '%s'" % data.get('date_from') + " AND l.date <= '%s'" % data.get(
                'date_to')
            WHERE_CURRENT += " AND a.id = %s" % account.id
            sql = ('''
                SELECT
                    l.id AS lid,
                    l.date AS ldate,
                    j.code AS lcode,
                    p.name AS partner_name,
                    m.name AS move_name,
                    l.name AS lname,
                    COALESCE(l.debit,0) AS debit,
                    COALESCE(l.credit,0) AS credit,
                    COALESCE(l.debit - l.credit,0) AS balance,
                    COALESCE(l.amount_currency,0) AS amount_currency
                FROM account_move_line l
                JOIN account_move m ON (l.move_id=m.id)
                JOIN account_account a ON (l.account_id=a.id)
                LEFT JOIN account_analytic_account anl ON (l.analytic_account_id=anl.id)
                LEFT JOIN account_analytic_tag_account_move_line_rel analtag ON analtag.account_move_line_id = l.id
                LEFT JOIN res_currency c ON (l.currency_id=c.id)
                LEFT JOIN res_currency cc ON (l.company_currency_id=cc.id)
                LEFT JOIN res_partner p ON (l.partner_id=p.id)
                JOIN account_journal j ON (l.journal_id=j.id)
                WHERE %s
                --GROUP BY l.id, l.account_id, l.date, j.code, l.currency_id, l.debit_currency, l.credit_currency, l.ref, l.name, m.id, m.name, c.rounding, cc.rounding, cc.position, c.position, c.symbol, cc.symbol, p.name
                ORDER BY %s
            ''') % (WHERE_CURRENT, ORDER_BY_CURRENT)
            cr.execute(sql)
            current_lines = cr.dictfetchall()
            for row in current_lines:
                row['initial_bal'] = False
                row['ending_bal'] = False

                current_balance = row['balance']
                row['balance'] = opening_balance + current_balance
                opening_balance += current_balance
                row['initial_bal'] = False

                move_lines[account.code]['lines'].append(row)
            if data.get('initial_balance'):
                WHERE_FULL = WHERE + " AND l.date <= '%s'" % data.get('date_to')
            else:
                WHERE_FULL = WHERE + " AND l.date >= '%s'" % data.get('date_from') + " AND l.date <= '%s'" % data.get(
                    'date_to')
            WHERE_FULL += " AND a.id = %s" % account.id
            sql = ('''
                SELECT 
                    COALESCE(SUM(l.debit),0) AS debit, 
                    COALESCE(SUM(l.credit),0) AS credit, 
                    COALESCE(SUM(l.debit - l.credit),0) AS balance
                FROM account_move_line l
                JOIN account_move m ON (l.move_id=m.id)
                JOIN account_account a ON (l.account_id=a.id)
                LEFT JOIN account_analytic_account anl ON (l.analytic_account_id=anl.id)
                LEFT JOIN account_analytic_tag_account_move_line_rel analtag ON analtag.account_move_line_id = l.id
                LEFT JOIN res_currency c ON (l.currency_id=c.id)
                LEFT JOIN res_partner p ON (l.partner_id=p.id)
                JOIN account_journal j ON (l.journal_id=j.id)
                WHERE %s
            ''') % WHERE_FULL
            cr.execute(sql)
            for row in cr.dictfetchall():
                if data.get('display_accounts') == 'balance_not_zero' and currency.is_zero(row['debit'] - row['credit']):
                    move_lines.pop(account.code, None)
                else:
                    row['ending_bal'] = True
                    row['initial_bal'] = False
                    move_lines[account.code]['lines'].append(row)
                    move_lines[account.code]['debit'] = row['debit']
                    move_lines[account.code]['credit'] = row['credit']
                    move_lines[account.code]['balance'] = row['balance']
                    move_lines[account.code]['company_currency_id'] = currency.id
                    move_lines[account.code]['company_currency_symbol'] = symbol
                    move_lines[account.code]['company_currency_precision'] = rounding
                    move_lines[account.code]['company_currency_position'] = position
                    move_lines[account.code]['count'] = len(current_lines)
                    move_lines[account.code]['pages'] = self.get_page_list(len(current_lines))
                    move_lines[account.code]['single_page'] = True if len(current_lines) <= FETCH_RANGE else False
        return move_lines