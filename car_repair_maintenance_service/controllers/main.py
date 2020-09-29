# -*- coding: utf-8 -*-

import base64
from odoo import http, _
from odoo.http import request
#from odoo import models,registry, SUPERUSER_ID odoo13
from odoo.addons.portal.controllers.portal import CustomerPortal as website_account

class CarRepairSupport(http.Controller):

    @http.route(['/page/car_repair_support_ticket'], type='http', auth="public", website=True)
    def open_car_repair_request(self, **post):
        service_ids = request.env['car.service.nature'].sudo().search([])
        srvice_type_ids = request.env['car.repair.type'].sudo().search([])
        return request.render("car_repair_maintenance_service.website_car_repair_support_ticket", {
            'service_ids': service_ids,
            'srvice_type_ids': srvice_type_ids,
        })

    def _prepare_car_repair_service_vals(self, Partner, post):
        team_obj = request.env['car.support.team']
        team_match = team_obj.sudo().search([('is_team','=', True)], limit=1)

        return {
            'subject': post['subject'],
            'team_id' :team_match.id,
            #'partner_id' :team_match.leader_id.id, odoo13
            'user_id' :team_match.leader_id.id,
            'email': post['email'],
            'phone': post['phone'],
            #'category': post['category'],
            'description': post['description'],
            'priority': post['priority'],
            'partner_id': Partner.id,
            'website_brand': post['brand'],
            'website_model': post['model'],
            'damage': post['damage'],
            'website_year': post['year'],
#            'nature_of_service_id': int(post['service_id']),
            'nature_of_service_id': int(post['service_id']) if post['service_id'] else False,
            #'repair_types_ids': [(4, int(post['srvice_type_id']))]
            'custome_client_user_id': request.env.user.id,
         }

    @http.route(['/car_repair_maintenance_service/request_submitted'], type='http', auth="public", methods=['POST'], website=True)
    def request_submitted(self, **post):
        if request.env.user.has_group('base.group_public'):
            Partner = request.env['res.partner'].sudo().search([('email', '=', post['email'])], limit=1)
        else:
            Partner = request.env.user.partner_id
        if Partner:
            team_obj = request.env['car.support.team']
            team_match = team_obj.sudo().search([('is_team','=', True)], limit=1)
            car_repair_service_vals = self._prepare_car_repair_service_vals(Partner, post)
            support = request.env['car.repair.support'].sudo().create(car_repair_service_vals)
#            support = request.env['car.repair.support'].sudo().create({
#                                                            'subject': post['subject'],
#                                                            'team_id' :team_match.id,
##                                                            'partner_id' :team_match.leader_id.id, odoo13
#                                                            'user_id' :team_match.leader_id.id,
#                                                            'email': post['email'],
#                                                            'phone': post['phone'],
##                                                             'category': post['category'],
#                                                            'description': post['description'],
#                                                            'priority': post['priority'],
#                                                            'partner_id': Partner.id,
#                                                            'website_brand': post['brand'],
#                                                            'website_model': post['model'],
#                                                            'damage': post['damage'],
#                                                            'website_year': post['year'],
#                                                            'nature_of_service_id': int(post['service_id']),
##                                                             'repair_types_ids': [(4, int(post['srvice_type_id']))]
#                                                            'custome_client_user_id': request.env.user.id,
#                                                             })
            values = {
                'support':support,
                'user':request.env.user
            }
            attachment_list = request.httprequest.files.getlist('attachment')
            for image in attachment_list:
                if post.get('attachment'):
                    attachments = {
                               'res_name': image.filename,
                               'res_model': 'car.repair.support',
                               'res_id': support,
                               'datas': base64.encodestring(image.read()),
                               'type': 'binary',
                               #'datas_fname': image.filename,
                               'name': image.filename,
                           }
                    attachment_obj = http.request.env['ir.attachment']
                    attach = attachment_obj.sudo().create(attachments)
            if len(attachment_list) > 0:
                group_msg = _('Customer has sent %s attachments to this car repair ticket. Name of attachments are: ') % (len(attachment_list))
                for attach in attachment_list:
                    group_msg = group_msg + '\n' + attach.filename
                group_msg = group_msg + '\n'  +  '. You can see top attachment menu to download attachments.'
                support.sudo().message_post(body=group_msg,message_type='comment')
            return request.render('car_repair_maintenance_service.thanks_mail_send_car', values)
        else:
            return request.render('car_repair_maintenance_service.support_invalid_car',{'user':request.env.user})
            
#odoo13 not used
#    @http.route(['/car_repair_maintenance_service/invite'], auth='public', website=True, methods=['POST'])
#    def index_user_invite(self, **kw):
#        email = kw.get('email')
#        name = kw.get('name')
#         cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
#        user = request.env['res.users'].browse(request.uid)
#        user_exist = request.env['res.users'].sudo().search([('login','=',str(email))])
#        vals = {
#                  'user_id':user_exist,
#                }
#        if user_exist:
#            return http.request.render('car_repair_maintenance_service.user_alredy_exist', vals)
#        value={
#              'name': name,
#              'email': email,
#              'invitation_date':datetime.date.today(),
#              'referrer_user_id':user.id,
#              }
#        user_info_id = self.create_history(value)
#        base_url = http.request.env['ir.config_parameter'].get_param('web.base.url', default='http://localhost:8069') + '/page/car_repair_maintenance_service.user_thanks'
#        url = "%s?user_info=%s" %(base_url, user_info_id.id)
#        reject_url = http.request.env['ir.config_parameter'].get_param('web.base.url', default='http://localhost:8069') + '/page/machine_#repair_management.user_thanks_reject'
#        reject_url = http.request.env['ir.config_parameter'].get_param('web.base.url', default='http://localhost:8069') + '/page/car_repair_maintenance_service.user_thanks_reject'
#        rejected_url = "%s?user_info=%s" %(reject_url, user_info_id.id)
#        local_context = http.request.env.context.copy()
#        issue_template = http.request.env.ref('car_repair_maintenance_service.email_template_car_ticket1')
#        local_context.update({'user_email': email, 'url': url, 'name':name,'rejected_url':rejected_url})
#        issue_template.sudo().with_context(local_context).send_mail(request.uid)
       
    @http.route(['/car_repair_email/feedback/<int:order_id>'], type='http', auth='public', website=True)
    def feedback_email(self, order_id, **kw):
        values = {}
        values.update({'car_ticket_id': order_id})
        return request.render("car_repair_maintenance_service.car_repair_feedback", values) 
       
    @http.route(['/car_repari/feedback/'],
                methods=['POST'], auth='public', website=True)
    def start_rating(self, **kw):
        partner_id = kw['partner_id']
        user_id = kw['car_ticket_id']
        ticket_obj = request.env['car.repair.support'].sudo().browse(int(user_id))
        #if partner_id == UserInput.partner_id.id:
        vals = {
              'rating':kw['star'],
              'comment':kw['comment'],
            }
        ticket_obj.sudo().write(vals)
        customer_msg = _(ticket_obj.partner_id.name + 'has send this feedback rating is %s and comment is %s') % (kw['star'],kw['comment'],)
        ticket_obj.sudo().message_post(body=customer_msg)
        #return http.request.render("machine_repair_management.successful_feedback")
        return http.request.render("car_repair_maintenance_service.successful_feedback_car")
            
class website_account(website_account):

    def _prepare_portal_layout_values(self): # odoo11
        values = super(website_account, self)._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        values.update({
            'repair_request_count': request.env['car.repair.support'].sudo().search_count([('partner_id', 'child_of', [partner.commercial_partner_id.id])]),
        })
        return values
#     @http.route()
#     def account(self, **kw):
#         """ Add ticket documents to main account page """
#         response = super(website_account, self).account(**kw)
#         partner = request.env.user.partner_id
#         ticket = request.env['machine.repair.support']
#         ticket_count = ticket.sudo().search_count([
#         ('partner_id', 'child_of', [partner.commercial_partner_id.id])
#           ])
#         response.qcontext.update({
#         'ticket_count': ticket_count,
#         })
#         return response
        
    @http.route(['/my/repair_requests', '/my/repair_requests/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_repair_request(self, page=1, **kw):
        response = super(website_account, self)
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        car_obj = http.request.env['car.repair.support']
        domain = [
            ('partner_id', 'child_of', [partner.commercial_partner_id.id])
        ]
        # pager
        pager = request.website.pager(
            url="/my/repair_requests",
            total=values.get('repair_request_count'),
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        repair_request = car_obj.sudo().search(domain, limit=self._items_per_page, offset=pager['offset'])
        values.update({
            'repair_requests': repair_request,
            'page_name': 'repair_requests',
            'pager': pager,
            'default_url': '/my/repair_requests',
        })
        #return request.render("machine_repair_management.display_repair_requests", values)
        return request.render("car_repair_maintenance_service.display_car_repair_requests", values)
       
    #@http.route(['/my/repair_request/<model("machine.repair.support"):repair_request>'], type='http', auth="user", website=True)
    @http.route(['/my/repair_request/<model("car.repair.support"):repair_request>'], type='http', auth="user", website=True)
    def my_repair_request(self, repair_request=None, **kw):
        attachment_list = request.httprequest.files.getlist('attachment')
        #support_obj = http.request.env['machine.repair.support'].sudo().browse(repair_request.id)
        support_obj = http.request.env['car.repair.support'].sudo().browse(repair_request.id)
        for image in attachment_list:
            if kw.get('attachment'):
                attachments = {
                           'res_name': image.filename,
                           'res_model': 'car.repair.support',
                           'res_id': repair_request.id,
                           'datas': base64.encodestring(image.read()),
                           'type': 'binary',
                           #'datas_fname': image.filename,
                           'name': image.filename,
                       }
                attachment_obj = http.request.env['ir.attachment']
                attachment_obj.sudo().create(attachments)
        if len(attachment_list) > 0:
            group_msg = _('Customer has sent %s attachments to this Car repair ticket. Name of attachments are: ') % (len(attachment_list))
            for attach in attachment_list:
                group_msg = group_msg + '\n' + attach.filename
            group_msg = group_msg + '\n'  +  '. You can see top attachment menu to download attachments.'
            support_obj.sudo().message_post(body=group_msg,message_type='comment')
            customer_msg = _('%s') % (kw.get('ticket_comment'))
            support_obj.sudo().message_post(body=customer_msg,message_type='comment')
            return http.request.render('car_repair_maintenance_service.successful_car_ticket_send',{
            })
        if kw.get('ticket_comment'):
           # customer_msg = _('%s') % (kw.get('ticket_comment'))
#            support_obj.sudo().message_post(body=customer_msg,message_type='comment')
            return http.request.render('car_repair_maintenance_service.successful_car_ticket_send',{
            })
        return request.render("car_repair_maintenance_service.display_car_repair_request_from", {'repair_request': repair_request, 'user': request.env.user})
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
