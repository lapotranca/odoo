# -*- coding: utf-8 -*-
import uuid
from odoo import models, fields, api, _


class ResUsers(models.Model):
    _inherit = "res.users"

    as_token = fields.Char()

    def get_user_access_token(self):
        return uuid.uuid4().hex

    @api.model
    def get_token(self):
        token = self.get_user_access_token()
        self.token = token        
        return self.token