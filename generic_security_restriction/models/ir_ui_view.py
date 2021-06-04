import json
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    def _apply_group(self, model, node, modifiers, fields):

        result = super(IrUiView, self)._apply_group(
            model, node, modifiers, fields)

        # Rules not work for superuser
        if not result or self.env.user._is_superuser():
            return result

        fields_security = self.env['ir.model']._get(model).mapped(
            'field_security_ids')

        for field_security in fields_security:
            if self.env.user.groups_id & field_security.group_ids:
                if (node.tag == 'field' and
                        node.get('name') == field_security.field_id.name):
                    if field_security.set_invisible:
                        node.set('invisible', '1')
                        modifiers['invisible'] = field_security.set_invisible
                    if field_security.set_readonly:
                        node.set('readonly', '1')
                        modifiers['readonly'] = field_security.set_readonly
                    if (field_security.field_type == 'many2one' and
                            field_security.rewrite_options):
                        options = {
                            'no_open': field_security.set_no_open,
                            'no_create': field_security.set_no_create,
                            'no_quick_create':
                                field_security.set_no_quick_create,
                            'no_create_edit': field_security.set_no_create_edit
                        }
                        node.set('options', json.dumps(options))
                if node.tag in ('button', 'a'):
                    if any([i.get('name') == field_security.field_id.name
                            for i in node.iter(tag='field')]):
                        if field_security.hide_stat_button:
                            node.set('invisible', '1')
                            modifiers['invisible'] = \
                                field_security.hide_stat_button
        return True
