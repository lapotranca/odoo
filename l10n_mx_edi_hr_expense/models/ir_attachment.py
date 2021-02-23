# Copyright 2018, Vauxoo, S.A. de C.V.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64
import logging
from io import BytesIO

from lxml import objectify
from odoo import api, models
from odoo.tools.xml_utils import _check_with_xsd
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def l10n_mx_edi_is_expense(self):
        self.ensure_one()

        # Using sudo because we need to be as efficient as possible here
        # jumping the ACL process.
        if not self.sudo().res_model == 'hr.expense' and not \
                self.sudo().company_id.country_id == self.env.ref('base.mx'):
            return False
        return True

    @api.model
    def l10n_mx_edi_is_cfdi33(self):
        self.ensure_one()
        if not self.datas:
            return False
        try:
            datas = base64.b64decode(self.datas).replace(
                b'xmlns:schemaLocation', b'xsi:schemaLocation')
            cfdi = objectify.fromstring(datas)
        except (SyntaxError, ValueError):
            return False

        attachment = self.env.ref('l10n_mx_edi.xsd_cached_cfdv33_xsd', False)
        schema = base64.b64decode(attachment.datas) if attachment else b''
        try:
            if cfdi.get('Version') != '3.3':
                return False
            if hasattr(cfdi, 'Addenda'):
                cfdi.remove(cfdi.Addenda)
            if not hasattr(cfdi, 'Complemento'):
                return False
            if not attachment:
                return cfdi
            attribute = 'registrofiscal:CFDIRegistroFiscal'
            namespace = {
                'registrofiscal': 'http://www.sat.gob.mx/registrofiscal'}
            node = cfdi.Complemento.xpath(attribute, namespaces=namespace)
            if node:
                cfdi.Complemento.remove(node[0])
            with BytesIO(schema) as xsd:
                _check_with_xsd(cfdi, xsd)
            return cfdi
        except ValueError:
            return False
        except IOError:
            return False
        except UserError:
            return False
        except etree.XMLSyntaxError:
            return False
        return False

