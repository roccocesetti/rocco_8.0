# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>).
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

from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp import SUPERUSER_ID
class website_cloud(http.Controller):

    @http.route(['/cloud/account.x.service','/cloud/'], type='http', auth="public", website=True)
    def cloud(self, cloud=None, **post):
        cr, uid, context = request.cr, request.uid, request.context
        
        render_values = {
            'partner_id': post.get('partner_id'),
            'name': post.get('name'),
            'date_service':  post.get('date_service'),
            'date_next_invoice':  post.get('date_next_invoice'),
            'amount_untaxed':  post.get('amount_untaxed'),
            'amount_tax':  post.get('amount_tax'),
            'amount_total':  post.get('amount_total'),
            'partner_id': post.get('partner_id'),

        }
        return request.website.render("website_cloud.index", render_values)
    @http.route(['/cloud/account.x.service', '/cloud/x_service'], type='http', auth="public", website=True)
    def x_service(self, **kwargs):
        values = {}
        for field in ['id', 'name', 'x_service_ids']:
            if kwargs.get(field):
                values[field] = kwargs.pop(field)
        values.update(kwargs=kwargs.items())
        return request.website.render("website_cloud.index", values)

    @http.route(['/cloud/website_cloud.cloudus_partner', '/cloud/cloudus'], type='http', auth="public", website=True)
    def cloudus(self, **post):
        cr, uid, context = request.cr, request.uid, request.context
        partner_obj = request.registry['res.partner']
        user_obj = request.registry['res.users']
        user_ids_obj=user_obj.browse(request.cr, SUPERUSER_ID, request.uid,
                                          request.context)
        if user_ids_obj:
            if user_ids_obj.partner_id:
                    partner_ids = partner_obj.search(request.cr, SUPERUSER_ID, [('id', '=', post.get('partner_id',user_ids_obj.partner_id.id))],
                                     context=request.context)
            else:
                    partner_ids=[]
        partner_ids_obj=partner_obj.browse(request.cr, SUPERUSER_ID, partner_ids,
                                          request.context)
        values = {'x_service_ids': partner_ids_obj.x_service_ids
                  }
        return request.website.render("website_cloud.cloud_index", values)
