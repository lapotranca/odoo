# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    def generate_email(self, res_ids, fields=None):
        self.ensure_one()
        res = super(MailTemplate, self).generate_email(res_ids, fields=fields)
        if self.model != 'hr.payslip':
            return res
        for payslip in self.env['hr.payslip'].browse(res_ids):
            company = payslip.company_id or payslip.contract_id.company_id
            if company.country_id != self.env.ref('base.mx'):
                continue  # pragma: no cover
            attachment = payslip.l10n_mx_edi_retrieve_last_attachment()
            if attachment:
                res[payslip.id].get('attachments', []).append(
                    (attachment.name, attachment.datas))
        return res
