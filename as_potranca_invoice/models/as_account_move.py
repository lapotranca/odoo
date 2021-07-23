# -*- coding: utf-8 -*-
import base64
from lxml import etree, objectify
from odoo import _, api, fields, models
from odoo.tools.float_utils import float_is_zero
from odoo.tools import float_round
from odoo.exceptions import UserError

class AccountMove(models.Model):
    """Heredado modelo account.move para agregar campos"""
    _inherit = 'account.move'
    _description = "Heredado modelo account.move para agregar campos"

    @api.model_create_multi
    def create(self, vals):
        result = super(AccountMove, self).create(vals)
        journal_user = result.env.user.as_journal_id
        if journal_user and result.type == 'out_invoice':
            result.journal_id = journal_user
        return result

    @api.model
    def _get_default_journal(self):
        move_type = self._context.get('default_type', 'entry')
        journal = super(AccountMove, self)._get_default_journal()
        journal_user = self.env.user.as_journal_id
        if journal_user and move_type == 'out_invoice':
            journal = journal_user
        return journal

    journal_id = fields.Many2one('account.journal', string='Diario', required=True, readonly=True,
        states={'draft': [('readonly', False)]},
        domain="[('company_id', '=', company_id)]",
        default=_get_default_journal)