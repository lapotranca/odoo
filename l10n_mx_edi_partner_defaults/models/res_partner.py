# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models, fields


class Partner(models.Model):
    _inherit = "res.partner"

    l10n_mx_edi_payment_method_id = fields.Many2one(
        'l10n_mx_edi.payment.method',
        string="Payment Method",
        help='This payment method will be used by default in the related '
        'documents (invoices, payments, and bank statements).',
        default=lambda self: self.env.ref('l10n_mx_edi.payment_method_otros',
                                          raise_if_not_found=False))

    def _get_usage_selection(self):
        return self.env['account.move'].fields_get().get(
            'l10n_mx_edi_usage').get('selection')

    l10n_mx_edi_usage = fields.Selection(
        _get_usage_selection, 'Usage', default='P01',
        help='This usage will be used instead of the default one for invoices.'
    )
