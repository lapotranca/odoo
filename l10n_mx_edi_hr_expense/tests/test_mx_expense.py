# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import os

from odoo.tests.common import TransactionCase
from odoo.tools import misc
from odoo.tests.common import Form


INVOICE = ' {"invoices": [{"id": 622, "date": "2018-02-19 12:42:39", ' \
          '"number": "35", "serie": "INV 2018", "address": "37200", ' \
          '"payment": "PPD", "name": "Your Vendor SA de CV", "fp": "601", ' \
          '"sent_by": "EKU9003173C9", "received_by": "ULC051129GC0", ' \
          '"subtotal": 13754.0, "discount": 0.0, "tax": 2200.64, ' \
          '"withhold": 0.0, "currency": "MXN", "total": 15954.64, ' \
          '"uuid": "90999ED0-5D15-4991-A82C-B8ED06B3D8C3"}], ' \
          '"total": 15954.64, "subtotal": 13754.0, "taxes": 2200.64, ' \
          '"withhold": 2200.64} '


class EdiHrExpense(TransactionCase):
    def setUp(self):
        super(EdiHrExpense, self).setUp()
        self.product = self.env.ref('hr_expense.product_product_fixed_cost')
        self.employee = self.env.ref('hr.employee_admin')
        self.env.ref('base.main_company').vat = 'ULC051129GC0'
        self.xml_signed = misc.file_open(os.path.join(
            'l10n_mx_edi_hr_expense', 'tests', 'INV-INV20180035-MX-3-3.xml'),
            'r').read().encode('UTF-8')
        self.account = self.env['account.account'].create({
            'code': '201.xx.xx',
            'name': 'Pieter Card',
            'user_type_id': self.ref('account.data_account_type_credit_card'),
            'reconcile': True,
        })
        self.journal = self.env['account.journal'].create({
            'name': 'Pieter Card',
            'type': 'cash',
            'code': 'EP',
            'default_debit_account_id': self.account.id,
            'default_credit_account_id': self.account.id,
        })
        self.uid = self.env['res.users'].create({
            'name': 'User expense mx',
            'login': 'mx_expense_user',
            'email': 'mx_expense_user@yourcompany.com',
            'company_id': self.env.ref('base.main_company').id,
            'groups_id': [(6, 0, [self.ref(
                'hr_expense.group_hr_expense_manager'),
                self.ref('hr.group_hr_user')])]
        })

    def create_attachment(self, expense_id):
        return self.env['ir.attachment'].sudo().create({
            'name': 'expense.xml',
            'datas': base64.b64encode(self.xml_signed),
            'description': 'XML signed.',
            'res_model': 'hr.expense',
            'res_id': expense_id,
        })

    def test_create_sheet(self):
        sheet = self.env['hr.expense.sheet'].with_env(self.env(user=self.uid))
        res = sheet.create({'name': 'Hello', 'employee_id': 2})
        self.assertTrue(res.display_name.find(']') > 0,
                        'Name is not what expected for a sheet')
        res.approve_expense_sheets()

    def test_create_expense(self):
        """On this module I am forcing the posibility of write the total then
        test that, and check the proper default value was set as downloaded."""
        expense = self.env['hr.expense'].with_env(self.env(
            user=self.uid)).create({
                'name': 'Expense demo',
                'product_id': self.product.id,
                'employee_id': self.employee.id,
            })
        self.assertTrue(expense.state == 'downloaded',
                        "The default value downloaded for expenses failed to "
                        "be set.")
        expense.write({'total_amount': 100.0})
        self.assertTrue(expense.total_amount == 100.0,
                        "The inverse method for total_amount on expenses "
                        "failed")
        expense.write({
            'l10n_mx_edi_analysis': INVOICE,
            'l10n_mx_edi_rfc': 'EKU9003173C9',
        })

        self.assertTrue(expense.total_amount == 100.0,
                        "The inverse method for total_amount on expenses "
                        "failed")

    def test_create_partner_from_cfdi(self):
        """Creating vendor from CFDI and compute partner_id."""
        expenses = self.env['hr.expense'].with_env(self.env(user=self.uid))
        expense = expenses.create({
            'name': 'Expense demo',
            'product_id': self.product.id,
            'employee_id': self.employee.id,
        })
        expense.write({
            'l10n_mx_edi_analysis': INVOICE,
            'l10n_mx_edi_rfc': 'EKU9003173C9',
        })
        expense.create_partner_from_cfdi()
        self.assertTrue(bool(expense.partner_id),
                        "The Partner was not assigned once created from "
                        "expense")
        self.assertTrue(expense.partner_id.name == 'Your Vendor SA de CV',
                        "Name was incorrectly set on create partner from "
                        "expense")
        self.assertTrue(expense.partner_id.vat == 'EKU9003173C9',
                        "Vat was incorrectly set on create partner from "
                        "expense")
        self.assertTrue(expense.partner_id.zip == '37200',
                        "Zip code was incorrectly set on created partner "
                        "from expense")
        expense.create_partner_from_cfdi()
        self.assertTrue(expense.partner_id.vat == 'EKU9003173C9',
                        "Vat the partner was found and is correct")
        expense2 = expenses.create({
            'name': 'Expense demo',
            'product_id': self.product.id,
            'employee_id': self.employee.id,
            'l10n_mx_edi_rfc': 'EKU9003173C9',
        })
        self.assertTrue(bool(expense.partner_id),
                        "The Partner was not assigned once expense is created "
                        "and partner exists with proper rfc on the record")
        self.assertTrue(expense2.partner_id.vat == 'EKU9003173C9',
                        "Vat the partner was found and is correct with "
                        "compute")

    def test_force_create_super_employee(self):
        """Testing try creation of the first super employee"""
        expenses = self.env['hr.expense'].with_env(self.env(user=self.uid))
        super_employee = expenses._force_create_super_employee()
        self.assertTrue(bool(super_employee), "Super employee creation failed")
        super_employee2 = expenses._force_create_super_employee()
        self.assertTrue(super_employee2 == super_employee,
                        "Super employee creation failed")

    def test_demo_check_fiscal_status(self):
        """Force run the check fiscal method and see if the data was extracted
        properly from the xml"""
        expense = self.env.ref('l10n_mx_edi_hr_expense.ciel')
        expense.check_fiscal_status()
        self.assertTrue(expense.l10n_mx_edi_rfc == 'ECO820331KB5',
                        "The extracted RFC is not the one I expected,"
                        " I expected: ECO820331KB5")
        self.assertTrue(expense.l10n_mx_edi_received_rfc == 'EKU9003173C9',
                        "The extracted RFC is not the one I expected,"
                        " I expected: EKU9003173C9")
        self.assertEquals(expense.total_amount, 124.00,
                          "The extracted amount was not set")
        self.assertTrue(
            expense.l10n_mx_edi_uuid == 'F759C51C-42BC-46F6-8349-9C59EB088ABF',
            "UUID extracted incorrectly")
        # Due to the fact that We are using a manually changed UUID then I
        # expect it is not found in SAT.
        self.assertTrue(
            expense.l10n_mx_edi_sat_status == 'not_found',
            "UUID extracted incorrectly")

    def test_demo_duplicated_partner(self):
        """it is pretty common have duplicated partner then anything can fail
        on such case."""
        expense = self.env.ref('l10n_mx_edi_hr_expense.amazon')
        partner = self.env.ref('l10n_mx_edi_hr_expense.amazon_contact')
        partners = self.env['res.partner'].search(
            [('vat', '=', 'ANE140618P37')])
        expense.check_fiscal_status()
        self.assertTrue(expense.partner_id in partners,
                        "It did not pick an existing partner "
                        "%s - id: %s and partners are: partner: %s or "
                        "all in the BD: %s" % (
                            expense.partner_id.name, expense.partner_id.id,
                            partner.id, partners.ids))

    def test_create_journal(self):
        # Not interested to check if it is done by a normal employee just
        # the logic.
        employee = self.env['hr.employee'].sudo().create(
            {'name': "Test Employee for journal"})
        employee.create_petty_cash_journal()
        self.assertTrue(employee.journal_id.name == employee.name,
                        "The journal was not created when the action is "
                        "called from the employee.")

    def test_create_expense_wo_cfdi(self):
        """Case CFE where do not have CFDI but is necessary an invoice."""
        partner = self.env.ref('l10n_mx_edi_hr_expense.amazon_contact')
        partner.sudo().category_id = [(6, 0, self.env.ref(
            'l10n_mx_edi_hr_expense.tag_force_invoice_generation').ids)]
        expense = self.env['hr.expense'].with_env(self.env(
            user=self.uid)).create({
                'name': 'Expense CFDE',
                'product_id': self.product.id,
                'employee_id': self.employee.id,
                'partner_id': partner.id,
                'quantity': 2,
                'unit_amount': 100,
                'state': 'draft',
                'l10n_mx_edi_functionally_approved': True,
                'l10n_mx_edi_fiscally_approved': True,
            })
        data = expense.action_submit_expenses()
        sheet = self.env['hr.expense.sheet'].with_context(
            data['context']).create({
                'name': '%s' % expense.name,
            })
        sheet.action_submit_sheet()
        sheet.approve_expense_sheets()
        sheet.l10n_mx_edi_accrue_expenses()
        self.assertTrue(expense.l10n_mx_edi_invoice_id,
                        'The invoice was not created')

    def test_accountant_to_supplier_mxn(self):
        """Check that the accountant is assigned from the supplier"""
        expense = self.env.ref('l10n_mx_edi_hr_expense.ciel')
        expense.check_fiscal_status()
        expense.write({
            'l10n_mx_edi_functionally_approved': True,
            'l10n_mx_edi_fiscally_approved': True,
            'state': 'draft',
        })
        expense.partner_id.sudo().category_id = [(6, 0, self.env.ref(
            'l10n_mx_edi_hr_expense.tag_vendors').ids)]
        accountant = self.env.user.copy({'name': 'Accountant'})
        expense.partner_id.sudo().accountant_company_currency_id = accountant
        data = expense.action_submit_expenses()
        sheet = self.env['hr.expense.sheet'].with_context(
            data['context']).create({
                'name': '%s' % expense.name,
            })
        self.assertEquals(sheet.l10n_mx_edi_accountant, accountant,
                          'Accountant not assigned correctly.')

    def test_expense_state(self):
        """Generate an expense with CFDI, and pay the invoice, after
        unreconcile the payment"""
        expense = self.env.ref('l10n_mx_edi_hr_expense.ciel')
        expense.check_fiscal_status()
        expense.write({
            'l10n_mx_edi_functionally_approved': True,
            'l10n_mx_edi_fiscally_approved': True,
            'state': 'draft',
        })
        taxes = self.env['account.tax'].sudo().search([
            ('type_tax_use', '=', 'purchase'),
            ('amount', '=', 0.0)])
        taxes.mapped('invoice_repartition_line_ids').write(
            {'tag_ids': [(4, self.ref('l10n_mx.tag_iva'))]})
        expense.partner_id.sudo().category_id = [(6, 0, self.env.ref(
            'l10n_mx_edi_hr_expense.tag_vendors').ids)]
        accountant = self.env.user.copy({'name': 'Accountant'})
        expense.partner_id.sudo().accountant_company_currency_id = accountant
        data = expense.action_submit_expenses()
        sheet = self.env['hr.expense.sheet'].with_context(
            data['context']).create({
                'name': '%s' % expense.name,
            })
        sheet.action_submit_sheet()
        sheet.approve_expense_sheets()
        sheet.sudo().l10n_mx_edi_accrue_expenses()
        invoice = expense.l10n_mx_edi_invoice_id
        ctx = {'active_model': 'account.move', 'active_ids': [invoice.id]}
        bank_journal = self.env['account.journal'].search([
            ('type', '=', 'bank')], limit=1)
        payment_register = Form(self.env[
            'account.payment'].sudo().with_context(ctx))
        payment_register.payment_date = invoice.date
        payment_register.payment_method_id = self.env.ref(
            'account.account_payment_method_manual_in')
        payment_register.journal_id = bank_journal
        payment_register.communication = invoice.name
        payment_register.amount = invoice.amount_total
        payment_register.save().post()
        self.assertEquals('done', expense.state,
                          'The expense was not marked like paid')
        move_line = invoice._get_reconciled_payments().sudo().move_line_ids
        self.env['account.unreconcile'].with_context(
            active_ids=move_line.ids,
            invoice_id=invoice.id).sudo().trans_unrec()
        self.assertEquals('approved', expense.state,
                          'The expense was not unpaid')
