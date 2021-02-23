# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import json
import base64
import logging

from os.path import splitext
from lxml import objectify
from lxml.objectify import fromstring
import requests

from odoo import _, api, models, fields, registry, tools, SUPERUSER_ID
from odoo.api import Environment
from odoo.osv import expression
from odoo.tools import email_split, float_is_zero, float_round
from odoo.tools.misc import html_escape
from odoo.tools.float_utils import float_repr, float_compare
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    from json2html import json2html
except ImportError:
    _logger.error("Please install `pip install json2html`")

CFDI_SAT_QR_STATE = {
    'No Encontrado': 'not_found',
    'Cancelado': 'cancelled',
    'Vigente': 'valid',
}


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    @api.model
    def _get_user_domain(self):
        users = self.env['hr.employee'].search([
            ('expense_manager_id', '!=', False)]).mapped('expense_manager_id')
        return [('id', 'in', users.ids)]

    l10n_mx_edi_accountant = fields.Many2one(
        "res.users", string="Accountant",
        compute="_compute_l10n_mx_edi_accountant",
        store=True, inverse="_inverse_accountant",
        help="This user will be the responsible to review the expenses report "
             "after the manager actually approve it.")
    l10n_mx_edi_expenses_count = fields.Integer(
        'Number of Expenses', compute='_compute_expenses_count')
    l10n_mx_edi_open_expenses_count = fields.Integer(
        'Number of Open Expenses', compute='_compute_expenses_count')
    l10n_mx_edi_paid_expenses_count = fields.Integer(
        'Number of Paid Expenses', compute='_compute_expenses_count')
    l10n_mx_edi_paid_invoices_count = fields.Integer(
        'Number of Paid Invoices', compute='_compute_invoices_count')
    l10n_mx_edi_invoices_count = fields.Integer(
        'Number of Open Invoices', compute='_compute_invoices_count')
    payment_mode = fields.Selection(track_visibility='onchange')
    petty_journal_id = fields.Many2one(
        'account.journal', 'Petty Cash',
        help='Specifies the journal that will be used to make the '
             'reimbursements to employees, for expenses with type '
        '"Petty Cash"', readonly=False, states={'post': [('readonly', True)],
                                                'done': [('readonly', True)],
                                                'cancel': [('readonly', True)]}
    )
    user_id = fields.Many2one(domain=lambda self: self._get_user_domain())

    def _inverse_accountant(self):
        pass

    def _compute_display_name(self):
        res = super(HrExpenseSheet, self)._compute_display_name()
        for record in self:
            record.display_name = f'[{record.id}] {record.name}'
        return res

    def _compute_expenses_count(self):
        for sheet in self:
            paid = sheet.expense_line_ids.filtered(
                lambda exp: exp.state == 'done')
            sheet.l10n_mx_edi_expenses_count = len(sheet.expense_line_ids)
            sheet.l10n_mx_edi_paid_expenses_count = len(paid)
            sheet.l10n_mx_edi_open_expenses_count = len(
                sheet.expense_line_ids - paid)

    def _compute_invoices_count(self):
        for sheet in self:
            invoices = sheet.expense_line_ids.mapped('l10n_mx_edi_invoice_id')
            sheet.l10n_mx_edi_paid_invoices_count = len(invoices.filtered(
                lambda inv: inv.invoice_payment_state == 'paid'))
            sheet.l10n_mx_edi_invoices_count = len(invoices.filtered(
                lambda inv: inv.state in ('posted', 'draft')))

    @api.depends('employee_id', 'expense_line_ids.partner_id')
    def _compute_l10n_mx_edi_accountant(self):
        label = self.env.ref('l10n_mx_edi_hr_expense.tag_vendors')
        for sheet in self:
            employee = sheet.employee_id
            supplier = sheet.expense_line_ids.mapped(
                'partner_id.commercial_partner_id')
            company = sheet.company_id
            currency = sheet.expense_line_ids.mapped('currency_id')
            sheet.l10n_mx_edi_accountant = ((
                employee.l10n_mx_edi_accountant if len(supplier) != 1 or
                label not in supplier.category_id else (
                    supplier.accountant_company_currency_id if
                    currency == company.currency_id else
                    supplier.accountant_foreign_currency_id)) or
                (company.accountant_company_currency_id if
                 currency == company.currency_id else
                 company.accountant_foreign_currency_id))

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100,
                     name_get_uid=None):
        args = args or []
        if operator == 'ilike' and not (name or '').strip():
            domain = []
        else:
            domain = ['|', ('name', 'ilike', name), ('id', 'ilike', name)]
        sheet_ids = self._search(expression.AND([domain, args]), limit=limit,
                                 access_rights_uid=name_get_uid)
        return self.browse(sheet_ids).name_get()

    def l10n_mx_edi_accrue_expenses(self):
        for sheet in self:
            sheet.action_sheet_move_create()
            sheet.l10n_mx_edi_create_invoice()
            sheet.activity_update()

    def l10n_mx_edi_create_invoice(self):
        for sheet in self:
            expenses = sheet.expense_line_ids
            expenses.l10n_mx_edi_create_expense_invoice()
            sheet.write({'state': 'post'})
            with_cfdi = expenses.filtered('l10n_mx_edi_invoice_id')
            if not with_cfdi or all(
                    inv.invoice_payment_state == 'paid' for inv in
                    with_cfdi.mapped('l10n_mx_edi_invoice_id')):
                sheet.write({'state': 'done'})

    def action_open_invoices(self):
        return {
            'name': _('Invoices Open'),
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.expense_line_ids.mapped(
                'l10n_mx_edi_invoice_id').filtered(
                    lambda inv: inv.state in ('posted', 'draft')).ids)],
            'context': {'type': 'in_invoice',
                        'search_default_group_by_partner_id': 1},
        }

    def action_open_invoices_paid(self):
        return {
            'name': _('Invoices Paid'),
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.expense_line_ids.mapped(
                'l10n_mx_edi_invoice_id').filtered(
                    lambda inv: inv.invoice_payment_state == 'paid').ids)],
            'context': {'type': 'in_invoice',
                        'search_default_group_by_partner_id': 1},
        }

    def action_get_expenses_paid_view(self):
        self.ensure_one()
        return {
            'name': _('Expenses Paid'),
            'view_mode': 'tree,form',
            'res_model': 'hr.expense',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.expense_line_ids.filtered(
                lambda exp: exp.state == 'done').ids)],
        }

    def action_get_expenses_view(self):
        self.ensure_one()
        return {
            'name': _('Expenses'),
            'view_mode': 'tree,form',
            'res_model': 'hr.expense',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.expense_line_ids.filtered(
                lambda exp: exp.state != 'done').ids)],
        }

    def activity_update(self):
        res = super(HrExpenseSheet, self).activity_update()
        for expense_report in self.filtered(lambda sh: sh.state == 'approve'
                                            and sh.l10n_mx_edi_accountant):
            self.activity_schedule(
                'hr_expense.mail_act_expense_approval',
                user_id=expense_report.sudo().l10n_mx_edi_accountant.id)
        self.filtered(lambda hol: hol.state == 'post').activity_feedback(
            ['hr_expense.mail_act_expense_approval'])
        return res

    def approve_expense_sheets(self):
        """Temporary overwritten the method, waiting
        for https://github.com/odoo/odoo/pull/31573"""
        if not self.user_has_groups('hr_expense.group_hr_expense_user'):
            raise UserError(_(
                "Only Managers and HR Officers can approve expenses"))
        elif not self.user_has_groups('hr_expense.group_hr_expense_manager'):
            current_managers = self.employee_id.parent_id.user_id | self.employee_id.department_id.manager_id.user_id | self.employee_id.expense_manager_id  # noqa

            if self.employee_id.user_id == self.env.user:
                raise UserError(_("You cannot approve your own expenses"))

            managers = self.env['hr.department'].search([]).mapped(
                'manager_id.user_id')
            employees = self.employee_id.search([])
            parents = employees.mapped('parent_id.user_id')
            responsibles = employees.mapped('expense_manager_id.user_id')
            other_managers = managers | parents | responsibles

            if self.env.user not in current_managers | other_managers and not self.user_has_groups('l10n_mx_edi_hr_expense.allow_to_approve_exp_wo_being_responsible'): # noqa
                raise UserError(_(
                    "You can only approve your department expenses"))

        responsible_id = self.user_id.id or self.env.user.id
        self.write({'state': 'approve', 'user_id': responsible_id})
        self.activity_update()

    def refuse_sheet(self, reason):
        """Temporary overwritten the method, waiting
        for https://github.com/odoo/odoo/pull/31573"""
        if not self.user_has_groups('hr_expense.group_hr_expense_user'):
            raise UserError(
                _("Only Managers and HR Officers can approve expenses"))
        elif not self.user_has_groups('hr_expense.group_hr_expense_manager'):
            current_managers = self.employee_id.parent_id.user_id | self.employee_id.department_id.manager_id.user_id | self.employee_id.expense_manager_id  # noqa

            if self.employee_id.user_id == self.env.user:
                raise UserError(_("You cannot refuse your own expenses"))

            if self.env.user not in current_managers:
                raise UserError(_(
                    "You can only refuse your department expenses"))

        self.write({'state': 'cancel'})
        for sheet in self:
            sheet.message_post_with_view(
                'hr_expense.hr_expense_template_refuse_reason',
                values={'reason': reason, 'is_sheet': True, 'name': self.name})
        self.activity_update()

    def action_submit_sheet(self):
        limit = self.mapped('company_id').l10n_mx_expenses_amount
        act = 'l10n_mx_edi_hr_expense.mail_act_expense_approval_amount_limit'
        for expense in self.mapped('expense_line_ids').filtered(
                lambda exp: exp.total_amount_company > limit):
            users = expense.company_id.l10n_mx_edi_employee_ids.mapped(
                'user_id')
            for user in users:
                expense.activity_schedule(act, user_id=user.id)

        return super(HrExpenseSheet, self).action_submit_sheet()


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    active = fields.Boolean(
        help="In the line this will be necessary to split the expenses once"
             " they are received.", track_visibility='onchange',
        default=True
    )

    l10n_mx_edi_functionally_approved = fields.Boolean(
        "Functionally Approved", copy=False,
        help="Comply with the functional checks?", track_visibility='onchange',
        default=False, readonly=1, force_save=1
    )

    l10n_mx_edi_fiscally_approved = fields.Boolean(
        "Fiscally Approved", copy=False,
        help="Comply with the fiscal checks?", track_visibility='onchange',
        default=False, readonly=1, force_save=1
    )

    l10n_mx_edi_forced_approved = fields.Boolean(
        "Forced Approved", copy=False,
        help="This is a paid not deductible", track_visibility='onchange',
        default=False, readonly=1, force_save=1
    )

    name = fields.Char(states={'downloaded': [('readonly', False)],
                               'draft': [('readonly', False)],
                               'refused': [('readonly', False)]})
    product_id = fields.Many2one(states={'downloaded': [('readonly', False)],
                                         'draft': [('readonly', False)],
                                         'refused': [('readonly', False)]},
                                 track_visibility='onchange')
    quantity = fields.Float(states={'downloaded': [('readonly', False)],
                                    'draft': [('readonly', False)],
                                    'refused': [('readonly', False)]})
    unit_amount = fields.Float(states={'downloaded': [('readonly', False)],
                                       'draft': [('readonly', False)],
                                       'refused': [('readonly', False)]},
                               default=0.00)
    date = fields.Date(states={'downloaded': [('readonly', False)],
                               'draft': [('readonly', False)],
                               'refused': [('readonly', False)]},
                       track_visibility='onchange',
                       help="Date the payment was created in the system")
    l10n_mx_edi_uuid = fields.Text(
        "UUID", track_visibility='onchange',
        help="UUID of the xml's attached comma separated if more than one.")
    total_amount = fields.Monetary(inverse='_inverse_amount')

    l10n_mx_edi_date = fields.Date("Date (att)", track_visibility='onchange',
                                   help="Date on the CFDI attached [If 1 if "
                                        "several we will need to split them]")
    l10n_mx_edi_subtotal = fields.Float("Amount Subtotal")
    l10n_mx_edi_tax = fields.Float(
        "Tax", track_visibility='onchange')
    l10n_mx_edi_discount = fields.Float(
        "Discount", track_visibility='onchange')
    l10n_mx_edi_withhold = fields.Float(
        "Withhold", track_visibility='onchange')
    l10n_mx_edi_analysis = fields.Text(
        "Analysis", copy=False, track_visibility='onchange',
        help="See in json (and future with a fancy widget) the summary of the"
             " test run and their result [Per fiscal test]")
    l10n_mx_edi_analysis_html = fields.Html(
        "Analysis HTML", compute="_compute_analysis_html",
        track_visibility='onchange')
    l10n_mx_edi_functional_details = fields.Text(
        'Functional Details', copy=False, track_visibility="onchange",
        help="See in json (and future with a fancy widget) the summary of the"
             " test run and their result [Per functional test]")
    l10n_mx_edi_functional_details_html = fields.Html(
        "Functional", compute="_compute_functional_details_html")
    l10n_mx_edi_accountant = fields.Many2one(
        "res.users", string="Accountant",
        related="sheet_id.l10n_mx_edi_accountant",
        store=True, inverse="_inverse_accountant",
        help="This user will be the responsible to review the expenses report "
             "after the manager actually approve it.")
    l10n_mx_edi_move_id = fields.Many2one(
        'account.move', 'Journal Entry', readonly=True, force_save=1,
    )
    l10n_mx_edi_move_line_id = fields.Many2one(
        'account.move.line', 'Journal Item', readonly=True, force_save=1,
    )
    account_id = fields.Many2one(track_visibility='onchange',
                                 states={'downloaded': [('readonly', False)],
                                         'draft': [('readonly', False)],
                                         'refused': [('readonly', False)]},
                                 readonly=True)
    tax_ids = fields.Many2many(states={'downloaded': [('readonly', False)],
                                       'draft': [('readonly', False)],
                                       'refused': [('readonly', False)]},
                               readonly=True)

    def _inverse_accountant(self):
        pass

    def get_expense_errors(self):
        errors = []
        if any(expense.sheet_id for expense in self):
            errors.append(_("You cannot report twice the same line!"))
        if len(self.mapped('employee_id')) != 1:
            errors.append(_("You cannot report expenses for different "
                            "employees in the same report."))
        if any(expense.state != 'draft' for expense in self):
            errors.append(_("You can not report a line in any state different"
                            " from draft if it is in **Downloaded** state wait"
                            "for the automatic check."))
        if any(expense.state != 'draft' for expense in self):
            errors.append(_("You can not report a line in any state different"
                            " from draft if it is in **Just Downloaded** "
                            "state wait for the automatic check."))
        if not all(
                expense.l10n_mx_edi_functionally_approved for expense in self):
            errors.append(_("This expense is not functionally approved, see "
                            "errors or ask your supervisor to force the "
                            "functional exception"))
        if not all(expense.l10n_mx_edi_fiscally_approved for expense in self):
            errors.append(_("This expense looks as do not comply with the "
                            "fiscal validation, please load a valid invoice "
                            "or ask you supervisor to approve this exception, "
                            "sending a message."))
        if any(expense.state != 'draft' for expense in self):
            errors.append(_("You can not report a line in any state different"
                            " from draft if it is in **Just Downloaded** "
                            "state wait for the automatic check."))
        if any(not expense.employee_id.journal_id for expense in self
               if expense.payment_mode == 'own_account'):
            errors.append(_("You can not report a line paid by the employee "
                            "and that they do not have a journal configured."))
        if len(set(self.mapped('payment_mode'))) > 1:
            errors.append(_("You can not report lines with different payment "
                            "mode."))
        if any(expense for expense in self if not expense.payment_mode):
            errors.append(_("You can not report a line without payment mode."))
        label = self.env.ref(
            'l10n_mx_edi_hr_expense.tag_force_invoice_generation', False)
        if any(exp for exp in self if exp.l10n_mx_edi_is_to_check and
               label not in exp.partner_id.category_id):
            errors.append(_("This expense is marked to be checked but the "
                            "supplier does not have the label that forces the "
                            "invoice generation."))
        return errors

    def action_submit_expenses(self):
        errors = self.get_expense_errors()
        if errors:
            raise UserError('\n'.join(errors))
        todo = self.filtered(
            lambda x: x.payment_mode == 'own_account') or self.filtered(
                lambda x: x.payment_mode == 'company_account') or self.filtered(  # noqa
                    lambda x: x.payment_mode == 'petty_account')
        employee = self[0].employee_id
        return {
            'name': _('New Expense Report'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'hr.expense.sheet',
            'target': 'current',
            'context': {
                'default_expense_line_ids': todo.ids,
                'default_employee_id': employee.id,
                'default_name': todo[0].name if len(todo) == 1 else '',
                'default_petty_journal_id': employee.journal_ids.id if len(
                    employee.journal_ids) == 1 and todo[
                        0].payment_mode == 'petty_account' else False,
            }
        }

    def _compute_functional_details_html(self):
        for expense in self:
            expense.l10n_mx_edi_functional_details_html = self.json2qweb(
                expense.l10n_mx_edi_functional_details
            )

    def json2qweb(self, json_input=None):
        if not json_input:
            return False
        values = json.loads(json_input)
        result = {**values.get('ok', {}), **values.get('fail', {})}
        template = self.env.ref(
            'l10n_mx_edi_hr_expense.expense_checks_content')
        sorted_keys = sorted([int(k) for k in result.keys()])
        qcontext = {
            'animate': self.env.context.get('animate', True),
            'sorted_keys': sorted_keys,
            'messages': result,
            'failed': values.get('fail', {}),
            'succeeded': values.get('ok', {}),
        }
        return self.env['ir.qweb'].render(template.id, qcontext)

    def _compute_analysis_html(self):
        for expense in self:
            expense.l10n_mx_edi_analysis_html = json2html.convert(
                expense.l10n_mx_edi_analysis
            )

    l10n_mx_edi_rfc = fields.Text("Emitter")
    l10n_mx_edi_received_rfc = fields.Text("Received By")
    state = fields.Selection(
        selection_add=[
            ('downloaded', 'Just Downloaded')
        ],
        default="downloaded",
        readonly=False,
        inverse='_inverse_state',
        track_visibility='onchange',
    )
    payment_mode = fields.Selection(
        selection_add=[('petty_account',
                        'Petty Cash (Debit from the custody of the employee)'),
                       ('company_account',
                        'Company (Generate a payable for the supplier).')],
        default='company_account',
        track_visibility='onchange',
    )
    l10n_mx_edi_sat_status = fields.Selection(
        selection=[
            ('none', 'State not defined'
                     '(answer on sat not possible to manage)'),
            ('undefined', 'Not synced yet with SAT'),
            ('not_found', 'We could not find it in the SAT'),
            ('cancelled', 'Cancelled on SAT'),
            ('valid', 'Perfectly valid on SAT'),
            ('more_than_one', 'Please split in several lines there is more '
                              'than one invoice to check with SAT'),
        ],
        string='SAT status',
        help='Refers to the status of the invoice(s) inside the SAT system.',
        readonly=True,
        copy=False,
        required=True,
        track_visibility='onchange',
        default='undefined'
    )
    l10n_mx_edi_functional = fields.Selection(
        selection=[
            ('undefined', 'Not checked yet'),
            ('fail', 'Something failed, please check the message log'),
            ('ok', 'All the functional checks Ok!'),
            ('error', 'Trying to check occurred an error, check the log'),
        ],
        string='Functional status',
        help="Inform the functional status regarding other data in the system",
        readonly=True,
        copy=False,
        required=True,
        track_visibility='onchange',
        default='undefined'
    )
    email_from = fields.Char(
        track_visibility='onchange',)
    partner_id = fields.Many2one(
        "res.partner", "Supplier",
        track_visibility='onchange',
        help="Partner that generated this invoices",
        ondelete='restrict',
        compute="_compute_partner_id", store=True, inverse='_inverse_partner')
    l10n_mx_count_cfdi = fields.Integer(
        "Count CFDI's", track_visibility='onchange')
    l10n_mx_edi_invoice_id = fields.Many2one(
        'account.move', 'Invoice', help='Invoice created with this expense',
        readonly=True, copy=False)
    l10n_mx_edi_document_type = fields.Selection(
        [('in_invoice', 'Vendor Bill'), ('in_refund', 'Vendor Credit Note')],
        'Document Type', help="Save the document type in the CFDI.")
    l10n_mx_edi_is_to_check = fields.Boolean(
        'Is to check?', copy=False,
        help='If is marked, the expense wait for the CFDI with the fiscal '
        'data, and must be merged with the expense with a CFDI.')

    def create_partner_from_cfdi(self):
        partner = self.env['res.partner']
        for expense in self.filtered('l10n_mx_edi_rfc'):
            element = json.loads(expense.l10n_mx_edi_analysis)
            partner = partner.sudo().search(
                [('vat', '=', expense.l10n_mx_edi_rfc),
                 ('is_company', '=', True)], limit=1)
            if not partner:
                partner = partner.sudo().search(
                    [('vat', '=', expense.l10n_mx_edi_rfc)], limit=1)
            if not partner:
                partner = partner.create({
                    'vat': expense.l10n_mx_edi_rfc,
                    'name': element.get('invoices')[0].get('name'),
                    'zip': element.get('invoices')[0].get('address'),
                    'country_id': self.env.ref('base.mx').id,
                    'is_company': True,
                    'category_id': [(6, 0, self.env.ref('l10n_mx_edi_hr_expense.tag_expenses').ids)]  # noqa
                })
            expense.update({'partner_id': partner})

    @api.depends('l10n_mx_edi_rfc')
    def _compute_partner_id(self):
        partner = self.env['res.partner'].sudo()
        for expense in self.filtered('l10n_mx_edi_rfc'):
            # TODO; do a more complex logic, i.e.: instead take the first
            #  take the one with more invoices ore something like that.
            expense_partner = partner.search(
                [('vat', '=', expense.l10n_mx_edi_rfc),
                 ('is_company', '=', True),
                 ('vat', '!=', False)], limit=1)
            if not expense_partner:
                expense_partner = partner.search(
                    [('vat', '=', expense.l10n_mx_edi_rfc),
                     ('vat', '!=', False)], limit=1)
            expense.partner_id = expense_partner
        for expense in self - self.filtered('l10n_mx_edi_rfc'):
            expense.partner_id = expense.partner_id

    def _inverse_state(self):
        pass

    def _inverse_amount(self):
        pass

    def _inverse_partner(self):
        pass

    @api.depends('quantity', 'unit_amount', 'tax_ids', 'currency_id')
    def _compute_amount(self):
        res = super(HrExpense, self)._compute_amount()
        for expense in self.filtered('l10n_mx_edi_analysis'):
            total = json.loads(
                expense.l10n_mx_edi_analysis).get('invoices')[0].get('total')
            expense.total_amount = total
        for expense in self - self.filtered('l10n_mx_edi_analysis'):
            expense.total_amount = expense.total_amount
        return res

    @api.depends('sheet_id', 'sheet_id.account_move_id', 'sheet_id.state',
                 'l10n_mx_edi_invoice_id.state',
                 'l10n_mx_edi_invoice_id.invoice_payment_state')
    def _compute_state(self):
        for expense in self:
            if not expense.sheet_id:
                expense.state = "downloaded"
            elif expense.sheet_id.state == 'draft':
                expense.state = "draft"
            elif expense.sheet_id.state == "cancel":
                expense.state = "refused"
            elif (expense.sheet_id.state in ('done', 'post') and
                  expense.l10n_mx_edi_invoice_id and
                  expense.l10n_mx_edi_invoice_id.invoice_payment_state != 'paid'):  # noqa
                expense.state = 'approved'
            elif (expense.sheet_id.state == "done" or
                  expense.l10n_mx_edi_invoice_id.invoice_payment_state == 'paid'):  # noqa
                expense.state = "done"
            elif expense.sheet_id.state in ["approve", "post"]:
                expense.state = "approved"
            elif not expense.sheet_id.account_move_id:
                expense.state = "reported"
            else:
                expense.state = "done"

    @api.model
    def _force_create_super_employee(self):
        with Environment.manage():
            with registry(self.env.cr.dbname).cursor() as _cr:
                _env = api.Environment(_cr, SUPERUSER_ID, self.env.context)
                employee = _env['hr.employee'].with_context(
                    active_test=False).sudo().search(
                    [('user_id', '=', SUPERUSER_ID)], limit=1)
                if not employee:
                    employee = employee.create({
                        'name': 'Odoo Bot [Autocreated]',
                        'user_id': SUPERUSER_ID,
                        'work_email': '__system__@__system__.com'
                    })
                # Ensure this wired value for odoo bot employee (the user
                # is other history do not confuse here and that it is
                # active..
                employee.write({
                    'active': True,
                    'work_email': '__system__@__system__.com'})
                _cr.commit()
                return employee.id

    def ack(self):
        """Send an email, given the moment of the expense grouped by sheet when
        needed

        **context**:

        'mode': The sufix of the template to be used on xml_id
        'user': The recordset of the user which the mail will be sent (default,
                employee user).
        'email_cc': if you want cc sombody specific.
        'partner_to': recordset of the partner(s)
                      If you want to ensuere a partner receive any info.
        """
        states = [
            'downloaded',
            'draft',
            'reported',
            'approved',
            'paid',
            'refused'
        ]
        mode = self.env.context.get('mode')
        user = self.env.context.get('user')
        template = self.env.ref(
            'l10n_mx_edi_hr_expense.mail_template_expense_%s' % mode,
            raise_if_not_found=False
        )
        if mode not in states or not template:
            return
        assert template._name == 'mail.template'
        for expense in self:
            user = user or expense.employee_id.user_id
            template_values = {
                'email_to': user.login,
                'email_cc': self.env.context.get('email_cc', False),
            }
            if not user:
                _logger.error(
                    "Impossible to send any ACK from expenses if employee "
                    "incorrectly set.",
                )

            with self.env.cr.savepoint():
                mail = template.with_context(lang=user.lang).send_mail(
                    expense.id,
                    raise_exception=True,
                    email_values=template_values,
                    notif_layout='mail.mail_notification_light',
                )
            _logger.info(
                "Expenses email was sent for expense <%s> with name"
                " <%s> with id: %s",
                expense.id, expense.name, mail
            )

    def email_split(self, msg):
        """Copied from the technique used in tasks to set the the
        followers by default instead expect an expense to be followed manually
        the point is ensure the mail to is not the alias itself.
        """
        email_list = tools.email_split(
            (msg.get('to') or '') + ','
            + (msg.get('cc') or '') + ','
            + (msg.get('email_from') or ''))
        # check left-part is not already an alias
        aliases = self.env.ref(
            'hr_expense.mail_alias_expense').mapped('display_name')
        return [x for x in email_list if x.split('@')[0] not in aliases]

    @api.model
    def message_new(self, msg, custom_values=None):
        """Mail Thread Overwritten totally from hr_expense because we need some
special cases to work with:

1. If not XML attached it is a normal expense (possible but not ideal).
2. It can not fail by any mean, better if we log the failure as an expense done
   by odoo bot then fix it if possible.
3. We will try to do an action depending on the key from the mail which are.:

    'message_type', 'message_id', 'subject', 'from', 'to', 'cc', 'email_from',
    'date', 'body', 'attachments', 'author_id'`
        """
        if custom_values is None:
            custom_values = {}
        email_address = email_split(msg.get('email_from', False))[0]
        # Even an inactive employee can have things pending to declare.
        # In the approval process this will be redirected.
        employees = self.env['hr.employee'].with_context(active_test=False)
        domain = ['|', ('work_email', 'ilike', email_address),
                  ('user_id.email', 'ilike', email_address)]
        employee = employees.search(domain, limit=1)
        if not employee:
            msg['email_from'] = 'OdooBot <__system__@__system__.com>'
            employee_id = self._force_create_super_employee()
            employee = employees.browse(employee_id)

        expense_description = msg.get('subject', '')

        # Match the first occurrence of '[]' in the string and extract the
        # content inside it Example: '[foo] bar (baz)' becomes 'foo'. This is
        # potentially the product code of the product to encode on the expense.
        # If not, take the default product instead which is 'Fixed Cost'
        default_product = self.env.ref('hr_expense.product_product_fixed_cost')
        pattern = r'\[([^)]*)\]'
        product_code = re.search(pattern, expense_description)
        if product_code is None:
            product = default_product
        else:
            expense_description = expense_description.replace(
                product_code.group(), '')
            products = self.env['product.product'].search(
                [('default_code', 'ilike',
                  product_code.group(1))]) or default_product
            product = products.filtered(
                lambda p: p.default_code == product_code.group(1)) or \
                products[0]
        account = product.product_tmpl_id._get_product_accounts()['expense']

        pattern = r'[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?'
        # Match the last occurrence of a float in the string
        # Example: '[foo] 50.3 bar 34.5' becomes '34.5'.
        # This is potentially the price
        # to encode on the expense. If not, take 1.0 instead
        expense_price = re.findall(pattern, expense_description)
        # TODO: International formatting
        if not expense_price:
            price = 1.0
        else:
            price = expense_price[-1][0]
            expense_description = expense_description.replace(price, '')
            try:
                price = float(price)
            except ValueError:
                price = 1.0

        custom_values.update({
            'name': expense_description.strip(),
            'employee_id': employee.id,
            'payment_mode': employee.l10n_mx_edi_payment_mode,
            'product_id': product.id,
            'product_uom_id': product.product_uom_id.id,
            'tax_ids': [(4, tax.id, False)
                        for tax in product.supplier_taxes_id],
            'quantity': 1,
            'unit_amount': price,
            'company_id': employee.company_id.id,
            'state': 'downloaded',
            'email_from': email_address,
        })
        if account:
            custom_values['account_id'] = account.id
        expense = super(HrExpense, self).message_new(msg, custom_values)
        email_list = expense.email_split(msg)
        partner_ids = [p for p in expense._find_partner_from_emails(
            email_list, force_create=False) if p]
        expense.message_subscribe(partner_ids)
        return expense

    def l10n_mx_edi_log_error(self, message):
        self.ensure_one()
        self.message_post(body=_('Error during the process: %s') % message)

    def l10n_mx_edi_update_sat_status(self):
        url = 'https://consultaqr.facturaelectronica.sat.gob.mx/' \
              'ConsultaCFDIService.svc?wsdl'
        headers = {
            'SOAPAction': 'http://tempuri.org/IConsultaCFDIService/Consulta',
            'Content-Type': 'text/xml; charset=utf-8'}
        template = """<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:ns0="http://tempuri.org/"
 xmlns:ns1="http://schemas.xmlsoap.org/soap/envelope/"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
   <SOAP-ENV:Header/>
   <ns1:Body>
      <ns0:Consulta>
         <ns0:expresionImpresa>${data}</ns0:expresionImpresa>
      </ns0:Consulta>
   </ns1:Body>
</SOAP-ENV:Envelope>"""
        namespace = {
            'a': 'http://schemas.datacontract.org/2004/07/Sat.Cfdi.Negocio.'
                 'ConsultaCfdi.Servicio'}
        for rec in self:
            supplier_rfc = rec.l10n_mx_edi_rfc
            customer_rfc = rec.l10n_mx_edi_received_rfc
            total = float_repr(
                rec.total_amount,
                precision_digits=rec.currency_id.decimal_places
            )
            uuid = rec.l10n_mx_edi_uuid
            params = '?re=%s&amp;rr=%s&amp;tt=%s&amp;id=%s' % (
                html_escape(html_escape(supplier_rfc.strip() or '')),
                html_escape(html_escape(customer_rfc.strip() or '')),
                total or 0.0, uuid or '')
            soap_env = template.format(data=params)
            try:
                soap_xml = requests.post(url, data=soap_env, headers=headers)
                response = fromstring(soap_xml.text)
                status = response.xpath('//a:Estado', namespaces=namespace)
            except Exception as e:
                rec.l10n_mx_edi_log_error(str(e))
                continue
            rec.l10n_mx_edi_sat_status = CFDI_SAT_QR_STATE.get(
                status[0] if status else '', 'none')

    def check_fiscal_status(self):
        atts = self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
        ])

        # In order to discard all CFDI at once that will not be checked and
        # subtract them from the recordset to avoid walk for all of them
        # one by one when heavy check comes forward.
        invoices = atts
        invoices_cache = {}
        for att in atts:
            cfdi = att.l10n_mx_edi_is_cfdi33()
            if not cfdi:
                invoices -= att
                continue
            cfdi = self.env['account.move'].l10n_mx_edi_get_tfd_etree(cfdi)
            if cfdi is None:
                invoices -= att
                continue
            uuid = cfdi.get('UUID')
            invoices_cache[att.id] = uuid
        self.l10n_mx_count_cfdi = len(invoices_cache.keys())
        expenses = self.split_expense()
        dict_document_type = {'I': 'in_invoice', 'E': 'in_refund'}
        for expense in expenses:
            # Now that I have a clear domain of which attachments to check I
            # will read the content to jsonify a compound of invoices, now
            # the variable atts contains only the attachments that are actual
            # invoices and can be parsed.
            res = []
            currency = expense.currency_id
            for att in invoices.sudo().filtered(
                    lambda inv: inv.res_id == expense.id):
                datas = base64.b64decode(att.datas).replace(
                    b'xmlns:schemaLocation', b'xsi:schemaLocation')
                invoice = objectify.fromstring(datas)
                currency = currency.search(
                    [('name', '=', invoice.get('Moneda', ''))], limit=1)
                cfdi_related = []
                relation_type = ''
                if hasattr(invoice, 'CfdiRelacionados'):
                    relation_type = invoice.CfdiRelacionados.get(
                        'TipoRelacion')
                    for doc in invoice.CfdiRelacionados.CfdiRelacionado:
                        cfdi_related.append(doc.get('UUID'))
                document_type = invoice.get('TipoDeComprobante', ' ')
                data = {
                    'cfdi_related': cfdi_related,
                    'relation_type': relation_type,
                    'id': att.id,
                    'date': invoice.get('Fecha', ' ').replace('T', ' '),
                    'document_type': document_type,
                    'number': invoice.get('Folio', ''),
                    'serie': invoice.get('Serie', ''),
                    'address': invoice.get('LugarExpedicion', ' '),
                    'payment': invoice.get('MetodoPago', ' '),
                    'payment_conditions': invoice.get('CondicionesDePago', ''),
                    'payment_way': invoice.get('FormaPago', ''),
                    'name': invoice.Emisor.get('Nombre', ' '),
                    'fp': invoice.Emisor.get('RegimenFiscal', ' '),
                    'sent_by': invoice.Emisor.get('Rfc', ' '),
                    'received_by': invoice.Receptor.get('Rfc', ' '),
                    'subtotal': float(invoice.get('SubTotal', '0.0')),
                    'discount': float(invoice.get('Descuento', '0.0')),
                    'tax': 0.0,
                    'withhold': 0.0,
                    'currency': invoice.get('Moneda', ''),
                    'total': float(invoice.get('Total', 0.00)),
                    'use_cfdi': invoice.Receptor.get('UsoCFDI', ''),
                    'uuid': invoices_cache.get(att.id),
                }
                if hasattr(invoice, 'Impuestos'):
                    taxes = invoice.Impuestos
                    total_ieps = 0
                    for tax in taxes.Traslados.Traslado if hasattr(
                            taxes, 'Traslados') else []:
                        if tax.get('Impuesto') != '003':
                            continue
                        total_ieps += float(tax.get('Importe'))
                    data.update({
                        'tax': float(invoice.Impuestos.get(
                            'TotalImpuestosTrasladados', '0.0')),
                        'withhold': float(invoice.Impuestos.get(
                            'TotalImpuestosRetenidos', '0.0')),
                        'total_ieps': total_ieps,
                    })
                lines = []
                for line in invoice.Conceptos.Concepto:
                    lines.append({
                        'description': line.get('Descripcion', ' '),
                        'sat_code': line.get('ClaveProdServ', ' '),
                        'no_id': line.get('NoIdentificacion', ' '),
                        'uom_code': line.get('ClaveUnidad', ' '),
                        'amount': float(line.get('Importe', '0.0')),
                        'qty': float(line.get('Cantidad', '0.0')),
                        'price_unit': float(line.get('ValorUnitario', '0.0')),
                        'discount': float(line.get('Descuento', '0.0')),
                        'taxes': self._get_taxes_line(line),
                    })

                data.update({'lines': lines})
                data.update({'local_taxes': expense.get_local_taxes(invoice)})
                res.append(data)
            # Now I save such analysis in a json in order to render it
            # properly in the expenses view.
            if not res:
                _logger.info(
                    'Nothing fiscally valid on expense: %s' % expense.id)
                return {}
            total = sum([i['total'] for i in res])
            subtotal = sum([i['subtotal'] for i in res])
            taxes = sum([i['tax'] for i in res])
            withhold = sum([i['withhold'] for i in res])
            discount = sum([i['discount'] for i in res])
            uuid = ', '.join([i['uuid'] for i in res])
            rfc = ', '.join([i['sent_by'] for i in res])
            received_rfc = ', '.join([i['received_by'] for i in res])
            date = [i['date'] for i in res][0]
            references = ', '.join(['%s/%s' % (i['serie'], i['number'])
                                    for i in res])
            expense.update({
                'currency_id': currency.id,
                'l10n_mx_edi_analysis': json.dumps({
                    'invoices': res,
                    'total': total,
                    'subtotal': subtotal,
                    'taxes': taxes,
                    'withhold': taxes,
                }),
                'reference': references,
                'l10n_mx_edi_date': date,
                'l10n_mx_edi_uuid': uuid,
                'l10n_mx_edi_subtotal': subtotal,
                'total_amount': total,
                'l10n_mx_edi_tax': taxes,
                'l10n_mx_edi_discount': discount,
                'l10n_mx_edi_withhold': withhold,
                'l10n_mx_edi_rfc': rfc,
                'l10n_mx_edi_received_rfc': received_rfc,
                'l10n_mx_count_cfdi': len(res),
                'l10n_mx_edi_document_type': dict_document_type.get(
                    document_type, False),
            })
            if not expense.company_id:
                company = self.env['res.company'].search([
                    ('vat', '=', invoice.Receptor.get('Rfc', ' '))], limit=1)
                expense.company_id = company.id
            expense.l10n_mx_edi_update_sat_status()
            # TODO: Document better? this is a design decision, If partner do
            #  not exists and he/she is sending a valid CFID this should be
            #  created (delegate the defensive layer to the method itself).
            expense.create_partner_from_cfdi()
            expense.l10n_mx_edi_fiscally_approved = True
            expense.split_concepts()

    def split_concepts(self):
        """The airlines some cases has the next case:
            Concept: {Importe: 4497.00, Taxes: {0%: 1125.00, 16%: 3372.00}}
        In this case, must be splitted in two lines, one by each tax"""
        self.ensure_one()
        airline = self.env.ref('l10n_mx_edi_hr_expense.tag_is_airline')
        if airline not in self.partner_id.category_id:
            return False
        analysis = json.loads(self.l10n_mx_edi_analysis)
        invoice = analysis.get('invoices')[0]
        lines = invoice.get('lines')
        new_lines = []
        for concept in lines:
            if len(concept.get('taxes')) <= 1:
                new_lines.append(concept)
                continue
            for tax in concept.get('taxes'):
                line = concept.copy()
                line['qty'] = 1
                line['price_unit'] = tax.get('base')
                line['taxes'] = [tax]
                new_lines.append(line)
        invoice['lines'] = new_lines
        analysis['invoices'] = [invoice]
        self.l10n_mx_edi_analysis = json.dumps(analysis)
        return True

    def _get_taxes_line(self, line):
        if not hasattr(line, 'Impuestos'):
            return []
        taxes_line = []
        taxes = line.Impuestos
        for tax in taxes.Traslados.Traslado if hasattr(
                taxes, 'Traslados') else []:
            taxes_line.append({
                'type': 'tax',
                'tax': tax.get('Impuesto', ''),
                'rate': float(tax.get('TasaOCuota', '0.0')),
                'base': float(tax.get('Base', 0)),
            })
        for tax in taxes.Retenciones.Retencion if hasattr(
                taxes, 'Retenciones') else []:
            if float_is_zero(float(tax.get('TasaOCuota', '')),
                             precision_digits=6):
                continue
            taxes_line.append({
                'type': 'ret',
                'tax': tax.get('Impuesto', ''),
                'rate': float(tax.get('TasaOCuota', '')),
            })
        return taxes_line

    def functional1(self):
        """Check if the invoice is generated for this company"""
        return self.l10n_mx_edi_received_rfc == self.company_id.partner_id.vat

    def functional2(self):
        # TODO: This check will be really time consuming find a solution.
        # For suppliers mostly
        return True

    def functional3(self):
        """Check if somebody else did not try to generate an expense with this
        uuid but such invoice has not been posted yet"""
        uuids = self.mapped('l10n_mx_edi_uuid')
        return not bool(self.sudo().search(
            [('l10n_mx_edi_uuid', 'in', uuids), ('id', 'not in', self.ids),
             ('l10n_mx_edi_uuid', '!=', False)]))

    def functional4(self):
        return self.partner_id

    def functional5(self):
        return True

    def functional6(self):
        return True

    def functional7(self):
        return True

    def functional8(self):
        return bool(self.mapped('l10n_mx_edi_uuid'))

    def functional9(self):
        """Check if somebody else did generate an invoice previously with this
        reference for this partner but such invoice has not been posted yet"""
        references = self.mapped('reference')
        partners = self.mapped('partner_id').ids
        return not bool(self.env['account.move'].sudo().search(
            [('ref', 'in', references),
             ('id', 'not in', self.ids),
             ('ref', '!=', False),
             ('commercial_partner_id', 'not in', partners)]))

    def functional10(self):
        return not self.mapped('l10n_mx_count_cfdi')[0] > 1

    def functional11(self):
        payment = json.loads(
            self.l10n_mx_edi_analysis).get('invoices')[0].get('payment')
        if payment != 'PPD' and self.payment_mode == 'company_account':
            return False
        return True

    def functional12(self):
        payment = json.loads(
            self.l10n_mx_edi_analysis).get('invoices')[0].get('payment_way')
        if self.payment_mode == 'company_account' and payment != '99':
            return False
        return True

    def functional13(self):
        if self.l10n_mx_edi_sat_status != 'valid':
            return False
        return True

    def functional14(self):
        """Check if all the taxes are found in this company"""
        # TODO improve to check only one time, not by line
        invoice = json.loads(self.l10n_mx_edi_analysis).get('invoices')
        for line in invoice[0].get('lines', []):
            for tax in line['taxes']:
                if tax['tax'] != '003' and not self.l10n_mx_edi_get_tax(tax):
                    return False
        return True

    def functional15(self):
        """Check that the employee has a journal"""
        if not self.employee_id.journal_id and self.payment_mode in [
                'own_account', 'petty_account']:
            return False
        return True

    def functional16(self):
        """Checking that if the CFDI is a refund, the expense is paid by
        the company"""
        document = self.l10n_mx_edi_document_type
        if self.payment_mode != 'company_account' and document == 'in_refund':
            return False
        return True

    def functional17(self):
        """Checking that if the CFDI is a refund, the CFDI related is found"""
        document_type = self.l10n_mx_edi_document_type
        if document_type != 'in_refund':
            return True
        invoice = self.env['account.move']
        data = json.loads(self.l10n_mx_edi_analysis).get('invoices')[0]
        for cfdi in data['cfdi_related']:
            if not invoice.search([
                    ('partner_id', '=', self.partner_id.id),
                    ('l10n_mx_edi_cfdi_name', '!=', False),
                    ('type', '=', 'in_invoice')]).filtered(
                        lambda inv: inv.l10n_mx_edi_cfdi_uuid == cfdi) and not self.search(  # noqa
                            [('l10n_mx_edi_uuid', '=', cfdi),
                             ('partner_id', '=', self.partner_id.id)],
                            limit=1):
                return False
        return True

    def functional18(self):
        """Checking that if the CFDI is a refund, the node CfdiRelacionado is
        found"""
        data = json.loads(
            self.l10n_mx_edi_analysis).get('invoices')[0]
        document_type = self.l10n_mx_edi_document_type
        if document_type == 'in_refund' and not data['cfdi_related']:
            return False
        return True

    def functional19(self):
        """If the CFDI have local taxes complement, verify that the taxes are
        found."""
        data = json.loads(
            self.l10n_mx_edi_analysis).get('invoices')[0]
        if not data.get('local_taxes'):
            return True
        for tax in data['local_taxes']:
            if tax['tax'].upper() in self._get_taxes_to_omit():
                continue
            local = self.l10n_mx_edi_get_local_tax(tax)
            if not local:
                return False
        return True

    def functional20(self):
        """If the CFDI have local taxes complement, verify that the taxes are
        found and the account is configured."""
        data = json.loads(
            self.l10n_mx_edi_analysis).get('invoices')[0]
        if not data.get('local_taxes'):
            return True
        if not self.functional19():
            return False
        for tax in data['local_taxes']:
            if tax['tax'].upper() in self._get_taxes_to_omit():
                continue
            local = self.l10n_mx_edi_get_local_tax(tax)
            if local and not local.account_id:
                return False
        return True

    @staticmethod
    def _remove_method(element):
        """check method is not serializable"""
        element.pop('check')
        return element

    def _render_email_check(self, result):
        """If something fail (which frequently will not be all in or all out
        prepare a proper output in order to deliver a readable message for the
        user

        :params: result Json with all errors that not passed the check
                        'ok': {code: {'title': 'Subject',
                                      'message', 'Message'}
                        'fail': {code: {'title': 'Subject',
                                        'message', 'Message'}
        """
        ok = {k: self._remove_method(v) for (k, v)
              in self.functional_errors().items() if k not in result}
        fail = {k: self._remove_method(v) for (k, v) in result.items()}
        return json.dumps({"ok": ok, "fail": fail}, skipkeys='check')

    def check_functional(self):
        # TODO: maybe all in a try to catch any programming error?
        if not self.l10n_mx_edi_analysis or \
                not json.loads(self.l10n_mx_edi_analysis).get('invoices'):
            self.sudo().message_post(
                body=_("This expense is not possible to verify functionally "
                       "because there is not CFDI associated yet, add the xml "
                       "or ask for extra permissions to propose as an "
                       "expense."))
            return
        errors = self.functional_errors()
        result = errors.copy()
        for error in errors:
            if not errors[error].get('check')():
                continue
            result.pop(error)
        message = self._render_email_check(result)
        self.write({'l10n_mx_edi_functional': 'fail' if result else 'ok',
                    'l10n_mx_edi_functional_details': ''.join(message),
                    'l10n_mx_edi_functionally_approved': bool(not result)})
        return errors

    def functional_errors(self):
        return {
            1: {
                "title": _("Incorrect RFC"),
                "title_ok": _("Correct RFC"),
                "message": _(
                    "The RFC of this invoice is not for this company, maybe "
                    "your supplier made a mistake generating the CFDI of it "
                    "simply was sent by mistake."),
                "message_ok": _("The RFC used on this CFDI is the one on "
                                "this company"),
                "check": self.functional1,
            },
            2: {
                # TODO: If not UUID this must fail!
                "title": _("UUID Duplicated on invoices"),
                "title_ok": _("New UUID"),
                "message": _("The XML UUID belongs to other invoice already "
                             "loaded on the system."),
                "message_ok": _("No other invoice with this uuid has been "
                                "declared in the system"),
                "check": self.functional2,
            },
            3: {
                "title": _("UUID Duplicated on expenses"),
                "title_ok": _("UUID Without declaration"),
                "message": _("The XML UUID belongs to other expense already "
                             "loaded on the system."),
                "message_ok": _("Neither you or somebody else try to declare "
                                "this UUID as expenses before."),
                "check": self.functional3,
            },
            4: {
                "title": _("We never bought to this partner."),
                "title_ok": _("This vendor has been used  before"),
                "message": _("The administrative team will need to check if "
                             "invoices for this vendor are valid, and if we "
                             "need to pay something to them this will need "
                             "further communication to have the payment "
                             "information."),
                "message_ok": _("We have old invoices from this vendor, stay"
                                "in touch if we need something extra."),
                "check": self.functional4,
            },
            5: {
                "title": _("Currency Disabled"),
                "title_ok": _("Currency Active"),
                "message": _("The currency in the XML was not found or is "
                             "disabled"),
                "message_ok": _("The currency declared in the CFDI is valid "
                                "and is configured properly"),
                "check": self.functional5,
            },
            6: {
                "title": _("Not in the period"),
                "title_ok": _("Date Valid in period"),
                "message": _(
                    "The date on the CFDI is not on this period, this will "
                    "need and extra approval of your expense"),
                "message_ok": _("It is inside the safety period (current "
                                "period or max 5 days at the beginning of the "
                                "next)"),
                "check": self.functional6,
            },
            7: {
                "title": _("Company Address do not match"),
                "title_ok": _("Address looks Ok"),
                "message": _(
                    "The zip code used in the invoice is not the same we have"
                    " in in the company or in the offices (invoice address in"
                    " the contacts of the company)"),
                "message_ok": _("We reviewed if the zip code of the receiver "
                                "company is the same than this company"),
                "check": self.functional7,
            },
            8: {
                "title": _("It is not deductible."),
                "title_ok": _("This has a valid invoice"),
                "message": _("This expense is not deductible, it looks like "
                             "an expense without valid CFDI in the invoice"),
                "message_ok": _("I checked if there is a valid xml in the "
                                "expense attached"),
                "check": self.functional8,
            },
            9: {
                "title": _("This invoice looks duplicated"),
                "title_ok": _("Invoice reference unique"),
                "message": _("This invoice reference was loaded for this "
                             "partner invoice reference belongs to other "
                             "invoice of the same partner."),
                "message_ok": _("The reference (folio/serie) is first time we "
                                "see it in this system"),
                "check": self.functional9,
            },
            10: {
                "title": _("More than 1 CFDI"),
                "title_ok": _("Only 1 CFDI"),
                "message": _("It looks like you tried to create an expense "
                             "with more than 1 cfdi, please send 1 email per "
                             "cfdi or split them manually throught odoo"),
                "message_ok": _("Ok"),
                "check": self.functional10,
            },
            11: {
                "title": _("Payment method is not PPD to be paid by us"),
                "title_ok": _("Payment Method is PPD and will be paid by us "
                              "or PUE and was paid by the employee"),
                "message": _("It looks like this expense must be paid by the "
                             "company but our policy is that this must be PPD "
                             "in order to be paid as a payable after "
                             "approval or this was paid by the employee and"
                             " is a mistake, change the payment mode and try "
                             "again to check functionally (clicking on the "
                             "button)"),
                "message_ok": _("Payment method is Ok!"),
                "check": self.functional11,
            },
            12: {
                "title": _("Payment way is not '99' to be paid by us"),
                "title_ok": _("Payment way is '99' and will be paid by us"),
                "message": _("It looks like this expense must be paid by the "
                             "company but our policy is that the payment way "
                             "must be '99' in order to be paid as a payable "
                             "after approval or this was paid by the employee "
                             "and is a mistake, change the payment mode and "
                             "try again to check functionally (clicking on "
                             "the button)"),
                "message_ok": _("Payment way is Ok!"),
                "check": self.functional12,
            },
            13: {
                "title": _("CFDI is not valid in the SAT"),
                "title_ok": _("CFDI is valid in the SAT"),
                "message": _("It looks like the CFDI attached is not "
                             "registered in the SAT system or is cancelled."),
                "message_ok": _("SAT status Ok!"),
                "check": self.functional13,
            },
            14: {
                "title": _("Taxes in the CFDI not found"),
                "title_ok": _("Taxes in the CFDI found!"),
                "message": _("The taxes in the XML was not found or are "
                             "disabled"),
                "message_ok": _("The taxes declared in the CFDI are valid "
                                "and are configured properly"),
                "check": self.functional14,
            },
            15: {
                "title": _("Journal not defined for the employee"),
                "title_ok": _("Journal defined for the employee!"),
                "message": _("The journal in the employee is required for "
                             "expenses paid for the employee or with petty "
                             "cash."),
                "message_ok": _("This expense was paid for the employee or "
                                "with petty cash and the journal is correctly "
                                "configured."),
                "check": self.functional15,
            },
            16: {
                "title": _("The CFDI is a refund and not be paid by us"),
                "title_ok": _("The CFDI is a refund and be paid by us!"),
                "message": _("It looks like you tried to create an expense "
                             "for a refund, and in that case must be paid "
                             "by the company."),
                "message_ok": _("It looks like you tried to create an expense "
                                "for a refund, and is paid by the company."),
                "check": self.functional16,
            },
            17: {
                "title": _("The CFDI is a refund, and the CFDI related is not "
                           "found"),
                "title_ok": _("The CFDI is a refund, and the CFDI related is "
                              "found!"),
                "message": _("It looks like you tried to create an expense "
                             "for a refund, but the CFDI related is not found."
                             " First create the invoice and after the refund."
                             ),
                "message_ok": _("The CFDI is a refund and the CFDI related is "
                                "found in the instance."),
                "check": self.functional17,
            },
            18: {
                "title": _("The CFDI is a refund, and the node "
                           "'CfdiRelacionados' is not found"),
                "title_ok": _("The CFDI is a refund, and the node "
                              "'CfdiRelacionados' is found"),
                "message": _("It looks like you tried to create an expense "
                             "for a refund, but the node 'CfdiRelacionados' "
                             "is not found."),
                "message_ok": _("It looks like you tried to create an expense "
                                "for a refund and the node "
                                "'CfdiRelacionados' in the CFDI is found."),
                "check": self.functional18,
            },
            19: {
                "title": _(
                    "The CFDI have Local Taxes and that are not found"),
                "title_ok": _("The CFDI have Local Taxes and that are found"),
                "message": _("It looks like the CFDI have Local Taxes "
                             "complement and some of that taxes are not "
                             "found."),
                "message_ok": _("It looks like the CFDI have Local Taxes "
                                "complement and that taxes are found."),
                "check": self.functional19,
            },
            20: {
                "title": _(
                    "The CFDI have Local Taxes and that are found but is "
                    "missing the account in the tax"),
                "title_ok": _("The CFDI have Local Taxes, the taxes are found "
                              "and are properly configured"),
                "message": _("It looks like the CFDI have Local Taxes "
                             "complement, the taxes are found but the account "
                             "is missing in the tax."),
                "message_ok": _("It looks like the CFDI have Local Taxes "
                                "complement, the taxes are found and the "
                                "account is properly in the tax."),
                "check": self.functional20,
            },
        }

    def force_functional(self):
        for exp in self:
            if not self.env.user.has_group(
                    'l10n_mx_edi_hr_expense.force_expense'):
                raise UserError(_("You can not force to approve an expense "
                                  "by any mean if you do not belong to the "
                                  "proper group"))
            exp.write({'l10n_mx_edi_functionally_approved': True})
            exp.message_post(body=_('Functionally Approved was forced'))

    def force_fiscal(self):
        for exp in self:
            if not self.env.user.has_group(
                    'l10n_mx_edi_hr_expense.force_expense'):
                raise UserError(_("You can not force to approve an expense "
                                  "by any mean if you do not belong to the "
                                  "proper group"))
            exp.write({'l10n_mx_edi_fiscally_approved': True})
            exp.message_post(body=_('Fiscally Approved was forced'))

    def force_approved(self):
        for exp in self.filtered(
                lambda e: e.payment_mode != 'company_account'):
            exp.write({
                'l10n_mx_edi_functionally_approved': True,
                'l10n_mx_edi_fiscally_approved': True,
                'l10n_mx_edi_forced_approved': True,
            })
            exp.message_post(body=_('Approved was forced'))

    def action_open_invoices(self):
        self.ensure_one()
        return {
            'name': _('Invoices'),
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.mapped(
                'l10n_mx_edi_invoice_id').ids)],
            'context': {
                'type': 'in_invoice',
            }
        }

    def l10n_mx_edi_create_expense_invoice(self):
        payment = self.env['account.payment.register']
        expenses = self.filtered(
            lambda e: e.l10n_mx_edi_functionally_approved and
            e.l10n_mx_edi_fiscally_approved and e.l10n_mx_edi_analysis)
        label = self.env.ref(
            'l10n_mx_edi_hr_expense.tag_force_invoice_generation', False)
        label_draft = self.env.ref('l10n_mx_edi_hr_expense.tag_invoice_draft')
        expenses_forced = self.filtered(
            lambda e: e.l10n_mx_edi_functionally_approved and
            e.l10n_mx_edi_fiscally_approved and not e.l10n_mx_edi_analysis and
            label in e.partner_id.category_id)
        expenses_forced.l10n_mx_edi_create_invoice_wh_cfdi()
        to_omit = (expenses + expenses_forced).filtered(
            lambda exp: exp.l10n_mx_edi_invoice_id.state and
            exp.l10n_mx_edi_invoice_id.state != 'cancel')
        for exp in to_omit:
            exp.message_post(body=_(
                'This expense already have an invoice related.'))
        for exp in expenses - to_omit:
            invoices = json.loads(exp.l10n_mx_edi_analysis).get('invoices')
            if not invoices:
                continue
            inv = invoices[0]
            data = exp.l10n_mx_edi_get_invoice_data(inv)
            if not data.get('company_id'):
                data.update({'company_id': exp.company_id.id})
            invoice = self.env['account.move'].sudo().create(data)
            invoice.with_context(
                check_move_validity=False)._onchange_invoice_date()
            for tax in inv.get('local_taxes'):
                if tax['tax'].upper() in self._get_taxes_to_omit():
                    nl_data = exp.create_extra_line_local_taxes(tax)
                    nl_data.update({'invoice_id': invoice.id})
                    invoice.invoice_line_ids.create(nl_data)
                    continue
                local = self.l10n_mx_edi_get_local_tax(tax)
                invoice.tax_line_ids.create({
                    'account_id': local.account_id.id,
                    'name': tax['tax'],
                    'amount': tax['amount'] * (
                        -1 if tax['type'] == 'ret' else 1),
                    'invoice_id': invoice.id,
                })
            attachments = []
            cfdi = exp.l10n_mx_edi_get_cfdi()
            for att in cfdi + exp.get_pdf_expenses():
                attachments.append(att.copy({
                    'res_model': 'account.move',
                    'res_id': invoice.id,
                }).id)
            invoice.l10n_mx_edi_cfdi_name = cfdi.name
            exp.l10n_mx_edi_invoice_id = invoice.id
            invoice.l10n_mx_edi_expense_id = exp.id
            invoice.with_context(no_new_invoice=True).message_post_with_view(
                'mail.message_origin_link',
                values={'self': invoice, 'origin': exp},
                subtype_id=self.env.ref('mail.mt_note').id,
                attachment_ids=[(6, 0, attachments)])
            if label_draft in invoice.partner_id.category_id:
                continue
            invoice.with_context({}).action_post()
            exp.l10n_mx_edi_move_id = invoice.id
            invoice.l10n_mx_edi_update_sat_status()
            petty_cash = exp.sheet_id.petty_journal_id
            if exp.payment_mode == 'company_account' or (
                    exp.payment_mode == 'petty_account' and not petty_cash):
                continue
            ctx = {'active_model': 'account.move',
                   'active_ids': invoice.ids}
            journal = exp.employee_id.journal_id\
                if exp.payment_mode == 'own_account' else petty_cash
            payment_method = journal.outbound_payment_method_ids
            payment.with_context(ctx).sudo().create({
                'payment_date': invoice.date_invoice,
                'payment_method_id': payment_method[
                    0].id if payment_method else False,
                'journal_id': journal.id,
                'communication': exp.name,
                'amount': invoice.amount_total,
            }).create_payments()
        return True

    def _get_taxes_to_omit(self):
        """Some taxes are not found in the system, but is correct, because that
        taxes should be adds in the invoice like expenses.
        To make dynamic this, could be add an system parameter with the name:
            l10n_mx_taxes_for_expense, and the value set the taxes name,
        and if are many taxes, split the names by ','"""
        taxes = self.env['ir.config_parameter'].sudo().get_param(
            'l10n_mx_taxes_for_expense', '')
        return taxes.split(',')

    def create_extra_line_local_taxes(self, tax):
        self.ensure_one()
        ieps = self.env.ref(
            'l10n_mx_edi_hr_expense.product_product_ieps', False) if 'IEPS' in tax['tax'].upper() else False  # noqa
        account = ieps.product_tmpl_id.get_product_accounts()[
            'expense'].id if ieps else self.account_id.id
        return{
            'product_id': ieps.id if ieps else self.product_id.id,
            'account_id': account,
            'name': tax['tax'].upper(),
            'quantity': 1,
            'product_uom_id': ieps.product_uom_id.id if ieps else self.product_uom_id.id,  # noqa
            'price_unit': tax['amount'],
            'analytic_account_id': self.analytic_account_id.id,
            'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
        }

    def l10n_mx_edi_get_invoice_data(self, inv):
        invoice = self.env['account.move']
        prod = self.env['product.product']
        sat_code = self.env['l10n_mx_edi.product.sat.code']
        acc_pay_term = self.env['account.payment.term']
        uom = self.env['uom.uom']

        document_type = self.l10n_mx_edi_document_type
        journal = invoice.with_context(
            default_type=document_type)._get_default_journal()
        account = self.account_id.id or (
            journal.default_credit_account_id.id if document_type in (
                'out_invoice', 'in_refund') else
            journal.default_debit_account_id.id)
        invoice_line_ids = []
        tax_global = self._get_tax_global()
        label = self.env.ref('l10n_mx_edi_hr_expense.tag_force_invoice_total')
        for line in inv.get('lines', []):
            no_id = line['no_id']
            self._cr.execute(
                """SELECT pp.id
                FROM product_product as pp
                INNER JOIN product_template as pt ON pp.product_tmpl_id = pt.id
                WHERE pp.default_code ILIKE %s OR pt.name ILIKE %s
                LIMIT 1""", (no_id, line['description'])
            )
            res = self._cr.dictfetchone()
            if not res:
                no_id = no_id.replace('-', '%')
                self._cr.execute(
                    """SELECT pp.id
                    FROM product_product as pp
                    INNER JOIN product_template as pt ON pp.product_tmpl_id = pt.id
                    WHERE pp.default_code ILIKE %s
                    LIMIT 1""", (no_id, ))  # noqa
                res = self._cr.dictfetchone()
            product = res.get('id') if res else self.product_id.id
            account = prod.browse(
                product).product_tmpl_id.get_product_accounts()[
                    'expense'].id if res else account
            amount = line['amount']
            discount = (line['discount'] / amount) * 100 if line[
                'discount'] and amount else 0.0

            code_sat = sat_code.search([
                ('code', '=', line['uom_code'])], limit=1)
            uom_id = uom.search([
                ('l10n_mx_edi_code_sat_id', '=', code_sat.id)], limit=1)

            line_taxes = []
            taxes = tax_global or line['taxes']
            for tax in taxes:
                if tax['tax'] == '003':
                    continue
                line_taxes.append(self.l10n_mx_edi_get_tax(tax, product))
            if len(line_taxes) >= 1:
                line_taxes = self.l10n_mx_edi_get_tax_group(line_taxes)

            qty = line['qty']
            price = line['price_unit']
            total_line = line['amount']
            if label in self.partner_id.category_id and float_compare(
                    total_line, qty * price, precision_digits=2) != 0:
                price = total_line / qty
            if line['sat_code'] in self._get_fuel_codes() and len(
                    line['taxes']) == 1:
                qty = 1.0
                base = sum([t.get('base', 0) for t in line['taxes']])
                invoice_line_ids.append((0, 0, {
                    'account_id': account,
                    'name': _('FUEL - IEPS'),
                    'quantity': 1,
                    'product_uom_id': uom_id.id,
                    'price_unit': line['amount'] - base
                }))
                price = base

            invoice_line_ids.append((0, 0, {
                'product_id': product,
                'account_id': account,
                'name': line['description'],
                'quantity': qty,
                'product_uom_id': uom_id.id,
                'tax_ids': [(6, 0, line_taxes)],
                'price_unit': price,
                'discount': discount,
                'analytic_account_id': self.analytic_account_id.id,
                'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
            }))
        if inv.get('total_ieps'):
            product_ieps = self.env.ref(
                'l10n_mx_edi_hr_expense.product_product_ieps', False)
            account = product_ieps.product_tmpl_id.get_product_accounts()[
                'expense'].id if product_ieps else account
            invoice_line_ids.append((0, 0, {
                'product_id': product_ieps.id or False,
                'account_id': account,
                'name': product_ieps.name or 'IEPS',
                'quantity': 1,
                'product_uom_id': product_ieps.product_uom_id.id or False,
                'price_unit': inv['total_ieps'],
                'analytic_account_id': self.analytic_account_id.id,
                'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
            }))

        payment_method = self.env['l10n_mx_edi.payment.method'].search(
            [('code', '=', inv['payment_way'])], limit=1)
        acc_pay_term = acc_pay_term.search([
            ('name', '=', inv['payment_conditions'])], limit=1)
        acc_pay_term = (
            self.partner_id.property_supplier_invoice_payment_term_id
            if not acc_pay_term and inv['payment'] in (
                'PPD', False) else acc_pay_term)
        cfdi_origin = ''
        if inv.get('relation_type'):
            cfdi_origin = '%s|%s' % (inv['relation_type'],
                                     ','.join(inv['cfdi_related']))
        return {
            'partner_id': self.partner_id.id,
            'ref': f'{inv["serie"]}{inv["number"]}',
            'invoice_payment_term_id': acc_pay_term.id,
            'l10n_mx_edi_payment_method_id': payment_method.id,
            'l10n_mx_edi_usage': inv['use_cfdi'],
            'date_invoice': self.l10n_mx_edi_date,
            'date': self.date,
            'currency_id': self.currency_id.id,
            'invoice_line_ids': invoice_line_ids,
            'type': document_type,
            'journal_id': journal.id,
            'l10n_mx_edi_origin': cfdi_origin,
        }

    def l10n_mx_edi_get_tax(self, tax, product_id=False):
        if tax['tax'] == '003':
            return False
        tag_codes = {
            '001': self.env.ref('l10n_mx.tag_isr').ids,
            '002': self.env.ref('l10n_mx.tag_iva').ids,
            '003': self.env.ref('l10n_mx.tag_ieps').ids}
        rate = float_round(tax['rate'] * 100, 4)
        if tax['type'] == 'ret':
            rate = rate * -1
        domain = [('invoice_repartition_line_ids.tag_ids', 'in',
                   tag_codes.get(tax['tax'])),
                  ('type_tax_use', '=', 'purchase'),
                  ('amount', '=', rate)]
        if tax['type'] == 'ret' and rate <= -10.66 and rate >= -10.67:
            domain[-1] = ('|')
            domain.append(('amount', '=', rate))
            domain.append('&')
            domain.append(('amount', '<=', -10.66))
            domain.append(('amount', '>=', -10.67))
        elif tax['type'] == 'ret':
            domain.append(('amount', '<', 0))
        taxes_found = self.env['account.tax'].search(domain)
        if len(taxes_found) <= 1:
            return taxes_found.id

        # If there were multiple taxes found, but some of them is configured
        # in the product, take it
        product = self.env['product.product'].browse(product_id)
        product_taxes = taxes_found & product.supplier_taxes_id
        return product_taxes[0].id if product_taxes else taxes_found[0].id

    def l10n_mx_edi_get_tax_group(self, taxes):
        tax = self.env['account.tax']
        tag_tax = self.env.ref('l10n_mx.tag_iva').id
        tag_taxes = tax.browse(taxes).sudo().filtered(
            lambda tax: tag_tax in
            tax.invoice_repartition_line_ids.tag_ids.ids)
        tax16 = tax.browse(taxes).filtered(lambda t: t.amount == 16.0)
        if len(tag_taxes) <= 1 or not tax16:
            return taxes
        grouped_taxes = tax.search([
            ('type_tax_use', '=', 'purchase'),
            ('amount_type', '=', 'group'),
        ])
        # Here change the tax 16.0 for 5.333
        tax5 = tax.search([
            ('description', '=', tax16.description),
            ('amount', '=', 5.3333)])
        if not tax5 or not grouped_taxes:
            return taxes
        taxes_copy = taxes[:]
        taxes.remove(tax16.id)
        taxes.append(tax5.id)
        tag_taxes = tax.browse(taxes).filtered(
            lambda tax: tag_tax in
            tax.invoice_repartition_line_ids.tag_ids.ids)
        for group in grouped_taxes:
            if set(tag_taxes.ids).issubset(group.children_tax_ids.ids):
                return (group + tax.browse(taxes).filtered(
                    lambda tax: tag_tax not in
                    tax.invoice_repartition_line_ids.tag_ids.ids)).ids
        # Here change the tax 16.0 for 12 for "Fletes"
        tax12 = tax.search([
            ('description', '=', tax16.description),
            ('amount', '=', 12.0)])
        if not tax12 or not grouped_taxes:
            return taxes_copy
        taxes_copy = taxes_copy[:]
        taxes.remove(tax5.id)
        taxes.append(tax12.id)
        tag_taxes = tax.browse(taxes).filtered(
            lambda tax: tag_tax in
            tax.invoice_repartition_line_ids.tag_ids.ids)
        for group in grouped_taxes:
            if set(tag_taxes.ids).issubset(group.children_tax_ids.ids):
                return (group + tax.browse(taxes).filtered(
                    lambda tax: tag_tax not in
                    tax.invoice_repartition_line_ids.tag_ids.ids)).ids
        return taxes_copy

    def l10n_mx_edi_get_cfdi(self):
        """Return the CFDI in the expense"""
        self.ensure_one()
        atts = self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
        ])
        attachments = atts.filtered(lambda a: a.l10n_mx_edi_is_cfdi33())
        if len(attachments) <= 1:
            return attachments
        uuids = []
        for attachment in attachments:
            uuid = attachment.l10n_mx_edi_is_cfdi33()
            if uuid in uuids:
                attachment.unlink()
            uuids.append(uuid)
        return attachments.exists()

    @api.onchange('employee_id')
    def _onchange_l10n_mx_employee_id(self):
        self.payment_mode = self.employee_id.l10n_mx_edi_payment_mode or \
            self.payment_mode

    def action_move_create(self):
        label = self.env.ref(
            'l10n_mx_edi_hr_expense.tag_force_invoice_generation', False)
        expenses = self.filtered(lambda exp: not exp.l10n_mx_edi_analysis and
                                 label not in exp.partner_id.category_id and
                                 not exp.l10n_mx_edi_move_line_id)
        res = super(HrExpense, expenses).action_move_create()
        lines = self.env['account.move.line']
        for expense in expenses:
            line = lines.search([
                ('expense_id', '=', expense.id),
                ('product_id', '=', expense.product_id.id)])
            expense.l10n_mx_edi_move_line_id = line.id
            expense.l10n_mx_edi_move_id = line.move_id.id
        return res

    def l10n_mx_edi_reclassify_journal_entries(self):
        ctx = {
            'active_model': self._name,
            'active_ids': self.ids,
        }
        compose_form = self.env.ref(
            'l10n_mx_edi_hr_expense.view_l10n_mx_edi_reclassify_journal_entries', False)  # noqa
        return {
            'name': _('Reclassify Journal Entries'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'l10n_mx_edi.reclassify.journal.entries',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    @staticmethod
    def dumps():
        """Helper method to have this available for server actions."""
        import json
        return json.dumps

    @staticmethod
    def loads():
        """Helper method to have this available for server actions."""
        import json
        return json.loads

    def get_pdf_expenses(self):
        self.ensure_one()
        return self.env['ir.attachment'].search([
            ('res_id', '=', self.id),
            ('res_model', '=', self._name),
            ('name', 'ilike', '.pdf')])

    @api.model
    def _get_fuel_codes(self):
        """Return the codes that could be used in FUEL"""
        return [str(r) for r in range(15101500, 15101513)]

    def get_local_taxes(self, xml):
        if not hasattr(xml, 'Complemento'):
            return []
        local_taxes = xml.Complemento.xpath(
            'implocal:ImpuestosLocales',
            namespaces={'implocal': 'http://www.sat.gob.mx/implocal'})
        if not local_taxes:
            return []
        taxes = local_taxes[0]
        taxes_list = []
        if hasattr(taxes, 'RetencionesLocales'):
            for tax in taxes.RetencionesLocales:
                taxes_list.append({
                    'type': 'ret',
                    'tax': tax.get('ImpLocRetenido'),
                    'rate': float(tax.get('TasadeRetencion', 0)),
                    'amount': float(tax.get('Importe', 0))
                })
        if hasattr(taxes, 'TrasladosLocales'):
            for tax in taxes.TrasladosLocales:
                taxes_list.append({
                    'type': 'tax',
                    'tax': tax.get('ImpLocTrasladado'),
                    'rate': float(tax.get('TasadeTraslado', 0)),
                    'amount': float(tax.get('Importe', 0))
                })
        return taxes_list

    def l10n_mx_edi_get_local_tax(self, tax):
        rate = float_round(tax['rate'], 4)
        local = self.env.ref('l10n_mx_edi_hr_expense.tag_local', False)
        if tax['type'] == 'ret':
            rate = rate * -1
        domain = [('invoice_repartition_line_ids', 'in', local.id),
                  ('type_tax_use', '=', 'purchase'),
                  ('amount', '=', rate)]
        if tax['type'] == 'ret' and rate <= -10.66 and rate >= -10.67:
            domain[-1] = ('|')
            domain.append(('amount', '=', rate))
            domain.append('&')
            domain.append(('amount', '<=', -10.66))
            domain.append(('amount', '>=', -10.67))
        elif tax['type'] == 'ret' and rate:
            domain.append(('amount', '<', 0))
        return self.env['account.tax'].search(domain, limit=1)

    def _get_tax_global(self):
        """Supported the next case with the CFDI:
            Line1 without tax
            Line2 without tax
            Line3 with the tax amount of the tree lines"""
        self.ensure_one()
        label = self.env.ref('l10n_mx_edi_hr_expense.tag_split_taxes', False)
        if not label or label not in self.partner_id.category_id:
            return []
        invoices = json.loads(self.l10n_mx_edi_analysis).get('invoices')
        if not invoices:
            return []
        lines = invoices[0].get('lines', [])
        if len(lines) <= 1:
            return []
        for line in lines:
            if not line.get('taxes'):
                continue
            return line['taxes']

    def split_expense(self):
        """If the expense has many CFDIs split this in one record for each CFDI
        """
        self.ensure_one()
        if self.l10n_mx_count_cfdi <= 1:
            return self
        invoice_atts = self.env['ir.attachment']
        all_atts = invoice_atts.search([
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
        ])
        for att in all_atts:
            uuid = att.l10n_mx_edi_is_cfdi33()
            if not uuid:
                continue
            invoice_atts += att
        not_invoice_atts = all_atts - invoice_atts
        count = 1
        expenses = self
        for att in invoice_atts[:-1]:
            count += 1
            expense = self.copy({
                'name': '%s - %s' % (self.name, count)})
            expenses += expense
            att.write({'res_id': expense.id})
            att_name = splitext(att.name)[0]
            alt_atts = not_invoice_atts.filtered(lambda _att: (
                splitext(_att.name)[0] == att_name))
            alt_atts.write({'res_id': expense.id})
            not_invoice_atts -= alt_atts
            expense.message_post_with_view(
                'l10n_mx_edi_hr_expense.hr_expense_splited_from',
                values={'self': expense, 'origin': self})
        expenses -= self
        self.message_post_with_view(
            'l10n_mx_edi_hr_expense.hr_expense_splited_to',
            values={'self': self, 'dest': expenses})
        return expenses + self

    def l10n_mx_records_autovalidate(self):
        return self.search([
            ('sheet_id', '=', False),
            ('l10n_mx_edi_fiscally_approved', '=', True),
            ('l10n_mx_edi_functionally_approved', '=', True),
            ('l10n_mx_edi_forced_approved', '=', False),
            ('state', '=', 'draft'),
        ])

    def l10n_mx_edi_create_invoice_wh_cfdi(self):
        """Create an invoice without CFDI for the partners with the tag
        tag_force_invoice_generation"""
        invoice = self.env['account.move']
        for expense in self:
            inv_type = expense.l10n_mx_edi_document_type or 'in_invoice'
            journal = invoice.with_context(
                default_type=inv_type)._get_default_journal()
            product = expense.product_id
            account = product.product_tmpl_id.get_product_accounts()[
                'expense'].id
            invoice_line_ids = [(0, 0, {
                'product_id': product.id,
                'account_id': expense.account_id.id or account,
                'name': expense.name,
                'quantity': expense.quantity,
                'product_uom_id': expense.product_uom_id.id,
                'tax_ids': [(6, 0, expense.tax_ids.ids)],
                'price_unit': expense.unit_amount,
                'discount': expense.l10n_mx_edi_discount,
                'analytic_account_id': expense.analytic_account_id.id,
                'analytic_tag_ids': [(6, 0, expense.analytic_tag_ids.ids)],
            })]
            data = {
                'partner_id': expense.partner_id.id,
                'date_invoice': expense.l10n_mx_edi_date or expense.date,
                'date': expense.date,
                'currency_id': expense.currency_id.id,
                'invoice_line_ids': invoice_line_ids,
                'type': inv_type,
                'journal_id': journal.id,
            }
            if not data.get('company_id'):
                data.update({'company_id': expense.company_id.id})
            inv = invoice.sudo().create(data)
            inv.with_context(
                check_move_validity=False)._onchange_invoice_date()
            expense.l10n_mx_edi_invoice_id = inv
            inv.l10n_mx_edi_expense_id = expense

    def l10n_mx_edi_revert_expense(self):
        if not self.user_has_groups(
                'l10n_mx_edi_hr_expense.allow_to_revert_expenses'):
            raise UserError(_(
                'Only the users in the group "Allow to Revert Expenses" could '
                'execute this action.'))
        move_ids = self.env['account.move']
        for record in self.filtered('sheet_id'):
            invoice = record.l10n_mx_edi_invoice_id
            if invoice and invoice.state != 'cancel':
                moves = invoice.payment_move_line_ids
                moves.mapped('payment_id').cancel()
                invoice.mapped('line_ids').remove_move_reconcile()
                move_ids |= invoice
                invoice.action_cancel()
                invoice.write({
                    'move_name': False,
                    'ref': '%s-cancelled' % invoice.ref,
                })
            if not invoice and record.l10n_mx_edi_move_line_id:
                move = record.l10n_mx_edi_move_line_id
                move.button_cancel()
                move.line_ids.filtered(
                    lambda aml: aml.expense_id == record).unlink()
                if not move.line_ids:
                    move_ids |= move
                    record.sheet_id.account_move_id = False
            record.state = 'approved'
            record.sheet_id.state = 'approve'
        move_ids.exists().unlink()

    def _get_expense_account_destination(self):
        self.ensure_one()
        res = super(HrExpense, self)._get_expense_account_destination()
        if self.payment_mode not in ('petty_account', 'own_account'):
            return res
        sheet = self.sheet_id
        journal = (sheet.petty_journal_id if
                   self.payment_mode == 'petty_account' else
                   sheet.employee_id.journal_id)
        if not journal:
            return res
        return journal.default_credit_account_id.id

    @api.depends('employee_id')
    def _compute_is_ref_editable(self):
        """Inherit to extend the state in which could be write the reference"""
        res = super(HrExpense, self)._compute_is_ref_editable()
        for expense in self.filtered(lambda exp: not exp.is_ref_editable):
            if expense.state in ('draft', 'downloaded') or expense.sheet_id.state in ['draft', 'submit']:  # noqa
                expense.is_ref_editable = True
        return res

    def l10n_mx_edi_retrieve_payment(self):
        """Method to be inherited"""
        return True
