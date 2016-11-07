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
from openerp.tools.translate import _
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
from datetime import datetime
import time
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
class seo_url(osv.osv):
    _name = 'rocco.seo.url'
    _description = 'siti per seo statistico'
    _columns = {
        'name': fields.char('identificativo seo', size=64 , required=True),
        'url_seo': fields.char('url Seo', size=256 , required=True),
        'url_link': fields.char('url link', size=256 , required=True),
        'method': fields.char('method', size=256 , required=True),
        'active': fields.boolean('Attivo', required=False), 
     }

class seo_send(osv.osv):
    _name = 'rocco.seo.send'
    _description = 'avvio seo statistico'
    _columns = {
        'name': fields.char('identificativo seo', size=64 , required=True),
        'data_seo': fields.datetime('Date'),
        'active': fields.boolean('Attivo', required=False), 
        'url_seo_id':fields.many2one('rocco.seo.url', 'url seo', required=False), 
        'url_link': fields.char('url link', size=256 , required=False),
        'method': fields.char('method', size=256 , required=True),
     }
    _defaults = {  
        'data_seo': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'active': True, 
        }
    def onchange_url_seo_id(self, cr, uid, ids, url_seo_id, context=None):
        if not url_seo_id:
            return {'value': {'url_link': False,'method': False}}

        url_seo_id_obj = self.pool.get('rocco.seo.url').browse(cr, uid, url_seo_id, context=context)
        val = {
            'url_link': url_seo_id_obj.url_link,
            'method': url_seo_id_obj.method,
        }
        return {'value': val}

    def send_seo(self,cr,uid,ids=None,context=None):
        date_today=datetime.today()
        db_name = cr.dbname
        pool = pooler.get_pool(db_name)
        seo_url_obj = pool.get('rocco.seo.url')
        seo_send_obj = pool.get('rocco.seo.send')
        if ids==None:
            send_seo_id=self.create(cr,uid,{'name':'seo_robot'})
            ids=[send_seo_id]
        if hasattr(ids, '__iter__')==False:
            ids=[ids]
        for send_seo_id in ids:
            send_seo_id_obj=self.browse(cr,uid,send_seo_id,context=context)
            if  send_seo_id_obj.url_seo_id:
                    url_seo_id_obj=send_seo_id_obj.url_seo_id
                    seo_ids_obj=[url_seo_id_obj]  
                    url_link=send_seo_id_obj.url_link
                    method=send_seo_id_obj.method
            else:
                seo_ids=seo_url_obj.search(cr,uid,[('active','=',True)],context=context)
                seo_ids_obj=seo_url_obj.browse(cr,uid,seo_ids,context=context)
                url_link=None
                method=None
                break
                                     
        http = httplib2.Http()
        for seo_id_obj in seo_ids_obj:
                    url = seo_id_obj.url_seo
                    if url_link==None:
                        url_link=seo_id_obj.url_link
                    if method==None:
                        method=seo_id_obj.method
                    request="Test Seo"
                    body = {'xml': request}
                    headers = {'Content-type': 'application/x-www-form-urlencoded'}
                    responses, contents = http.request(url, method, headers=headers, body=urllib.urlencode(body))
                    print contents
                    if responses.status==200:
                          for content in  contents:
                              if  content.find(url_link):
                                        responses, contents = http.request(url, method, headers=headers, body=urllib.urlencode(body))
                                        if responses.status==200:
                                            print contents

