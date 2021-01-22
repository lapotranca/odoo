# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd.
# - © Technaureus Info Solutions Pvt. Ltd 2019. All rights reserved.

from odoo import models, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def button_confirm(self):
        is_purchase_manager = self.env['res.users'].has_group('purchase.group_purchase_manager')
        for line in self.order_line:
            if line.product_id.purchase_manager_apv:
                if not is_purchase_manager:
                    raise UserError(_('You have no permission to confirm this Purchase Order.Please contact the Administrator'))
        return super(PurchaseOrder, self).button_confirm()

