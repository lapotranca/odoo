# -*- coding: utf-8 -*-
from odoo import models, api, _, fields

class AccountChartOfAccountReport(models.AbstractModel):
    _inherit = "account.coa.report"

    filter_v_cost_centers = []
    filter_v_cost_center = True
    filter_v_departments = []
    filter_v_department = True
