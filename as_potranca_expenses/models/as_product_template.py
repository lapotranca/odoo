# -*- coding: utf-8 -*-

from odoo import models,fields,api
    
class as_product_template(models.Model):
    """Heredado modelo product.templates para agregar campos"""
    _inherit = 'product.template'
    _description = "Heredado modelo product.templates para agregar campos"

    as_expense_xml =fields.Boolean(string='Factura XML Oblogatoria') 


class as_account_move(models.Model):
    """Heredado modelo account_move para agregar campos"""
    _inherit = 'account.move'

    @api.constrains('line_ids', 'journal_id')
    def _validate_move_modification(self):
        if 'posted' in self.mapped('line_ids.payment_id.state'):
            if self.as_no_edit != True:
                raise ValidationError(_("You cannot modify a journal entry linked to a posted payment."))