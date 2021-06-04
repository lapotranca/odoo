from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    hidden_menu_ids = fields.Many2many(
        'ir.ui.menu', 'ir_ui_menu_res_users_hidden_rel',
        'user_id', 'menu_id', string='Hidden menus')
    hidden_reports_ids = fields.Many2many(
        'ir.actions.report', 'ir_actions_report_res_users_hidden_reports_rel',
        'user_id', 'report_id', string='Hidden print reports')

    @api.model
    def create(self, values):
        self.env['ir.ui.menu'].clear_caches()
        return super(ResUsers, self).create(values)

    def write(self, values):
        self.env['ir.ui.menu'].clear_caches()
        return super(ResUsers, self).write(values)
