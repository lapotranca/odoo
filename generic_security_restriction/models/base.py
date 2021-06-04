import logging

from odoo import models, api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False,
                        submenu=False):

        res = super(Base, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar,
            submenu=submenu)

        if self._uid == SUPERUSER_ID:
            return res

        if not res.get('toolbar', {}).get('print', []):
            return res

        hidden_reports = self.env.user.hidden_reports_ids
        hidden_reports += self.env.user.groups_id.mapped('hidden_report_ids')

        new_actions = []
        for act in res['toolbar']['print']:

            if act['id'] not in hidden_reports.ids:
                # Remove field that contains user or groups restrictions to
                # avoid passing it to js client.
                act.pop('hide_for_user_ids', False)
                act.pop('hide_for_group_ids', False)
                new_actions += [act]
        res['toolbar']['print'] = new_actions

        return res
