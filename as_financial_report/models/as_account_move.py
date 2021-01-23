# -*- coding: utf-8 -*-

from odoo import models, fields, api

class account_move_line(models.Model):
    _inherit = "account.move.line"

    cost_center_id = fields.Many2one('tf.cost.center', 'Cost Center')
    department_id = fields.Many2one('tf.department', string='Departments')
    regiones_id = fields.Many2one('tf.regiones', string='Región')
    

    @api.onchange('product_id')
    def get_coste_center(self):
        usuario = self.env.user
        if self.move_id.type in ('out_invoice','out_refund'):
            for move_line in self:
                move_line.analytic_tag_ids = usuario.analytic_tag_ids.ids
                move_line.regiones_id = usuario.regiones_id.id
                move_line.cost_center_id = usuario.cost_center_id.id
                move_line.department_id = usuario.departmento_id.id
            for move_line in self:
                move_line.analytic_tag_ids = usuario.analytic_tag_ids.ids
                move_line.regiones_id = usuario.regiones_id.id
                move_line.cost_center_id = usuario.cost_center_id.id
                move_line.department_id = usuario.departmento_id.id
        else:
            for move_line in self:
                move_line.analytic_tag_ids = usuario.analytic_tag_purchase_ids.ids
                move_line.regiones_id = usuario.regiones_purchase_id.id
                move_line.cost_center_id = usuario.cost_purchase_center_id.id
                move_line.department_id = usuario.department_puechase_id.id
            for move_line in self:
                move_line.analytic_tag_ids = usuario.analytic_tag_purchase_ids.ids
                move_line.regiones_id = usuario.regiones_purchase_id.id
                move_line.cost_center_id = usuario.cost_purchase_center_id.id
                move_line.department_id = usuario.department_puechase_id.id

class account_move(models.Model):
    _inherit = "account.move"

    as_employee_id = fields.Many2one('hr.employee', string='employee')

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

        return res    


    def write(self, vals):
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
                move_line.analytic_tag_ids = self.as_employee_id.analytic_tag_ids.ids
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

