# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        env['ir.attachment'].update_all_uuids()
