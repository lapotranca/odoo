# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ReportAccountFinancialReport(models.Model):
    _inherit = "account.financial.html.report"

    v_cost_center = fields.Boolean('Allow Cost Center Filters')
    v_department = fields.Boolean('Allow Department Filters')


    def _with_correct_filters(self):
        res = super(ReportAccountFinancialReport, self)._with_correct_filters()
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

    def _get_lines(self, options, line_id=None):
        # res = super(ReportAccountFinancialReport, self)._get_lines(options=options, line_id=line_id)
        line_obj = self.line_ids
        if line_id:
            line_obj = self.env['account.financial.html.report.line'].search([('id', '=', line_id)])
        if options.get('comparison') and options.get('comparison').get('periods'):
            line_obj = line_obj.with_context(periods=options['comparison']['periods'])
        if options.get('ir_filters'):
            line_obj = line_obj.with_context(periods=options.get('ir_filters'))

        currency_table = self._get_currency_table()
        domain, group_by = self._get_filter_info(options)

        if options.get('v_cost_center'):
            if not domain:
                domain = []
            domain += self._get_options_v_cost_center_domain(options)

        if options.get('v_department'):
            if not domain:
                domain = []
            domain += self._get_options_v_department_domain(options)

        if group_by:
            options['groups'] = {}
            options['groups']['fields'] = group_by
            options['groups']['ids'] = self._get_groups(domain, group_by)

        amount_of_periods = len((options.get('comparison') or {}).get('periods') or []) + 1
        amount_of_group_ids = len(options.get('groups', {}).get('ids') or []) or 1
        linesDicts = [[{} for _ in range(0, amount_of_group_ids)] for _ in range(0, amount_of_periods)]

        res = line_obj.with_context(
            filter_domain=domain,
        )._get_lines(self, currency_table, options, linesDicts)
        return res