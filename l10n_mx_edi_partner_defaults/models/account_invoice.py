# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        """Set payment method and usage"""
        res = super()._onchange_partner_id()
        if self.type in ('in_invoice', 'in_refund'
                         ) or not self.partner_id.commercial_partner_id:
            return res
        self.l10n_mx_edi_payment_method_id = (
            self.partner_id.commercial_partner_id
            .l10n_mx_edi_payment_method_id)
        self.l10n_mx_edi_usage = (self.partner_id.commercial_partner_id
                                  .l10n_mx_edi_usage)
        return res

    @api.model
    def create(self, vals):
        onchanges = {
            '_onchange_partner_id': [
                'l10n_mx_edi_payment_method_id', 'l10n_mx_edi_usage',
                'l10n_mx_edi_partner_bank_id'],
        }
        for onchange_method, changed_fields in onchanges.items():
            if any(f not in vals for f in changed_fields):
                invoice = self.new(vals)
                getattr(invoice, onchange_method)()
                for field in changed_fields:
                    if field not in vals and invoice[field]:
                        vals[field] = invoice._fields[
                            field].convert_to_write(invoice[field], invoice)
        return super().create(vals)
