# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-today OpenERP SA (<http://www.openerp.com>)
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

import openerp
from openerp.addons.crm import crm
from openerp.osv import fields, osv
from openerp import tools
from openerp.tools.translate import _
from openerp.tools import html2plaintext
from openerp import SUPERUSER_ID


class crm_claim(osv.osv):
    """ Crm claim
    """
    def _service_count(self, cr, uid, ids, field_name, arg, context=None):
        x_service = self.pool['account.x.service']
        return {
            partner_id: x_service.search_count(cr,uid, [('partner_id', '=', partner_id)], context=context)
            for partner_id in ids
        }
    _inherit = "crm.claim"
    _columns = {
        'x_service_id': fields.many2one('account.x.service', 'Servizio Cloud',  select=True),
    }




    def onchange_partner_id(self, cr, uid, ids, partner_id, email=False, context=None):
        res= super(crm_claim, self).onchange_partner_id(cr, uid, partner_id,email, context=context)
        """This function returns value of partner address based on partner
           :param email: ignored
        """
        if not partner_id:
            return {'value': {'email_from': False, 'partner_phone': False}}
        address = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
        res['value']['email_cc']=address.user_id.partner_id.email
        res['value']['section_id']=address.section_id.id
        #print 'sale team-->',address.section_id.id
        return res
    def create(self, cr, uid, vals, context=None):
        mtp_obj = self.pool.get('email.template')
        user_id_obj=self.pool.get('res.users').browse(cr,SUPERUSER_ID,uid,context=context)
        if user_id_obj:
            if not vals.get('partner_id'): 
                vals['partner_id']=user_id_obj.partner_id.id
            if not vals.get('section_id'): 
                vals['section_id']=user_id_obj.section_id.id
            if not vals.get('email_cc'):          
                 vals['email_cc']=user_id_obj.partner_id.user_id.partner_id.email
        # context: no_log, because subtype already handle this
        res=super(crm_claim, self).create(cr, SUPERUSER_ID, vals, context=context)
        try:
                    template_ids = mtp_obj.search(cr, SUPERUSER_ID, [('name','ilike', '%NOTIFICA_RECLAMO%')])
                                #template_id = ir_model_data.get_object_reference(cr, uid, 'rc_Cloudonthecloud', 'email_template_edi_account_x_service_01')[1]
                    if template_ids:    
                                    template_id=template_ids[0]
                    else:
                                    template_id=False     
                    mtp_obj.send_mail(cr, SUPERUSER_ID, template_id, res, context=context)

        except ValueError:
                    template_id = False

        
        return res
    def write(self, cr, uid,ids, vals, context=None):
        res=super(crm_claim, self).write(cr, uid,ids, vals, context=context)
        mtp_obj = self.pool.get('email.template')
        if vals.get('stage_id'): 
            try:
                        template_ids = mtp_obj.search(cr,uid, ids, [('name','ilike', '%NOTIFICA_RECLAMO%')])
                                    #template_id = ir_model_data.get_object_reference(cr, uid, 'rc_Cloudonthecloud', 'email_template_edi_account_x_service_01')[1]
                        if template_ids:    
                                        template_id=template_ids[0]
                        else:
                                        template_id=False     
                        mtp_obj.send_mail(cr,uid, ids, template_id, ids[0], context=context)
    
            except ValueError:
                        template_id = False

        
        return res


    # -------------------------------------------------------
    # Mail gateway
    # -------------------------------------------------------

    def message_new(self, cr, uid, msg, custom_values=None, context=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        return super(crm_claim, self).message_new(cr, uid, msg, custom_values=custom_values, context=context)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
