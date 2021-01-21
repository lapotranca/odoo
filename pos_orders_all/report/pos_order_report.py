
from odoo import api, fields, models, tools


class PosOrderReport(models.Model):
	_inherit = "report.pos.order"
	def _select(self):
		
		return """
			SELECT
				MIN(l.id) AS id,
				COUNT(*) AS nbr_lines,
				s.date_order AS date,
				SUM(l.qty) AS product_qty,
				SUM(l.qty * l.price_unit) AS price_sub_total,
				CASE WHEN l.discount_line_type = 'Fixed'
					THEN  SUM((l.price_unit-l.discount)*l.qty)
					ELSE  SUM((l.qty * l.price_unit) * (100 - l.discount) / 100)
				END AS price_total, 
				CASE WHEN l.discount_line_type = 'Fixed'
					THEN  SUM((l.price_unit*l.qty)-(l.price_unit-l.discount)*l.qty)
					ELSE  SUM((l.qty * l.price_unit) * (l.discount / 100))
				END AS total_discount, 
				-- SUM((l.qty * l.price_unit) * (l.discount / 100)) AS total_discount,
				(SUM(l.qty*l.price_unit)/SUM(l.qty * u.factor))::decimal AS average_price,
				SUM(cast(to_char(date_trunc('day',s.date_order) - date_trunc('day',s.create_date),'DD') AS INT)) AS delay_validation,
				s.id as order_id,
				s.partner_id AS partner_id,
				s.state AS state,
				s.user_id AS user_id,
				s.location_id AS location_id,
				s.company_id AS company_id,
				s.sale_journal AS journal_id,
				l.product_id AS product_id,
				pt.categ_id AS product_categ_id,
				p.product_tmpl_id,
				ps.config_id,
				pt.pos_categ_id,
				s.pricelist_id,
				s.session_id,
				s.account_move IS NOT NULL AS invoiced

		"""

	def _from(self):
		return """
			FROM pos_order_line AS l
				INNER JOIN pos_order s ON (s.id=l.order_id)
				LEFT JOIN product_product p ON (l.product_id=p.id)
				LEFT JOIN product_template pt ON (p.product_tmpl_id=pt.id)
				LEFT JOIN uom_uom u ON (u.id=pt.uom_id)
				LEFT JOIN pos_session ps ON (s.session_id=ps.id)
		"""

	def _group_by(self):
		return """
			GROUP BY
				s.id, s.date_order, s.partner_id,s.state, pt.categ_id,
				s.user_id, s.location_id, s.company_id, s.sale_journal,
				s.pricelist_id, s.account_move, s.create_date, s.session_id,
				l.product_id,
				l.discount_line_type,
				pt.categ_id, pt.pos_categ_id,
				p.product_tmpl_id,
				ps.config_id
		"""

	def _having(self):
		return """
			HAVING
				SUM(l.qty * u.factor) != 0
		"""

	def init(self):
		tools.drop_view_if_exists(self._cr, self._table)
		self._cr.execute("""
			CREATE OR REPLACE VIEW %s AS (
				%s
				%s
				%s
				%s
			)
		""" % (self._table, self._select(), self._from(), self._group_by(),self._having())
		)