# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import tools
from openerp.osv import fields, osv
class sale_report(osv.osv):
    _name = "sale.report.duplicatestockmove"
    _description = "Sales Orders stock move duplicate"
    _auto = False
    _rec_name = 'date_ord'

    _columns = {
        'id': fields.integer('# id', readonly=True),  # TDE FIXME master: rename into nbr_lines
        'date_ord': fields.datetime('Date Order', readonly=True),  # TDE FIXME master: rename into date_order
        'num_ord':fields.char('num_ord', size=64, required=False, readonly=False),
        'nr_so': fields.integer('# of Lines', readonly=True),  # TDE FIXME master: rename into nbr_lines
        'date_picking': fields.datetime('Date picking', readonly=True),  # TDE FIXME master: rename into date_order
        'num_picking':fields.char('num_picking', size=64, required=False, readonly=False),
        'nr_pk': fields.integer('# of move', readonly=True),  # TDE FIXME master: rename into nbr_lines
        'note':fields.char('note x esc', size=256, required=False, readonly=False),
    }
    _order = 'date_ord desc,num_ord'

    def _select(self):
        select_str = """
select v_sol.id as id,v_sol.date_ord,v_sol.num_ord,nr_so,v_sm.date_picking,v_sm.num_picking,nr_pk,v_sm.note


        """
        return select_str

    def _from(self):
        from_str = """
(select so.id,so.date_order as date_ord,so.name as num_ord,sol.order_id,count(sol.order_id) as nr_so from sale_order_line sol inner join sale_order so on sol.order_id=so.id 
where sol.product_id<>11986 and sol.product_id<>12671 group by so.id,so.date_order,so.name,sol.order_id) v_sol inner join

(select sp.date as date_picking,sp.origin as num_ord,sp.name as num_picking,sm.picking_id,count(sm.picking_id) as nr_pk,sp.note from stock_move sm inner join stock_picking sp on sm.picking_id=sp.id 
where sp.picking_type_id=2 and sp.state<>'cancel' group by sp.date,sp.origin,sp.name,sm.picking_id,sp.note) v_sm on  v_sol.num_ord=v_sm.num_ord             
"""
        return from_str

    def _group_by(self):
        group_by_str = """

        """
        return group_by_str
    def _where(self):
        where_str = """
          where v_sol.nr_so<>v_sm.nr_pk 
        """
        return where_str

    def init(self, cr):
        # self._table = sale_report
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            FROM ( %s )
            %s
            %s
            )""" % (self._table, self._select(), self._from(), self._where(), self._group_by()))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
