import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class IrModel(models.Model):
    _inherit = 'ir.model'

    field_security_ids = fields.One2many(
        'generic.security.restriction.field', 'model_id',
        index=True, string='Security Fields')
