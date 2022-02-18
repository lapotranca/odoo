# Copyright 2019 Vauxoo (https://www.vauxoo.com) <info@vauxoo.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64
import io
import os
import zipfile

from odoo import fields, models, tools
from odoo.addons.base.models.ir_ui_view import keep_query


class IrAttachmentZip(models.TransientModel):
    _name = 'ir.attachment.zip'
    _description = 'Get zip attachments'

    attachment_ids = fields.Many2many('ir.attachment')
    zip_file = fields.Binary(readonly=True)
    zip_name = fields.Char(required=True)

    def _set_zip_file(self):
        filestore = tools.config.filestore(self.env.cr.dbname)
        if not self.attachment_ids:
            self.zip_file = None
            return
        with io.BytesIO() as fio:
            with zipfile.ZipFile(fio, "w") as fzip:
                for attach in self.attachment_ids:
                    fpath = os.path.join(filestore, attach.store_fname)
                    fname = self._get_attachment_zip_name(attach)
                    fzip.write(fpath, fname)
            fio.seek(0)
            self.zip_file = base64.b64encode(fio.read())

    def _get_attachment_zip_name(self, attach):
        """Get name for the attachment on the zip File"""
        if attach.mimetype == 'application/pdf':
            return '%s.pdf' % attach.name
        elif attach.l10n_mx_edi_cfdi_uuid:
            return "%s.xml" % attach.l10n_mx_edi_cfdi_uuid
        return attach.name

    def _get_action_download(self):
        if not self.zip_file:
            return {}
        url_base = "web/content"
        url_data = {
            'model': self._name,
            'id': self.id,
            'filename_field': 'zip_name',
            'field': 'zip_file',
            'download': 'true',
            'filename': self.zip_name,
        }
        action = {
            'name': 'Download attachment ZIP',
            'type': 'ir.actions.act_url',
            'url': "%s/?%s" % (url_base, keep_query(**url_data)),
            'target': 'self',
            'data': url_data,
        }
        return action
