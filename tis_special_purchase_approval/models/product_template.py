# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd.
# - © Technaureus Info Solutions Pvt. Ltd 2019. All rights reserved.

from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = "product.template"

    purchase_manager_apv = fields.Boolean(string="Purchase Manager Approval Required?", default=False)
