# coding: utf-8
from odoo import fields, models


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    l10n_mx_edi_code = fields.Char(
        'Our Code', help='Code defined by the company to this record, could '
        'not be related with the SAT catalog. Must be used to indicate the '
        'attribute "Clave" in the payslip lines, if this is empty will be '
        'used the value in the field "Code".')
