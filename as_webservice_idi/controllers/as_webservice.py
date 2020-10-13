# -*- coding: utf-8 -*-
from odoo.tools.translate import _
from odoo import http
from odoo import http
from odoo.http import request
from tabulate import tabulate
from bs4 import BeautifulSoup
import json
import sys
# import yaml
import logging
_logger = logging.getLogger(__name__)

from werkzeug import urls
from werkzeug.wsgi import wrap_file

class as_webservice(http.Controller):
    @http.route(["/tiamericas/clientes/","/tiamericas/clientes/<partner_id>"], auth='public', type="http")

    def partner(self, partner_id = None, **post):
        el_token = post.get('token') or 'sin_token'
        current_user = request.env['res.users'].sudo().search([('as_token', '=', el_token)])
        if not current_user:
            res_json = json.dumps({'error': ('Token Invalido')})
            callback = post.get('callback')
            return '{0}({1})'.format(callback, res_json)  
        if current_user:
            partner_model = request.env['res.partner']
            
            # filtrar ID partner desde el URL
            filtro = '[]'
            if partner_id:
                filtro = [('id','=',partner_id)]
                partner_ids = partner_model.sudo().search(filtro)
            else:
                partner_ids = partner_model.sudo().search([('active', '=', True)])   
                        
            # partner_ids = partner_model.sudo().search([('phone','=',phone)],limit=1)
            if not partner_ids:
                res_json = json.dumps({'error': _('Cliente/Proveedor no encontrado')})
                callback = post.get('callback')
                return '{0}({1})'.format(callback, res_json)
            else:
                rp = {}
                json_partners = []

                for partner in partner_ids:  
                    so_json_dict = []
                    index = 0
                    rp = {
                            "id": partner.id,
                            "name": partner.name, #Nombre cliente
                            "phone": partner.phone, #Telefono
                            "street": partner.street, #Direccion
                            "email": partner.email, #Email
                            "rfc": partner.vat, #Email
                        }
                    json_partners.append(rp)
                res = json.dumps(json_partners)
                callback = post.get('callback')
                return '{0}({1})'.format(callback, res)    
    
    @http.route('/tiamericas/get_token', type='json',  auth='user')
    def get_token(self, **post):        
        user = request.env['res.users'].sudo().browse(post['local_context']['uid'])
        res = user.get_token()
        return res

    # http://localhost:10000/tiamericas/token/?login=admin&password=123&db=ODOO12_APP
    @http.route(['/tiamericas/token',], auth="public", type="http", csrf=False)
    def token(self, **post):
        """
            Para autenticar se deben enviar usuario y password
            servidor.com:8069/tiamericas/token?login=admin&password=admin
        """
        res = {}
        try:
            uid = request.session.authenticate(request.params['db'], request.params['login'], request.params['password'])
            if uid:
                user = request.env['res.users'].sudo().browse(uid)
                token = user.get_user_access_token()
                user.as_token = token
                res['token'] = token
                request.session.logout()
            else:
                res['error'] = "Login o Password erroneo"
            res_json = json.dumps(res)
            callback = post.get('callback')
            return '{0}({1})'.format(callback, res_json)
        except:
            res['error'] = "Envia login y password"
            res_json = json.dumps(res)
            callback = post.get('callback')
            return '{0}({1})'.format(callback, res_json)