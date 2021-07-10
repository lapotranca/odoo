# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools


class SaleReport(models.Model):
    _inherit = "sale.report"

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
        ('OTROS AGRICOLAS','OTROS AGRICOLAS'),
        ], string='Laboratorios / Marcas', default='SERVICIOS')
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
        ('OTROS AGRICOLAS','OTROS AGRICOLAS'),
        ], string='Linea de producto', default='ACEROS NACIONALES')

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        fields['as_laboratorio'] = ', l.as_laboratorio as as_laboratorio'
        fields['as_line_product'] = ', l.as_line_product as as_line_product'
        groupby += ', l.as_laboratorio'
        groupby += ', l.as_line_product'

        return super(SaleReport, self)._query(with_clause, fields, groupby, from_clause)