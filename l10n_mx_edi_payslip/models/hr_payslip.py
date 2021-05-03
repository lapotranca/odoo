# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from __future__ import division

import base64
import logging
import re
import time
from io import BytesIO
from itertools import groupby
from calendar import monthrange
from pytz import timezone
import requests

from lxml import etree, objectify
from werkzeug import url_encode
from zeep import Client
from zeep.transports import Transport

from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError, UserError
from odoo.tools import DEFAULT_SERVER_TIME_FORMAT
from odoo.tools.xml_utils import _check_with_xsd

_logger = logging.getLogger(__name__)


PAYSLIP_TEMPLATE = 'l10n_mx_edi_payslip.payroll12'
CFDI_XSLT_CADENA = 'l10n_mx_edi/data/3.3/cadenaoriginal.xslt'


def create_list_html(array):
    """Convert an array of string to a html list.
    :param list array: A list of strings
    :return: empty string if not array, an html list otherwise.
    :rtype: str"""
    if not array:  # pragma: no cover
        return ''  # pragma: no cover
    msg = ''
    for item in array:
        msg += '<li>' + item + '</li>'
    return '<ul>' + msg + '</ul>'


class HrPayslipInability(models.Model):
    _name = 'hr.payslip.inability'
    _description = 'Pay Slip inability'

    payslip_id = fields.Many2one(
        'hr.payslip', required=True, ondelete='cascade',
        help='Payslip related with this inability')
    sequence = fields.Integer(required=True, default=10)
    days = fields.Integer(
        help='Number of days in which the employee performed inability in '
        'the payslip period', required=True)
    inability_type = fields.Selection(
        [('01', 'Risk of work'),
         ('02', 'Disease in general'),
         ('03', 'Maternity'),
         ('04', 'License for medical care of children diagnosed with cancer.')
         ], 'Type', required=True, default='01',
        help='Reason for inability: Catalog published in the SAT portal')
    amount = fields.Float(help='Amount for the inability', required=True)


class HrPayslip(models.Model):
    _name = 'hr.payslip'
    _inherit = ['hr.payslip', 'mail.thread', 'l10n_mx_edi.pac.sw.mixin']

    l10n_mx_edi_payment_date = fields.Date(
        'Payment Date', required=True, readonly=True,
        states={'draft': [('readonly', False)]},
        default=time.strftime('%Y-%m-01'), help='Save the payment date that '
        'will be added on CFDI.')
    l10n_mx_edi_cfdi_name = fields.Char(
        string='CFDI name', copy=False, readonly=True,
        help='The attachment name of the CFDI.')
    l10n_mx_edi_cfdi = fields.Binary(
        'CFDI content', copy=False, readonly=True,
        help='The cfdi xml content encoded in base64.',
        compute='_compute_cfdi_values')
    l10n_mx_edi_inability_line_ids = fields.One2many(
        'hr.payslip.inability', 'payslip_id', 'Inabilities',
        readonly=True, states={'draft': [('readonly', False)]},
        help='Used in XML like optional node to express disabilities '
        'applicable by employee.', copy=True)
    l10n_mx_edi_overtime_line_ids = fields.One2many(
        'hr.payslip.overtime', 'payslip_id', 'Extra hours',
        readonly=True, states={'draft': [('readonly', False)]},
        help='Used in XML like optional node to express the extra hours '
        'applicable by employee.', copy=True)
    l10n_mx_edi_pac_status = fields.Selection(
        [('retry', 'Retry'),
         ('to_sign', 'To sign'),
         ('signed', 'Signed'),
         ('to_cancel', 'To cancel'),
         ('cancelled', 'Cancelled')], 'PAC status',
        help='Refers to the status of the payslip inside the PAC.',
        readonly=True, copy=False)
    l10n_mx_edi_sat_status = fields.Selection(
        [('none', 'State not defined'),
         ('undefined', 'Not Synced Yet'),
         ('not_found', 'Not Found'),
         ('cancelled', 'Cancelled'),
         ('valid', 'Valid')], 'SAT status',
        help='Refers to the status of the payslip inside the SAT system.',
        readonly=True, copy=False, required=True, track_visibility='onchange',
        default='undefined')
    l10n_mx_edi_cfdi_uuid = fields.Char(
        'Fiscal Folio', copy=False, readonly=True,
        help='Folio in electronic payroll, is returned by SAT when send to '
        'stamp.', compute='_compute_cfdi_values')
    l10n_mx_edi_cfdi_supplier_rfc = fields.Char(
        'Supplier RFC', copy=False, readonly=True,
        help='The supplier tax identification number.',
        compute='_compute_cfdi_values')
    l10n_mx_edi_cfdi_customer_rfc = fields.Char(
        'Customer RFC', copy=False, readonly=True,
        help='The customer tax identification number.',
        compute='_compute_cfdi_values')
    l10n_mx_edi_cfdi_amount = fields.Float(
        'Total Amount', copy=False, readonly=True,
        help='The total amount reported on the cfdi.',
        compute='_compute_cfdi_values')
    l10n_mx_edi_action_title_ids = fields.One2many(
        'hr.payslip.action.titles', 'payslip_id', string='Action or Titles',
        help='If the payslip have perceptions with code 045, assign here the '
        'values to the attribute in XML, use the perception type to indicate '
        'if apply to exempt or taxed.')
    l10n_mx_edi_extra_node_ids = fields.One2many(
        'hr.payslip.extra.perception', 'payslip_id',
        string='Extra data to perceptions',
        help='If the payslip have perceptions with code in 022, 023 or 025,'
        'must be created a record with data that will be assigned in the '
        'node "SeparacionIndemnizacion", or if the payslip have perceptions '
        'with code in 039 or 044 must be created a record with data that will '
        'be assigned in the node "JubilacionPensionRetiro". Only must be '
        'created a record by node.')
    l10n_mx_edi_balance_favor = fields.Float(
        'Balance in Favor', help='If the payslip include other payments, and '
        'one of this records have the code 004 is need add the balance in '
        'favor to assign in node "CompensacionSaldosAFavor".')
    l10n_mx_edi_comp_year = fields.Integer(
        'Year', help='If the payslip include other payments, and '
        'one of this records have the code 004 is need add the year to assign '
        'in node "CompensacionSaldosAFavor".')
    l10n_mx_edi_remaining = fields.Float(
        'Remaining', help='If the payslip include other payments, and '
        'one of this records have the code 004 is need add the remaining to '
        'assign in node "CompensacionSaldosAFavor".')
    l10n_mx_edi_source_resource = fields.Selection([
        ('IP', 'Own income'),
        ('IF', 'Federal income'),
        ('IM', 'Mixed income')], 'Source Resource',
        help='Used in XML to identify the source of the resource used '
        'for the payment of payroll of the personnel that provides or '
        'performs a subordinate or assimilated personal service to salaries '
        'in the dependencies. This value will be set in the XML attribute '
        '"OrigenRecurso" to node "EntidadSNCF".')
    l10n_mx_edi_amount_sncf = fields.Float(
        'Own resource', help='When the attribute in "Source Resource" is "IM" '
        'this attribute must be added to set in the XML attribute '
        '"MontoRecursoPropio" in node "EntidadSNCF", and must be less that '
        '"TotalPercepciones" + "TotalOtrosPagos"')
    l10n_mx_edi_cfdi_string = fields.Char(
        'CFDI Original String', help='Attribute "cfdi_cadena_original" '
        'returned by PAC request when is stamped the CFDI, this attribute is '
        'used on report.')
    l10n_mx_edi_cfdi_certificate_id = fields.Many2one(
        'l10n_mx_edi.certificate', string='Certificate', copy=False,
        readonly=True, help='The certificate used during the generation of '
        'the cfdi.', compute='_compute_cfdi_values')
    l10n_mx_edi_origin = fields.Char(
        string='CFDI Origin', copy=False,
        help='In some cases the payroll must be regenerated to fix data in it.'
        ' In that cases is necessary this field filled, the format is: '
        '\n04|UUID1, UUID2, ...., UUIDn.\n'
        'Example:\n"04|89966ACC-0F5C-447D-AEF3-3EED22E711EE,'
        '89966ACC-0F5C-447D-AEF3-3EED22E711EE"')
    l10n_mx_edi_expedition_date = fields.Date(
        string='Payslip date', readonly=True, copy=False, index=True,
        states={'draft': [('readonly', False)]},
        help="Keep empty to use the current date")
    l10n_mx_edi_time_payslip = fields.Char(
        string='Time payslip', readonly=True, copy=False,
        states={'draft': [('readonly', False)]},
        help="Keep empty to use the current México central time")
    sent = fields.Boolean(readonly=True, default=False, copy=False,
                          help="It indicates that the payslip has been sent.")
    # Add parameter copy=True
    input_line_ids = fields.One2many(copy=True)

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    @api.model
    def l10n_mx_edi_get_tfd_etree(self, cfdi):
        """Get the TimbreFiscalDigital node from the cfdi.

        :param cfdi: The cfdi as etree
        :type cfdi: etree
        :return: the TimbreFiscalDigital node
        :rtype: etree
        """
        # TODO - This method is the same that invoice.
        if not hasattr(cfdi, 'Complemento'):
            return None
        attribute = 'tfd:TimbreFiscalDigital[1]'
        namespace = {'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital'}
        node = cfdi.Complemento.xpath(attribute, namespaces=namespace)
        return node[0] if node else None

    @api.model
    def l10n_mx_edi_get_payroll_etree(self, cfdi):
        """Get the Complement node from the cfdi.
        :param cfdi: The cfdi as etree
        :type cfdi: etree
        :return: the Payment node
        :rtype: etree
        """
        if not hasattr(cfdi, 'Complemento'):
            return None
        attribute = '//nomina12:Nomina'
        namespace = {'nomina12': 'http://www.sat.gob.mx/nomina12'}
        node = cfdi.Complemento.xpath(attribute, namespaces=namespace)
        return node[0] if node else None

    def _get_extra_nodes(self):
        """Create the extra nodes dict(s)
        :return: a list with the extra nodes to apply
        :rtype: list
        """
        self.ensure_one()
        nodes = []
        categ_g = self.env.ref(
            'l10n_mx_edi_payslip.hr_salary_rule_category_perception_mx_taxed')
        categ_e = self.env.ref(
            'l10n_mx_edi_payslip.hr_salary_rule_category_perception_mx_exempt')
        perceptions = self.line_ids.filtered(
            lambda r: r.category_id in [categ_g, categ_e] and r.total and
            r.code[-3:] in ('022', '023', '025', '039', '044'))
        separation_line_ids = perceptions.filtered(
            lambda line: line.code[-3:] in ('022', '023', '025'))
        total = round(sum(separation_line_ids.mapped('total')), 2)
        if separation_line_ids and total:
            seniority = self.contract_id.get_seniority(date_to=self.date_to)
            years = round(seniority.get('years'), 0) if seniority.get(
                'months') > 6 or (seniority.get('months') == 6 and seniority
                                  .get('days') > 1) else seniority.get('years')
            nodes.append({
                'node': 'separation',
                'amount_total': total,
                'last_salary': self.contract_id.wage,
                'service_years': years,
                'non_accumulable_income': (total - self.contract_id.wage) if (
                    total > self.contract_id.wage) else 0,
                'accumulable_income': self.contract_id.wage if (
                    total > self.contract_id.wage) else total})
        retirement_line_ids = perceptions.filtered(
            lambda line: line.code[-3:] == '039')
        retirement_partial_ids = perceptions.filtered(
            lambda line: line.code[-3:] == '044')
        if retirement_line_ids and retirement_partial_ids:
            raise UserError(
                _("You have perceptions with code 039 and 044. "
                  "You can only have one of them."))
        retirement_line_ids = retirement_line_ids or retirement_partial_ids
        total = round(sum(retirement_line_ids.mapped('total')), 2)
        if retirement_line_ids and total:
            nodes.append({
                'node': 'retirement',
                'amount_total': total,
                'amount_daily': self.contract_id.wage/30 if (
                    retirement_line_ids[0].code[-3:] == '044') else 0,
                'non_accumulable_income': (total - self.contract_id.wage) if (
                    total > self.contract_id.wage) else 0,
                'accumulable_income': self.contract_id.wage if (
                    total > self.contract_id.wage) else total
            })
        self.l10n_mx_edi_extra_node_ids.unlink()
        return nodes

    @api.model
    def l10n_mx_edi_generate_cadena(self, xslt_path, cfdi_as_tree):
        """Generate the cadena of the cfdi based on an xslt file.
        The cadena is the sequence of data formed with the information
        contained within the cfdi. This can be encoded with the certificate
        to create the digital seal. Since the cadena is generated with the
        payslip data, any change in it will be noticed resulting in a different
        cadena and so, ensure the payslip has not been modified.
        :param xslt_path: The path to the xslt file.
        :type xslt_path: str
        :param cfdi_as_tree: The cfdi converted as a tree
        :type cfdi_as_tree: etree
        :return: A string computed with the payslip data called the cadena
        :rtype: str
        """
        # TODO - Same method that on invoice
        self.ensure_one()
        xslt_root = etree.parse(tools.file_open(xslt_path))
        return str(etree.XSLT(xslt_root)(cfdi_as_tree))

    def get_cfdi_related(self):
        """To node CfdiRelacionados get documents related with each payslip
        from l10n_mx_edi_origin, hope the next structure:
            relation type|UUIDs separated by ,"""
        # TODO - Same method that on invoice
        self.ensure_one()
        if not self.l10n_mx_edi_origin:
            return {}
        origin = self.l10n_mx_edi_origin.split('|')
        uuids = origin[1].split(',') if len(origin) > 1 else []
        return {
            'type': origin[0],
            'related': [u.strip() for u in uuids],
        }

    def l10n_mx_edi_is_required(self):
        self.ensure_one()
        company = self.company_id or self.contract_id.company_id
        return company.country_id == self.env.ref('base.mx')

    def l10n_mx_edi_log_error(self, message):
        # TODO - Same method that on invoice
        self.ensure_one()
        self.message_post(
            body=_('Error during the process: %s') % message,
            subtype='account.mt_invoice_validated')

    @api.model
    def _get_l10n_mx_edi_cadena(self):
        self.ensure_one()
        # get the xslt path
        xslt_path = CFDI_XSLT_CADENA
        # get the cfdi as eTree
        cfdi = self.l10n_mx_edi_get_xml_etree()
        # return the cadena
        return self.env['account.move'].l10n_mx_edi_generate_cadena(
            xslt_path, cfdi)

    # -------------------------------------------------------------------------
    # SAT/PAC service methods
    # -------------------------------------------------------------------------

    @api.model
    def _l10n_mx_edi_solfact_info(self, company_id, service_type):
        test = company_id.l10n_mx_edi_pac_test_env
        username = company_id.l10n_mx_edi_pac_username
        password = company_id.l10n_mx_edi_pac_password
        url = ('https://testing.solucionfactible.com/ws/services/Timbrado?wsdl'
               if test else
               'https://solucionfactible.com/ws/services/Timbrado?wsdl')
        return {
            'url': url,
            'multi': False,  # TODO: implement multi
            'username': 'testing@solucionfactible.com' if test else username,
            'password': 'timbrado.SF.16672' if test else password,
        }

    def _l10n_mx_edi_solfact_sign(self, pac_info):
        """SIGN for Solucion Factible.
        """
        url = pac_info['url']
        username = pac_info['username']
        password = pac_info['password']
        for record in self:
            cfdi = record.l10n_mx_edi_cfdi
            try:
                transport = Transport(timeout=20)
                client = Client(url, transport=transport)
                response = client.service.timbrar(
                    username, password, cfdi, False)
            except BaseException as e:
                record.l10n_mx_edi_log_error(str(e))
                continue
            msg = getattr(response.resultados[0], 'mensaje', None)
            code = getattr(response.resultados[0], 'status', None)
            xml_signed = getattr(response.resultados[0], 'cfdiTimbrado', None)
            record._l10n_mx_edi_post_sign_process(xml_signed, code, msg)

    def _l10n_mx_edi_solfact_cancel(self, pac_info):
        """CANCEL for Solucion Factible.
        """
        # TODO - Same method that on invoice
        url = pac_info['url']
        username = pac_info['username']
        password = pac_info['password']
        for record in self:
            uuids = [record.l10n_mx_edi_cfdi_uuid]
            certificate_id = record.sudo().l10n_mx_edi_cfdi_certificate_id
            cer_pem = base64.encodebytes(certificate_id.get_pem_cer(
                certificate_id.content))
            key_pem = base64.encodebytes(certificate_id.get_pem_key(
                certificate_id.key, certificate_id.password))
            key_password = certificate_id.password
            try:
                transport = Transport(timeout=20)
                client = Client(url, transport=transport)
                response = client.service.cancelar(
                    username, password, uuids, cer_pem, key_pem, key_password)
            except BaseException as e:
                record.l10n_mx_edi_log_error(str(e))
                continue
            msg = getattr(response.resultados[0], 'mensaje', None)
            code = getattr(response.resultados[0], 'statusUUID', None)
            cancelled = code in ('201', '202')
            record._l10n_mx_edi_post_cancel_process(cancelled, code, msg)

    def _l10n_mx_edi_finkok_info(self, company_id, service_type):
        test = company_id.l10n_mx_edi_pac_test_env
        username = company_id.l10n_mx_edi_pac_username
        password = company_id.l10n_mx_edi_pac_password
        if service_type == 'sign':
            url = (
                'http://demo-facturacion.finkok.com/servicios/soap/stamp.wsdl'
                if test else
                'http://facturacion.finkok.com/servicios/soap/stamp.wsdl')
        else:
            url = (
                'http://demo-facturacion.finkok.com/servicios/soap/cancel.wsdl'
                if test else
                'http://facturacion.finkok.com/servicios/soap/cancel.wsdl')
        return {
            'url': url,
            'multi': False,  # TODO: implement multi
            'username': 'cfdi@vauxoo.com' if test else username,
            'password': 'vAux00__' if test else password,
        }

    def _l10n_mx_edi_finkok_sign(self, pac_info):
        """SIGN for Finkok.
        """
        # TODO - Same method that on invoice
        url = pac_info['url']
        username = pac_info['username']
        password = pac_info['password']
        for record in self:
            cfdi = base64.decodestring(record.l10n_mx_edi_cfdi)
            try:
                transport = Transport(timeout=20)
                client = Client(url, transport=transport)
                response = client.service.stamp(cfdi, username, password)
            except BaseException as e:
                record.l10n_mx_edi_log_error(str(e))
                continue
            code = 0
            msg = None
            if response.Incidencias:
                code = getattr(
                    response.Incidencias.Incidencia[0], 'CodigoError', None)
                msg = getattr(
                    response.Incidencias.Incidencia[0],
                    'MensajeIncidencia', None)
            xml_signed = getattr(response, 'xml', None)
            if xml_signed:
                xml_signed = base64.b64encode(xml_signed.encode('utf-8'))
            record._l10n_mx_edi_post_sign_process(xml_signed, code, msg)

    def _l10n_mx_edi_finkok_cancel(self, pac_info):
        """CANCEL for Finkok.
        """
        url = pac_info['url']
        username = pac_info['username']
        password = pac_info['password']
        for record in self:
            uuid = record.l10n_mx_edi_cfdi_uuid
            certificate_id = record.sudo().l10n_mx_edi_cfdi_certificate_id
            company_id = self.company_id or self.contract_id.company_id
            cer_pem = base64.encodebytes(certificate_id.get_pem_cer(
                certificate_id.content)).decode('UTF-8')
            key_pem = base64.encodebytes(certificate_id.get_pem_key(
                certificate_id.key, certificate_id.password)).decode('UTF-8')
            cancelled = False
            code = False
            try:
                transport = Transport(timeout=20)
                client = Client(url, transport=transport)
                payslips_list = client.factory.create("UUIDS")
                uuid_type = client.get_type("ns0:stringArray")
                payslips_list = uuid_type([uuid])
                response = client.service.cancel(
                    payslips_list, username, password,
                    company_id.vat, cer_pem, key_pem)
            except BaseException as e:
                record.l10n_mx_edi_log_error(str(e))
                continue
            if not getattr(response, 'Folios', None):
                code = getattr(response, 'CodEstatus', None)
                msg = _("Cancelling got an error") if code else _(
                    'A delay of 2 hours has to be respected before to cancel')
            else:
                code = getattr(response.Folios[0][0], 'EstatusUUID', None)
                cancelled = code in ('201', '202')  # cancelled or previously cancelled  # noqa
                msg = '' if cancelled else _("Cancelling got an error")
                code = '' if cancelled else code
            record._l10n_mx_edi_post_cancel_process(cancelled, code, msg)

    def _l10n_mx_edi_call_service(self, service_type):
        """Call the right method according to the pac_name,
        it's info returned by the '_l10n_mx_edi_%s_info' % pac_name'
        method and the service_type passed as parameter.
        :param service_type: sign or cancel
        :type service_type: string
        """
        # Regroup the payslip by company (= by pac)
        comp_x_records = groupby(
            self, lambda r: r.company_id or r.contract_id.company_id)
        for company_id, records in comp_x_records:
            pac_name = company_id.l10n_mx_edi_pac
            if not pac_name:
                continue
            # Get the informations about the pac
            pac_info_func = '_l10n_mx_edi_%s_info' % pac_name
            service_func = '_l10n_mx_edi_%s_%s' % (pac_name, service_type)
            pac_info = getattr(self, pac_info_func)(company_id, service_type)
            # Call the service with payslips one by one or all together according to the 'multi' value.  # noqa
            multi = pac_info.pop('multi', False)
            if multi:
                # rebuild the recordset
                contract_ids = self.search(
                    [('company_id', '=', company_id.id)])
                records = self.search(
                    [('id', 'in', self.ids),
                     '|', ('company_id', '=', company_id.id),
                     ('contract_id', 'in', contract_ids.ids)])
                getattr(records, service_func)(pac_info)
            else:
                for record in records:
                    getattr(record, service_func)(pac_info)

    def _l10n_mx_edi_post_sign_process(self, xml_signed, code=None, msg=None):
        """Post process the results of the sign service.

        :param xml_signed: the xml signed datas codified in base64
        :type xml_signed: base64
        :param code: an eventual error code
        :type code: string
        :param msg: an eventual error msg
        :type msg: string
        """
        self.ensure_one()
        if xml_signed:
            body_msg = _('The sign service has been called with success')
            # Update the pac status
            self.l10n_mx_edi_pac_status = 'signed'
            self.l10n_mx_edi_cfdi = xml_signed
            # Update the content of the attachment
            attachment_id = self.l10n_mx_edi_retrieve_last_attachment()
            attachment_id.write({
                'datas': xml_signed,
                'mimetype': 'application/xml'
            })
            post_msg = [_('The content of the attachment has been updated')]
        else:
            body_msg = _('The sign service requested failed')
            post_msg = []
        if code:
            post_msg.extend([_('Code: ') + str(code)])
        if msg:
            post_msg.extend([_('Message: ') + msg])
        self.message_post(
            body=body_msg + create_list_html(post_msg),
            subtype='account.mt_invoice_validated')

    def _l10n_mx_edi_sign(self):
        """Call the sign service with records that can be signed.
        """
        records = self.search([
            ('l10n_mx_edi_pac_status', 'not in',
             ['signed', 'to_cancel', 'cancelled', 'retry']),
            ('id', 'in', self.ids)])
        records._l10n_mx_edi_call_service('sign')

    def _l10n_mx_edi_post_cancel_process(self, cancelled, code=None, msg=None):
        """Post process the results of the cancel service.

        :param cancelled: is the cancel has been done with success
        :type cancelled: bool
        :param code: an eventual error code
        :type code: string
        :param msg: an eventual error msg
        :type msg: string
        """

        self.ensure_one()
        if cancelled:
            body_msg = _('The cancel service has been called with success')
            self.l10n_mx_edi_pac_status = 'cancelled'
        else:
            body_msg = _('The cancel service requested failed')
        post_msg = []
        if code:
            post_msg.extend([_('Code: ') + str(code)])
        if msg:
            post_msg.extend([_('Message: ') + msg])
        self.message_post(
            body=body_msg + create_list_html(post_msg),
            subtype='account.mt_invoice_validated')

    def _l10n_mx_edi_cancel(self):
        """Call the cancel service with records that can be signed.
        """
        records = self.search([
            ('l10n_mx_edi_pac_status', 'in',
             ['to_sign', 'signed', 'to_cancel', 'retry']),
            ('id', 'in', self.ids)])
        for record in records:
            if record.l10n_mx_edi_pac_status in ['to_sign', 'retry']:
                record.l10n_mx_edi_pac_status = 'cancelled'
                record.message_post(body=_(
                    'The cancel service has been called with success'),
                    subtype='account.mt_invoice_validated')
            else:
                record.l10n_mx_edi_pac_status = 'to_cancel'
        records = self.search([
            ('l10n_mx_edi_pac_status', '=', 'to_cancel'),
            ('id', 'in', self.ids)])
        records._l10n_mx_edi_call_service('cancel')

    # -------------------------------------------------------------------------
    # Payslip methods
    # -------------------------------------------------------------------------

    @api.onchange('employee_id', 'struct_id', 'contract_id', 'date_from', 'date_to')  # noqa
    def _onchange_employee(self):
        res = super(HrPayslip, self)._onchange_employee()
        self.company_id = (self.employee_id.company_id or
                           self.contract_id.company_id or
                           self.env.user.company_id)
        return res

    def action_payslip_cancel(self):
        """Overwrite method when state is done, to allow cancel payslip in done
        """
        to_cancel = self.filtered(lambda r: r.state == 'done')
        to_cancel.write({'state': 'cancel'})
        self.refresh()
        res = super(HrPayslip, self).action_payslip_cancel()
        mx_payslip = self.filtered(lambda r: r.l10n_mx_edi_is_required())
        mx_payslip._l10n_mx_edi_cancel()
        return res

    def action_payroll_sent(self):
        """Open a window to compose an email, with the edi payslip template
        message loaded by default"""
        self.ensure_one()
        template = self.env.ref(
            'l10n_mx_edi_payslip.email_template_edi_payroll', False)
        compose_form = self.env.ref(
            'mail.email_compose_message_wizard_form', False)
        ctx = self._context.copy()
        ctx['default_model'] = 'hr.payslip'
        ctx['default_model'] = 'hr.payslip'
        ctx['default_res_id'] = self.id
        ctx['default_use_template'] = bool(template)
        ctx['default_template_id'] = template.id or False
        ctx['default_composition_mode'] = 'comment'
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    @api.depends('l10n_mx_edi_cfdi_name')
    def _compute_cfdi_values(self):
        """Fill the payroll fields from the CFDI values."""
        for record in self:
            attachment_id = record.l10n_mx_edi_retrieve_last_attachment()
            record.l10n_mx_edi_cfdi_uuid = None
            if not attachment_id:
                record.l10n_mx_edi_cfdi = None
                continue
            # At this moment, the attachment contains the file size in its
            # 'datas' field because to save some memory, the attachment will
            # store its data on the physical disk.
            # To avoid this problem, we read the 'datas' directly on the disk.
            datas = attachment_id._file_read(attachment_id.store_fname)
            record.l10n_mx_edi_cfdi = datas
            tree = record.l10n_mx_edi_get_xml_etree(base64.decodebytes(datas))
            # if already signed, extract uuid
            tfd_node = record.l10n_mx_edi_get_tfd_etree(tree)
            if tfd_node is not None:
                record.l10n_mx_edi_cfdi_uuid = tfd_node.get('UUID')
            record.l10n_mx_edi_cfdi_amount = tree.get(
                'Total', tree.get('total'))
            record.l10n_mx_edi_cfdi_supplier_rfc = tree.Emisor.get(
                'Rfc', tree.Emisor.get('rfc'))
            record.l10n_mx_edi_cfdi_customer_rfc = tree.Receptor.get(
                'Rfc', tree.Receptor.get('rfc'))
            record.l10n_mx_edi_cfdi_certificate_id = self.env[
                'l10n_mx_edi.certificate'].sudo().search([
                    ('serial_number', '=', tree.get(
                        'NoCertificado', tree.get('noCertificado')))],
                    limit=1)

    def action_payslip_draft(self):
        for record in self.filtered('l10n_mx_edi_cfdi_uuid'):
            record.l10n_mx_edi_origin = '04|%s' % record.l10n_mx_edi_cfdi_uuid
        self.write({
            'l10n_mx_edi_expedition_date': False,
            'l10n_mx_edi_time_payslip': False,
        })
        return super(HrPayslip, self).action_payslip_draft()

    def action_payslip_done(self):
        """Generates the cfdi attachments for mexican companies when validated.
        """
        result = super(HrPayslip, self).action_payslip_done()
        for record in self.filtered(lambda r: r.l10n_mx_edi_is_required()):
            company = record.company_id or record.contract_id.company_id
            partner = company.partner_id.commercial_partner_id
            tz = self.env['account.move']._l10n_mx_edi_get_timezone(
                partner.state_id.code)
            date_mx = fields.datetime.now(tz)
            if not record.l10n_mx_edi_expedition_date:
                record.l10n_mx_edi_expedition_date = date_mx.date()
            if not record.l10n_mx_edi_time_payslip:
                record.l10n_mx_edi_time_payslip = date_mx.strftime(
                    DEFAULT_SERVER_TIME_FORMAT)
            record.l10n_mx_edi_cfdi_name = ('%s-MX-Payroll-3-3.xml' % (
                record.number)).replace('/', '')
            record._l10n_mx_edi_retry()
        return result

    def compute_sheet(self):
        if (self.filtered(lambda r: r.l10n_mx_edi_is_required()) and
                not self.env.user.company_id.l10n_mx_edi_minimum_wage):
            raise ValidationError(_(
                'Please, you set the minimum wage in Mexico to that you '
                'can calculate the payroll'))
        res = super(HrPayslip, self).compute_sheet()
        for payslip in self:
            payslip.write({
                'l10n_mx_edi_extra_node_ids': [
                    (0, 0, node) for node in payslip._get_extra_nodes()]})
        return res

    def _l10n_mx_edi_retry(self):
        """Try to generate the cfdi attachment and then, sign it."""
        for record in self:
            cfdi_values = record._l10n_mx_edi_create_cfdi()
            error = cfdi_values.pop('error', None)
            cfdi = cfdi_values.pop('cfdi', None)
            if error:
                # cfdi failed to be generated
                record.l10n_mx_edi_pac_status = 'retry'
                record.message_post(body=error)
                continue
            # cfdi has been successfully generated
            record.l10n_mx_edi_pac_status = 'to_sign'

            ctx = self.env.context.copy()
            ctx.pop('default_type', False)
            filename = (
                '%s-MX-Payroll-3-3.xml' % (record.number)).replace('/', '')
            record.l10n_mx_edi_cfdi_name = filename
            attach_id = self.env['ir.attachment'].with_context(ctx).create({
                'name': filename,
                'res_id': record.id,
                'res_model': record._name,
                'datas': base64.encodebytes(cfdi),
                'description': 'Mexican payroll',
            })
            record.message_post(
                body=_('CFDI document generated (may be not signed)'),
                attachment_ids=[attach_id.id])
            record._l10n_mx_edi_sign()

    @api.model
    def l10n_mx_edi_retrieve_attachments(self):
        """Retrieve all the CFDI attachments generated for this payroll.
        Returns:
            recordset: An ir.attachment recordset"""
        self.ensure_one()
        if not self.l10n_mx_edi_cfdi_name:
            return []
        domain = [
            ('res_id', '=', self.id),
            ('res_model', '=', self._name),
            ('name', '=', self.l10n_mx_edi_cfdi_name)]
        return self.env['ir.attachment'].search(domain)

    @api.model
    def l10n_mx_edi_retrieve_last_attachment(self):
        attachment_ids = self.l10n_mx_edi_retrieve_attachments()
        return attachment_ids[0] if attachment_ids else None

    @api.model
    def l10n_mx_edi_get_xml_etree(self, cfdi=None):
        """Get an objectified tree representing the cfdi.
        If the cfdi is not specified, retrieve it from the attachment.
        :param str cfdi: The cfdi as string
        :type: str
        :return: An objectified tree
        :rtype: objectified"""
        # TODO helper which is not of too much help and should be removed
        self.ensure_one()
        if cfdi is None:
            cfdi = base64.decodebytes(self.l10n_mx_edi_cfdi)
        return objectify.fromstring(cfdi)

    @staticmethod
    def _l10n_mx_get_serie_and_folio(number):
        # TODO - Same method on invoice
        values = {'serie': None, 'folio': None}
        number_matchs = [rn for rn in re.finditer(r'\d+', number or '')]
        if number_matchs:
            last_number_match = number_matchs[-1]
            values['serie'] = number[:last_number_match.start()] or None
            values['folio'] = last_number_match.group().lstrip('0') or None
        return values

    @staticmethod
    def _get_string_cfdi(text, size=100):
        """Replace from text received the characters that are not found in the
        regex. This regex is taken from SAT documentation
        https://goo.gl/C9sKH6
        text: Text to remove extra characters
        size: Cut the string in size len
        Ex. 'Product ABC (small size)' - 'Product ABC small size'"""
        if not text:
            return None
        text = text.replace('|', ' ')
        return text.strip()[:size]

    def _l10n_mx_edi_create_cfdi_values(self):
        """Create the values to fill the CFDI template."""
        self.ensure_one()
        payroll = self._l10n_mx_edi_create_payslip_values()
        if payroll.get('error', False):
            return payroll
        subtotal = payroll['total_other'] + payroll['total_perceptions']
        deduction = payroll['total_deductions']
        company = self.company_id or self.contract_id.company_id
        values = {
            'record': self,
            'supplier': company.partner_id.commercial_partner_id,
            'customer': self.employee_id.address_home_id.commercial_partner_id,
            'amount_untaxed': '%.2f' % abs(subtotal or 0.0),
            'amount_discount': '%.2f' % abs(deduction or 0.0),
            'taxes': {},
            'outsourcing': [],  # TODO - How set the outsourcing?
        }

        values.update(self._l10n_mx_get_serie_and_folio(self.number))

        values.update(payroll)
        return values

    def _l10n_mx_edi_create_payslip_values(self):
        self.ensure_one()
        employee = self.employee_id
        if not self.contract_id:
            return {'error': _('Employee has not a contract and is required')}
        seniority = self.contract_id.get_seniority(
            date_to=self.date_to)['days'] / 7
        payroll = {
            'record': self,
            'company': self.company_id or self.contract_id.company_id,
            'employee': self.employee_id,
            'payslip_type': 'O',
            'number_of_days': int(sum(self.worked_days_line_ids.mapped(
                'number_of_days'))),
            'date_start': self.contract_id.date_start,
            'seniority_emp': 'P%sW' % int(seniority),
        }
        payroll.update(employee.get_cfdi_employee_data(self.contract_id))
        payroll.update(self.get_cfdi_perceptions_data())
        payroll.update(self.get_cfdi_deductions_data())
        payroll.update(self.get_cfdi_other_payments_data())
        return payroll

    def get_cfdi_perceptions_data(self):
        categ_g = self.env.ref(
            'l10n_mx_edi_payslip.hr_salary_rule_category_perception_mx_taxed')
        categ_e = self.env.ref(
            'l10n_mx_edi_payslip.hr_salary_rule_category_perception_mx_exempt')
        perceptions = self.line_ids.filtered(
            lambda r: r.category_id in [categ_g, categ_e] and r.total)
        total_taxed = round(sum(perceptions.filtered(
            lambda r: r.category_id == categ_g).mapped('total')), 2)
        total_exempt = round(sum(perceptions.filtered(
            lambda r: r.category_id == categ_e).mapped('total')), 2)
        total_salaries = round(sum(perceptions.filtered(
            lambda r: r.code[-3:] not in [
                '022', '023', '025', '039', '044']).mapped('total')), 2)
        total_compensation = round(sum(perceptions.filtered(
            lambda r: r.code[-3:] in ['022', '023', '025']).mapped(
                'total')), 2)
        total_retirement = sum(perceptions.filtered(
            lambda r: r.code[-3:] in ['039', '044']).mapped('total'))
        values = {
            'total_salaries': total_salaries,
            'total_compensation': total_compensation,
            'total_retirement': total_retirement,
            'total_taxed': total_taxed,
            'total_exempt': total_exempt,
            'total_perceptions': (
                total_salaries + total_compensation + total_retirement),
            'category_taxed': categ_g,
            'category_exempt': categ_e,
            'perceptions': perceptions,
        }
        # if the payslip contains only bonus or separation payments,
        # it is of Type "E"
        if (perceptions.filtered(lambda r: r.code[-3:] in ['002', '023']) and
                not perceptions.filtered(lambda r: r.code[-3:] in ['001'])):
            values.update({
                'payslip_type': 'E',
            })
        return values

    def get_cfdi_deductions_data(self):
        categ = self.env.ref(
            'l10n_mx_edi_payslip.hr_salary_rule_category_deduction_mx')
        deductions = self.line_ids.filtered(
            lambda r: r.category_id == categ and r.amount)
        total = sum(deductions.mapped('total'))
        total_other = sum(deductions.filtered(
            lambda r: r.code[-3:] != '002').mapped('total'))
        total_withheld = sum(deductions.filtered(
            lambda r: r.code[-3:] == '002').mapped('total'))
        return {
            'total_deductions': abs(total),
            'total_other_deductions': abs(total_other),
            'total_taxes_withheld': '%.2f' % abs(total_withheld) if total_withheld else None,  # noqa
            'deductions': deductions,
        }

    def get_cfdi_other_payments_data(self):
        """Records with category Other Payments are used in the node
        "OtrosPagos"."""
        categ = self.env.ref(
            'l10n_mx_edi_payslip.hr_salary_rule_category_other_mx')
        other_payments = self.line_ids.filtered(
            lambda r: r.category_id == categ and r.amount)
        return {
            'total_other': abs(sum(other_payments.mapped('total'))),
            'other_payments': other_payments,
        }

    def _l10n_mx_edi_create_cfdi(self):
        """Creates and returns a dictionary containing 'cfdi' if the cfdi is
        well created, 'error' otherwise."""
        self.ensure_one()
        qweb = self.env['ir.qweb']
        error_log = []
        company_id = self.company_id or self.contract_id.company_id
        pac_name = company_id.l10n_mx_edi_pac
        values = self._l10n_mx_edi_create_cfdi_values()

        # -----------------------
        # Check the configuration
        # -----------------------
        # - Check not errors in values generation
        if values.get('error'):
            error_log.append(values.get('error'))

        # -Check certificate
        certificate_ids = company_id.l10n_mx_edi_certificate_ids
        certificate_id = certificate_ids.sudo().get_valid_certificate()
        if not certificate_id:
            error_log.append(_('No valid certificate found'))

        # -Check PAC
        if pac_name:
            pac_test_env = company_id.l10n_mx_edi_pac_test_env
            pac_password = company_id.l10n_mx_edi_pac_password
            if not pac_test_env and not pac_password:
                error_log.append(_('No PAC credentials specified.'))
        else:
            error_log.append(_('No PAC specified.'))

        if error_log:
            return {'error': _(
                'Please check your configuration: ') + create_list_html(
                    error_log)}

        # -----------------------
        # Create the EDI document
        # -----------------------

        # -Compute certificate data
        time_payslip = fields.datetime.strptime(
            self.l10n_mx_edi_time_payslip, DEFAULT_SERVER_TIME_FORMAT).time()
        values['date'] = fields.datetime.combine(
            fields.Datetime.from_string(self.l10n_mx_edi_expedition_date),
            time_payslip).strftime('%Y-%m-%dT%H:%M:%S')
        values['certificate_number'] = certificate_id.serial_number
        values['certificate'] = certificate_id.sudo().get_data()[0]

        # -Compute cfdi
        cfdi = qweb.render(PAYSLIP_TEMPLATE, values=values)

        # -Compute cadena
        tree = self.l10n_mx_edi_get_xml_etree(cfdi)
        cadena = self.l10n_mx_edi_generate_cadena(CFDI_XSLT_CADENA, tree)

        # Post append cadena
        tree.attrib['Sello'] = certificate_id.sudo().get_encrypted_cadena(
            cadena)

        # Check with xsd
        attachment = self.env.ref('l10n_mx_edi.xsd_cached_cfdv33_xsd', False)
        xsd_datas = base64.b64decode(attachment.datas) if attachment else b''
        if xsd_datas:
            try:
                with BytesIO(xsd_datas) as xsd:
                    _check_with_xsd(tree, xsd)
            except (IOError, ValueError):
                _logger.info(_('The xsd file to validate the XML structure '
                               'was not found'))
            except BaseException as e:
                return {'error': (_('The cfdi generated is not valid') +
                                  create_list_html(str(e).split('\\n')))}

        return {'cfdi': etree.tostring(
            tree, pretty_print=True, xml_declaration=True, encoding='UTF-8')}

    def l10n_mx_edi_update_pac_status(self):
        """Synchronize both systems: Odoo & PAC if the payrolls need to be
        signed or cancelled."""
        for record in self:
            if record.l10n_mx_edi_pac_status in ('to_sign', 'retry'):
                record._l10n_mx_edi_retry()
            elif record.l10n_mx_edi_pac_status == 'to_cancel':
                record._l10n_mx_edi_cancel()

    def l10n_mx_edi_update_sat_status(self):
        """Synchronize both systems: Odoo & SAT to make sure the payroll is
        valid."""
        url = 'https://consultaqr.facturaelectronica.sat.gob.mx/ConsultaCFDIService.svc?wsdl'  # noqa
        headers = {'SOAPAction':
                   'http://tempuri.org/IConsultaCFDIService/Consulta',
                   'Content-Type': 'text/xml; charset=utf-8'}
        template = """<?xml version="1.0" encoding="UTF-8"?>
                      <SOAP-ENV:Envelope xmlns:ns0="http://tempuri.org/"
                       xmlns:ns1="http://schemas.xmlsoap.org/soap/envelope/"
                       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                       xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
                      <SOAP-ENV:Header/>
                      <ns1:Body>
                      <ns0:Consulta>
                          <ns0:expresionImpresa>?%s</ns0:expresionImpresa>
                      </ns0:Consulta>
                      </ns1:Body>
                      </SOAP-ENV:Envelope>"""
        namespace = {'a': 'http://schemas.datacontract.org/2004/07/'
                     'Sat.Cfdi.Negocio.ConsultaCfdi.Servicio'}
        cfdi_sat_status = {
            'No Encontrado': 'not_found',
            'Cancelado': 'cancelled',
            'Vigente': 'valid',
        }
        for record in self:
            if record.l10n_mx_edi_pac_status not in ['signed', 'cancelled']:
                continue
            supplier_rfc = record.l10n_mx_edi_cfdi_supplier_rfc
            customer_rfc = record.l10n_mx_edi_cfdi_customer_rfc
            total = record.l10n_mx_edi_cfdi_amount
            uuid = record.l10n_mx_edi_cfdi_uuid
            params = url_encode({
                're': supplier_rfc,
                'rr': customer_rfc,
                'tt': total,
                'id': uuid}, separator='&amp;')
            soap_env = template % (params)
            try:
                soap_xml = requests.post(url, data=soap_env, headers=headers)
                response = objectify.fromstring(soap_xml.text)
                status = response.xpath('//a:Estado', namespaces=namespace)
            except BaseException as e:  # pragma: no cover
                record.l10n_mx_edi_log_error(str(e) or e.reason.__repr__())  # noqa pragma: no cover
                continue  # pragma: no cover
            record.l10n_mx_edi_sat_status = cfdi_sat_status.get(
                status[0] if status else False, 'none')

    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        """Overwrite WORK100 to get all days
        """
        result = super(HrPayslip, self).get_worked_day_lines(
            contracts=contracts, date_from=date_from, date_to=date_to)
        res = []
        for line in result:
            if line.get('code') == 'WORK100':
                continue
            res.append(line)
        for contract in contracts.filtered(
                lambda contract: contract.resource_calendar_id):
            day_from = fields.datetime.combine(
                fields.Date.from_string(date_from), fields.datetime.min.time())
            day_to = fields.datetime.combine(
                fields.Date.from_string(date_to), fields.datetime.max.time())

            # compute leave days
            calendar = contract.resource_calendar_id
            tz = timezone(calendar.tz)
            day_leave_intervals = contract.employee_id.list_leaves(
                day_from, day_to, calendar=contract.resource_calendar_id)
            current_leave_days = 0
            for day, hours, leave in day_leave_intervals:
                work_hours = calendar.get_work_hours_count(
                    tz.localize(fields.datetime.combine(
                        day, fields.datetime.min.time())),
                    tz.localize(fields.datetime.combine(
                        day, fields.datetime.max.time())),
                    compute_leaves=False,
                )
                if work_hours:
                    current_leave_days += hours / work_hours

            # compute worked days
            work_data = contract.get_seniority(day_from, day_to)
            attendances = {
                'name': _("Normal Working Days paid at 100%"),
                'sequence': 1,
                'code': 'WORK100',
                'number_of_days': work_data['days'] + 1 - current_leave_days,
                'contract_id': contract.id,
            }

            res.append(attendances)
        return res

    def l10n_mx_edi_is_last_payslip(self):
        """Check if the date to in the payslip is the last of the current month
        and return True in that case, to know that is the last payslip"""
        if not self:
            return False
        self.ensure_one()
        if not self.date_to:
            return False
        if self.date_to.day == monthrange(
                self.date_to.year, self.date_to.month)[1]:
            return True
        return False


class HrEmployee(models.Model):

    _inherit = "hr.employee"

    l10n_mx_edi_syndicated = fields.Boolean(
        'Syndicated', help='Used in the XML to indicate if the worker is '
        'associated with a union. If it is omitted, it is assumed that it is '
        'not associated with any union.')
    l10n_mx_edi_risk_rank = fields.Many2one(
        'l10n_mx_edi.job.risk', 'Job Risk',
        help='Used in the XML to express the key according to the Class in '
        'which the employers must register, according to the activities '
        'carried out by their workers, as provided in article 196 of the '
        'Regulation on Affiliation Classification of Companies, Collection '
        'and Inspection, or in accordance with the regulations Of the Social '
        'Security Institute of the worker.')
    l10n_mx_edi_contract_regime_type = fields.Selection([
        ('02', 'Sueldos'),
        ('03', 'Jubilados'),
        ('04', 'Pensionados'),
        ('05', 'Asimilados Miembros Sociedades Cooperativas Produccion'),
        ('06', 'Asimilados Integrantes Sociedades Asociaciones Civiles'),
        ('07', 'Asimilados Miembros consejos'),
        ('08', 'Asimilados comisionistas'),
        ('09', 'Asimilados Honorarios'),
        ('10', 'Asimilados acciones'),
        ('11', 'Asimilados otros'),
        ('99', 'Otro Regimen')
    ])
    l10n_mx_edi_is_assimilated = fields.Boolean(
        'Is assimilated?', help='If this employee is assimilated, must be '
        'used this option, to get the correct rules on their payslips')

    def get_cfdi_employee_data(self, contract):
        self.ensure_one()
        return {
            'contract_type': contract.l10n_mx_edi_contract_type,
            'emp_syndicated': 'Sí' if self.l10n_mx_edi_syndicated else 'No',
            'working_day': self.get_working_date(),
            'emp_diary_salary': '%.2f' % contract.
            l10n_mx_edi_integrated_salary,
        }

    def get_working_date(self):
        """Based on employee category, verify if a category set in this
        employee come from this module and get code."""
        category = self.category_ids.filtered(lambda r: r.color == 3)
        if not category or not category[0].get_external_id()[
                category[0].id].startswith('l10n_mx_edi_payslip'):
            return ''
        return category[0].name[:2]


class HrPayslipOvertime(models.Model):
    _name = 'hr.payslip.overtime'
    _description = 'Pay Slip overtime'

    name = fields.Char('Description', required=True)
    payslip_id = fields.Many2one(
        'hr.payslip', required=True, ondelete='cascade',
        help='Payslip related.')
    days = fields.Integer(
        help="Number of days in which the employee performed overtime in the "
        "period", required=True)
    hours = fields.Integer(
        help="Number of overtime hours worked in the period", required=True)
    overtime_type = fields.Selection([
        ('01', 'Double'),
        ('02', 'Triples'),
        ('03', 'Simples')], 'Type', required=True, default='01',
        help='Used to express the type of payment of the hours extra.')
    amount = fields.Float(
        help="Amount paid for overtime", required=True, default=0.0)


class HrPayslipActionTitles(models.Model):
    _name = 'hr.payslip.action.titles'
    _description = 'Pay Slip action titles'

    payslip_id = fields.Many2one(
        'hr.payslip', required=True, ondelete='cascade',
        help='Payslip related.')
    category_id = fields.Many2one(
        'hr.salary.rule.category', 'Category', required=True,
        help='Indicate to which perception will be added this attributes in '
        'node XML')
    market_value = fields.Float(
        help='When perception type is 045 this value must be assigned in the '
        'line. Will be used in node "AccionesOTitulos" to the attribute '
        '"ValorMercado"', required=True)
    price_granted = fields.Float(
        help='When perception type is 045 this value must be assigned in the '
        'line. Will be used in node "AccionesOTitulos" to the attribute '
        '"PrecioAlOtorgarse"', required=True)


class HrPayslipExtraPerception(models.Model):
    _name = 'hr.payslip.extra.perception'
    _description = 'Pay Slip extra perception'

    payslip_id = fields.Many2one(
        'hr.payslip', required=True, ondelete='cascade',
        help='Payslip related.')
    node = fields.Selection(
        [('retirement', 'JubilacionPensionRetiro'),
         ('separation', 'SeparacionIndemnizacion')], help='Indicate what is '
        'the record purpose, if will be used to add in node '
        '"JubilacionPensionRetiro" or in "SeparacionIndemnizacion"')
    amount_total = fields.Float(
        help='If will be used in the node "JubilacionPensionRetiro" and '
        'will be used to one perception with code "039", will be used to '
        'the attribute "TotalUnaExhibicion", if will be used to one '
        'perception with code "044", will be used to the attribute '
        '"TotalParcialidad". If will be used in the node '
        '"SeparacionIndemnizacion" will be used in attribute "TotalPagado"')
    amount_daily = fields.Float(
        help='Used when will be added in node "JubilacionPensionRetiro", to '
        'be used in attribute "MontoDiario"')
    accumulable_income = fields.Float(
        help='Used to both nodes, each record must be have the valor to each '
        'one.')
    non_accumulable_income = fields.Float(
        help='Used to both nodes, each record must be have the valor to each '
        'one.')
    service_years = fields.Integer(
        help='Used when will be added in node "SeparacionIndemnizacion", to '
        'be used in attribute "NumAñosServicio"')
    last_salary = fields.Float(
        help='Used when will be added in node "SeparacionIndemnizacion", to '
        'be used in attribute "UltimoSueldoMensOrd"')


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    l10n_mx_edi_payment_date = fields.Date(
        'Payment Date', required=True,
        default=time.strftime('%Y-%m-01'), help='Save the payment date that '
        'will be added on all payslip created with this batch.')

    def action_payslips_done(self):
        self.ensure_one()
        # using search instead of filtered to keep performance in batch with many payslips  # noqa
        payslips = self.slip_ids.search(
            [('id', 'in', self.slip_ids.ids), ('state', '=', 'draft')])
        for payslip in payslips:
            try:
                with self.env.cr.savepoint():
                    payslip.action_payslip_done()
            except UserError as e:
                payslip.message_post(
                    body=_('Error during the process: %s') % e)
        retry_payslips = (self.slip_ids - payslips).filtered(
            lambda r: r.l10n_mx_edi_pac_status in [
                'retry', 'to_sign', 'to_cancel'])
        retry_payslips.l10n_mx_edi_update_pac_status()

    def action_payroll_sent(self):
        """Send email for all signed payslips"""
        self.ensure_one()
        template = self.env.ref(
            'l10n_mx_edi_payslip.email_template_edi_payroll', False)
        mail_composition = self.env['mail.compose.message']
        for payslip in self.slip_ids.filtered(
            lambda p: (p.state == 'done' and not p.sent and
                       p.l10n_mx_edi_pac_status == 'signed' and
                       p.employee_id.work_email)):
            res = mail_composition.create({
                'model': 'hr.payslip',
                'res_id': payslip.id,
                'template_id': template and template.id or False,
                'composition_mode': 'comment'})
            res.onchange_template_id_wrapper()
            mail_composition |= res
        # send all
        mail_composition.action_send_mail()
