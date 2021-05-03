from odoo import models


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    def send_mail(self, auto_commit=False):
        res = super(MailComposeMessage, self).send_mail(auto_commit)
        if 'hr.payslip' in self.mapped('model'):
            records = self.env['hr.payslip'].browse(self.mapped('res_id'))
            records.write({'sent': True})
        return res
