# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = "account.move"

    line_ids = fields.One2many('account.move.line', 'move_id', string='Journal Items', copy=True, readonly=True,
        states={'draft': [('readonly', False)],'posted': [('readonly', False)]})

class account_move_line(models.Model):
    _inherit = "account.move.line"

    cost_center_id = fields.Many2one('tf.cost.center', 'Cost Center')
    department_id = fields.Many2one('tf.department', string='Departments')
    regiones_id = fields.Many2one('tf.regiones', string='Región')
    group_ediat_account_posted = fields.Boolean(compute='as_get_edit_account')
    state = fields.Selection(related="move_id.state")

    def write(self, vals):
        if any(key in vals for key in ('tax_ids', 'tax_line_ids')):
            if self.move_id.state == 'posted':
                vals.pop('tax_ids')
        result = super(account_move_line, self).write(vals)
        return result


    @api.onchange('regiones_id')
    def compute_regiones(self):
        for rec in self:
            return {'domain': {
                'cost_center_id': [('id', 'in', rec.regiones_id.center_ids.ids)]
            }}

    @api.onchange('cost_center_id')
    def compute_department(self):
        for rec in self:
            return {'domain': {
                'department_id': [('id', 'in', rec.cost_center_id.department_ids.ids)]
            }}


    def _check_reconcile_validity(self):
        #Perform all checks on lines
        company_ids = set()
        all_accounts = []
        for line in self:
            company_ids.add(line.company_id.id)
            all_accounts.append(line.account_id)
            if (line.matched_debit_ids or line.matched_credit_ids) and line.reconciled:
                raise UserError(_('You are trying to reconcile some entries that are already reconciled.'))
        if len(company_ids) > 1:
            raise UserError(_('To reconcile the entries company should be the same for all entries.'))
        # if len(set(all_accounts)) > 1:
        #     raise UserError(_('Entries are not from the same account.'))
        if not (all_accounts[0].reconcile or all_accounts[0].internal_type == 'liquidity'):
            raise UserError(_('Account %s (%s) does not allow reconciliation. First change the configuration of this account to allow it.') % (all_accounts[0].name, all_accounts[0].code))
        
    @api.onchange('debit','credit')
    @api.depends('debit','credit')
    def as_get_edit_account(self):
        for line in self:
            line.group_ediat_account_posted = self.user_has_groups('as_financial_report.group_ediat_account_posted')

    @api.onchange('product_id')
    def get_coste_center(self):
        usuario = self.env.user
        if self.move_id.type in ('out_invoice','out_refund'):
            for move_line in self.move_id.invoice_line_ids:
                move_line.analytic_tag_ids = usuario.analytic_tag_ids.ids
                move_line.regiones_id = usuario.regiones_id.id
                move_line.cost_center_id = usuario.cost_center_id.id
                move_line.department_id = usuario.departmento_id.id
            for move_line in self.move_id.line_ids:
                move_line.analytic_tag_ids = usuario.analytic_tag_ids.ids
                move_line.regiones_id = usuario.regiones_id.id
                move_line.cost_center_id = usuario.cost_center_id.id
                move_line.department_id = usuario.departmento_id.id
        elif self.move_id.as_employee_id:
            for move_line in self.move_id.line_ids:
                move_line.analytic_tag_ids = self.move_id.as_employee_id.analytic_tag_ids.ids
                move_line.regiones_id = self.move_id.as_employee_id.regiones_purchase_id.id
                move_line.cost_center_id = self.move_id.as_employee_id.cost_purchase_center_id.id
                move_line.department_id = self.move_id.as_employee_id.department_puechase_id.id
        else:
            for move_line in self.move_id.invoice_line_ids:
                if move_line.payment_id:
                    if move_line.payment_id.payment_type in ('inbound'):
                        move_line.analytic_tag_ids = usuario.analytic_tag_ids.ids
                        move_line.regiones_id = usuario.regiones_id.id
                        move_line.cost_center_id = usuario.cost_center_id.id
                        move_line.department_id = usuario.departmento_id.id
                    else:
                        move_line.analytic_tag_ids = usuario.analytic_tag_purchase_ids.ids
                        move_line.regiones_id = usuario.regiones_purchase_id.id
                        move_line.cost_center_id = usuario.cost_purchase_center_id.id
                        move_line.department_id = usuario.department_puechase_id.id                        
                else:  
                    move_line.analytic_tag_ids = usuario.analytic_tag_purchase_ids.ids
                    move_line.regiones_id = usuario.regiones_purchase_id.id
                    move_line.cost_center_id = usuario.cost_purchase_center_id.id
                    move_line.department_id = usuario.department_puechase_id.id
            for move_line in self.move_id.line_ids:
                if move_line.payment_id:
                    if move_line.payment_id.payment_type in ('inbound'):
                        move_line.analytic_tag_ids = usuario.analytic_tag_ids.ids
                        move_line.regiones_id = usuario.regiones_id.id
                        move_line.cost_center_id = usuario.cost_center_id.id
                        move_line.department_id = usuario.departmento_id.id
                    else:
                        move_line.analytic_tag_ids = usuario.analytic_tag_purchase_ids.ids
                        move_line.regiones_id = usuario.regiones_purchase_id.id
                        move_line.cost_center_id = usuario.cost_purchase_center_id.id
                        move_line.department_id = usuario.department_puechase_id.id                        
                else: 
                    move_line.analytic_tag_ids = usuario.analytic_tag_purchase_ids.ids
                    move_line.regiones_id = usuario.regiones_purchase_id.id
                    move_line.cost_center_id = usuario.cost_purchase_center_id.id
                    move_line.department_id = usuario.department_puechase_id.id
        if self.move_id.as_extract_sale:
            for move_line in self.move_id.invoice_line_ids:
                move_line.analytic_tag_ids = usuario.analytic_tag_ids.ids
                move_line.regiones_id = usuario.regiones_id.id
                move_line.cost_center_id = usuario.cost_center_id.id
                move_line.department_id = usuario.departmento_id.id
            for move_line in self.move_id.line_ids:
                move_line.analytic_tag_ids = usuario.analytic_tag_ids.ids
                move_line.regiones_id = usuario.regiones_id.id
                move_line.cost_center_id = usuario.cost_center_id.id
                move_line.department_id = usuario.departmento_id.id
    
class account_move(models.Model):
    _inherit = "account.move"

    as_employee_id = fields.Many2one('hr.employee', string='employee')
    as_extract_sale = fields.Boolean(string='Extraer Tag y Region de Venta',default=False)

    @api.onchange('as_extract_sale')
    def get_tag_of_sale(self):
        usuario = self.env.user
        if self.as_extract_sale:
            for move_line in self.invoice_line_ids:
                move_line.analytic_tag_ids = usuario.analytic_tag_ids.ids
                move_line.regiones_id = usuario.regiones_id.id
                move_line.cost_center_id = usuario.cost_center_id.id
                move_line.department_id = usuario.departmento_id.id
            for move_line in self.line_ids:
                move_line.analytic_tag_ids = usuario.analytic_tag_ids.ids
                move_line.regiones_id = usuario.regiones_id.id
                move_line.cost_center_id = usuario.cost_center_id.id
                move_line.department_id = usuario.departmento_id.id
        else:
            for move_line in self.invoice_line_ids:
                move_line.analytic_tag_ids = usuario.analytic_tag_purchase_ids.ids
                move_line.regiones_id = usuario.regiones_purchase_id.id
                move_line.cost_center_id = usuario.cost_purchase_center_id.id
                move_line.department_id = usuario.department_puechase_id.id
            for move_line in self.line_ids:
                move_line.analytic_tag_ids = usuario.analytic_tag_purchase_ids.ids
                move_line.regiones_id = usuario.regiones_purchase_id.id
                move_line.cost_center_id = usuario.cost_purchase_center_id.id
                move_line.department_id = usuario.department_puechase_id.id


    @api.model
    def create(self, vals):
        res = super(account_move, self).create(vals)
        usuario = self.env.user
        if res.type in ('out_invoice','out_refund'):
            for move_line in res.invoice_line_ids:
                if move_line.payment_id:
                    if move_line.payment_id.payment_type in ('inbound'):
                        move_line.analytic_tag_ids = usuario.analytic_tag_ids.ids
                        move_line.regiones_id = usuario.regiones_id.id
                        move_line.cost_center_id = usuario.cost_center_id.id
                        move_line.department_id = usuario.departmento_id.id
                    else:
                        move_line.analytic_tag_ids = usuario.analytic_tag_purchase_ids.ids
                        move_line.regiones_id = usuario.regiones_purchase_id.id
                        move_line.cost_center_id = usuario.cost_purchase_center_id.id
                        move_line.department_id = usuario.department_puechase_id.id                        
                else:   
                    move_line.analytic_tag_ids = usuario.analytic_tag_ids.ids
                    move_line.regiones_id = usuario.regiones_id.id
                    move_line.cost_center_id = usuario.cost_center_id.id
                    move_line.department_id = usuario.departmento_id.id
            for move_line in res.line_ids:
                if move_line.payment_id:
                    if move_line.payment_id.payment_type in ('inbound'):
                        move_line.analytic_tag_ids = usuario.analytic_tag_ids.ids
                        move_line.regiones_id = usuario.regiones_id.id
                        move_line.cost_center_id = usuario.cost_center_id.id
                        move_line.department_id = usuario.departmento_id.id
                    else:
                        move_line.analytic_tag_ids = usuario.analytic_tag_purchase_ids.ids
                        move_line.regiones_id = usuario.regiones_purchase_id.id
                        move_line.cost_center_id = usuario.cost_purchase_center_id.id
                        move_line.department_id = usuario.department_puechase_id.id   
                else:
                    move_line.analytic_tag_ids = usuario.analytic_tag_ids.ids
                    move_line.regiones_id = usuario.regiones_id.id
                    move_line.cost_center_id = usuario.cost_center_id.id
                    move_line.department_id = usuario.departmento_id.id
        elif res.as_employee_id:
            for move_line in res.line_ids:
                move_line.analytic_tag_ids = res.as_employee_id.analytic_tag_purchase_ids.ids
                move_line.regiones_id = res.as_employee_id.regiones_purchase_id.id
                move_line.cost_center_id = res.as_employee_id.cost_purchase_center_id.id
                move_line.department_id = res.as_employee_id.department_puechase_id.id
        else:
            for move_line in res.invoice_line_ids:
                if move_line.payment_id:
                    if move_line.payment_id.payment_type in ('inbound'):
                        move_line.analytic_tag_ids = usuario.analytic_tag_ids.ids
                        move_line.regiones_id = usuario.regiones_id.id
                        move_line.cost_center_id = usuario.cost_center_id.id
                        move_line.department_id = usuario.departmento_id.id
                    else:
                        move_line.analytic_tag_ids = usuario.analytic_tag_purchase_ids.ids
                        move_line.regiones_id = usuario.regiones_purchase_id.id
                        move_line.cost_center_id = usuario.cost_purchase_center_id.id
                        move_line.department_id = usuario.department_puechase_id.id      
                else:
                    move_line.analytic_tag_ids = usuario.analytic_tag_purchase_ids.ids
                    move_line.regiones_id = usuario.regiones_purchase_id.id
                    move_line.cost_center_id = usuario.cost_purchase_center_id.id
                    move_line.department_id = usuario.department_puechase_id.id
            for move_line in res.line_ids:
                if move_line.payment_id:
                    if move_line.payment_id.payment_type in ('inbound'):
                        move_line.analytic_tag_ids = usuario.analytic_tag_ids.ids
                        move_line.regiones_id = usuario.regiones_id.id
                        move_line.cost_center_id = usuario.cost_center_id.id
                        move_line.department_id = usuario.departmento_id.id
                    else:
                        move_line.analytic_tag_ids = usuario.analytic_tag_purchase_ids.ids
                        move_line.regiones_id = usuario.regiones_purchase_id.id
                        move_line.cost_center_id = usuario.cost_purchase_center_id.id
                        move_line.department_id = usuario.department_puechase_id.id      
                else:
                    move_line.analytic_tag_ids = usuario.analytic_tag_purchase_ids.ids
                    move_line.regiones_id = usuario.regiones_purchase_id.id
                    move_line.cost_center_id = usuario.cost_purchase_center_id.id
                    move_line.department_id = usuario.department_puechase_id.id
        if res.as_extract_sale:
            for move_line in res.move_id.invoice_line_ids:
                move_line.analytic_tag_ids = usuario.analytic_tag_ids.ids
                move_line.regiones_id = usuario.regiones_id.id
                move_line.cost_center_id = usuario.cost_center_id.id
                move_line.department_id = usuario.departmento_id.id
            for move_line in res.move_id.line_ids:
                move_line.analytic_tag_ids = usuario.analytic_tag_ids.ids
                move_line.regiones_id = usuario.regiones_id.id
                move_line.cost_center_id = usuario.cost_center_id.id
                move_line.department_id = usuario.departmento_id.id
          
        return res    


    def write(self, vals):
        usuario = self.env.user
        if self.type in ('out_invoice','out_refund'):
            for move_line in self.invoice_line_ids:
                if not move_line.regiones_id or not move_line.cost_center_id or not move_line.department_id:
                    move_line.analytic_tag_ids = usuario.analytic_tag_ids.ids
                    move_line.regiones_id = usuario.regiones_id.id
                    move_line.cost_center_id = usuario.cost_center_id.id
                    move_line.department_id = usuario.departmento_id.id
            for move_line in self.line_ids:
                if not move_line.regiones_id or not move_line.cost_center_id or not move_line.department_id:
                    move_line.analytic_tag_ids = usuario.analytic_tag_ids.ids
                    move_line.regiones_id = usuario.regiones_id.id
                    move_line.cost_center_id = usuario.cost_center_id.id
                    move_line.department_id = usuario.departmento_id.id
        elif self.as_employee_id:
            for move_line in self.line_ids:
                if not move_line.regiones_id or not move_line.cost_center_id or not move_line.department_id:
                    move_line.analytic_tag_ids = self.as_employee_id.analytic_tag_ids.ids
                    move_line.regiones_id = self.as_employee_id.regiones_purchase_id.id
                    move_line.cost_center_id = self.as_employee_id.cost_purchase_center_id.id
                    move_line.department_id = self.as_employee_id.department_puechase_id.id
        else:
            for move_line in self.invoice_line_ids:
                if not move_line.regiones_id or not move_line.cost_center_id or not move_line.department_id:
                    if move_line.payment_id:
                        if move_line.payment_id.payment_type in ('inbound'):
                            move_line.analytic_tag_ids = usuario.analytic_tag_ids.ids
                            move_line.regiones_id = usuario.regiones_id.id
                            move_line.cost_center_id = usuario.cost_center_id.id
                            move_line.department_id = usuario.departmento_id.id
                        else:
                            move_line.analytic_tag_ids = usuario.analytic_tag_purchase_ids.ids
                            move_line.regiones_id = usuario.regiones_purchase_id.id
                            move_line.cost_center_id = usuario.cost_purchase_center_id.id
                            move_line.department_id = usuario.department_puechase_id.id                        
                    else:  
                        move_line.analytic_tag_ids = usuario.analytic_tag_purchase_ids.ids
                        move_line.regiones_id = usuario.regiones_purchase_id.id
                        move_line.cost_center_id = usuario.cost_purchase_center_id.id
                        move_line.department_id = usuario.department_puechase_id.id
            for move_line in self.line_ids:
                if move_line.payment_id:
                    if move_line.payment_id.payment_type in ('inbound'):
                        if not move_line.regiones_id or not move_line.cost_center_id or not move_line.department_id:
                            move_line.analytic_tag_ids = usuario.analytic_tag_ids.ids
                            move_line.regiones_id = usuario.regiones_id.id
                            move_line.cost_center_id = usuario.cost_center_id.id
                            move_line.department_id = usuario.departmento_id.id
                    else:
                        if not move_line.regiones_id or not move_line.cost_center_id or not move_line.department_id:
                            move_line.analytic_tag_ids = usuario.analytic_tag_purchase_ids.ids
                            move_line.regiones_id = usuario.regiones_purchase_id.id
                            move_line.cost_center_id = usuario.cost_purchase_center_id.id
                            move_line.department_id = usuario.department_puechase_id.id                        
                else: 
                    if not move_line.regiones_id or not move_line.cost_center_id or not move_line.department_id:
                        move_line.analytic_tag_ids = usuario.analytic_tag_purchase_ids.ids
                        move_line.regiones_id = usuario.regiones_purchase_id.id
                        move_line.cost_center_id = usuario.cost_purchase_center_id.id
                        move_line.department_id = usuario.department_puechase_id.id
        if self.as_extract_sale:
            for move_line in self.invoice_line_ids:
                if not move_line.regiones_id or not move_line.cost_center_id or not move_line.department_id:
                    move_line.analytic_tag_ids = usuario.analytic_tag_ids.ids
                    move_line.regiones_id = usuario.regiones_id.id
                    move_line.cost_center_id = usuario.cost_center_id.id
                    move_line.department_id = usuario.departmento_id.id
            for move_line in self.line_ids:
                if not move_line.regiones_id or not move_line.cost_center_id or not move_line.department_id:
                    move_line.analytic_tag_ids = usuario.analytic_tag_ids.ids
                    move_line.regiones_id = usuario.regiones_id.id
                    move_line.cost_center_id = usuario.cost_center_id.id
                    move_line.department_id = usuario.departmento_id.id
        return super(account_move, self).write(vals)

    def action_post(self):
        res = super(account_move, self).action_post()
        usuario = self.env.user
        if self.type in ('out_invoice','out_refund'):
            for move_line in self.invoice_line_ids:
                move_line.analytic_tag_ids = usuario.analytic_tag_ids.ids
                move_line.regiones_id = usuario.regiones_id.id
                move_line.cost_center_id = usuario.cost_center_id.id
                move_line.department_id = usuario.departmento_id.id
            for move_line in self.line_ids:
                move_line.analytic_tag_ids = usuario.analytic_tag_ids.ids
                move_line.regiones_id = usuario.regiones_id.id
                move_line.cost_center_id = usuario.cost_center_id.id
                move_line.department_id = usuario.departmento_id.id
        elif self.as_employee_id:
            for move_line in self.line_ids:
                move_line.analytic_tag_ids = self.as_employee_id.analytic_tag_purchase_ids.ids
                move_line.regiones_id = self.as_employee_id.regiones_purchase_id.id
                move_line.cost_center_id = self.as_employee_id.cost_purchase_center_id.id
                move_line.department_id = self.as_employee_id.department_puechase_id.id
        else:
            for move_line in self.invoice_line_ids:
                if move_line.payment_id:
                    if move_line.payment_id.payment_type in ('inbound'):
                        move_line.analytic_tag_ids = usuario.analytic_tag_ids.ids
                        move_line.regiones_id = usuario.regiones_id.id
                        move_line.cost_center_id = usuario.cost_center_id.id
                        move_line.department_id = usuario.departmento_id.id
                    else:
                        move_line.analytic_tag_ids = usuario.analytic_tag_purchase_ids.ids
                        move_line.regiones_id = usuario.regiones_purchase_id.id
                        move_line.cost_center_id = usuario.cost_purchase_center_id.id
                        move_line.department_id = usuario.department_puechase_id.id                        
                else: 
                    move_line.analytic_tag_ids = usuario.analytic_tag_purchase_ids.ids
                    move_line.regiones_id = usuario.regiones_purchase_id.id
                    move_line.cost_center_id = usuario.cost_purchase_center_id.id
                    move_line.department_id = usuario.department_puechase_id.id
            for move_line in self.line_ids:
                if move_line.payment_id:
                    if move_line.payment_id.payment_type in ('inbound'):
                        move_line.analytic_tag_ids = usuario.analytic_tag_ids.ids
                        move_line.regiones_id = usuario.regiones_id.id
                        move_line.cost_center_id = usuario.cost_center_id.id
                        move_line.department_id = usuario.departmento_id.id
                    else:
                        move_line.analytic_tag_ids = usuario.analytic_tag_purchase_ids.ids
                        move_line.regiones_id = usuario.regiones_purchase_id.id
                        move_line.cost_center_id = usuario.cost_purchase_center_id.id
                        move_line.department_id = usuario.department_puechase_id.id                        
                else: 
                    move_line.analytic_tag_ids = usuario.analytic_tag_purchase_ids.ids
                    move_line.regiones_id = usuario.regiones_purchase_id.id
                    move_line.cost_center_id = usuario.cost_purchase_center_id.id
                    move_line.department_id = usuario.department_puechase_id.id
        if self.as_extract_sale:
            for move_line in self.invoice_line_ids:
                move_line.analytic_tag_ids = usuario.analytic_tag_ids.ids
                move_line.regiones_id = usuario.regiones_id.id
                move_line.cost_center_id = usuario.cost_center_id.id
                move_line.department_id = usuario.departmento_id.id
            for move_line in self.line_ids:
                move_line.analytic_tag_ids = usuario.analytic_tag_ids.ids
                move_line.regiones_id = usuario.regiones_id.id
                move_line.cost_center_id = usuario.cost_center_id.id
                move_line.department_id = usuario.departmento_id.id
      
        return res    
    

class account_payment(models.Model):
    _inherit = "account.payment"

    def post(self):
        res = super(account_payment, self).post()
        usuario = self.env.user
        if self.payment_type in ('inbound'):
            for move_line in self.move_line_ids:
                move_line.analytic_tag_ids = usuario.analytic_tag_ids.ids
                move_line.regiones_id = usuario.regiones_id.id
                move_line.cost_center_id = usuario.cost_center_id.id
                move_line.department_id = usuario.departmento_id.id
    
        else:
            for move_line in self.move_line_ids:
                move_line.analytic_tag_ids = usuario.analytic_tag_purchase_ids.ids
                move_line.regiones_id = usuario.regiones_purchase_id.id
                move_line.cost_center_id = usuario.cost_purchase_center_id.id
                move_line.department_id = usuario.department_puechase_id.id
      

        return res  

