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
