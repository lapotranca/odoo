from odoo import fields, models, SUPERUSER_ID


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    hide_for_user_ids = fields.Many2many(
        'res.users', 'ir_actions_report_res_users_hidden_reports_rel',
        'report_id', 'user_id', string='Hidden print reports')

    hide_for_group_ids = fields.Many2many(
        'res.groups', 'ir_actions_report_res_groups_hidden_reports_rel',
        'report_id', 'group_id', string='Hidden print reports')

    def report_action(self, docids, data=None, config=True):
        hidden_reports = self.env.user.hidden_reports_ids
        hidden_reports += self.env.user.groups_id.mapped('hidden_report_ids')

        result = super(IrActionsReport, self).report_action(
            docids, data=data, config=config)
        if self._uid == SUPERUSER_ID:
            return result
        # Checking restrictions for current report
        if self.id not in hidden_reports.ids:
            return result
        return None
