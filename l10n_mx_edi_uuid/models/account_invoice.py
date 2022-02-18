# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv.expression import (NEGATIVE_TERM_OPERATORS,
                                 TERM_OPERATORS_NEGATION)
TERM_OPERATORS_POSITIVE = {v: k for k, v in TERM_OPERATORS_NEGATION.items()}


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_mx_edi_cfdi_uuid = fields.Char(
        compute='_compute_l10n_mx_edi_cfdi_uuid',
        search='_search_l10n_mx_edi_cfdi_uuid')

    @api.model
    def _name_search(self, name='', args=None, operator='ilike',
                     limit=100, name_get_uid=None):
        if args is None:
            args = []

        uuid_domain = self._search_l10n_mx_edi_cfdi_uuid(
            operator='=', value=name)
        invoices = self.search(uuid_domain + args, limit=limit)
        res = invoices.name_get()
        if not invoices:
            res = super()._name_search(name, args, operator, limit, name_get_uid)
        return res

    def _get_falsy_l10n_mx_edi_cfdi_uuid(self, search_domain=None):
        if search_domain is None:
            search_domain = []
        invs = self.env['account.move'].search(search_domain)
        inv_uuid = invs._compute_l10n_mx_edi_cfdi_uuid(return_dict=True)
        matched_invoice_ids = [
            inv_id for inv_id, uuid in inv_uuid.items() if uuid]
        return matched_invoice_ids

    def _search_l10n_mx_edi_cfdi_uuid(self, operator, value):
        domain_op = 'not in' if operator in NEGATIVE_TERM_OPERATORS else 'in'
        domain_op_falsy = (
            'in' if operator in NEGATIVE_TERM_OPERATORS else 'not in')
        if not value:
            invoice_ids = self._get_falsy_l10n_mx_edi_cfdi_uuid()
            domain = [('id', domain_op_falsy, invoice_ids)]
            return domain
        positive_operator = (
            TERM_OPERATORS_POSITIVE[operator]
            if operator in NEGATIVE_TERM_OPERATORS else operator)
        attachments = self.env['ir.attachment'].search_read([
            ('res_model', '=', 'account.move'),
            ('l10n_mx_edi_cfdi_uuid', positive_operator, value),
            ('l10n_mx_edi_cfdi_uuid', '!=', None)], ['res_id'])
        invoice_ids = list(set([
            attachment['res_id'] for attachment in attachments]))
        falsy_invoice_ids = None
        domain = [('id', domain_op, invoice_ids)]
        if isinstance(value, list) and (None in value or False in value):
            falsy_invoice_ids = self._get_falsy_l10n_mx_edi_cfdi_uuid()
            domain.append(('id', domain_op_falsy, falsy_invoice_ids))
            domain.insert(0, '&' if operator in NEGATIVE_TERM_OPERATORS
                          else '|')
        return domain

    @api.depends('l10n_mx_edi_cfdi_name')
    def _compute_l10n_mx_edi_cfdi_uuid(self, return_dict=None):
        if not self.ids:
            for inv in self:
                inv.l10n_mx_edi_cfdi_uuid = False
            return {}
        self.env.cr.execute("""
            SELECT res_id, l10n_mx_edi_cfdi_uuid
            FROM ir_attachment
            WHERE res_model = %s AND res_id IN %s
              AND l10n_mx_edi_cfdi_uuid IS NOT NULL
            ORDER BY create_date ASC, id ASC
        """, (self._name, tuple(self.ids)))
        res = dict(self.env.cr.fetchall())
        if return_dict:
            return res
        for inv in self:
            inv.l10n_mx_edi_cfdi_uuid = res.get(inv.id)

    @api.constrains('state', 'l10n_mx_edi_cfdi_name')
    def _check_uuid_duplicated(self):
        invoices = self.exists()
        mx_invoices = invoices.filtered(
            lambda r: r.company_id.country_id == self.env.ref('base.mx'))
        if invoices and not mx_invoices:
            return
        invoice_ids = mx_invoices.ids
        to_omit = self._context.get('states2omit', {'draft', 'cancel'})
        if invoice_ids and not set(mx_invoices.mapped('state')) - to_omit:
            # If exists invoice but has state draft or cancel then skip check
            return
        query = """
            SELECT
                MIN(l10n_mx_edi_cfdi_uuid), array_agg(DISTINCT inv.id)
            FROM
                ir_attachment att
            INNER JOIN
                account_move inv
            ON inv.id = att.res_id
                AND att.res_model = %%s
                AND inv.state NOT IN %%s
                AND l10n_mx_edi_cfdi_uuid IS NOT NULL
                AND inv.company_id = %%s
            %s
            GROUP BY trim(upper(l10n_mx_edi_cfdi_uuid))
            HAVING count(DISTINCT inv.id) >= 2
        """
        params = (self._name, tuple(to_omit), self.env.user.company_id.id)
        query_where = ""
        if invoice_ids:
            uuids = self.env['ir.attachment'].search_read([
                ('l10n_mx_edi_cfdi_uuid', '!=', None),
                ('res_id', 'in', invoice_ids),
                ('res_model', '=', 'account.move')],
                ['l10n_mx_edi_cfdi_uuid'])
            uuids = {uuid['l10n_mx_edi_cfdi_uuid'] for uuid in uuids}
            if not uuids:
                # Skip if exists invoices but don't have uuids
                return
            query_where = "WHERE l10n_mx_edi_cfdi_uuid IN %s"
            params += (tuple(uuids),)
        # pylint: disable=sql-injection
        self.env.cr.execute(query % query_where, params)
        res = dict(self.env.cr.fetchall())
        msg = ""
        for uuid, record_ids in res.items():
            records = self.browse(record_ids)
            msg += _("UUID duplicated %s for following invoices:\n%s\n") % (
                uuid, '\n'.join(['\t* %d: %s' % (rid, rname)
                                 for rid, rname in records.name_get()]))
        if msg:
            raise ValidationError(msg)

    @api.depends('l10n_mx_edi_cfdi_name', 'l10n_mx_edi_pac_status')
    def _compute_cfdi_values(self):
        """Inherit method to re-compute the field `l10n_mx_edi_cfdi_uuid` that is also set in this method.
        """
        res = super()._compute_cfdi_values()
        self._compute_l10n_mx_edi_cfdi_uuid()
        return res
