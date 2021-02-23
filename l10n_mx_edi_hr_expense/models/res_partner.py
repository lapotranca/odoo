# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    accountant_company_currency_id = fields.Many2one(
        "res.users", string="Accountant MXN", company_dependent=True,
        help="This user will be the accountant assigned in the expense sheets "
        "generated to this supplier.")
    accountant_foreign_currency_id = fields.Many2one(
        "res.users", string="Accountant Other Currencies",
        company_dependent=True,
        help="This user will be the accountant assigned in the expense sheets "
        "generated to this supplier.")
