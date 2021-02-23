# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools import convert_file


def pre_init_hook(cr):
    convert_file(
        cr, 'l10n_mx_edi_hr_expense', 'data/partner_tags.xml',
        {}, 'init', True, 'data', False)
