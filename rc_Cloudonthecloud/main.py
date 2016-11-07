# -*- coding: utf-8 -*-

try:
    import simplejson as json
except ImportError:
    import json
import logging
import pprint
import urllib2
import werkzeug
from openerp import http, SUPERUSER_ID
from openerp.http import request
_logger = logging.getLogger(__name__)


class PaypalController(http.Controller):
    _notify_url = '/cloud/payment/paypal/ipn/'
    _return_url = '/cloud/payment/paypal/dpn/'
    _cancel_url = '/cloud/payment/paypal/cancel/'

    def paypal_validate_data(self, **post):
        """ Paypal IPN: three steps validation to ensure data correctness

         - step 1: return an empty HTTP 200 response -> will be done at the end
           by returning ''
         - step 2: POST the complete, unaltered message back to Paypal (preceded
           by cmd=_notify-validate), with same encoding
         - step 3: paypal send either VERIFIED or INVALID (single word)

        Once data is validated, process it. """
        res = False
        new_post = dict(post, cmd='_notify-validate')
        #urequest = urllib2.Request("https://www.sandbox.paypal.com/cgi-bin/webscr", werkzeug.url_encode(new_post))
        urequest = urllib2.Request("https://www.paypal.com/cgi-bin/webscr", werkzeug.url_encode(new_post))
        uopen = urllib2.urlopen(urequest)
        resp = uopen.read()
        if resp == 'VERIFIED':
            _logger.info('Paypal: validated data')
            cr, uid, context = request.cr, SUPERUSER_ID, request.context
            res = request.registry['payment.transaction'].form_feedback(cr, uid, post, 'paypal', context=context)
        elif resp == 'INVALID':
            _logger.warning('Paypal: answered INVALID on data verification')
        else:
            _logger.warning('Paypal: unrecognized paypal answer, received %s instead of VERIFIED or INVALID' % resp.text)
        return res
    def paypal_validate_url(self, **post):
        """ Paypal IPN: three steps validation to ensure data correctness

         - step 1: return an empty HTTP 200 response -> will be done at the end
           by returning ''
         - step 2: POST the complete, unaltered message back to Paypal (preceded
           by cmd=_notify-validate), with same encoding
         - step 3: paypal send either VERIFIED or INVALID (single word)

        Once data is validated, process it. """
        cr, uid, context = request.cr, SUPERUSER_ID, request.context
        x_service_id=post.get('active_ids',False)
        if x_service_id:
            x_service_id_obj = request.registry['account.x.service'].browse(cr,uid,x_service_id,context)

            res = False
            new_get = dict(x_service_id_obj.paypalurl)
            #urequest = urllib2.Request("https://www.sandbox.paypal.com/cgi-bin/webscr", werkzeug.url_encode(new_post))
            urequest = urllib2.Request(x_service_id_obj.paypalurl, werkzeug.url_encode("TEST"))
            uopen = urllib2.urlopen(urequest)
            resp = uopen.read()
            
            request.redirect(x_service_id_obj.paypalurl)
            if resp == 'VERIFIED':
                _logger.info('Paypal: validated data')
                cr, uid, context = request.cr, SUPERUSER_ID, request.context
                res = request.registry['payment.transaction'].form_feedback(cr, uid, post, 'paypal', context=context)
            elif resp == 'INVALID':
                _logger.warning('Paypal: answered INVALID on data verification')
            else:
                _logger.warning('Paypal: unrecognized paypal answer, received %s instead of VERIFIED or INVALID' % resp.text)
            return res

    @http.route('/cloud/payment/paypal/ipn/', type='http', auth='none', methods=['POST'])
    def paypal_ipn(self, **post):
        """ Paypal IPN. """
        _logger.info('Beginning Paypal IPN form_feedback with post data %s', pprint.pformat(post))  # debug
        self.paypal_validate_data(**post)
        return ''
    @http.route('/cloud/payment/paypal/ipn/get/', type='http', auth='none', methods=['GET'])
    def paypal_ipn_get(self, **get):
        """ Paypal IPN. """
        _logger.info('Beginning Paypal IPN form_feedback with post data %s', pprint.pformat(get))  # debug
        self.paypal_validate_data(**get)
        return ''
    @http.route('/cloud/payment/paypal/url/get/', type='http', auth='none', methods=['GET'])
    def paypal_url_get(self, **get):
        """ Paypal url. """
        _logger.info('Beginning Paypal url form  with post data %s', pprint.pformat(get))  # debug
        self.paypal_validate_url(**get)
        return ''

    @http.route('/cloud/payment/paypal/dpn', type='http', auth="none", methods=['POST'])
    def paypal_dpn(self, **post):
        """ Paypal DPN """
        _logger.info('Beginning Paypal DPN form_feedback with post data %s', pprint.pformat(post))  # debug
        return_url = self._get_return_url(**post)
        self.paypal_validate_data(**post)
        return werkzeug.utils.redirect(return_url)

    @http.route('/cloud/payment/paypal/cancel', type='http', auth="none")
    def paypal_cancel(self, **post):
        """ When the user cancels its Paypal payment: GET on this route """
        cr, uid, context = request.cr, SUPERUSER_ID, request.context
        _logger.info('Beginning Paypal cancel with post data %s', pprint.pformat(post))  # debug
        return_url = self._get_return_url(**post)
        return werkzeug.utils.redirect(return_url)
class DomainController(http.Controller):
    _notify_url = '/cloud/domain/notify'
    _return_url = '/cloud/domain/create'
    _cancel_url = '/cloud/domain/cancel/'
    @http.route('/cloud/domain/login/get', type='http', auth='none', methods=['GET'])
    def domain_login_get(self, **get):
        """ domain IPN. """
        _logger.info('Beginning domain IPN  with post data %s', pprint.pformat(get))  # debug
        
        return self.domain_validate_login(**get)
    @http.route('/cloud/domain/login', type='http', auth='none', methods=['POST'])
    def domain_login(self, **post):
        """ domain IPN. """
        _logger.info('Beginning domain IPN  with post data %s', pprint.pformat(post))  # debug
        
        return self.domain_validate_login(**post)

    @http.route('/cloud/domain/create', type='http', auth='none', methods=['POST'])
    def domain_create(self, **post):
        """ domain IPN. """
        _logger.info('Beginning domain IPN form_feedback with post data %s', pprint.pformat(post))  # debug
        res=self.domain_validate_data(**post)
        return res
    @http.route('/cloud/domain/create/get', type='http', auth='none', methods=['GET'])
    def domain_create_get(self, **get):
        """ domain IPN. """
        _logger.info('Beginning domain IPN domain_validate_data with get data %s', pprint.pformat(get))  # debug
        res=self.domain_validate_data(**get)
        return res
    
    @http.route('/cloud/domain/verified/get', type='http', auth='none', methods=['GET'])
    def domain_verified_payment_get(self, **get):
        """ domain IPN. """
        _logger.info('Beginning domain IPN domain_validate_data with get data %s', pprint.pformat(get))  # debug
        res=self.domain_validate_payment(**get)
        return res

    @http.route('/cloud/domain/verified', type='http', auth='none', methods=['POST'])
    def domain_verified_payment(self, **post):
        """ domain IPN. """
        _logger.info('Beginning domain IPN form_feedback with post data %s', pprint.pformat(post))  # debug
        res=self.domain_validate_payment(**post)
        return res

    @http.route('/cloud/domain/cancel', type='http', auth='none', methods=['POST'])
    def domain_create_cancel(self, **post):
        """ domain IPN. """
        _logger.info('Beginning domain IPN form_feedback with post data %s', pprint.pformat(post))  # debug
        res=self.domain_validate_data(**post)
        return res
    @http.route('/cloud/domain/notify', type='http', auth='none', methods=['POST'])
    def domain_create_notify(self, **post):
        """ Paypal IPN. """
        _logger.info('Beginning domain IPN form_feedback with post data %s', pprint.pformat(post))  # debug
        res=self.domain_validate_data(**post)
        return res
    def domain_validate_data(self, **post):
        """ domain IPN: three steps validation to ensure data correctness

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
    def domain_validate_payment(self, **post):
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

    def domain_validate_login(self, **post):
        """ domain IPN: three steps validation to ensure data correctness

         - step 1: return an empty HTTP 200 response -> will be done at the end
           by returning ''
         - step 2: POST the complete, unaltered message back to Paypal (preceded
           by cmd=_notify-validate), with same encoding
         - step 3: paypal send either VERIFIED or INVALID (single word)

        Once data is validated, process it. """
        res = False
        new_post = dict(post)
        cr, uid, context = request.cr, SUPERUSER_ID, request.context
        partner_ids = request.registry['res.partner'].search(cr, uid, [('signup_token', '=', new_post.get('token',''))], context=context)
        if partner_ids:
                partner_ids_obj=request.registry['res.partner'].browse(cr, uid,partner_ids[0], context=context)
                if partner_ids_obj:
                    name=partner_ids_obj.name
                    name=str(name).encode()           
                    print 'name--code-encode-->',name
                    res='&%s&%s' % ('SI',name)
        else:
                res='NO'
        return res
    
