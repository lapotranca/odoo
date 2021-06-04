import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class FieldSecurity(models.Model):
    _name = 'generic.security.restriction.field'
    _description = 'Fields Security'

    model_id = fields.Many2one('ir.model', required=True, index=True)
    field_id = fields.Many2one('ir.model.fields', required=True, index=True)
    field_name = fields.Char(related='field_id.name', readonly=True)
    field_type = fields.Selection(related='field_id.ttype', readonly=True)
    group_ids = fields.Many2many(
        'res.groups', 'fields_security_restriction_group_relation',
        'group_id', 'field_security_id', required=True, string='Groups')
    set_readonly = fields.Boolean(default=False)
    set_invisible = fields.Boolean(default=False)
    rewrite_options = fields.Boolean(default=False)
    set_no_open = fields.Boolean(
        default=False, help="In read mode: do not render as a link.")
    set_no_create = fields.Boolean(
        default=False,
        help="It is no_quick_create and no_create_edit combined.")
    set_no_quick_create = fields.Boolean(
        default=False, help="Remove the *Create 'foo'* option.")
    set_no_create_edit = fields.Boolean(
        default=False, help="Remove the *Create and edit...* option.")
    hide_stat_button = fields.Boolean(default=False)

    @api.onchange('rewrite_options')
    def _onchange_rewrite_options(self):
        for rec in self:
            if not rec.rewrite_options:
                rec.set_no_open = False
                rec.set_no_create = False
                rec.set_no_quick_create = False
                rec.set_no_create_edit = False
