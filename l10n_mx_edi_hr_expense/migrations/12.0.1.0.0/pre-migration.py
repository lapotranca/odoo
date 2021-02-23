# coding: utf-8

from odoo.tools import convert_file


def pre_load_data(cr):
    convert_file(
        cr, 'l10n_mx_edi_hr_expense', 'data/partner_tags.xml',
        {}, 'init', True, 'data', False)


def migrate(cr, version):
    if not version:
        return
    pre_load_data(cr)
