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
import base64
import datetime
import dateutil.relativedelta as relativedelta
import logging
import lxml
import urlparse
from openerp import SUPERUSER_ID
from openerp import tools, api
from openerp.tools.translate import _
from urllib import urlencode, quote as quote
from openerp.osv import osv, fields
from openerp.tools.translate import _


_logger = logging.getLogger(__name__)

class account_x_service(osv.osv):
    _name = "account.x.service"
    _inherit = ['account.x.service', 'crm.tracking.mixin']
    _columns = {
        'categ_ids': fields.many2many('crm.case.categ', 'account_x_service_category_rel', 'x_service_id', 'category_id', 'Tags', \
            domain="[('object_id.model', '=', 'crm.lead')]", context="{'object_name': 'crm.lead'}")
    }
class crm_make_cloud(osv.osv_memory):
    """ Make sale  order for crm """

    _name = "crm.make.cloud"
    _description = "Make cloud"

    def _selectPartner(self, cr, uid, context=None):
        """
        This function gets default value for partner_id field.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param context: A standard dictionary for contextual values
        @return: default value of partner_id field.
        """
        if context is None:
            context = {}

        lead_obj = self.pool.get('crm.lead')
        active_id = context and context.get('active_id', False) or False
        if not active_id:
            return False

        lead = lead_obj.read(cr, uid, [active_id], ['partner_id'], context=context)[0]
        return lead['partner_id'][0] if lead['partner_id'] else False

    def view_init(self, cr, uid, fields_list, context=None):
        return super(crm_make_cloud, self).view_init(cr, uid, fields_list, context=context)

    def makecloud(self, cr, uid, ids, context=None):
        """
        This function  create Quotation on given case.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of crm make sales' ids
        @param context: A standard dictionary for contextual values
        @return: Dictionary value of created sales order.
        """
        # update context: if come from phonecall, default state values can make the quote crash lp:1017353
        context = dict(context or {})
        context.pop('default_state', False)        
        user_obj=self.pool.get('res.users')
        case_obj = self.pool.get('crm.lead')
        x_service_obj = self.pool.get('account.x.service')
        partner_obj = self.pool.get('res.partner')
        data = context and context.get('active_ids', []) or []

        for make in self.browse(cr, uid, ids, context=context):
            partner = make.partner_id
            new_ids = []
            for case in case_obj.browse(cr, uid, data, context=context):
                if partner.email:
                        user_ids=user_obj.search(cr, uid, [('login','=',partner.email)], context=context)
                        if  user_ids:
                            user_ids_id=user_ids[0]
                        else:
                            user_ids_id=False
                           
                else:
                        user_ids_id=False
                x_nod_id=x_service_obj.get_default_x_nods(cr,uid,context=context)
                vals = {
                    'note': _('Opportunity: %s') % str(case.id),
                    'name': _('Opportunity: %s') % str(case.id),
                    'categ_ids': [(6, 0, [categ_id.id for categ_id in case.categ_ids])],
                    'partner_id': partner.id,
                    'user_id': partner.user_id.id,
                    'user_customer_id': user_ids_id,
                    'F_invoice_repeat':True,
                    'x_nod_id':x_nod_id,
                }
                if partner.id:
                    vals['user_id'] = partner.user_id and partner.user_id.id or uid
                
                new_id = x_service_obj.create(cr, uid, vals, context=context)
                x_service = x_service_obj.browse(cr, uid, new_id, context=context)
                case_obj.write(cr, uid, [case.id], {'ref': 'account.x.service,%s' % new_id})
                new_ids.append(new_id)
                message = _("Opportunity has been <b>converted</b> to the Servizio Cloud <em>%s</em>.")  % (x_service.id)
                case.message_post(body=message)
            if make.close:
                case_obj.case_mark_won(cr, uid, data, context=context)
            if not new_ids:
                return {'type': 'ir.actions.act_window_close'}
            if len(new_ids)<=1:
                value = {
                    'domain': str([('id', 'in', new_ids)]),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'account.x.service',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'name' : _('Serizi Clouds'),
                    'res_id': new_ids and new_ids[0]
                }
            else:
                value = {
                    'domain': str([('id', 'in', new_ids)]),
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'account.x.service',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'name' : _('Servizi Cloud'),
                    'res_id': new_ids
                }
            return value


    _columns = {
        'partner_id': fields.many2one('res.partner', 'Customer', required=True, domain=[('customer','=',True)]),
        'close': fields.boolean('Mark Won', help='Check this to close the opportunity after having created the sales order.'),
    }
    _defaults = {
        'close': False,
        'partner_id': _selectPartner,
    }
class email_template(osv.osv):
    _inherit = 'email.template'
    def _replace_local_links(self, cr, uid, html, context=None):
        """ Post-processing of html content to replace local links to absolute
        links, using web.base.url as base url. """
        if not html:
            return html

        # form a tree
        root = lxml.html.fromstring(html)
        if not len(root) and root.text is None and root.tail is None:
            html = '<div>%s</div>' % html
            root = lxml.html.fromstring(html)
        _logger.info("root %s",root)
        _logger.info("html %s",html)

        base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url')
        (base_scheme, base_netloc, bpath, bparams, bquery, bfragment) = urlparse.urlparse(base_url)

        def _process_link(url):
            if url:
                new_url = url
                _logger.info("url %s",url)
    
                (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(url)
                if not scheme and not netloc:
                    new_url = urlparse.urlunparse((base_scheme, base_netloc, path, params, query, fragment))
                return new_url
            else:
                return '#'

        # check all nodes, replace :
        # - img src -> check URL
        # - a href -> check URL
        for node in root.iter():
            _logger.info("node %s",node)
            _logger.info("tag %s",node.tag)
            _logger.info("href %s",node.get('href'))
            _logger.info("src %s",node.get('src'))
            _logger.info("img %s",node.get('img'))
            
            if node.tag == 'a':
                node.set('href', _process_link(node.get('href')))
            elif node.tag == 'img' and not node.get('src', 'data').startswith('data'):
                node.set('src', _process_link(node.get('src')))

        html = lxml.html.tostring(root, pretty_print=False, method='html')
        # this is ugly, but lxml/etree tostring want to put everything in a 'div' that breaks the editor -> remove that
        if html.startswith('<div>') and html.endswith('</div>'):
            html = html[5:-6]
        return html




