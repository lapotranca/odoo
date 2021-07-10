from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta, date
import calendar
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

FETCH_RANGE = 2500


class InsPartnerAgeing(models.TransientModel):
    _name = "ins.partner.ageing"

    @api.onchange('partner_type')
    def onchange_partner_type(self):
        self.partner_ids = [(5,)]
        if self.partner_type:
            if self.partner_type == 'customer':
                partner_company_domain = [('parent_id', '=', False),
                                          ('customer_rank', '>', 0),
                                          '|',
                                          ('company_id', '=', self.env.company.id),
                                          ('company_id', '=', False)]

                self.partner_ids |= self.env['res.partner'].search(partner_company_domain)
            if self.partner_type == 'supplier':
                partner_company_domain = [('parent_id', '=', False),
                                          ('supplier_rank', '>', 0),
                                          '|',
                                          ('company_id', '=', self.env.company.id),
                                          ('company_id', '=', False)]

                self.partner_ids |= self.env['res.partner'].search(partner_company_domain)

    def name_get(self):
        res = []
        for record in self:
            res.append((record.id, 'Ageing'))
        return res

    as_on_date = fields.Date(string='As on date', required=True, default=fields.Date.today())
    bucket_1 = fields.Integer(string='Bucket 1', required=True, default=lambda self:self.env.company.bucket_1)
    bucket_2 = fields.Integer(string='Bucket 2', required=True, default=lambda self:self.env.company.bucket_2)
    bucket_3 = fields.Integer(string='Bucket 3', required=True, default=lambda self:self.env.company.bucket_3)
    bucket_4 = fields.Integer(string='Bucket 4', required=True, default=lambda self:self.env.company.bucket_4)
    bucket_5 = fields.Integer(string='Bucket 5', required=True, default=lambda self:self.env.company.bucket_5)
    include_details = fields.Boolean(string='Include Details', default=True)
    type = fields.Selection([('receivable','Receivable Accounts Only'),
                              ('payable','Payable Accounts Only')], string='Type')
    partner_type = fields.Selection([('customer', 'Customer Only'),
                             ('supplier', 'Supplier Only')], string='Partner Type')

    partner_ids = fields.Many2many(
        'res.partner', required=False
    )
    partner_category_ids = fields.Many2many(
        'res.partner.category', string='Partner Tag',
    )
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company
    )

    def write(self, vals):
        if not vals.get('partner_ids'):
            vals.update({
                'partner_ids': [(5, 0, 0)]
            })

        if vals.get('partner_category_ids'):
            vals.update({'partner_category_ids': vals.get('partner_category_ids')})
        if vals.get('partner_category_ids') == []:
            vals.update({'partner_category_ids': [(5,)]})

        ret = super(InsPartnerAgeing, self).write(vals)
        return ret

    def validate_data(self):
        if not(self.bucket_1 < self.bucket_2 and self.bucket_2 < self.bucket_3 and self.bucket_3 < self.bucket_4 and \
            self.bucket_4 < self.bucket_5):
            raise ValidationError(_('"Bucket order must be ascending"'))
        return True

    def get_filters(self, default_filters={}):

        partner_company_domain = [('parent_id','=', False),
                                  '|',
                                  ('customer_rank', '>', 0),
                                  ('supplier_rank', '>', 0),
                                  '|',
                                  ('company_id', '=', self.env.company.id),
                                  ('company_id', '=', False)]

        partners = self.partner_ids if self.partner_ids else self.env['res.partner'].search(partner_company_domain)
        categories = self.partner_category_ids if self.partner_category_ids else self.env['res.partner.category'].search([])

        filter_dict = {
            'partner_ids': self.partner_ids.ids,
            'partner_category_ids': self.partner_category_ids.ids,
            'company_id': self.company_id and self.company_id.id or False,
            'as_on_date': self.as_on_date,
            'type': self.type,
            'partner_type': self.partner_type,
            'bucket_1': self.bucket_1,
            'bucket_2': self.bucket_2,
            'bucket_3': self.bucket_3,
            'bucket_4': self.bucket_4,
            'bucket_5': self.bucket_5,
            'include_details': self.include_details,

            'partners_list': [(p.id, p.name) for p in partners],
            'category_list': [(c.id, c.name) for c in categories],
            'company_name': self.company_id and self.company_id.name,
        }
        filter_dict.update(default_filters)
        return filter_dict

    def process_filters(self):
        ''' To show on report headers'''

        data = self.get_filters(default_filters={})

        filters = {}

        filters['bucket_1'] = data.get('bucket_1')
        filters['bucket_2'] = data.get('bucket_2')
        filters['bucket_3'] = data.get('bucket_3')
        filters['bucket_4'] = data.get('bucket_4')
        filters['bucket_5'] = data.get('bucket_5')

        if data.get('partner_ids', []):
            filters['partners'] = self.env['res.partner'].browse(data.get('partner_ids', [])).mapped('name')
        else:
            filters['partners'] = ['All']

        if data.get('as_on_date', False):
            filters['as_on_date'] = data.get('as_on_date')

        if data.get('company_id'):
            filters['company_id'] = data.get('company_id')
        else:
            filters['company_id'] = ''

        if data.get('type'):
            filters['type'] = data.get('type')

        if data.get('partner_type'):
            filters['partner_type'] = data.get('partner_type')

        if data.get('partner_category_ids', []):
            filters['categories'] = self.env['res.partner.category'].browse(data.get('partner_category_ids', [])).mapped('name')
        else:
            filters['categories'] = ['All']

        if data.get('include_details'):
            filters['include_details'] = True
        else:
            filters['include_details'] = False

        filters['partners_list'] = data.get('partners_list')
        filters['category_list'] = data.get('category_list')
        filters['company_name'] = data.get('company_name')

        return filters

    def prepare_bucket_list(self):
        periods = {}
        date_from = self.as_on_date
        date_from = fields.Date.from_string(date_from)

        lang = self.env.user.lang
        language_id = self.env['res.lang'].search([('code', '=', lang)])[0]

        bucket_list = [self.bucket_1,self.bucket_2,self.bucket_3,self.bucket_4,self.bucket_5]

        start = False
        stop = date_from
        name = 'Not Due'
        periods[0] = {
            'bucket': 'As on',
            'name': name,
            'start': '',
            'stop': stop.strftime('%Y-%m-%d'),
        }

        stop = date_from
        final_date = False
        for i in range(5):
            ref_date = date_from - relativedelta(days=1)
            start = stop - relativedelta(days=1)
            stop = ref_date - relativedelta(days=bucket_list[i])
            name = '0 - ' + str(bucket_list[0]) if i==0 else  str(str(bucket_list[i-1] + 1)) + ' - ' + str(bucket_list[i])
            final_date = stop
            periods[i+1] = {
                'bucket': bucket_list[i],
                'name': name,
                'start': start.strftime('%Y-%m-%d'),
                'stop': stop.strftime('%Y-%m-%d'),
            }

        start = final_date -relativedelta(days=1)
        stop = ''
        name = str(self.bucket_5) + ' +'

        periods[6] = {
            'bucket': 'Above',
            'name': name,
            'start': start.strftime('%Y-%m-%d'),
            'stop': '',
        }
        return periods

    def process_detailed_data(self, offset=0, partner=0, fetch_range=FETCH_RANGE):
        '''

        It is used for showing detailed move lines as sub lines. It is defered loading compatable
        :param offset: It is nothing but page numbers. Multiply with fetch_range to get final range
        :param partner: Integer - Partner
        :param fetch_range: Global Variable. Can be altered from calling model
        :return: count(int-Total rows without offset), offset(integer), move_lines(list of dict)
        '''
        as_on_date = self.as_on_date
        period_dict = self.prepare_bucket_list()
        period_list = [period_dict[a]['name'] for a in period_dict]
        company_id = self.env.company

        type = ('receivable','payable')
        if self.type:
            type = tuple([self.type,'none'])

        offset = offset * fetch_range
        count = 0

        if partner:


            sql = """
                    SELECT COUNT(*)
                    FROM
                        account_move_line AS l
                    LEFT JOIN
                        account_move AS m ON m.id = l.move_id
                    LEFT JOIN
                        account_account AS a ON a.id = l.account_id
                    LEFT JOIN
                        account_account_type AS ty ON a.user_type_id = ty.id
                    LEFT JOIN
                        account_journal AS j ON l.journal_id = j.id
                    WHERE
                        l.balance <> 0
                        AND m.state = 'posted'
                        AND ty.type IN %s
                        AND l.partner_id = %s
                        AND l.date <= '%s'
                        AND l.company_id = %s
                """ % (type, partner, as_on_date, company_id.id)
            self.env.cr.execute(sql)
            count = self.env.cr.fetchone()[0]

            SELECT = """SELECT m.name AS move_name,
                                m.id AS move_id,
                                l.date AS date,
                                l.date_maturity AS date_maturity, 
                                j.name AS journal_name,
                                cc.id AS company_currency_id,
                                a.name AS account_name, """

            for period in period_dict:
                if period_dict[period].get('start') and period_dict[period].get('stop'):
                    SELECT += """ CASE 
                                    WHEN 
                                        COALESCE(l.date_maturity,l.date) >= '%s' AND 
                                        COALESCE(l.date_maturity,l.date) <= '%s'
                                    THEN
                                        sum(l.balance) +
                                        sum(
                                            COALESCE(
                                                (SELECT 
                                                    SUM(amount)
                                                FROM account_partial_reconcile
                                                WHERE credit_move_id = l.id AND max_date <= '%s'), 0
                                                )
                                            ) -
                                        sum(
                                            COALESCE(
                                                (SELECT 
                                                    SUM(amount) 
                                                FROM account_partial_reconcile 
                                                WHERE debit_move_id = l.id AND max_date <= '%s'), 0
                                                )
                                            )
                                    ELSE
                                        0
                                    END AS %s,"""%(period_dict[period].get('stop'),
                                                   period_dict[period].get('start'),
                                                   as_on_date,
                                                   as_on_date,
                                                   'range_'+str(period),
                                                   )
                elif not period_dict[period].get('start'):
                    SELECT += """ CASE 
                                    WHEN 
                                        COALESCE(l.date_maturity,l.date) >= '%s' 
                                    THEN
                                        sum(
                                            l.balance
                                            ) +
                                        sum(
                                            COALESCE(
                                                (SELECT 
                                                    SUM(amount)
                                                FROM account_partial_reconcile
                                                WHERE credit_move_id = l.id AND max_date <= '%s'), 0
                                                )
                                            ) -
                                        sum(
                                            COALESCE(
                                                (SELECT 
                                                    SUM(amount) 
                                                FROM account_partial_reconcile 
                                                WHERE debit_move_id = l.id AND max_date <= '%s'), 0
                                                )
                                            )
                                    ELSE
                                        0
                                    END AS %s,"""%(period_dict[period].get('stop'), as_on_date, as_on_date, 'range_'+str(period))
                else:
                    SELECT += """ CASE
                                    WHEN
                                        COALESCE(l.date_maturity,l.date) <= '%s' 
                                    THEN
                                        sum(
                                            l.balance
                                            ) +
                                        sum(
                                            COALESCE(
                                                (SELECT 
                                                    SUM(amount)
                                                FROM account_partial_reconcile
                                                WHERE credit_move_id = l.id AND max_date <= '%s'), 0
                                                )
                                            ) -
                                        sum(
                                            COALESCE(
                                                (SELECT 
                                                    SUM(amount) 
                                                FROM account_partial_reconcile 
                                                WHERE debit_move_id = l.id AND max_date <= '%s'), 0
                                                )
                                            )
                                    ELSE
                                        0
                                    END AS %s """%(period_dict[period].get('start'), as_on_date, as_on_date ,'range_'+str(period))

            sql = """
                    FROM
                        account_move_line AS l
                    LEFT JOIN
                        account_move AS m ON m.id = l.move_id
                    LEFT JOIN
                        account_account AS a ON a.id = l.account_id
                    LEFT JOIN
                        account_account_type AS ty ON a.user_type_id = ty.id
                    LEFT JOIN
                        account_journal AS j ON l.journal_id = j.id
                    LEFT JOIN 
                        res_currency AS cc ON l.company_currency_id = cc.id
                    WHERE
                        l.balance <> 0
                        AND m.state = 'posted'
                        AND ty.type IN %s
                        AND l.partner_id = %s
                        AND l.date <= '%s'
                        AND l.company_id = %s
                    GROUP BY
                        l.date, l.date_maturity, m.id, m.name, j.name, a.name, cc.id
                    OFFSET %s ROWS
                    FETCH FIRST %s ROWS ONLY
                """%(type, partner, as_on_date, company_id.id, offset, fetch_range)
            self.env.cr.execute(SELECT + sql)
            final_list = self.env.cr.dictfetchall() or 0.0
            move_lines = []
            for m in final_list:
                if (m['range_0'] or m['range_1'] or m['range_2'] or m['range_3'] or m['range_4'] or m['range_5']):
                    move_lines.append(m)

            if move_lines:
                return count, offset, move_lines, period_list
            else:
                return 0, 0, [], []

    def process_data(self):
        ''' Query Start Here
        ['partner_id':
            {'0-30':0.0,
            '30-60':0.0,
            '60-90':0.0,
            '90-120':0.0,
            '>120':0.0,
            'as_on_date_amount': 0.0,
            'total': 0.0}]
        1. Prepare bucket range list from bucket values
        2. Fetch partner_ids and loop through bucket range for values
        '''
        period_dict = self.prepare_bucket_list()

        domain = ['|',('company_id','=',self.env.company.id),('company_id','=',False)]
        if self.partner_type == 'customer':
            domain.append(('customer_rank','>',0))
        if self.partner_type == 'supplier':
            domain.append(('supplier_rank','>',0))

        if self.partner_category_ids:
            domain.append(('category_id','in',self.partner_category_ids.ids))

        partner_ids = self.partner_ids or self.env['res.partner'].search(domain)
        as_on_date = self.as_on_date
        company_currency_id = self.env.company.currency_id.id
        company_id = self.env.company

        type = ('receivable', 'payable')
        if self.type:
            type = tuple([self.type,'none'])

        partner_dict = {}
        for partner in partner_ids:
            partner_dict.update({partner.id:{}})

        partner_dict.update({'Total': {}})
        for period in period_dict:
            partner_dict['Total'].update({period_dict[period]['name']: 0.0})
        partner_dict['Total'].update({'total': 0.0, 'partner_name': 'ZZZZZZZZZ'})
        partner_dict['Total'].update({'company_currency_id': company_currency_id})

        for partner in partner_ids:
            partner_dict[partner.id].update({'partner_name':partner.name})
            total_balance = 0.0

            sql = """
                SELECT
                    COUNT(*) AS count
                FROM
                    account_move_line AS l
                LEFT JOIN
                    account_move AS m ON m.id = l.move_id
                LEFT JOIN
                    account_account AS a ON a.id = l.account_id
                LEFT JOIN
                    account_account_type AS ty ON a.user_type_id = ty.id
                WHERE
                    l.balance <> 0
                    AND m.state = 'posted'
                    AND ty.type IN %s
                    AND l.partner_id = %s
                    AND l.date <= '%s'
                    AND l.company_id = %s
            """%(type, partner.id, as_on_date, company_id.id)
            self.env.cr.execute(sql)
            fetch_dict = self.env.cr.dictfetchone() or 0.0
            count = fetch_dict.get('count') or 0.0

            if count:
                for period in period_dict:

                    where = " AND l.date <= '%s' AND l.partner_id = %s AND COALESCE(l.date_maturity,l.date) "%(as_on_date, partner.id)
                    if period_dict[period].get('start') and period_dict[period].get('stop'):
                        where += " BETWEEN '%s' AND '%s'" % (period_dict[period].get('stop'), period_dict[period].get('start'))
                    elif not period_dict[period].get('start'): # ie just
                        where += " >= '%s'" % (period_dict[period].get('stop'))
                    else:
                        where += " <= '%s'" % (period_dict[period].get('start'))

                    sql = """
                        SELECT
                            sum(
                                l.balance
                                ) AS balance,
                            sum(
                                COALESCE(
                                    (SELECT 
                                        SUM(amount)
                                    FROM account_partial_reconcile
                                    WHERE credit_move_id = l.id AND max_date <= '%s'), 0
                                    )
                                ) AS sum_debit,
                            sum(
                                COALESCE(
                                    (SELECT 
                                        SUM(amount) 
                                    FROM account_partial_reconcile 
                                    WHERE debit_move_id = l.id AND max_date <= '%s'), 0
                                    )
                                ) AS sum_credit
                        FROM
                            account_move_line AS l
                        LEFT JOIN
                            account_move AS m ON m.id = l.move_id
                        LEFT JOIN
                            account_account AS a ON a.id = l.account_id
                        LEFT JOIN
                            account_account_type AS ty ON a.user_type_id = ty.id
                        WHERE
                            l.balance <> 0
                            AND m.state = 'posted'
                            AND ty.type IN %s
                            AND l.company_id = %s
                    """%(as_on_date, as_on_date, type, company_id.id)
                    amount = 0.0
                    self.env.cr.execute(sql + where)
                    fetch_dict = self.env.cr.dictfetchall() or 0.0

                    if not fetch_dict[0].get('balance'):
                        amount = 0.0
                    else:
                        amount = fetch_dict[0]['balance'] + fetch_dict[0]['sum_debit'] - fetch_dict[0]['sum_credit']
                        total_balance += amount

                    partner_dict[partner.id].update({period_dict[period]['name']:amount})
                    partner_dict['Total'][period_dict[period]['name']] += amount
                partner_dict[partner.id].update({'count': count})
                partner_dict[partner.id].update({'pages': self.get_page_list(count)})
                partner_dict[partner.id].update({'single_page': True if count <= FETCH_RANGE else False})
                partner_dict[partner.id].update({'total': total_balance})
                partner_dict['Total']['total'] += total_balance
                partner_dict[partner.id].update({'company_currency_id': company_currency_id})
                partner_dict['Total'].update({'company_currency_id': company_currency_id})
            else:
                partner_dict.pop(partner.id, None)
        return period_dict, partner_dict

    def get_page_list(self, total_count):
        '''
        Helper function to get list of pages from total_count
        :param total_count: integer
        :return: list(pages) eg. [1,2,3,4,5,6,7 ....]
        '''
        page_count = int(total_count / FETCH_RANGE)
        if total_count % FETCH_RANGE:
            page_count += 1
        return [i+1 for i in range(0, int(page_count))] or []

    def get_report_datas(self, default_filters={}):
        '''
        Main method for pdf, xlsx and js calls
        :param default_filters: Use this while calling from other methods. Just a dict
        :return: All the datas for GL
        '''
        if self.validate_data():
            filters = self.process_filters()
            period_dict, ageing_lines = self.process_data()
            period_list = [period_dict[a]['name'] for a in period_dict]
            return filters, ageing_lines, period_dict, period_list

    def action_pdf(self):
        filters, ageing_lines, period_dict, period_list = self.get_report_datas()
        return self.env.ref(
            'account_dynamic_reports'
            '.action_print_partner_ageing').with_context(landscape=True).report_action(
                self, data={'Ageing_data': ageing_lines,
                        'Filters': filters,
                        'Period_Dict': period_dict,
                        'Period_List': period_list
                        })

    def action_xlsx(self):
        raise UserError(_('Please install a free module "dynamic_xlsx".'
                          'You can get it by contacting "pycustech@gmail.com". It is free'))

    def action_view(self):
        res = {
            'type': 'ir.actions.client',
            'name': 'Ageing View',
            'tag': 'dynamic.pa',
            'context': {'wizard_id': self.id}
        }
        return res