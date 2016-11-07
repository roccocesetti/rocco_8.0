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
from tools.translate import _
import base64
from tempfile import TemporaryFile
import csv
from openerp import tools
from openerp.osv import osv, fields
from lxml import etree
import openerp.pooler as pooler
import openerp.sql_db as sql_db
from functools import partial
import logging
from lxml.builder import ET
import xml.etree.ElementTree as ETE
import openerp
from openerp import SUPERUSER_ID
import openerp.exceptions
from openerp.osv.orm import browse_record
from datetime import datetime, timedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
import openerp.addons.decimal_precision as dp
from openerp import netsvc
import os
import sys, httplib
import urllib2 
import urllib
import httplib2

from email.MIMEText import MIMEText
from email.MIMEBase import MIMEBase
from email.MIMEMultipart import MIMEMultipart
from email.Charset import Charset
from email.Header import Header
from email.Utils import formatdate, make_msgid, COMMASPACE
from email import Encoders
import logging
import re
import smtplib
import threading
from openerp.tools import html2text
from openerp.loglevels import ustr
from urllib import urlencode
from urlparse import urljoin
import curses.ascii
_logger = logging.getLogger(__name__)
class product_site_export_can(osv.osv):
    """ product site export can"""

    _name = "product.site.export.can"
    _description = "Product site export can"
    _columns = {
        'anno':fields.integer('anno',help='anno'),
        'conto':fields.integer('conto',help='conto'),
        'data_can': fields.datetime('Date'),
      
     }
    _defaults = {
        'conto':0,
        'data_can': lambda *a: time.strftime('%Y-%m-%d'),
    } 
class product_export_can(osv.osv):
    """ product Import """

    _name = "product.export.can"
    _description = "Product export can"
    _columns = {
        'anno':fields.integer('anno',help='anno'),
        'conto':fields.integer('conto',help='conto'),
        'data_can': fields.datetime('Date'),
        'errate':fields.integer('errate',help='errate'),


     }
    _defaults = {
        'conto':0,
        'data_can': lambda *a: time.strftime('%Y-%m-%d'),
    }

    def export_can(self, cr, uid, ids=None, context=None):
            date_today=datetime.today().date()
            anno_today=date_today.year
            mese_today=date_today.month
            #date_max=datetime.strptime("31/12/2999","%d/%m/%Y").strftime("%Y-%m-%d")
            #date_min=datetime.strptime(str(date_today),"%Y-%m-%d").strftime("%Y-%m-%d")
            db_name = cr.dbname
            pool = pooler.get_pool(db_name)
            can_obj = pool.get('product.export.can')
            can_site_obj = pool.get('product.site.export.can')
            can_site_ids = can_site_obj.search(cr, uid, [('anno','=',anno_today )])    
            if can_site_ids:                            
                    can_site_ids_id=can_site_ids[0]
                    can_site_ids_rec=can_site_obj.browse(cr, uid,can_site_ids_id,context)
                    anno_can=can_site_ids_rec.anno
                    mese_can=can_site_ids_rec.conto
                    data_can=datetime.strptime(str(can_site_ids_rec.data_can),"%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
                    data_today_1=datetime.strptime(str(date_today),"%Y-%m-%d").strftime("%Y-%m-%d")
                    if can_site_ids_rec.conto<=0:
                        #data_can=can_site_ids_rec.data_can
                        if data_can>=data_today_1:
                                return True
                        else:
                                can_ids = can_obj.search(cr, uid, [('anno','=',anno_today )])    
                                if can_ids:
                                        can_ids_rec=can_obj.browse(cr, uid,can_ids[0],context)
                                        can_ids_rec.errate+=1
                                        can_obj.write(cr,uid,can_ids[0],{'errate' :can_ids_rec.errate},context)
                                else:
                                        can_obj.create(cr,uid,{'anno':anno_today,
                                                               'conto':can_site_ids_rec.conto,
                                                               'data_can':can_site_ids_rec.data_can,
                                                               'errate' :1},context)
 
                                return False
                    else:
                        return True            
                           
            else:
                        return False

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
