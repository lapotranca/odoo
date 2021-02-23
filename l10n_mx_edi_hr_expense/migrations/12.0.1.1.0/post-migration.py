import json

from odoo import SUPERUSER_ID, api


def update_document_type(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    expenses = env['hr.expense'].search([
        ('l10n_mx_edi_analysis', '!=', False)])
    dict_document_type = {'I': 'in_invoice', 'E': 'in_refund'}
    for expense in expenses:
        inv = json.loads(expense.l10n_mx_edi_analysis).get('invoices')[0]
        expense.l10n_mx_edi_document_type = dict_document_type.get(
            inv.get('document_type'))


def migrate(cr, version):
    if not version:
        return
    update_document_type(cr)
