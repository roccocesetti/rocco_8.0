# -*- coding: utf-8 -*-
import logging
import werkzeug

from openerp import SUPERUSER_ID
from openerp import http
from openerp import tools
from openerp.http import request
from openerp.tools.translate import _
from openerp.addons.website.models.website import slug
from openerp.addons.web.controllers.main import login_redirect
from openerp.addons.website.controllers.main import Website
from openerp.modules import get_module_resource
from docutils.core import publish_string
from openerp.tools import html_sanitize
try:
    import simplejson as json
except ImportError:
    import json
import logging
import pprint
PPG = 20 # Products Per Page
PPR = 4  # Products Per Row

_logger = logging.getLogger(__name__)

class sdaController(http.Controller):
    _notify_url = '/sda/notify'
    _return_url = '/sda/create'
    _cancel_url = '/sda/cancel/'
    @http.route('/sda/login/get', type='http', auth='none', methods=['GET'])
    def sda_login_get(self, **get):
        """ sda  """
        _logger.info('Beginning sda with post data %s', pprint.pformat(get))  # debug
        
        return self.sda_validate_login(**get)
    
    @http.route('/sda/login', type='json', auth='none', methods=['POST'])
    def sda_login(self, **post):
        """ sda """
        _logger.info('Beginning sda   with post data %s', pprint.pformat(post))  # debug
        
        return self.sda_validate_login(**post)

    @http.route('/cloud/sda/create', type='http', auth='none', methods=['POST'])
    def sda_create(self, **post):
        """ sda IPN. """
        _logger.info('Beginning sda IPN form_feedback with post data %s', pprint.pformat(post))  # debug
        res=self.sda_validate_data(**post)
        return res
    @http.route('/cloud/sda/create/get', type='http', auth='none', methods=['GET'])
    def sda_create_get(self, **get):
        """ sda IPN. """
        _logger.info('Beginning sda IPN sda_validate_data with get data %s', pprint.pformat(get))  # debug
        res=self.sda_validate_data(**get)
        return res
    
    @http.route('/cloud/sda/verified/get', type='http', auth='none', methods=['GET'])
    def sda_verified_payment_get(self, **get):
        """ sda IPN. """
        _logger.info('Beginning sda IPN sda_validate_data with get data %s', pprint.pformat(get))  # debug
        res=self.sda_validate_payment(**get)
        return res

    @http.route('/cloud/sda/verified', type='http', auth='none', methods=['POST'])
    def sda_verified_payment(self, **post):
        """ sda IPN. """
        _logger.info('Beginning sda IPN form_feedback with post data %s', pprint.pformat(post))  # debug
        res=self.sda_validate_payment(**post)
        return res

    @http.route('/cloud/sda/cancel', type='http', auth='none', methods=['POST'])
    def sda_create_cancel(self, **post):
        """ sda IPN. """
        _logger.info('Beginning sda IPN form_feedback with post data %s', pprint.pformat(post))  # debug
        res=self.sda_validate_data(**post)
        return res
    @http.route('/cloud/sda/notify', type='http', auth='none', methods=['POST'])
    def sda_create_notify(self, **post):
        """ Paypal IPN. """
        _logger.info('Beginning sda IPN form_feedback with post data %s', pprint.pformat(post))  # debug
        res=self.sda_validate_data(**post)
        return res
    def sda_validate_data(self, **post):
        """ sda IPN: three steps validation to ensure data correctness

         - step 1: return an empty HTTP 200 response -> will be done at the end
           by returning ''
         - step 2: POST the complete, unaltered message back to Paypal (preceded
           by cmd=_notify-validate), with same encoding
         - step 3: paypal send either VERIFIED or INVALID (single word)

        Once data is validated, process it. """
        res = False
        new_post = dict(post)
        cr, uid, context = request.cr, SUPERUSER_ID, request.context
        x_portal_domain_id_obj=request.registry['x.portal.domain'].browse(cr, uid,int(str(new_post.get('x_portal_domain_id')).decode()) , context=context)
        urequest = urllib2.Request(str(x_portal_domain_id_obj.partner_id.company_id.x_url_domain).strip(), werkzeug.url_encode(new_post))
        uopen = urllib2.urlopen(urequest)
        resp = uopen.read()
        res = request.registry['x.portal.domain'].create_sale(cr,uid,x_portal_domain_id_obj.id,new_post, context=context)
        #if resp == '1':
        #    _logger.info('Domain: validated data')
        #    res = request.registry['x.portal.domain'].create_sale(cr,uid,x_portal_domain_id_obj.id,new_post, context=context)
        #elif resp == '0':
        #    _logger.warning('Domain: answered INVALID on data verification')
        #else:
        #    _logger.warning('Domain: unrecognized Domain answer, received %s instead of 1 or 0' % resp.text)
        return res
    def sda_validate_payment(self, **post):
        """ domain IPN: three steps validation to ensure data correctness

         - step 1: return an empty HTTP 200 response -> will be done at the end
           by returning ''
         - step 2: POST the complete, unaltered message back to Paypal (preceded
           by cmd=_notify-validate), with same encoding
         - step 3: paypal send either VERIFIED or INVALID (single word)

        Once data is validated, process it. """
        res = False
        new_post = dict(post)
        order_id=int(str(new_post['order_id']))
        cr, uid, context = request.cr, SUPERUSER_ID, request.context
        pay_ids = request.registry['payment.transaction'].search(cr, SUPERUSER_ID, [('sale_order_id','=',order_id)],context=context)
        if pay_ids:
                    pay_ids_obj = request.registry['payment.transaction'].browse(cr, SUPERUSER_ID, pay_ids[0],context=context)
                    if pay_ids_obj.paypal_txn_id:
                        res='Pagato'
                    else:
                        res='NonPagato'    
        else:
            res='NonTrovato'
        return res

    def sda_validate_login(self, **post):
        res = False
        new_post = dict(post)
        cr, uid, context = request.cr, SUPERUSER_ID, request.context
        check_ids = request.registry['delivery.carrier.sda.check'].search(cr, uid, [('sda_customer', '=', new_post.get('sda_customer','')),('sda_monitor', '=', new_post.get('sda_monitor',''))], context=context)
        if check_ids:
                check_ids_obj=request.registry['delivery.carrier.sda.check'].browse(cr, uid,check_ids[0], context=context)
                if check_ids_obj:
                    sda_monitor=check_ids_obj.sda_monitor
                    sda_monitor=str(sda_monitor).encode()           
                    print 'name--code-encode-->',sda_monitor
                    res='&%s&%s' % ('SI',sda_monitor)
        else:
                res='NO'
        return res
    @http.route(['/sda/sdacustomer',
                     
                 
                 ], type='json', auth="public", methods=['POST'])
    def sda_customer_json(self, **post):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        url = "/sda"
        check_obj=pool['delivery.carrier.sda.check']
        value={}
        post=post.get('check',{})
        print 'post',post
        if post.get('sda_customer',None):
            check_ids = check_obj.search(cr, SUPERUSER_ID, [('sda_customer','=',post["sda_customer"])], context=context)
            if check_ids:
                for check_id_obj in check_obj.browse(cr,SUPERUSER_ID,check_ids,context=context):
                        if  check_id_obj.sda_monitor!=post.get('sda_monitor',None) :
                            value['sda_monitor'] = 0
                            return value
                                 
            else:
                check_id=check_obj.create(cr,SUPERUSER_ID,{
                                        'sda_customer':post.get('sda_customer',None),
                                         #'sda_monitor':post.get('sda_monitor',None),
                                         #'sda_monitor_count':post.get('sda_monitor_count',None),
                                         'sda_company_name':post.get('sda_company_name',None),
                                         'sda_company_city':post.get('sda_company_city',None),
                                         'sda_company_street':post.get('sda_company_street',None),
                                         'sda_user':post.get('sda_user',None),
                                         'sda_password':post.get('sda_password',None),
                                         'sda_url':post.get('sda_url',None),
                                         'sda_url_trk':post.get('sda_url_trk',None),
                                         },context=context)
                check_id_obj=check_obj.browse(cr,SUPERUSER_ID,check_id,context=context)
                value['sda_monitor']=check_id_obj.sda_monitor
                value['sda_monitor_count']=check_id_obj.sda_monitor
        return value

    @http.route(['/sda/sdarun'], type='json', auth="public", methods=['POST'],website=True)
    def sda_customer_json(self, **post):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        url = "/sda"
        check_obj=pool['delivery.carrier.sda.check']
        value={}
        post=post.get('check',{})
        if post.get('sda_customer',None):
            check_ids = check_obj.search(cr, SUPERUSER_ID, [('sda_customer','=',post["sda_customer"])], context=context)
            if check_ids:
                for check_id_obj in check_obj.browse(cr,SUPERUSER_ID,check_ids,context=context):
                        if  check_id_obj.sda_monitor!=post.get('sda_monitor',None) :
                            value={}
                            return value
                        
                        if str(check_id_obj.sda_url).find('https')>=0:
                            if check_id_obj.usa_cert==False:
                                req = requests.post(check_id_obj.sda_url, data=json.dumps(body),headers=headers,verify=False,auth=HTTPBasicAuth(check_id_obj.sda_user,check_id_obj.sda_password)) 
                                response=req.text
                                #print 'response',response
                            else:
                                req = requests.post(check_id_obj.sda_url, data=json.dumps(body),
                                                    headers=headers,verify=True,
                                                    cert=filepath,
                                                    auth=HTTPBasicAuth(check_id_obj.sda_user,check_id_obj.sda_password)) 
                                response=req.text
                        else:
                                req = requests.post(check_id_obj.sda_url, data=json.dumps(body),headers=headers,verify=False,auth=HTTPBasicAuth(check_id_obj.sda_user,check_id_obj.sda_password)) 
                                response=req.text
                                #print 'response',response
                        if response:
                            ret=json.loads(response)
                            return   ret             
                        
                        else:
                            return  {}             
                        


        return value

    @http.route(['/sda/sdaruntrk'], type='json', auth="public", methods=['POST'],website=True)
    def sda_customer_json(self, **post):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        url = "/sda"
        check_obj=pool['delivery.carrier.sda.check']
        value={}
        if post.get('sda_customer',None):
            check_ids = check_obj.search(cr, SUPERUSER_ID, [('sda_customer','=',post["sda_customer"])], context=context)
            if check_ids:
                for check_id_obj in check_obj.browse(cr,SUPERUSER_ID,check_ids,context=context):
                        if  check_id_obj.sda_monitor!=post.get('sda_monitor',None) :
                            value={}
                            return value
                        
                        if str(check_id_obj.sda_url_trk).find('https')>=0:
                            if check_id_obj.usa_cert==False:
                                req = requests.post(check_id_obj.sda_url_trk, data=json.dumps(body),headers=headers,verify=False,auth=HTTPBasicAuth(check_id_obj.sda_user,check_id_obj.sda_password)) 
                                response=req.text
                                #print 'response',response
                            else:
                                req = requests.post(check_id_obj.sda_url_trk, data=json.dumps(body),
                                                    headers=headers,verify=True,
                                                    cert=filepath,
                                                    auth=HTTPBasicAuth(check_id_obj.sda_user,check_id_obj.sda_password)) 
                                response=req.text
                        else:
                                req = requests.post(check_id_obj.sda_url_trk, data=json.dumps(body),headers=headers,verify=False,auth=HTTPBasicAuth(check_id_obj.sda_user,check_id_obj.sda_password)) 
                                response=req.text
                                #print 'response',response
                        if response:
                            ret=json.loads(response)
                            return   ret             
                        
                        else:
                            return  {}             
                        


        return value


# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
