# -*- coding: utf-8 -*-

from odoo import models, fields, api

class as_sale_order(models.Model):
    _inherit = "sale.order.line"

    # @api.onchange('regiones_id')
    # def compute_regiones(self):
    #     for rec in self:
    #         return {'domain': {
    #             'department_id': [('id', 'in', rec.regiones_id.cost_center_id.ids)]
    #         }}

    # @api.onchange('cost_center_id')
    # def compute_department(self):
    #     for rec in self:
    #         return {'domain': {
    #             'department_id': [('id', 'in', rec.cost_center_id.department_ids.ids)]
    #         }}


    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    regiones_id = fields.Many2one('tf.regiones', string='Región')
    cost_center_id = fields.Many2one('tf.cost.center', 'Cost Center')
    department_id = fields.Many2one('tf.department', string='Departments')
    as_laboratorio = fields.Selection(selection=[
        ('SERVICIOS','SERVICIOS'),
        ('ACEROS NACIONALES','ACEROS NACIONALES'),
        ('ANDOCI','ANDOCI'),
        ('ARANDA','ARANDA'),
        ('BAYER','BAYER'),
        ('OSATU','OSATU'),
        ('CORTEVA','CORTEVA'),
        ('QUALYMILK','QUALYMILK'),
        ('CHINOIN','CHINOIN'),
        ('GALLAGHER','GALLAGHER'),
        ('MSD antes intervet','MSD antes intervet'),
        ('LAPISA','LAPISA'),
        ('CUAJOS','CUAJOS'),
        ('NOVARTIS','NOVARTIS'),
        ('PANAMERICANA','PANAMERICANA'),
        ('PARFARM','PARFARM'),
        ('REPRODUCCIÓN ANIMAL','REPRODUCCIÓN ANIMAL'),
        ('ROTOPLAS','ROTOPLAS'),
        ('SANFER','SANFER'),
        ('TALABARTERIA','TALABARTERIA'),
        ('TORNELL','TORNELL'),
        ('TRUPER','TRUPER'),
        ('BOEHRINGER','BOEHRINGER'),
        ('VETOQUINOL','VETOQUINOL'),
        ('WITTNEY','WITTNEY'),
        ('ZIRIN','ZIRIN'),
        ('VARIOS','VARIOS'),
        ('SEMILLAS','SEMILLAS'),
        ('ACCESORIOS','ACCESORIOS'),
        ('ZOETIS','ZOETIS'),
        ('AGROQUIMICOS','AGROQUIMICOS'),
        ('PISA','PISA'),
        ('SAMEI','SAMEI'),
        ('PROMOCIONALES','PROMOCIONALES'),
        ('NIPRO','NIPRO'),
        ('OUROFINO','OUROFINO'),
        ('TIBET','TIBET'),
        ('PHARMA PETSS','PHARMA PETSS'),
        ('PROANSA','PROANSA'),
        ('BOTAS ESTABLO','BOTAS ESTABLO'),
        ('EQUISAN','EQUISAN'),
        ('HOLLAND','HOLLAND'),
        ('INTERZENDA','INTERZENDA'),
        ('VIRBAC','VIRBAC'),
        ('CASALS antes veravet','CASALS antes veravet'),
        ('OSTER','OSTER'),
        ('WEIZUR','WEIZUR'),
        ('CHIVALI','CHIVALI'),
        ('KIRON','KIRON'),
        ('ACCESORIOS CLINICAS','ACCESORIOS CLINICAS'),
        ('NUTRES','NUTRES'),
        ('AGRICULTURA NACIONAL','AGRICULTURA NACIONAL'),
        ('ALLYSTER','ALLYSTER'),
        ('ARRIETA','ARRIETA'),
        ('REPROMAX','REPROMAX'),
        ('HYUNDAI','HYUNDAI'),
        ('APLIGEN','APLIGEN'),
        ('COMPROVET','COMPROVET'),
        ('VEROIL','VEROIL'),
        ('RIMSA','RIMSA'),
        ('TECNOCAMPO','TECNOCAMPO'),
        ('ECOVET','ECOVET'),
        ('ALEBET','ALEBET'),
        ('TERUMO','TERUMO'),
        ('VERAMÍN - NUTRIMENTOS MINERALES','VERAMÍN - NUTRIMENTOS MINERALES'),
        ('DEKALB - BAYER SEMILLAS','DEKALB - BAYER SEMILLAS'),
        ('MENTA','MENTA'),
        ('REAFRIO','REAFRIO'),
        ('ROTAM','ROTAM'),
        ('GIMENES','GIMENES'),
        ('BIMEDA','BIMEDA'),
        ('SANA ENERGY','SANA ENERGY'),
        ('SERAP','SERAP'),
        ('LALLEMAND','LALLEMAND'),
        ('ILGUM TARIM','ILGUM TARIM'),
        ('SIORCO','SIORCO'),
        ('BEKAERT TRADE','BEKAERT TRADE'),
        ('RAIKER','RAIKER'),
        ('PLURINOX','PLURINOX'),
        ('GOWAN MEXICANA','GOWAN MEXICANA'),
        ('TERRA FERTIL','TERRA FERTIL'),
        ('AGROVET','AGROVET'),
        ('DISTRICAMPO','DISTRICAMPO'),
        ('SIJI','SIJI'),
        ('TECNOLOGIA ANIMAL','TECNOLOGIA ANIMAL'),
        ('INSTRUVET','INSTRUVET'),
        ('VERSA','VERSA'),
        ('CERES ','CERES '),
        ('OTROS AGRICOLAS','OTROS AGRICOLAS'),
        ], string='Laboratorios / Marcas', default='')
    as_line_product = fields.Selection(selection=[
        ('ACEROS NACIONALES','ACEROS NACIONALES'),
        ('OSATU','OSATU'),
        ('CORTEVA','CORTEVA'),
        ('QUALYMILK','QUALYMILK'),
        ('QUALYMILK - ALTERNA','QUALYMILK - ALTERNA'),
        ('OTROS ACCESORIOS','OTROS ACCESORIOS'),
        ('OTROS MEDICAMENTOS','OTROS MEDICAMENTOS'),
        ('BOEHRINGER','BOEHRINGER'),
        ('SEMILLAS','SEMILLAS'),
        ('OTROS AGROQUIMICOS','OTROS AGROQUIMICOS'),
        ('PISA','PISA'),
        ('VERAMIN','VERAMIN'),
        ('DEKALB','DEKALB'),
        ('BIMEDA','BIMEDA'),
        ('TERRAFERTIL','TERRAFERTIL'),
        ('ZOETIS GANADERA','ZOETIS GANADERA'),
        ('ZOETIS EQUINO','ZOETIS EQUINO'),
        ('ZOETIS PE','ZOETIS PE'),
        ('ZOETIS CERDOS','ZOETIS CERDOS'),
        ('VIRBAC PE','VIRBAC PE'),
        ('VIRBAC GE','VIRBAC GE'),
        ('VIRBAC HPM','VIRBAC HPM'),
        ('VERSA','VERSA'),
        ('OTROS AGRICOLAS','OTROS AGRICOLAS'),
        ], string='Linea de producto', default='')


    @api.onchange('product_id')
    def get_coste_center(self):
        usuario = self.env.user
        self.analytic_tag_ids = usuario.analytic_tag_ids.ids
        self.regiones_id = usuario.regiones_id.id
        self.cost_center_id = usuario.cost_center_id.id
        self.department_id = usuario.departmento_id.id
        self.as_laboratorio = self.product_id.as_laboratorio
        self.as_line_product = self.product_id.as_line_product
