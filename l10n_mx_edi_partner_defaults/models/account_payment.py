from odoo import api, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        res = super()._onchange_partner_id()
        if self.partner_type == 'customer':
            partner = self.partner_id.commercial_partner_id
            self.l10n_mx_edi_payment_method_id = (
                partner.l10n_mx_edi_payment_method_id)
        return res
