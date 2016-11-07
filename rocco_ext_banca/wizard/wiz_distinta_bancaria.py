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
import openerp.pooler as pooler
import openerp.sql_db as sql_db
from openerp.osv import fields,osv,orm

from openerp.tools.translate import _

from datetime import datetime, timedelta
import time
import base64
import cStringIO
from xml.etree.ElementTree import parse
import xml.etree.ElementTree as ETree
from xml.etree.ElementTree import Element, SubElement, Comment, ElementTree
from xml.dom import minidom
class riba_distinta_print(osv.osv_memory):

    _name = "riba.distinta.print"
    _description = "Stampa Distinta Bancaria "

    _columns = {
        'name': fields.char(string='Nome', size=64),
        'date': fields.date('Data stampa'),
    }
    _defaults = {  
        'name': 'distinta',  
        'date': lambda *a: time.strftime('%Y-%m-%d'),  
}
    def view_init(self, cr, uid, fields_list, context=None):
        if context is None:
            context = {}
        res = super(riba_distinta_print, self).view_init(cr, uid, fields_list, context=context)
        active_ids = context.get('active_ids',[])
        return res

    def distinta_bancaria_print(self, cr, uid, ids, context=None):
        this = self.browse(cr, uid, ids[0])
        riba_ids =  ids[0]
        return self._print_report(cr, uid,ids,riba_ids,  context=context)
    def _print_report(self, cr, uid, ids,riba_ids,  context=None):
        if context is None:
            context = {}
        data={}
        riba_ids.sort()
        data['ids'] = riba_ids
        data['model'] = context.get('riba.distinta', 'ir.ui.menu')
        #data['form'].update(self.read(cr, uid, ids, ['da_data','a_data'], context=context)[0])
        report_name = 'report.rocco_ext_banca.distinta.bancaria.print'
        return {'type': 'ir.actions.report.xml', 'report_name': report_name, 'datas': data}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
