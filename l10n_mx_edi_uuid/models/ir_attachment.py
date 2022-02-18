# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from lxml import etree
from lxml.objectify import fromstring

from odoo import api, fields, models

FIELDS = ['store_fname', 'res_model', 'res_id', 'name', 'datas']


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    l10n_mx_edi_cfdi_uuid = fields.Char(
        string="Fiscal Folio", index=True,
        prefetch=False, readonly=True)

    def update_uuid(self, check_duplicated=True):
        if not self.ids or not self.exists():
            return
        uuid_attachments = self.search(self._get_uuid_domain() + [('id', 'in', self.ids)])
        attachments_skipped_ids = []
        invoice_ids = []
        for attach in uuid_attachments.with_context(prefetch_fields=False):
            if not attach.datas:
                attachments_skipped_ids.append(attach.id)
                continue
            cfdi = base64.decodestring(attach.datas).replace(
                b'xmlns:schemaLocation', b'xsi:schemaLocation')
            model = self.env[attach.res_model].browse(attach.res_id)
            try:
                tree = fromstring(cfdi)
            except etree.XMLSyntaxError:
                # it is a invalid xml
                attachments_skipped_ids.append(attach.id)
                continue

            tfd_node = model.l10n_mx_edi_get_tfd_etree(tree)
            if tfd_node is None:
                # It is not a signed xml
                attachments_skipped_ids.append(attach.id)
                continue
            attach.with_context(force_l10n_mx_edi_cfdi_uuid=True).write({
                'l10n_mx_edi_cfdi_uuid': tfd_node.get('UUID', '').upper().strip()})
            if model._name == 'account.move':
                invoice_ids.append(model.id)
        attachments_skipped = self.browse(attachments_skipped_ids)
        (self - uuid_attachments + attachments_skipped).with_context(
            force_l10n_mx_edi_cfdi_uuid=True).write({
                'l10n_mx_edi_cfdi_uuid': False})
        if check_duplicated and invoice_ids:
            invoices = self.env['account.move'].browse(invoice_ids)
            invoices.sudo()._check_uuid_duplicated()
        return True

    @api.model
    def update_all_uuids(self):
        uuid_attachments = self.search(self._get_uuid_domain() + [('l10n_mx_edi_cfdi_uuid', '=', False)])
        return uuid_attachments.update_uuid(check_duplicated=False)

    @api.model
    def _get_uuid_domain(self):
        """Domain to retrieve all attachments that could correspond to a document with UUID"""
        return [
            ('res_id', '!=', False),
            ('res_model', 'in', ['account.move', 'account.payment']),
            '|',
            ('name', '=ilike', '%.xml'),
            ('name', 'not like', '.'),
        ]

    def write(self, vals):
        if self.env.context.get('force_l10n_mx_edi_cfdi_uuid'):
            return super().write(vals)
        vals.pop('l10n_mx_edi_cfdi_uuid', None)
        with self.env.cr.savepoint():
            # Secure way if someone catch the exception to skip a rollback
            res = super(IrAttachment, self).write(vals)
            if set(vals.keys()) & set(FIELDS):
                self.update_uuid()
        return res

    @api.model
    def create(self, vals):
        vals.pop('l10n_mx_edi_cfdi_uuid', None)
        with self.env.cr.savepoint():
            # Secure way if someone catch the exception and skip a rollback
            records = super(IrAttachment, self).create(vals)
            if set(vals.keys()) & set(FIELDS):
                records.update_uuid()
        return records
