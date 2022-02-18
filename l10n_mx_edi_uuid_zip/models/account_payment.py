# Copyright 2019 Vauxoo (https://www.vauxoo.com) <info@vauxoo.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import os
import re

from odoo import _, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @staticmethod
    def get_valid_filename(filename):
        filename, ext = os.path.splitext(filename)
        filename = filename.strip().replace(' ', '')
        return (re.sub(r'(?u)[^-\w]', '', filename) + ext).lower()

    def _l10n_mx_edi_uuid_zip_post(self):
        ctx = self.env.context.copy()
        ctx.pop('default_type', False)
        msg_subt = 'l10n_mx_edi_uuid_zip.mt_payment_invoices_zip'
        for payment in self.filtered(
                lambda r: r.company_id.country_id == self.env.ref('base.mx')):
            invoice_zip = self.env.ref(
                'l10n_mx_edi_uuid_zip.invoice_download_uuid_xml_server_action')
            action = invoice_zip.with_context(
                active_ids=payment.invoice_ids.ids,
                active_model='account.move').run()
            if not action:
                continue
            data = action['data']
            zipf = self.env[data['model']].browse(data['id'])[data['field']]
            fname = 'cfdi_uuid_{1}_{0}.zip'.format(*payment.name_get()[0])
            fname = self.get_valid_filename(fname)
            attach = self.env['mail.message'].search([
                ('id', 'in', payment.message_ids.ids),
                ('subtype_id', '=', self.env.ref(msg_subt).id),
                ('attachment_ids', '!=', False),
            ], order='id DESC', limit=1).attachment_ids
            if attach:
                attach[0].write({
                    'name': fname,
                    'datas': zipf,
                })
                payment.message_post(
                    body="%s %s" % (_('Invoices CFDI XMLs'), _('updated')),
                    subtype=msg_subt)
                continue
            attach = self.env['ir.attachment'].with_context(ctx).create({
                'name': fname,
                'res_id': payment.id,
                'res_model': payment._name,
                'datas': zipf,
                'description': 'Mexican invoices from payment XML ZIP',
            })
            payment.message_post(
                body=_('Invoices CFDI XMLs'),
                attachment_ids=attach.ids,
                subtype=msg_subt)
