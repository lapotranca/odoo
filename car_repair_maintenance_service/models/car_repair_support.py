# -*- coding: utf-8 -*-

import time

from odoo import models, fields, api, _
from odoo.exceptions import UserError, Warning

class CarRepairSupport(models.Model):
    _name = 'car.repair.support'
    _description = 'Car Repair Support'
    _order = 'id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'format.address.mixin', 'portal.mixin']
    
    
#     @api.multi
#     def _write(self, vals):#this is to fix access error on stage write with other records.
#         if len(vals.keys()) == 1 and 'state' in vals:
#             return super(CarRepairSupport, self.sudo())._write(vals)
#         return super(CarRepairSupport, self)._write(vals)
    
    @api.model
    def create(self, vals):

        if vals.get('custome_client_user_id', False):
            client_user_id = self.env['res.users'].browse(int(vals.get('custome_client_user_id')))
            if client_user_id:
                vals.update({'company_id' : client_user_id.company_id.id})
        else:
            vals.update({'custome_client_user_id': self.env.user.id})

        if vals.get('name', False):
            if not vals.get('name', 'New') == 'New':
                vals['subject'] = vals['name']
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('car.repair.support') or 'New'
        if vals.get('partner_id', False):
#            if 'phone' and 'email' not in vals:
#                partner = self.env['res.partner'].sudo().browse(vals['partner_id'])
#                if partner:
#                    vals.update({
#                        'email': partner.email,
#                        'phone': partner.phone,
#                    })
            partner = self.env['res.partner'].sudo().browse(vals['partner_id'])
            if partner:
                if 'phone' not in vals:
                    vals.update({
                        'phone': partner.phone,
                    })
                if 'email' not in vals:
                    vals.update({
                        'email': partner.email,
                    })
                    
        return super(CarRepairSupport, self).create(vals)
    
#    @api.multi odoo13
    @api.depends('timesheet_line_ids.unit_amount')
    def _compute_total_spend_hours(self):
        for rec in self:
            spend_hours = 0.0
            for line in rec.timesheet_line_ids:
                spend_hours += line.unit_amount
            rec.total_spend_hours = spend_hours
    
    @api.onchange('project_id')
    def onchnage_project(self):
        for rec in self:
            rec.analytic_account_id = rec.project_id.analytic_account_id
          
#    @api.one odoo13
    def set_to_close(self):
        if self.is_close != True:
            self.is_close = True
            self.close_date = fields.Datetime.now()#time.strftime('%Y-%m-%d')
            self.state = 'closed'
            template = self.env.ref('car_repair_maintenance_service.email_template_car_ticket1')
            template.send_mail(self.id)
            
#    @api.one odoo13
    def set_to_reopen(self):
        self.state = 'work_in_progress'
        if self.is_close != False:
            self.is_close = False

#    @api.multi odoo13
    def create_car_diagnosys(self):
        for rec in self:
            name = ''
            if rec.subject:
                name = rec.subject +'('+rec.name+')'
            else:
                name = rec.name
            task_vals = {
                'name' : str(name),
                'user_id' : rec.user_id.id,
                'date_deadline' : rec.close_date,
                'project_id' : rec.project_id.id,
                'partner_id' : rec.partner_id.id,
                'description' : rec.description,
                'car_ticket_id' : rec.id,
                'car_task_type': 'diagnosys',
            }
            task_id= self.env['project.task'].sudo().create(task_vals)
        action = self.env.ref('car_repair_maintenance_service.action_view_task_diagnosis_car')
        result = action.read()[0]
        result['domain'] = [('id', '=', task_id.id)]
        return result

#    @api.multi odoo13
    def create_work_order(self):
        for rec in self:
#            odoo13
            work_orde_name = ''
            if rec.subject:
                work_orde_name = rec.subject +'('+rec.name+')'
            else:
                work_orde_name = rec.name
            task_vals = {
            'name' : work_orde_name,
            'user_id' : rec.user_id.id,
            'date_deadline' : rec.close_date,
            'project_id' : rec.project_id.id,
            'partner_id' : rec.partner_id.id,
            'description' : rec.description,
            'car_ticket_id' : rec.id,
            'car_task_type': 'work_order',
            }
            task_id= self.env['project.task'].sudo().create(task_vals)
        action = self.env.ref('car_repair_maintenance_service.action_view_task_workorder')
        result = action.read()[0]
        result['domain'] = [('id', '=', task_id.id)]
        return result

    @api.onchange('product_id')
    def onchnage_product(self):
        for rec in self:
            rec.brand = rec.product_id.car_brand
            rec.color = rec.product_id.car_color
            rec.model = rec.product_id.car_model
            rec.year = rec.product_id.car_year
    
    name = fields.Char(
        string='Number', 
        required=False,
        default='New',
        copy=False, 
        readonly=True, 
    )
    state = fields.Selection(
        [('new','New'),
         ('assigned','Assigned'),
         ('work_in_progress','Work in Progress'),
         ('needs_more_info','Needs More Info'),
         ('needs_reply','Needs Reply'),
         ('reopened','Reopened'),
         ('solution_suggested','Solution Suggested'),
         ('closed','Closed')],
        track_visibility='onchange',
        default='new',
        copy=False, 
    )
    email = fields.Char(
        string="Email",
        required=False
    )
    phone = fields.Char(
        string="Phone"
    )
    category = fields.Selection(
        [('technical', 'Technical'),
        ('functional', 'Functional'),
        ('support', 'Support')],
        string='Category',
    )
    subject = fields.Char(
        string="Subject"
    )
    description = fields.Text(
        string="Description"
    )
    priority = fields.Selection(
        [('0', 'Low'),
        ('1', 'Middle'),
        ('2', 'High')],
        string='Priority',
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
    )
    request_date = fields.Datetime(
        string='Create Date',
        default=fields.Datetime.now,
        copy=False,
    )
    close_date = fields.Datetime(
        string='Close Date',
    )
    user_id = fields.Many2one(
        'res.users',
        string='Responsible Repair Technician',
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department'
    )
    timesheet_line_ids = fields.One2many(
        'account.analytic.line',
        'car_repair_request_id',
        string='Timesheets',
    )
    is_close = fields.Boolean(
        string='Is Ticket Closed ?',
        track_visibility='onchange',
        default=False,
        copy=False,
    )
    total_spend_hours = fields.Float(
        string='Total Hours Spent',
        compute='_compute_total_spend_hours'
    )
    project_id = fields.Many2one(
        'project.project',
        string='Project',
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
    )
    team_id = fields.Many2one(
        'car.support.team',
        string='Car Repair Team',
        default=lambda self: self.env['car.support.team'].sudo()._get_default_team_id(user_id=self.env.uid),
    )
    team_leader_id = fields.Many2one(
        'res.users',
        string='Repair Manager',
    )
    journal_id = fields.Many2one(
        'account.journal',
         string='Journal',
     )
    task_id = fields.Many2one(
        'project.task',
        string='Task',
        readonly = True,
    )
    is_task_created = fields.Boolean(
        string='Is Task Created ?',
        default=False,
    )
    company_id = fields.Many2one(
        'res.company', 
        default=lambda self: self.env.user.company_id, 
        string='Company',
#        readonly=True,
        readonly=False,
     )
    comment = fields.Text(
        string='Customer Comment',
        readonly=True,
    )
    rating = fields.Selection(
        [('poor', 'Poor'),
        ('average', 'Average'),
        ('good', 'Good'),
        ('very good', 'Very Good'),
        ('excellent', 'Excellent')],
        string='Customer Rating',
        readonly=True,
    )
    product_category = fields.Many2one(
        'product.category',
        string="Product Category"
    )
    product_id = fields.Many2one(
        'product.product',
        domain="[('is_car', '=', True)]",
        string="Product"
    )
    brand = fields.Char(
        string = "Brand"
    )
    color = fields.Char(
        string = "Color"
    )
    model = fields.Char(
        string="Model"
    )
    year = fields.Char(
        string="Year"
    )
    accompanying_items = fields.Text(
        string="Accompanying Items",
    )
    damage = fields.Text(
        string="Damage",
    )
    warranty = fields.Boolean(
        string="Warranty",
    )
    img1 = fields.Binary(
        string="Images1",
    )
    img2 = fields.Binary(
        string="Images2",
    )
    img3 = fields.Binary(
        string="Images3",
    )
    img4 = fields.Binary(
        string="Images4",
    )
    img5 = fields.Binary(
        string="Images5",
    )
    repair_types_ids = fields.Many2many(
        'car.repair.type',
        string="Repair Type"
    )
    problem = fields.Text(
       string="Problem",
       copy=True,
    )
    cosume_part_ids = fields.One2many(
      'car.product.consume.part',
      'car_id',
      string="Product Consume Part"
    )
    nature_of_service_id = fields.Many2one(
        'car.service.nature',
        string="Nature Of service"
    )
    lot_id = fields.Many2one(
        'stock.production.lot',
        string="Lot",
    )
    website_brand = fields.Char(
        string = "Website Brand",
        copy=True,
    )
    website_model = fields.Char(
        string = "Website Model",
        copy=True,
    )
    website_year = fields.Char(
        string = "Website Year",
        copy=True,
    )
#     @api.multi
#     @api.depends('analytic_account_id')
#     def compute_total_hours(self):
#         total_remaining_hours = 0.0
#         for rec in self:
#             rec.remaining_hours = rec.analytic_account_id.remaining_hours
#     
    total_consumed_hours = fields.Float(
        string='Total Consumed Hours',
#         compute='compute_total_hours',
#         store=True,
    )
    
    custome_client_user_id = fields.Many2one(
        'res.users',
        string="Ticket Created User",
        readonly = True,
        track_visibility='always',
    )
    
#    @api.multi odoo13
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        for rec in self:
            if rec.partner_id:
                rec.email = rec.partner_id.email
                rec.phone = rec.partner_id.phone
    
#    @api.multi odoo13
    @api.onchange('product_category')
    def product_id_change(self):
        return {'domain':{'product_id':[('is_car', '=', True),('categ_id', '=', self.product_category.id)]}}

#    @api.multi odoo13
    @api.onchange('team_id')
    def team_id_change(self):
        for rec in self:
            rec.team_leader_id = rec.team_id.leader_id.id
    
#    @api.one odoo13
    def unlink(self):
        for rec in self:
            if rec.state != 'new':
                raise Warning(_('You can not delete record which are not in draft state.'))
        return super(CarRepairSupport, self).unlink()
    
#    @api.multi odoo13
    def show_car_diagnosys_task(self):
        for rec in self:
            res = self.env.ref('car_repair_maintenance_service.action_view_task_diagnosis_car')
            res = res.read()[0]
            res['domain'] = str([('car_task_type','=','diagnosys'), ('car_ticket_id', '=', rec.id)])
            res['context'] = {'default_car_ticket_id': rec.id, 'default_car_task_type': 'diagnosys'}
        return res
    
#    @api.multi odoo13
    def show_work_order_task(self):
        for rec in self:
            res = self.env.ref('project.action_view_task')
            res = res.read()[0]
            res['domain'] = str([('car_task_type','=','work_order'), ('car_ticket_id', '=', rec.id)])
            res['context'] = {'default_car_ticket_id': rec.id, 'default_car_task_type': 'work_order'}
        return res


class HrTimesheetSheet(models.Model):
    _inherit = 'account.analytic.line'

    car_support_request_id = fields.Many2one(
        'car.repair.support',
        domain=[('is_close','=',False)],
        string='Car Repair Support',
    )
    billable = fields.Boolean(
        string='Chargable?',
        default=True,
    )
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
