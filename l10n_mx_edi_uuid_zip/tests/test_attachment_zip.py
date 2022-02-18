# Copyright 2019 Vauxoo (https://www.vauxoo.com) <info@vauxoo.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64
import os

from lxml import etree, objectify

from odoo import tools
from odoo.tests import TransactionCase


class TestAttachmentZip(TransactionCase):
    def setUp(self):
        super(TestAttachmentZip, self).setUp()
        self.attach = self.env['ir.attachment']
        xml_expected_str = tools.file_open(os.path.join(
            'l10n_mx_edi', 'tests', 'expected_cfdi33.xml')
        ).read().encode('UTF-8')
        self.xml_expected = objectify.fromstring(xml_expected_str)

    def create_attachment(self, model, uuid=None):
        tfd = model.l10n_mx_edi_get_tfd_etree(self.xml_expected)
        tfd.attrib['UUID'] = uuid or ''
        if uuid is None:
            del tfd.attrib['UUID']
        xml_str = etree.tostring(self.xml_expected)
        attachment = self.attach.create({
            'name': model.l10n_mx_edi_cfdi_name,
            'datas': base64.b64encode(xml_str),
            'res_id': model.id,
            'res_model': model._name,
        })
        return attachment

    def create_invoice(self, cfdi_name='test01.xml'):
        inv = self.env['account.move'].create({'type': 'out_invoice'})
        inv.l10n_mx_edi_cfdi_name = cfdi_name
        return inv

    def test_attachment_zip(self):
        # TODO: Consider xml without uuid
        # TOOD: Consider without attachments
        inv = self.create_invoice()
        attach = self.create_attachment(inv, '123-456')
        attach_zip = self.env['ir.attachment.zip'].create({
            'attachment_ids': [(6, 0, attach.ids)],
            'zip_name': 'test01.zip',
        })
        attach_zip._set_zip_file()
        # action = attach_zip._get_action_download()
        # TODO: add asserts reading zip content
