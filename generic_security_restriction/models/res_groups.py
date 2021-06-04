from odoo import models, fields, api


class Groups(models.Model):
    _inherit = "res.groups"

    menu_access_restrict = fields.Many2many(
        'ir.ui.menu', 'ir_ui_menu_group_restrict_rel',
        'gres_id', 'menu_id', string='Restrict Access Menu')
    hidden_report_ids = fields.Many2many(
        'ir.actions.report', 'ir_actions_report_res_groups_hidden_reports_rel',
        'group_id', 'report_id', string='Restrict Access Reoprts')

    @api.model
    def create(self, values):
        self.env['ir.ui.menu'].clear_caches()
        return super(Groups, self).create(values)

    def write(self, values):
        self.env['ir.ui.menu'].clear_caches()
        return super(Groups, self).write(values)
