# -*- coding: utf-8 -*-
from lxml import etree
from lxml.objectify import fromstring
from odoo import models, api, _, fields, tools
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
from odoo.tools.xml_utils import _check_with_xsd
import logging
_logger = logging.getLogger(__name__)


class ReportTrialBalanceReport(models.AbstractModel):
    _inherit = "l10n_mx.trial.report"

    v_cost_center = fields.Boolean('Allow Cost Center Filters')
    v_department = fields.Boolean('Allow Department Filters')


    def _with_correct_filters(self):
        res = super(ReportTrialBalanceReport, self)._with_correct_filters()
        if res.v_cost_center:
            res.filter_v_cost_centers = []
            res.filter_v_cost_center = True
        if res.v_department:
            res.filter_v_departments = []
            res.filter_v_department = True
        return res

    @api.model
    def _init_filter_v_cost_center(self, options, previous_options=None):
        if not self.filter_v_cost_center:
            return

        options['v_cost_center'] = self.filter_v_cost_center
        CostCenter = self.env['tf.cost.center'].sudo()
        options['v_cost_centers'] = previous_options and previous_options.get('v_cost_centers') or []
        record_ids = [int(acc_grp) for acc_grp in options['v_cost_centers']]
        selected_v_cost_centers = record_ids and CostCenter.browse(record_ids) or CostCenter
        options['selected_v_cost_center_names'] = selected_v_cost_centers.mapped('name')

    @api.model
    def _get_options_v_cost_center_domain(self, options):
        domain = []
        if options.get('v_cost_centers'):
            v_cost_center_ids = [int(acc_grp) for acc_grp in options['v_cost_centers']]
            domain.append(('cost_center_id', 'in', v_cost_center_ids))
        return domain

    @api.model
    def _init_filter_v_department(self, options, previous_options=None):
        if not self.filter_v_department:
            return
        options['v_department'] = self.filter_v_department
        CostCenter = self.env['tf.department'].sudo()
        options['v_departments'] = previous_options and previous_options.get('v_departments') or []
        record_ids = [int(acc_grp) for acc_grp in options['v_departments']]
        selected_v_departments = record_ids and CostCenter.browse(record_ids) or CostCenter
        options['selected_v_department_names'] = selected_v_departments.mapped('name')

    @api.model
    def _get_options_v_department_domain(self, options):
        domain = []
        if options.get('v_departments'):
            v_department_ids = [int(rec) for rec in options['v_departments']]
            domain.append(('department_id', 'in', v_department_ids))
        return domain

    @api.model
    def _get_lines(self, options, line_id=None):
        # Create new options with 'unfold_all' to compute the initial balances.
        # Then, the '_do_query' will compute all sums/unaffected earnings/initial balances for all comparisons.
        new_options = options.copy()
        new_options['unfold_all'] = True
        options_list = self._get_options_periods_list(new_options)
        accounts_results, taxes_results = self.env['account.general.ledger']._do_query(options_list, fetch_lines=False)

        grouped_accounts = {}
        initial_balances = {}
        comparison_table = [options.get('date')]
        comparison_table += options.get('comparison') and options['comparison'].get('periods') or []
        for account, periods_results in accounts_results:
            grouped_accounts.setdefault(account, [])
            for i, res in enumerate(periods_results):
                if i == 0:
                    initial_balances[account] = res.get('initial_balance', {}).get('balance', 0.0)

                domain_cd = []
                if options.get('v_cost_centers'):
                    domain_cd += self._get_options_v_cost_center_domain(options)
                if options.get('v_departments'):
                    domain_cd += self._get_options_v_department_domain(options)

                if domain_cd:
                    domain_cd.append(('account_id', '=', account.id))
                    domain_cd.append(('date', '>', comparison_table[0]['date_from']))
                    domain_cd.append(('date', '<', comparison_table[0]['date_to']))
                    tf_acc_mv_line_ids = [x for x in self.env['account.move.line'].search(domain_cd)]
                    grouped_accounts[account].append({
                        'balance': res.get('sum', {}).get('balance', 0.0),
                        'debit': sum(x.debit for x in tf_acc_mv_line_ids),
                        'credit': sum(x.credit for x in tf_acc_mv_line_ids),
                    })
                else:
                    grouped_accounts[account].append({
                        'balance': res.get('sum', {}).get('balance', 0.0),
                        'debit': res.get('sum', {}).get('debit', 0.0),
                        'credit': res.get('sum', {}).get('credit', 0.0),
                    })

        return self._post_process(grouped_accounts, initial_balances, options, comparison_table)

    @api.model
    def _get_lines_third_level(self, line, grouped_accounts, initial_balances,
                               options, comparison_table):
        """Return list of accounts found in the third level"""
        lines = []
        domain = safe_eval(line.domain or '[]')
        domain += [
            ('deprecated', '=', False),
            ('company_id', 'in', self.env.context['company_ids']),
        ]

        domain_cd = []
        if options.get('v_cost_centers'):
            domain_cd += self._get_options_v_cost_center_domain(options)
        if options.get('v_departments'):
            domain_cd += self._get_options_v_department_domain(options)

        if domain_cd:
            tf_line_ids = self.env['account.move.line'].search(domain_cd)
            if tf_line_ids:
                domain.append(('id', 'in', [tf_x.account_id.id for tf_x in tf_line_ids]))

        basis_account_ids = self.env['account.tax'].search_read(
            [('cash_basis_base_account_id', '!=', False)], ['cash_basis_base_account_id'])
        basis_account_ids = [account['cash_basis_base_account_id'][0] for account in basis_account_ids]
        domain.append((('id', 'not in', basis_account_ids)))
        account_ids = self.env['account.account'].search(domain, order='code')
        tags = account_ids.mapped('tag_ids').filtered(
            lambda r: r.color == 4).sorted(key=lambda a: a.name)
        for tag in tags:
            accounts = account_ids.search([
                ('tag_ids', 'in', [tag.id]),
                ('id', 'in', account_ids.ids),
            ])
            name = tag.name
            name = name[:63] + "..." if len(name) > 65 else name
            cols = [{'name': ''}]
            childs = self._get_lines_fourth_level(accounts, grouped_accounts, initial_balances, options,
                                                  comparison_table)
            if not childs:
                continue
            if not options.get('coa_only'):
                n_cols = len(comparison_table) * 2 + 2
                child_cols = [c['columns'] for c in childs]
                cols = []
                for col in range(n_cols):
                    cols += [sum(a[col] for a in child_cols)]
            lines.append({
                'id': 'level_two_%s' % tag.id,
                'parent_id': 'level_one_%s' % line.id,
                'name': name,
                'columns': cols,
                'level': 3,
                'unfoldable': True,
                'unfolded': True,
                'tag_id': tag.id,
            })
            lines.extend(childs)
        return lines


    def _get_lines_fourth_level(self, accounts, grouped_accounts, initial_balances, options, comparison_table):
        lines = []
        company_id = self.env.context.get('company_id') or self.env.company
        is_zero = company_id.currency_id.is_zero
        for account in accounts:
            # skip accounts with all periods = 0 (debit and credit) and no initial balance
            if not options.get('coa_only'):
                non_zero = False
                for period in range(len(comparison_table)):
                    if account in grouped_accounts and (
                        not is_zero(initial_balances.get(account, 0)) or
                        not is_zero(grouped_accounts[account][period]['debit']) or
                        not is_zero(grouped_accounts[account][period]['credit'])
                    ):
                        non_zero = True
                        break
                if not non_zero:
                    continue
            name = account.code + " " + account.name
            name = name[:63] + "..." if len(name) > 65 else name
            tag = account.tag_ids.filtered(lambda r: r.color == 4)
            if len(tag) > 1:
                raise UserError(_(
                    'The account %s is incorrectly configured. Only one tag is allowed.'
                ) % account.name)
            nature = dict(tag.fields_get()['nature']['selection']).get(tag.nature, '')
            cols = [{'name': nature}]
            if not options.get('coa_only'):
                self = self.with_context(tf_options=options)
                cols = self._get_cols(initial_balances, account, comparison_table, grouped_accounts, options)
            lines.append({
                'id': account.id,
                'parent_id': 'level_two_%s' % tag.id,
                'name': name,
                'level': 4,
                'columns': cols,
                'caret_options': 'account.account',
            })
        return lines

    def _get_cols(self, initial_balances, account, comparison_table, grouped_accounts, options=None):
        cols = [initial_balances.get(account, 0.0)]
        total_periods = 0
        for period in range(len(comparison_table)):
            amount = grouped_accounts[account][period]['balance']
            total_periods += amount
            cols += [grouped_accounts[account][period]['debit'],
                     grouped_accounts[account][period]['credit']]
        cols += [initial_balances.get(account, 0.0) + total_periods]

        cols[0] = 0
        # compare_sql_string = "account_id=%s" % account.id
        #
        # if options and options.get('v_departments'):
        #     count = 1
        #     arg_code_string = ""
        #     for tmp in options['v_departments']:
        #         if count == 1:
        #             arg_code_string += " and department_id=%s" % str(tmp)
        #         else:
        #             arg_code_string += " or department_id=%s" % str(tmp)
        #         count += 1
        #     compare_sql_string += arg_code_string
        # if options and options.get('v_cost_centers'):
        #     count = 1
        #     arg_code_string = ""
        #     for tmp in options['v_cost_centers']:
        #         if count == 1:
        #             arg_code_string += " and cost_center_id=%s" % str(tmp)
        #         else:
        #             arg_code_string += " or cost_center_id=%s" % str(tmp)
        #         count += 1
        #     compare_sql_string += arg_code_string
        #
        # compare_date = comparison_table[0]['date_from']
        # self.env.cr.execute("select sum(debit) as debit, sum(credit) as credit \
        #                                  from account_move_line \
        #                                  where " + compare_sql_string + " and date < \' " + str(compare_date) + " \'")
        # ml_id = self.env.cr.dictfetchall()
        # # ml_id = self.env['account.move.line'].search([('account_id', '=', bal['account_id']), ('date', '<', str(compare_date))])
        # if ml_id:
        #     ml = ml_id[0]
        #     debit = 0
        #     credit = 0
        #     if ml.get('debit'):
        #         debit = ml.get('debit')
        #     if ml.get('credit'):
        #         credit = ml.get('credit')
        #     if debit or credit:
        #         cols[0] = debit - credit

        domain_cd = [('account_id', '=', account.id), ('date', '<', comparison_table[0]['date_from'])]
        if options.get('v_cost_centers'):
            domain_cd += self._get_options_v_cost_center_domain(options)
        if options.get('v_departments'):
            domain_cd += self._get_options_v_department_domain(options)

        tf_acc_mv_line_ids = [x for x in self.env['account.move.line'].search(domain_cd)]
        cols[0] = sum(x.debit for x in tf_acc_mv_line_ids) - sum(x.credit for x in tf_acc_mv_line_ids)

        return cols