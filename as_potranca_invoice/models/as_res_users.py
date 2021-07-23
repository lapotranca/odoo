# -*- coding: utf-8 -*-

from odoo import models,fields,api
    
class s_res_users(models.Model):
    """Heredado modelo res.users para agregar campos"""
    _inherit = 'res.users'
    _description = "Heredado modelo res.users para agregar campos"

    as_journal_id = fields.Many2one('account.journal', string='Diario Factura Cliente', domain="[('company_id', '=', company_id)]")