from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta, date
import calendar
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from operator import itemgetter


class InsTrialBalance(models.TransientModel):
    _name = "ins.trial.balance"

    def _get_journals(self):
        return self.env['account.journal'].search([])

    @api.onchange('date_range', 'financial_year')
    def onchange_date_range(self):
        if self.date_range:
            date = datetime.today()
            if self.date_range == 'today':
                self.date_from = date.strftime("%Y-%m-%d")
                self.date_to = date.strftime("%Y-%m-%d")
            if self.date_range == 'this_week':
                day_today = date - timedelta(days=date.weekday())
                self.date_from = (day_today - timedelta(days=date.weekday())).strftime("%Y-%m-%d")
                self.date_to = (day_today + timedelta(days=6)).strftime("%Y-%m-%d")
            if self.date_range == 'this_month':
                self.date_from = datetime(date.year, date.month, 1).strftime("%Y-%m-%d")
                self.date_to = datetime(date.year, date.month, calendar.mdays[date.month]).strftime("%Y-%m-%d")
            if self.date_range == 'this_quarter':
                if int((date.month - 1) / 3) == 0:  # First quarter
                    self.date_from = datetime(date.year, 1, 1).strftime("%Y-%m-%d")
                    self.date_to = datetime(date.year, 3, calendar.mdays[3]).strftime("%Y-%m-%d")
                if int((date.month - 1) / 3) == 1:  # Second quarter
                    self.date_from = datetime(date.year, 4, 1).strftime("%Y-%m-%d")
                    self.date_to = datetime(date.year, 6, calendar.mdays[6]).strftime("%Y-%m-%d")
                if int((date.month - 1) / 3) == 2:  # Third quarter
                    self.date_from = datetime(date.year, 7, 1).strftime("%Y-%m-%d")
                    self.date_to = datetime(date.year, 9, calendar.mdays[9]).strftime("%Y-%m-%d")
                if int((date.month - 1) / 3) == 3:  # Fourth quarter
                    self.date_from = datetime(date.year, 10, 1).strftime("%Y-%m-%d")
                    self.date_to = datetime(date.year, 12, calendar.mdays[12]).strftime("%Y-%m-%d")
            if self.date_range == 'this_financial_year':
                if self.financial_year == 'january_december':
                    self.date_from = datetime(date.year, 1, 1).strftime("%Y-%m-%d")
                    self.date_to = datetime(date.year, 12, 31).strftime("%Y-%m-%d")
                if self.financial_year == 'april_march':
                    if date.month < 4:
                        self.date_from = datetime(date.year - 1, 4, 1).strftime("%Y-%m-%d")
                        self.date_to = datetime(date.year, 3, 31).strftime("%Y-%m-%d")
                    else:
                        self.date_from = datetime(date.year, 4, 1).strftime("%Y-%m-%d")
                        self.date_to = datetime(date.year + 1, 3, 31).strftime("%Y-%m-%d")
                if self.financial_year == 'july_june':
                    if date.month < 7:
                        self.date_from = datetime(date.year - 1, 7, 1).strftime("%Y-%m-%d")
                        self.date_to = datetime(date.year, 6, 30).strftime("%Y-%m-%d")
                    else:
                        self.date_from = datetime(date.year, 7, 1).strftime("%Y-%m-%d")
                        self.date_to = datetime(date.year + 1, 6, 30).strftime("%Y-%m-%d")
            date = (datetime.now() - relativedelta(days=1))
            if self.date_range == 'yesterday':
                self.date_from = date.strftime("%Y-%m-%d")
                self.date_to = date.strftime("%Y-%m-%d")
            date = (datetime.now() - relativedelta(days=7))
            if self.date_range == 'last_week':
                day_today = date - timedelta(days=date.weekday())
                self.date_from = (day_today - timedelta(days=date.weekday())).strftime("%Y-%m-%d")
                self.date_to = (day_today + timedelta(days=6)).strftime("%Y-%m-%d")
            date = (datetime.now() - relativedelta(months=1))
            if self.date_range == 'last_month':
                self.date_from = datetime(date.year, date.month, 1).strftime("%Y-%m-%d")
                self.date_to = datetime(date.year, date.month, calendar.mdays[date.month]).strftime("%Y-%m-%d")
            date = (datetime.now() - relativedelta(months=3))
            if self.date_range == 'last_quarter':
                if int((date.month - 1) / 3) == 0:  # First quarter
                    self.date_from = datetime(date.year, 1, 1).strftime("%Y-%m-%d")
                    self.date_to = datetime(date.year, 3, calendar.mdays[3]).strftime("%Y-%m-%d")
                if int((date.month - 1) / 3) == 1:  # Second quarter
                    self.date_from = datetime(date.year, 4, 1).strftime("%Y-%m-%d")
                    self.date_to = datetime(date.year, 6, calendar.mdays[6]).strftime("%Y-%m-%d")
                if int((date.month - 1) / 3) == 2:  # Third quarter
                    self.date_from = datetime(date.year, 7, 1).strftime("%Y-%m-%d")
                    self.date_to = datetime(date.year, 9, calendar.mdays[9]).strftime("%Y-%m-%d")
                if int((date.month - 1) / 3) == 3:  # Fourth quarter
                    self.date_from = datetime(date.year, 10, 1).strftime("%Y-%m-%d")
                    self.date_to = datetime(date.year, 12, calendar.mdays[12]).strftime("%Y-%m-%d")
            date = (datetime.now() - relativedelta(years=1))
            if self.date_range == 'last_financial_year':
                if self.financial_year == 'january_december':
                    self.date_from = datetime(date.year, 1, 1).strftime("%Y-%m-%d")
                    self.date_to = datetime(date.year, 12, 31).strftime("%Y-%m-%d")
                if self.financial_year == 'april_march':
                    if date.month < 4:
                        self.date_from = datetime(date.year - 1, 4, 1).strftime("%Y-%m-%d")
                        self.date_to = datetime(date.year, 3, 31).strftime("%Y-%m-%d")
                    else:
                        self.date_from = datetime(date.year, 4, 1).strftime("%Y-%m-%d")
                        self.date_to = datetime(date.year + 1, 3, 31).strftime("%Y-%m-%d")
                if self.financial_year == 'july_june':
                    if date.month < 7:
                        self.date_from = datetime(date.year - 1, 7, 1).strftime("%Y-%m-%d")
                        self.date_to = datetime(date.year, 6, 30).strftime("%Y-%m-%d")
                    else:
                        self.date_from = datetime(date.year, 7, 1).strftime("%Y-%m-%d")
                        self.date_to = datetime(date.year + 1, 6, 30).strftime("%Y-%m-%d")

    @api.model
    def _get_default_date_range(self):
        return self.env.company.date_range

    def name_get(self):
        res = []
        for record in self:
            res.append((record.id, 'Trial Balance'))
        return res

    financial_year = fields.Selection(
        [('april_march', '1 April to 31 March'),
         ('july_june', '1 july to 30 June'),
         ('january_december', '1 Jan to 31 Dec')],
        string='Financial Year', default=lambda self: self.env.company.financial_year, required=True)

    date_range = fields.Selection(
        [('today', 'Today'),
         ('this_week', 'This Week'),
         ('this_month', 'This Month'),
         ('this_quarter', 'This Quarter'),
         ('this_financial_year', 'This financial Year'),
         ('yesterday', 'Yesterday'),
         ('last_week', 'Last Week'),
         ('last_month', 'Last Month'),
         ('last_quarter', 'Last Quarter'),
         ('last_financial_year', 'Last Financial Year')],
        string='Date Range', default=_get_default_date_range
    )
    strict_range = fields.Boolean(
        string='Strict Range',
        default=lambda self: self.env.company.strict_range
    )
    show_hierarchy = fields.Boolean(
        string='Show hierarchy'
    )
    target_moves = fields.Selection(
        [('all_entries', 'All entries'),
         ('posted_only', 'Posted Only')], string='Target Moves',
        default='posted_only', required=True
    )
    display_accounts = fields.Selection(
        [('all', 'All'),
         ('balance_not_zero', 'With balance not zero')], string='Display accounts',
        default='balance_not_zero', required=True
    )
    date_from = fields.Date(
        string='Start date',
    )
    date_to = fields.Date(
        string='End date',
    )
    account_ids = fields.Many2many(
        'account.account', string='Accounts'
    )
    analytic_ids = fields.Many2many(
        'account.analytic.account', string='Analytic Accounts'
    )
    journal_ids = fields.Many2many(
        'account.journal', string='Journals',
        default=_get_journals
    )
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company
    )

    def write(self, vals):

        if vals.get('date_range'):
            vals.update({'date_from': False, 'date_to': False})
        if vals.get('date_from') and vals.get('date_to'):
            vals.update({'date_range': False})

        if vals.get('journal_ids'):
            vals.update({'journal_ids': vals.get('journal_ids')})
        if vals.get('journal_ids') == []:
            vals.update({'journal_ids': [(5,)]})

        if vals.get('analytic_ids'):
            vals.update({'analytic_ids': vals.get('analytic_ids')})
        if vals.get('analytic_ids') == []:
            vals.update({'analytic_ids': [(5,)]})

        ret = super(InsTrialBalance, self).write(vals)
        return ret

    def validate_data(self):
        if self.date_from > self.date_to:
            raise ValidationError(_('"Date from" must be less than or equal to "Date to"'))
        return True

    def process_filters(self, data):
        ''' To show on report headers'''
        filters = {}

        if data.get('date_from') > data.get('date_to'):
            raise ValidationError(_('From date must not be less than to date'))

        if not data.get('date_from') or not data.get('date_to'):
            raise ValidationError(_('From date and To dates are mandatory for this report'))

        if data.get('journal_ids',[]):
            filters['journals'] = self.env['account.journal'].browse(data.get('journal_ids',[])).mapped('code')
        else:
            filters['journals'] = ''

        if data.get('analytic_ids', []):
            filters['analytics'] = self.env['account.analytic.account'].browse(data.get('analytic_ids', [])).mapped(
                'name')
        else:
            filters['analytics'] = ['All']

        if data.get('display_accounts') == 'all':
            filters['display_accounts'] = 'All'
        else:
            filters['display_accounts'] = 'With balance not zero'

        if data.get('date_from',False):
            filters['date_from'] = data.get('date_from')
        if data.get('date_to', False):
            filters['date_to'] = data.get('date_to')

        if data.get('show_hierarchy', False):
            filters['show_hierarchy'] = True
        else:
            filters['show_hierarchy'] = False

        if data.get('strict_range', False):
            filters['strict_range'] = True
        else:
            filters['strict_range'] = False

        filters['journals_list'] = data.get('journals_list')
        filters['analytics_list'] = data.get('analytics_list')
        filters['company_name'] = data.get('company_name')

        return filters

    def prepare_hierarchy(self, move_lines):
        '''
        It will process the move lines as per the hierarchy.
        :param move_lines: list of dict
        :return: list of dict with hierarchy levels
        '''

        def prepare_tmp(id=False, code=False, indent_list=[], parent=[]):
            return {
                'id': id,
                'code': code,
                'initial_debit': 0,
                'initial_credit': 0,
                'initial_balance': 0,
                'debit': 0,
                'credit': 0,
                'balance': 0,
                'ending_debit': 0,
                'ending_credit': 0,
                'ending_balance': 0,
                'dummy': True,
                'indent_list': indent_list,
                'len': len(indent_list) or 1,
                'parent': ' a'.join(['0'] + parent)
            }

        if move_lines:
            hirarchy_list = []
            parent_1 = []
            parent_2 = []
            parent_3 = []
            for line in move_lines:

                q = move_lines[line]
                tmp = q.copy()
                tmp.update(prepare_tmp(id=str(tmp['id']) + 'z1',
                                  code=str(tmp['code'])[0],
                                  indent_list=[1],
                                  parent=[]))
                if tmp['code'] not in [k['code'] for k in hirarchy_list]:
                    hirarchy_list.append(tmp)
                    parent_1 = [tmp['id']]

                tmp = q.copy()
                tmp.update(prepare_tmp(id=str(tmp['id']) + 'z2',
                                  code=str(tmp['code'])[:2],
                                  indent_list=[1,2],
                                  parent=parent_1))
                if tmp['code'] not in [k['code'] for k in hirarchy_list]:
                    hirarchy_list.append(tmp)
                    parent_2 = [tmp['id']]

                tmp = q.copy()
                tmp.update(prepare_tmp(id=str(tmp['id']) + 'z3',
                                  code=str(tmp['code'])[:3],
                                  indent_list=[1, 2, 3],
                                  parent=parent_1 + parent_2))

                if tmp['code'] not in [k['code'] for k in hirarchy_list]:
                    hirarchy_list.append(tmp)
                    parent_3 = [tmp['id']]
                final_parent = ['0'] + parent_1 + parent_2 + parent_3
                tmp = q.copy()
                tmp.update({'code': str(tmp['code']), 'parent': ' a'.join(final_parent), 'dummy': False, 'indent_list': [1, 2, 3, 4],})
                hirarchy_list.append(tmp)

            for line in move_lines:
                q = move_lines[line]
                for l in hirarchy_list:
                    if str(q['code'])[0] == l['code'] or \
                            str(q['code'])[:2] == l['code'] or \
                            str(q['code'])[:3] == l['code']:
                        l['initial_debit'] += q['initial_debit']
                        l['initial_credit'] += q['initial_credit']
                        l['initial_balance'] += q['initial_balance']
                        l['debit'] += q['debit']
                        l['credit'] += q['credit']
                        l['balance'] += q['balance']
                        l['ending_debit'] += q['ending_debit']
                        l['ending_credit'] += q['ending_credit']
                        l['ending_balance'] += q['ending_balance']

            return sorted(hirarchy_list, key=itemgetter('code'))
        return []

    def process_data(self, data):
        if data:
            cr = self.env.cr
            WHERE = '(1=1)'

            if data.get('journal_ids',[]):
                WHERE += ' AND j.id IN %s' % str(tuple(data.get('journal_ids'))+tuple([0]))

            if data.get('analytic_ids', []):
                WHERE += ' AND anl.id IN %s' % str(tuple(data.get('analytic_ids')) + tuple([0]))

            if data.get('company_id', False):
                WHERE += ' AND l.company_id = %s' % data.get('company_id')

            if data.get('target_moves') == 'posted_only':
                WHERE += " AND m.state = 'posted'"

            account_ids = self.env['account.account'].search([])
            company_currency_id = self.env.company.currency_id

            move_lines = {x.code: {'name':x.name,'code':x.code,'id':x.id,
                                 'initial_debit':0.0, 'initial_credit':0.0,'initial_balance':0.0,
                                 'debit':0.0, 'credit':0.0, 'balance':0.0,
                                 'ending_credit':0.0, 'ending_debit':0.0, 'ending_balance':0.0,
                                 'company_currency_id': company_currency_id.id} for x in account_ids} # base for accounts to display
            retained = {}
            retained_earnings = 0.0
            retained_credit = 0.0
            retained_debit = 0.0
            total_deb = 0.0
            total_cre = 0.0
            total_bln = 0.0
            total_init_deb = 0.0
            total_init_cre = 0.0
            total_init_bal = 0.0
            total_end_deb = 0.0
            total_end_cre = 0.0
            total_end_bal = 0.0
            for account in account_ids:
                currency = account.company_id.currency_id or self.env.company.currency_id
                WHERE_INIT = WHERE + " AND l.date < '%s'" % data.get('date_from')
                WHERE_INIT += " AND l.account_id = %s" % account.id
                init_blns = 0.0
                deb = 0.0
                cre = 0.0
                end_blns = 0.0
                end_cr = 0.0
                end_dr = 0.0
                sql = ('''
                    SELECT 
                        COALESCE(SUM(l.debit),0) AS initial_debit,
                        COALESCE(SUM(l.credit),0) AS initial_credit,
                        COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit),0) AS initial_balance
                    FROM account_move_line l
                    JOIN account_move m ON (l.move_id=m.id)
                    JOIN account_account a ON (l.account_id=a.id)
                    LEFT JOIN account_analytic_account anl ON (l.analytic_account_id=anl.id)
                    LEFT JOIN res_currency c ON (l.currency_id=c.id)
                    LEFT JOIN res_partner p ON (l.partner_id=p.id)
                    JOIN account_journal j ON (l.journal_id=j.id)
                    WHERE %s
                ''')%WHERE_INIT
                cr.execute(sql)
                init_blns = cr.dictfetchone()

                move_lines[account.code]['initial_balance'] = init_blns['initial_balance']
                move_lines[account.code]['initial_debit'] = init_blns['initial_debit']
                move_lines[account.code]['initial_credit'] = init_blns['initial_credit']

                if account.user_type_id.include_initial_balance and self.strict_range:
                    move_lines[account.code]['initial_balance'] = 0.0
                    move_lines[account.code]['initial_debit'] = 0.0
                    move_lines[account.code]['initial_credit'] = 0.0
                    if self.strict_range and account.user_type_id != self.env.ref('account.data_unaffected_earnings'):
                        retained_earnings += init_blns['initial_balance']
                        retained_credit += init_blns['initial_credit']
                        retained_debit += init_blns['initial_debit']
                total_init_deb += init_blns['initial_debit']
                total_init_cre += init_blns['initial_credit']
                total_init_bal += init_blns['initial_balance']
                WHERE_CURRENT = WHERE + " AND l.date >= '%s'" % data.get('date_from') + " AND l.date <= '%s'" % data.get('date_to')
                WHERE_CURRENT += " AND a.id = %s" % account.id
                sql = ('''
                    SELECT
                        COALESCE(SUM(l.debit),0) AS debit,
                        COALESCE(SUM(l.credit),0) AS credit,
                        COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit),0) AS balance
                    FROM account_move_line l
                    JOIN account_move m ON (l.move_id=m.id)
                    JOIN account_account a ON (l.account_id=a.id)
                    LEFT JOIN account_analytic_account anl ON (l.analytic_account_id=anl.id)
                    LEFT JOIN res_currency c ON (l.currency_id=c.id)
                    LEFT JOIN res_partner p ON (l.partner_id=p.id)
                    JOIN account_journal j ON (l.journal_id=j.id)
                    WHERE %s
                ''') % WHERE_CURRENT
                cr.execute(sql)
                op = cr.dictfetchone()
                deb = op['debit']
                cre = op['credit']
                bln = op['balance']
                move_lines[account.code]['debit'] = deb
                move_lines[account.code]['credit'] = cre
                move_lines[account.code]['balance'] = bln

                end_blns = init_blns['initial_balance'] + bln
                end_cr = init_blns['initial_credit'] + cre
                end_dr = init_blns['initial_debit'] + deb

                move_lines[account.code]['ending_balance'] = end_blns
                move_lines[account.code]['ending_credit'] = end_cr
                move_lines[account.code]['ending_debit'] = end_dr

                if data.get('display_accounts') == 'balance_not_zero':
                    if end_blns: # debit or credit exist
                        total_deb += deb
                        total_cre += cre
                        total_bln += bln
                    elif bln:
                        continue
                    else:
                        move_lines.pop(account.code)
                else:
                    total_deb += deb
                    total_cre += cre
                    total_bln += bln

            if self.strict_range:
                retained = {'RETAINED': {'name':'Unallocated Earnings','code':'','id':'RET',
                                        'initial_credit':company_currency_id.round(retained_credit),
                                         'initial_debit':company_currency_id.round(retained_debit),
                                         'initial_balance':company_currency_id.round(retained_earnings),
                                         'credit':0.0, 'debit':0.0, 'balance': 0.0,
                                         'ending_credit':company_currency_id.round(retained_credit),
                                         'ending_debit':company_currency_id.round(retained_debit),
                                         'ending_balance':company_currency_id.round(retained_earnings),
                                         'company_currency_id': company_currency_id.id}}
            subtotal = {'SUBTOTAL': {
                'name': 'Total',
                'code': '',
                'id': 'SUB',
                'initial_credit': company_currency_id.round(total_init_cre),
                'initial_debit':company_currency_id.round(total_init_deb),
                'initial_balance':company_currency_id.round(total_init_bal),
                'credit': company_currency_id.round(total_cre),
                'debit':company_currency_id.round(total_deb),
                'balance':company_currency_id.round(total_bln),
                'ending_credit': company_currency_id.round(total_init_cre + total_cre),
                'ending_debit': company_currency_id.round(total_init_deb + total_deb),
                'ending_balance': company_currency_id.round(total_init_bal + total_bln),
                'company_currency_id': company_currency_id.id}}

            if self.show_hierarchy:

                move_lines = self.prepare_hierarchy(move_lines)
            return [move_lines, retained, subtotal]

    def get_filters(self, default_filters={}):

        self.onchange_date_range()

        company_domain = [('company_id', '=', self.env.company.id)]

        journals = self.journal_ids if self.journal_ids else self.env['account.journal'].search(company_domain)
        analytics = self.analytic_ids if self.analytic_ids else self.env['account.analytic.account'].search(company_domain)

        filter_dict = {
            'journal_ids': self.journal_ids.ids,
            'analytic_ids': self.analytic_ids.ids,
            'company_id': self.company_id and self.company_id.id or False,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'display_accounts': self.display_accounts,
            'show_hierarchy': self.show_hierarchy,
            'strict_range': self.strict_range,
            'target_moves': self.target_moves,

            'journals_list': [(j.id, j.name) for j in journals],
            'analytics_list': [(anl.id, anl.name) for anl in analytics],
            'company_name': self.company_id and self.company_id.name,
        }
        filter_dict.update(default_filters)
        return filter_dict

    def get_report_datas(self, default_filters={}):
        '''
        Main method for pdf, xlsx and js calls
        :param default_filters: Use this while calling from other methods. Just a dict
        :return: All the datas for GL
        '''
        if self.validate_data():
            data = self.get_filters(default_filters)
            filters = self.process_filters(data)
            account_lines, retained, subtotal = self.process_data(data)
            return filters, account_lines, retained, subtotal

    def action_pdf(self):
        filters, account_lines, retained, subtotal = self.get_report_datas()
        return self.env.ref(
            'account_dynamic_reports'
            '.action_print_trial_balance').with_context(landscape=True).report_action(
            self, data={'Ledger_data':account_lines,
                        'Retained':retained,
                        'Subtotal':subtotal,
                        'Filters':filters
                        })

    def action_xlsx(self):
        raise UserError(_('Please install a free module "dynamic_xlsx".'
                          'You can get it by contacting "pycustech@gmail.com". It is free'))

    def action_view(self):
        res = {
            'type': 'ir.actions.client',
            'name': 'TB View',
            'tag': 'dynamic.tb',
            'context': {'wizard_id': self.id}
        }
        return res
