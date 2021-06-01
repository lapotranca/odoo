# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools import float_is_zero, pycompat

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model
    def get_pos_quants(self, data):
        lots = []
        product_id = data[0]
        picking_type_id = int(data[1])
        picking_type_id = self.env['stock.picking.type'].browse(picking_type_id).exists()
        location_id = picking_type_id.default_location_src_id.id
        domain = [('product_id','=',product_id)]
        domain = domain + [('location_id','=',location_id)]
        for quant in self.search_read(domain, order='id DESC',):
            if not quant['lot_id']:
                continue
            final_qty = quant['quantity'] - quant['reserved_quantity']
            # final_qty = quant['quantity']
            if final_qty <= 0:
                continue
            # if not quant['lot_id']:
            #     quant['lot_id'] = [-1,'']
            # if lot does not exists we get following error
            # You need to supply a Lot/Serial number for product during validating a picking
            lots.append({'id':quant['id'],
                'lot_id':quant['lot_id'],
                'location_id':quant['location_id'],
                'package_id': quant['package_id'],
                'quantity': final_qty})

        return lots

class POSOrder(models.Model):
    _inherit = 'pos.order'

    def create_picking(self):
        """Create a picking for each order and validate it."""
        Picking = self.env['stock.picking']
        # If no email is set on the user, the picking creation and validation will fail be cause of
        # the 'Unable to log message, please configure the sender's email address.' error.
        # We disable the tracking in this case.
        if not self.env.user.partner_id.email:
            Picking = Picking.with_context(tracking_disable=True)
        Move = self.env['stock.move']
        StockWarehouse = self.env['stock.warehouse']
        for order in self:
            if not order.lines.filtered(lambda l: l.product_id.type in ['product', 'consu']):
                continue
            address = order.partner_id.address_get(['delivery']) or {}
            picking_type = order.picking_type_id
            return_pick_type = order.picking_type_id.return_picking_type_id or order.picking_type_id
            order_picking = Picking
            return_picking = Picking
            moves = Move
            location_id = picking_type.default_location_src_id.id
            if order.partner_id:
                destination_id = order.partner_id.property_stock_customer.id
            else:
                if (not picking_type) or (not picking_type.default_location_dest_id):
                    customerloc, supplierloc = StockWarehouse._get_partner_locations()
                    destination_id = customerloc.id
                else:
                    destination_id = picking_type.default_location_dest_id.id

            if picking_type:
                message = _("This transfer has been created from the point of sale session: <a href=# data-oe-model=pos.order data-oe-id=%d>%s</a>") % (order.id, order.name)
                picking_vals = {
                    'origin': order.name,
                    'partner_id': address.get('delivery', False),
                    'user_id': False,
                    'date_done': order.date_order,
                    'picking_type_id': picking_type.id,
                    'company_id': order.company_id.id,
                    'move_type': 'direct',
                    'note': order.note or "",
                    'location_id': location_id,
                    'location_dest_id': destination_id,
                }
                pos_qty = any([x.qty > 0 for x in order.lines if x.product_id.type in ['product', 'consu']])
                if pos_qty:
                    order_picking = Picking.create(picking_vals.copy())
                    if self.env.user.partner_id.email:
                        order_picking.message_post(body=message)
                    else:
                        order_picking.sudo().message_post(body=message)
                neg_qty = any([x.qty < 0 for x in order.lines if x.product_id.type in ['product', 'consu']])
                if neg_qty:
                    return_vals = picking_vals.copy()
                    return_vals.update({
                        'location_id': destination_id,
                        'location_dest_id': return_pick_type != picking_type and return_pick_type.default_location_dest_id.id or location_id,
                        'picking_type_id': return_pick_type.id
                    })
                    return_picking = Picking.create(return_vals)
                    if self.env.user.partner_id.email:
                        return_picking.message_post(body=message)
                    else:
                        return_picking.message_post(body=message)

            lot_movelines_created = False
            for line in order.lines.filtered(lambda l: l.product_id.type in ['product', 'consu'] and not float_is_zero(l.qty, precision_rounding=l.product_id.uom_id.rounding)):
                new_move = Move.create({
                    'name': line.name,
                    'product_uom': line.product_id.uom_id.id,
                    'picking_id': order_picking.id if line.qty >= 0 else return_picking.id,
                    'picking_type_id': picking_type.id if line.qty >= 0 else return_pick_type.id,
                    'product_id': line.product_id.id,
                    'product_uom_qty': abs(line.qty),
                    'state': 'draft',
                    'location_id': location_id if line.qty >= 0 else destination_id,
                    'location_dest_id': destination_id if line.qty >= 0 else return_pick_type != picking_type and return_pick_type.default_location_dest_id.id or location_id,
                })
                # only customization is following code
                # ************************************
                lot_lines = []
                for pos_line_lot in line.lot_ids:
                    lot_lines.append((0, 0, {
                        'lot_id': pos_line_lot.lot_id.id,
                        'qty_done': pos_line_lot.qty_done,
                        'product_uom_id': new_move.product_uom.id,
                        'product_id': new_move.product_id.id,
                        'location_id': new_move.location_id.id,
                        'location_dest_id': new_move.location_dest_id.id,
                        'picking_id': order_picking.id or return_picking.id,
                        'package_id': pos_line_lot.package_id.id,
                        # 'state': 'assigned',
                     }))
                if lot_lines:
                    new_move.write({'move_line_ids': lot_lines})
                    lot_movelines_created = True
                moves |= new_move
                # ************************************


            # prefer associating the regular order picking, not the return
            order.write({'picking_id': order_picking.id or return_picking.id})

            if return_picking:
                order._force_picking_done(return_picking)
            if order_picking:
                order._force_picking_done(order_picking)
            # ************************************
            # check here if picking is not done yet and order has has_product_customlot true
            customlot_lines = order.lines.filtered(lambda line:line.has_product_customlot)
            has_customlot_lines = order.lines.mapped('has_product_customlot')
            if customlot_lines and order.picking_id.state!='done' and lot_movelines_created:
                order.picking_id.action_assign()
                order.picking_id.action_done()
            # ************************************

            # when the pos.config has no picking_type_id set only the moves will be created
            if moves and not return_picking and not order_picking:
                moves._action_assign()
                moves.filtered(lambda m: m.product_id.tracking == 'none')._action_done()

        return True

class ProductionLots(models.Model):
    _name = 'stock.pos.line.lot'
    _description = 'Manage POS Lots'

    lot_id = fields.Many2one('stock.production.lot', 'Lot')
    package_id = fields.Many2one('stock.quant.package', 'Package')
    qty_done = fields.Float('Quantity done')
    pos_order_line_id = fields.Many2one('pos.order.line','POS Order Line')

class POSOrderLine(models.Model):
    _inherit = 'pos.order.line'

    lot_ids = fields.One2many('stock.pos.line.lot','pos_order_line_id')
    has_product_customlot = fields.Boolean('Custom Lot')

    def _order_line_fields(self, line, session_id=None):
        line_data = super(POSOrderLine, self)._order_line_fields(line, session_id)
        if len(line_data)<1:
            return line_data

        line_dict = line_data[2]
        if not 'lot_ids' in line_dict:
            return line_data

        lot_ids = line_dict.pop('lot_ids')
        lot_ids_list = []
        for lotd in lot_ids:
            if lotd['lot_id'] == -1:
                lotd['lot_id'] = ''
            if lotd['package_id']:
                lotd['package_id'] = int(lotd['package_id'])
            lot_ids_list.append((0, 0, lotd))
        line_data[2]['lot_ids'] = lot_ids_list
        return line_data
