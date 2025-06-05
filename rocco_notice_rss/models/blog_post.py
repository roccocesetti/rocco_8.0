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
import time
import datetime
from email import utils
import openerp
from openerp import models,  api ,fields as opn_fields
from openerp.http import request as req_2
import xml.etree.ElementTree as ET
import base64
try:
    import simplejson as json
except ImportError:
    import json
import logging
import openerp.addons.decimal_precision as dp
from openerp.osv import orm, osv, fields

class BlogPost(models.Model):
    _inherit = 'blog.blog'
    _columns = {
                
               'x_rss_channel':fields.char('x_rss_channel', size=256, required=False, readonly=False),
               'x_rss_number': fields.integer('Numero Articoli'),
               'x_elimina_art':fields.boolean('Elimina articoli', required=False),              
               'x_site_channel_image':fields.char('x_site_channel_image', size=256, required=False, readonly=False),           
               'x_image_tag':fields.char('x_image_tag', size=256, required=False, readonly=False),
               'company_id':fields.many2one('res.company', 'Azienda', required=False),
               'x_tag_ids': fields.many2many('blog.tag', string='Tags' ),
               'website_noindex':fields.boolean('Blocca indicizzazione', required=False), 
            
                    }
    _defaults = {  
        'x_rss_number':10,
        'x_elimina_art':True
        }
BlogPost()
class BlogPostMemory(osv.osv_memory):
    _name = "blog.post.temp"
    _description = "Blog Post temp"
    _inherit = 'blog.post'
    _order = 'id DESC'
    _columns = {
        'history_ids':fields.char('dummy', size=64, required=False, readonly=False),             
                    }
