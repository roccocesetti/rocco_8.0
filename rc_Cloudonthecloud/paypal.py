# -*- coding: utf-'8' "-*-"

import base64
try:
    import simplejson as json
except ImportError:
    import json
import logging
import urlparse
import werkzeug.urls
import urllib2

from openerp.addons.payment.models.payment_acquirer import ValidationError
from openerp.addons.payment_paypal.controllers.main import PaypalController
from openerp.osv import osv, fields
from openerp.tools.float_utils import float_compare
from openerp import SUPERUSER_ID
_logger = logging.getLogger(__name__)




class TxPaypal(osv.Model):
    _inherit = 'payment.transaction'
    def write(self,cr,uid,ids,vals,context=None):
        transaction_obj=self.pool.get('payment.transaction')
        x_service_notify_obj=self.pool.get('account.x.service.notify')
        x_service_obj=self.pool.get('account.x.service')

        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if vals.get('paypal_txn_id'):
            trans_ids_obj=transaction_obj.browse(cr,SUPERUSER_ID,ids,context=context)
            for trans in trans_ids_obj:
                    if trans.notify_id:
                            #if trans.paypal_txn_id:
                                x_service_notify_obj.write(cr,SUPERUSER_ID,trans.notify_id.id,{'paypal_status':'VERIFIED'})
                                for x_notify_line in trans.notify_id.notify_ids:
                                    if x_notify_line.x_service_id:
                                        x_service_obj.write(cr,SUPERUSER_ID,x_notify_line.x_service_id.id,{'paypal_status':'VERIFIED','state':'paid','paypal_id':trans.id})
                    if trans.x_service_id:
                                        x_service_obj.write(cr,SUPERUSER_ID,trans.x_service_id.id,{'paypal_status':'VERIFIED','state':'paid','paypal_id':trans.id})
        return super(TxPaypal, self).write(
                cr, uid, ids, vals, context=context)        
    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------
    def _paypal_form_get_tx_from_data(self, cr, uid, data, context=None):
        invoice,reference, txn_id = data.get('invoice'),data.get('item_number'), data.get('txn_id')
        if not reference:
            reference=invoice
        if data:
            data['item_number']=reference
        return super(TxPaypal,self)._paypal_form_get_tx_from_data(cr, uid, data, context=None)

    def _paypal_form_get_invalid_parameters(self, cr, uid, tx, data, context=None):
        return super(TxPaypal,self)._paypal_form_get_invalid_parameters(cr, uid, tx, data, context=context)

    def _paypal_form_validate(self, cr, uid, tx, data, context=None):
        transaction_obj=self.pool.get('payment.transaction')
        status = data.get('payment_status')
        data = {
            'acquirer_reference': data.get('txn_id'),
            'paypal_txn_id': data.get('txn_id'),
            'paypal_txn_type': data.get('payment_type'),
            'partner_reference': data.get('payer_id')
        }
        if status in ['Completed', 'Processed']:
            _logger.info('Validated Paypal payment for tx %s: set as done' % (tx.reference))
            data.update(state='done', date_validate=data.get('payment_date', fields.datetime.now()))
            #return tx.write(data)
            return transaction_obj.write(cr,uid,tx.id,data,context=context)
        elif status in ['Pending', 'Expired']:
            _logger.info('Received notification for Paypal payment %s: set as pending' % (tx.reference))
            data.update(state='pending', state_message=data.get('pending_reason', ''))
            return transaction_obj.write(cr,uid,tx.id,data,context=context)
        else:
            error = 'Received unrecognized status for Paypal payment %s: %s, set as error' % (tx.reference, status)
            _logger.info(error)
            data.update(state='error', state_message=error)
            return transaction_obj.write(cr,uid,tx.id,data,context=context)
