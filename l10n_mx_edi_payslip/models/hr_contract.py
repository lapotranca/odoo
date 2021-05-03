# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from math import floor
from dateutil.relativedelta import relativedelta

from odoo import fields, models, _


class HrContract(models.Model):
    _inherit = 'hr.contract'

    l10n_mx_edi_holidays = fields.Integer(
        string="Days of holidays", default=6, track_visibility='onchange',
        help="Initial number of days for holidays. The minimum is 6 days.")
    l10n_mx_edi_vacation_bonus = fields.Integer(
        string="Vacation bonus (%)", default=25, track_visibility='onchange',
        help="Percentage of vacation bonus. The minimum is 25 %.")
    l10n_mx_edi_christmas_bonus = fields.Integer(
        string="Christmas bonus (days)", default=15, help="Number of day for "
        "the Christmas bonus. The minimum is 15 days' pay",
        track_visibility='onchange')
    l10n_mx_edi_integrated_salary = fields.Float(
        'Integrated Salary', track_visibility='onchange',
        help='Used in the CFDI to express the salary '
        'that is integrated with the payments made in cash by daily quota, '
        'gratuities, perceptions, room, premiums, commissions, benefits in '
        'kind and any other quantity or benefit that is delivered to the '
        'worker by his work, Pursuant to Article 84 of the Federal Labor '
        'Law. (Used to calculate compensation).')
    l10n_mx_edi_sdi_variable = fields.Float(
        'Variable SDI', default=0, track_visibility='onchange',
        help='Used when the salary type is mixed or variable. This value is '
        'integrated by the sum of perceptions in the previous two months and '
        'divided by the number of days worked. Also, it affects the '
        'integrated salary value.')
    # Overwrite options & default
    l10n_mx_edi_schedule_pay = fields.Selection([
        ('01', 'Daily'),
        ('02', 'Weekly'),
        ('03', 'Biweekly'),
        ('04', 'Fortnightly'),
        ('05', 'Monthly'),
        ('06', 'Bimonthly'),
        ('07', 'Unit work'),
        ('08', 'Commission'),
        ('09', 'Raised price'),
        ('10', 'Decennial'),
        ('99', 'Other')], default='02', string=' Schedule Pay')

    l10n_mx_edi_contract_type = fields.Selection([
        ('01', 'Contrato de trabajo por tiempo indeterminado'),
        ('02', 'Contrato de trabajo para obra determinada'),
        ('03', 'Contrato de trabajo por tiempo determinado'),
        ('04', 'Contrato de trabajo por temporada'),
        ('05', 'Contrato de trabajo sujeto a prueba'),
        ('06', 'Contrato de trabajo con capacitación inicial'),
        ('07', 'Modalidad de contratación por pago de hora laborada'),
        ('08', 'Modalidad de trabajo por comisión laboral'),
        ('09', 'Modalidades de contratación donde no existe relación de '
         'trabajo'),
        ('10', 'Jubilación, pensión, retiro'),
        ('99', 'Otro contrato')], string='Contract Type')
    l10n_mx_edi_integrated_salary = fields.Float(
        'Integrated Salary', track_visibility='onchange',
        help='Used in the CFDI to express the salary '
        'that is integrated with the payments made in cash by daily quota, '
        'gratuities, perceptions, room, premiums, commissions, benefits in '
        'kind and any other quantity or benefit that is delivered to the '
        'worker by his work, Pursuant to Article 84 of the Federal Labor '
        'Law. (Used to calculate compensation).')

    l10n_mx_edi_infonavit_type = fields.Selection(
        [('percentage', _('Percentage')),
         ('vsm', _('Number of minimum wages')),
         ('fixed_amount', _('Fixed amount')), ],
        string='INFONAVIT discount', help="INFONAVIT discount type that "
        "is calculated in the employee's payslip")
    l10n_mx_edi_infonavit_rate = fields.Float(
        string='Infonavit rate', help="Value to be deducted in the employee's"
        " payment for the INFONAVIT concept.This depends on the INFONAVIT "
        "discount type as follows: \n- If the type is percentage, then the "
        "value of this field can be 1 - 100 \n- If the type is number of "
        "minimum wages, the value of this field may be 1 - 25, since it is "
        "\n- If the type is a fixed story, the value of this field must be "
        "greater than zero. In addition, the amount of this deduction must "
        "correspond to the payment period.")

    def compute_integrated_salary(self):
        """Compute Daily Salary Integrated according to Mexican laws"""
        # the integrated salary cannot be more than 25 UMAs
        max_sdi = self.company_id.l10n_mx_edi_uma * 25
        for record in self:
            sdi = record._get_static_SDI() + (
                record.l10n_mx_edi_sdi_variable or 0)
            # the integrated salary cannot be less than 1 minimum wages
            sdi = self.company_id.l10n_mx_edi_minimum_wage if (
                sdi < self.company_id.l10n_mx_edi_minimum_wage) else sdi
            sdi = sdi if sdi < max_sdi else max_sdi
            record.l10n_mx_edi_integrated_salary = sdi

    def _get_static_SDI(self):
        """Get the integrated salary for the static perceptions like:
            - Salary
            - holidays
            - Christmas bonus
        """
        self.ensure_one()
        return self.wage / 30 * self._get_integration_factor()

    def _get_integration_factor(self):
        """get the factor used to get the static integrated salary
        overwrite to add new static perceptions.
        factor = 1 + static perceptions/365
        new_factor = factor + new_perception / 365
        """
        self.ensure_one()
        vacation_bonus = (self.l10n_mx_edi_vacation_bonus or 25) / 100
        holidays = self.get_current_holidays() * vacation_bonus
        bonus = self.l10n_mx_edi_christmas_bonus or 15
        return 1 + (holidays + bonus)/365

    def get_current_holidays(self):
        """return number of days according with the seniority and holidays"""
        self.ensure_one()
        holidays = self.l10n_mx_edi_holidays or 6
        seniority = self.get_seniority()['years']
        if seniority < 4:
            return holidays + 2 * (seniority)
        return holidays + 6 + 2 * floor((seniority + 1) / 5)

    def get_seniority(self, date_from=False, date_to=False, method='r'):
        """Return seniority between contract's date_start and date_to or today

        :param date_from: start date (default contract.date_start)
        :type date_from: str
        :param date_to: end date (default today)
        :type date_to: str
        :param method: {'r', 'a'} kind of values returned
        :type method: str
        :return: a dict with the values years, months, days.
            These values can be relative or absolute.
        :rtype: dict
        """
        self.ensure_one()
        datetime_start = date_from or self.date_start
        date = date_to or fields.Date.today()
        relative_seniority = relativedelta(date, datetime_start)
        if method == 'r':
            return {'years': relative_seniority.years,
                    'months': relative_seniority.months,
                    'days': relative_seniority.days}
        return {'years': relative_seniority.years,
                'months': (relative_seniority.months + relative_seniority
                           .years * 12),
                'days': (date - datetime_start).days + 1}

    @staticmethod
    def _l10n_mx_edi_get_days(date_start, date_end):
        """Given two dates return the days elapsed between both dates"""
        date_start = fields.Date.from_string(date_start)
        date = fields.Date.from_string(date_end)
        days_work = ((date - date_start).days - 1)
        return 0 if days_work < 0 else days_work

    def _get_days_in_current_period(self, date_to=False, start_year=False):
        """Get days at current period to compute payments' proportional part

        :param date_to: date to get the days
        :type date_to: str
        :param start_year: period start at 1 Jan
        :type start_year: boolean
        :return: number of days of the contract in current period
        :rtype: int
        """
        date = date_to or fields.Date.today()
        contract_date = self.date_start
        if start_year:
            date_start = fields.date(date.year, 1, 1)
            if (contract_date - date_start).days > 0:
                date_start = contract_date
            return (date - date_start).days + 1
        date_start = fields.date(
            contract_date.year, contract_date.month, contract_date.day)
        if (date - date_start).days < 0:
            date_start = fields.date(
                date.year - 1, contract_date.month, contract_date.day)
        return (date - date_start).days + 1


class L10nMxEdiJobRank(models.Model):
    _name = "l10n_mx_edi.job.risk"
    _description = "Used to define the percent of each job risk."

    name = fields.Char(help='Job risk provided by the SAT.')
    code = fields.Char(help='Code assigned by the SAT for this job risk.')
    percentage = fields.Float(help='Percentage for this risk, is used in the '
                              'payroll rules.')
