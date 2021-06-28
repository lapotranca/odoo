# -*- coding: utf-8 -*-
import base64
from lxml import etree, objectify
from odoo import _, api, fields, models
from odoo.tools.float_utils import float_is_zero
from odoo.tools import float_round
from odoo.exceptions import UserError

class as_hr_expenses(models.Model):
    """Heredado modelo hr.expenses para agregar campos"""
    _inherit = 'hr.expense'
    _description = "Heredado modelo hr.expenses para agregar campos"

    as_xml_invocie = fields.Binary(string='Factura (XML)', attachment=False)  
    UUID = fields.Char(string='UUID') 
    as_attachment = fields.Many2many('ir.attachment', string='Archvos de gasto')
    as_expense_id = fields.Many2one('hr.expense', string='Gasto')
    as_subido =fields.Boolean(string='Subido',default=False) 
    as_no_subido =fields.Boolean(string='No subido',default=False) 
    as_repetida =fields.Boolean(string='Factura repetida',default=False) 
    as_no_company =fields.Boolean(string='No compania',default=False) 
    as_require_xml =fields.Boolean(related='product_id.as_expense_xml',string='Requerido XML') 

    @api.model_create_multi
    def create(self, vals):
        result = super(as_hr_expenses, self).create(vals)
        if result.as_xml_invocie:
            tree = self._compute_cfdi_values(result.as_xml_invocie)
            tfd_node = self.l10n_mx_edi_get_tfd_etree(tree)
            rfc_receptor = tree.Receptor.get('Rfc')
            if result.company_id.vat == rfc_receptor:
                gasto = self.env['hr.expense'].search([('UUID', '=', tfd_node.get('UUID')), ('id', '!=', result.id)])
                if gasto:
                    raise UserError(_('La Factura que intenta adjuntar, ya existe en el sistema!'))
                else:
                    result.UUID = tfd_node.get('UUID')
                    attachment_vals = {
                        'name': 'Factura_'+result.name+'.xml',
                        'datas': result.as_xml_invocie,
                        'res_model': 'hr.expense',
                        'res_id': result.id,
                        'type': 'binary',
                    }
                    result.as_xml_invocie = result.as_xml_invocie
                    attach = self.env['ir.attachment'].create(attachment_vals)
                    result.as_attachment=attach.ids
                    result.as_subido = True
            else:
                raise UserError(_('Subida Fallida, la factura que intenta subir no pertenece a la compañia del gasto!!'))

        return result

    def write(self, vals):
        if 'as_xml_invocie' in vals and vals['as_xml_invocie'] and not self.as_xml_invocie:
            attachment_data = self.env['ir.attachment'].search([('res_model', '=', 'hr.expense'), ('res_id', '=', self.id)])
            attachment_data.unlink()   
            tree = self._compute_cfdi_values(bytes(vals['as_xml_invocie'],encoding="UTF-8"))
            tfd_node = self.l10n_mx_edi_get_tfd_etree(tree)
            rfc_receptor = tree.Receptor.get('Rfc')
            if self.company_id.vat == rfc_receptor:
                gasto = self.env['hr.expense'].search([('UUID', '=', tfd_node.get('UUID')), ('id', '!=', self.id)])
                if gasto:
                    raise UserError(_('La Factura que intenta adjuntar, ya existe en el sistema!'))
                else:
                    vals['UUID'] = tfd_node.get('UUID')
                    attachment_vals = {
                        'name': 'Factura_'+self.name+'.xml',
                        'datas': bytes(vals['as_xml_invocie'],encoding="UTF-8"),
                        'res_model': 'hr.expense',
                        'res_id': self.id,
                        'type': 'binary',
                    }
                    attach = self.env['ir.attachment'].create(attachment_vals)
                    vals['as_attachment']=attach.ids
                    vals['as_subido'] = True
            else:
                raise UserError(_('Subida Fallida, la factura que intenta subir no pertenece a la compañia del gasto!!'))
        res = super().write(vals)
        return res

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

    def action_submit_expenses(self):
        if self.product_id.as_expense_xml and self.attachment_number <=0:
            raise UserError(_("Para continuar debe adjuntar el XML de la Factura!"))
        if any(expense.state != 'draft' or expense.sheet_id for expense in self):
            raise UserError(_("You cannot report twice the same line!"))
        if len(self.mapped('employee_id')) != 1:
            raise UserError(_("You cannot report expenses for different employees in the same report."))
        if any(not expense.product_id for expense in self):
            raise UserError(_("You can not create report without product."))

        todo = self.filtered(lambda x: x.payment_mode=='own_account') or self.filtered(lambda x: x.payment_mode=='company_account')
        return {
            'name': _('New Expense Report'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'hr.expense.sheet',
            'target': 'current',
            'context': {
                'default_expense_line_ids': todo.ids,
                'default_company_id': self.company_id.id,
                'default_employee_id': self[0].employee_id.id,
                'default_name': todo[0].name if len(todo) == 1 else ''
            }
        }
