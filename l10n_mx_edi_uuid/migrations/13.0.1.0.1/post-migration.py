# Copyright 2020 Vauxoo
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).


def migrate(cr, version):
    set_uppercase_l10n_mx_edi_cfdi_uuid(cr)


def set_uppercase_l10n_mx_edi_cfdi_uuid(cr):
    """Set the l10n_mx_edi_cfdi_uuid to upper case in order to perform case-insensitive search"""
    cr.execute("""
         UPDATE
            ir_attachment
         SET
            l10n_mx_edi_cfdi_uuid = trim(upper(l10n_mx_edi_cfdi_uuid))
     """)
