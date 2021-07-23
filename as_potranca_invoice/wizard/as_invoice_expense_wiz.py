# Copyright 2017, Jarsa Sistemas, S.A. de C.V.

import base64
from lxml import etree, objectify
from odoo import _, api, fields, models
from odoo.tools.float_utils import float_is_zero
from odoo.tools import float_round
from odoo.exceptions import UserError
from lxml import etree, objectify
import base64

class InvoiceExpense(models.TransientModel):
    _name = 'as.invoice.expense'
    _description = "Wizard para adjuntar facturas a gastos"

    as_xml_invocie = fields.Binary(string='Factura (XML)', required=True) 
    as_attachment = fields.Many2many('ir.attachment', string='Archvos de gasto')
    as_expense_id = fields.Many2one('hr.expense', string='Gasto')
    as_subido =fields.Boolean(string='Subido') 
    as_no_subido =fields.Boolean(string='No subido') 
    as_repetida =fields.Boolean(string='Factura repetida') 
    as_no_company =fields.Boolean(string='No compania') 

    @api.model
    def default_get(self, fields):
        rec = super(InvoiceExpense, self).default_get(fields)
        rec['as_expense_id'] = self._context['active_id']
        attachment_data = self.env['ir.attachment'].search([('res_model', '=', 'hr.expense'), ('res_id', '=', self._context['active_id'])])
        if attachment_data:
            rec['as_xml_invocie'] = attachment_data[0].datas
            rec['as_attachment'] = attachment_data.ids
            rec['as_subido'] = False
            rec['as_no_subido'] = False
            rec['as_repetida'] = False
            rec['as_no_company'] = False
        return rec

    @api.model_create_multi
    def create(self, vals):
        result = super(InvoiceExpense, self).create(vals)
        attachment_data = self.env['ir.attachment'].search([('res_model', '=', 'hr.expense'), ('res_id', '=', self._context['active_id'])])
        if len(attachment_data) <= 0:
            tree = self._compute_cfdi_values(result.as_xml_invocie)
            tfd_node = self.l10n_mx_edi_get_tfd_etree(tree)
            rfc_receptor = tree.Receptor.get('Rfc')
            if result.as_expense_id.company_id.vat == rfc_receptor:
                gasto = self.env['hr.expense'].search([('UUID', '=', tfd_node.get('UUID')), ('id', '!=', self._context['active_id'])])
                if gasto:
                    result.as_repetida = True
                else:
                    result.as_expense_id.UUID = tfd_node.get('UUID')
                    attachment_vals = {
                        'name': 'Factura_'+result.as_expense_id.name+'.xml',
                        'datas': result.as_xml_invocie,
                        'res_model': 'hr.expense',
                        'res_id': result.as_expense_id.id,
                        'type': 'binary',
                    }
                    result.as_expense_id.as_xml_invocie = result.as_xml_invocie
                    attach = self.env['ir.attachment'].create(attachment_vals)
                    result.as_attachment=attach.ids
                    result.as_subido = True
            else:
                result.as_no_company = True
        else:
            result.as_no_subido = True
        return result

    # def write(self, vals):
    #     vals['as_subido']= False
    #     vals['as_no_subido']= False
    #     attachment_data = self.env['ir.attachment'].search([('res_model', '=', 'hr.expense'), ('res_id', '=', self._context['active_id'])])
    #     if len(attachment_data) <= 0:
    #         tree = self._compute_cfdi_values(self.as_xml_invocie)
    #         tfd_node = self.l10n_mx_edi_get_tfd_etree(tree)
    #         rfc_receptor = tree.Receptor.get('Rfc')
    #         if self.as_expense_id.company_id.vat == rfc_receptor:
    #             gasto = self.env['hr.expense'].search([('UUID', '=', tfd_node.get('UUID')), ('id', '!=', self._context['active_id'])])
    #             if gasto:
    #                 vals['as_repetida'] = False
    #             else:
    #                 vals['as_subido'] = True
    #         else:
    #             vals['as_no_company'] = True
    #     else:
    #         vals['as_no_subido'] = True
    #     res = super().write(vals)
    #     return res

    def as_delete_xml(self):
        self.as_expense_id.as_xml_invocie = False
        self.as_expense_id.UUID = ''
        for file in self.as_attachment:
            file.unlink()
            # expense.as_xml_invocie = self.as_xml_invocie
        return True

    def _compute_cfdi_values(self,attachment):
        '''Fill the invoice fields from the cfdi values.
        '''
        datas = attachment
        cfdi = base64.decodestring(datas).replace(
            b'xmlns:schemaLocation', b'xsi:schemaLocation')
        tree = objectify.fromstring(cfdi)
        # # if already signed, extract uuid
        # tfd_node = inv.l10n_mx_edi_get_tfd_etree(tree)
        # if tfd_node is not None:
        #     inv.l10n_mx_edi_cfdi_uuid = tfd_node.get('UUID')
        #     _logger.debug("\n\n\n\n\nse ha adjuntado uuid %s",inv.l10n_mx_edi_cfdi_uuid)
        # inv.l10n_mx_edi_cfdi_amount = tree.get('Total', tree.get('total'))
        # inv.l10n_mx_edi_cfdi_supplier_rfc = tree.Emisor.get(
        #     'Rfc', tree.Emisor.get('Rfc'))
        # inv.l10n_mx_edi_cfdi_customer_rfc = tree.Receptor.get(
        #     'Rfc', tree.Receptor.get('Rfc'))
        # certificate = tree.get('noCertificado', tree.get('NoCertificado'))
        return tree


    @api.model
    def l10n_mx_edi_get_tfd_etree(self, cfdi):
        '''Get the TimbreFiscalDigital node from the cfdi.

        :param cfdi: The cfdi as etree
        :return: the TimbreFiscalDigital node
        '''
        if not hasattr(cfdi, 'Complemento'):
            return None
        attribute = 'tfd:TimbreFiscalDigital[1]'
        namespace = {'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital'}
        node = cfdi.Complemento.xpath(attribute, namespaces=namespace)
        return node[0] if node else None
