# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, Warning


class ProjectTask(models.Model):
    _inherit = "project.task"
    
    car_ticket_id = fields.Many2one(
        'car.repair.support',
        string='Car Repair Ticket',
        readonly=True,
        copy=False,
    )
    car_task_type = fields.Selection(
        selection= [
            ('diagnosys', 'Diagnosys'),
            ('work_order', 'Work Order'),
        ],
        string="Type",
        readonly = True,
    )
    car_repair_estimation_line_ids = fields.One2many(
       'car.repair.estimation.lines',
       'task_id',
       string="Repair Estimation Lines"
    )

#    @api.multi odoo13
    def show_quotation(self):
        for rec in self:
            res = self.env.ref('sale.action_quotations')
            res = res.read()[0]
            res['domain'] = str([('car_task_id','=', rec.id)])
        return res
    
#    @api.multi odoo13
    def create_quotation(self):
        for rec in self:
#            print("@@@@@@@@@") odoo13
            if not rec.car_repair_estimation_line_ids:
                raise UserError(_('Please add Estimation detail to create quotation!'))
            vales = {
                'car_task_id': rec.id,
                'partner_id': rec.partner_id.id,
                'user_id': rec.user_id.id,
                'pricelist_id': self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id or False,
            }
            # print("vales",vales) odoo13
            order_id = self.env['sale.order'].sudo().create(vales)

            print("order_id",order_id)
            for line in rec.car_repair_estimation_line_ids:

                if not line.product_id:
                    raise UserError(_('Product not defined on Estimation Repair Lines!'))
                
                price_unit = line.price
                print("price_unit",price_unit)
                if order_id.pricelist_id:
                    price_unit, rule_id = order_id.pricelist_id.get_product_price_rule(
                        line.product_id,
                        line.qty or 1.0,
                        order_id.partner_id
                    )
                
                orderlinevals = {
                    'order_id' : order_id.id,
                    'product_id' : line.product_id.id,
                    'product_uom_qty' : line.qty,
                    'product_uom' : line.product_uom.id,
                    'price_unit' : price_unit,
                    'name' : line.notes or '',
                }
#                print("orderlinevals",orderlinevals)odoo13
                line_id = self.env['sale.order.line'].create(orderlinevals)
#                print("line_id",line_id)odoo13
        action = self.env.ref('sale.action_quotations')
        result = action.read()[0]
        result['domain'] = [('id', '=', order_id.id)]
        return result
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
