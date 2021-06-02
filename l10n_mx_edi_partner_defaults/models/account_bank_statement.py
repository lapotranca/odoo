from odoo import api, models


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Set payment method"""
        self.l10n_mx_edi_payment_method_id = (
            self.partner_id.l10n_mx_edi_payment_method_id)
