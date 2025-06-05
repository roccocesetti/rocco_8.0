# coding: utf-8
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C)2010-  OpenERP SA (<http://openerp.com>). All Rights Reserved
#    App Author: Vauxoo
#
#    Developed by Oscar Alcala
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from datetime import datetime
import difflib
import lxml
import random

from openerp import tools
from openerp import SUPERUSER_ID
from openerp.addons.website.models.website import slug
from openerp.osv import osv, fields
from openerp.tools.translate import _


class check_sda(osv.Model):
    _name = 'delivery.carrier.sda.check'
    _description = 'delivery.carrier.sda.check'
    _inherit = ['mail.thread', 'website.seo.metadata']
    _order = 'sda_customer'
    _rec_name = 'sda_customer' 
    _columns = {
        'sda_customer': fields.char('codice cliente sda'),
        'sda_monitor': fields.integer('chiave sda'),
        'sda_monitor_count': fields.integer('contatore chiave sda'),
        'sda_company_name':fields.char('sda_company_name'),
        'sda_company_city':fields.char('sda_company_city'),
        'sda_company_street':fields.char('sda_company_street'),
        'sda_user':fields.char('sda_user'),
        'sda_password':fields.char('sda_password'),
        'sda_url':fields.char('url', size=256, required=True, readonly=False),
        'sda_url_trk':fields.char('url tracking ', size=256, required=False, readonly=False),



    }
    _defaults = {  
        'sda_monitor': lambda *a: random.randint(10000,20000),
        'sda_monitor_count':1  
        }
