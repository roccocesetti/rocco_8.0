# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 Davide Corio <davide.corio@lsweb.it>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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

from openerp.osv import fields, orm
import requests
import xml.etree.ElementTree as ET
import lxml.etree as XET
from lxml import etree
import re
import suds.client
from pprint import PrettyPrinter
#from suds.wsse import UsernameToken
#from suds.wsse import Security
#from suds import WebFault
#from suds.sax.element import Element
#from suds.sax.attribute import Attribute
#from suds.xsd.sxbasic import Import
import logging

logging.basicConfig(level=logging.INFO)
logging.getLogger('suds.client').setLevel(logging.DEBUG)
from logging import getLogger
from suds import *
from suds.sudsobject import Object
from suds.sax.element import Element
from suds.sax.attribute import Attribute
from suds.sax.date import UTC
from datetime import datetime, timedelta
from base64 import b64encode
from base64 import b64decode
from suds.wsse import Security,Token,UsernameToken
from tempfile import TemporaryFile
import tempfile
import os, sys
import base64
import time
import json
import urllib2 
import urllib
import httplib2
import sys, httplib
from requests import Request as Session
from requests.auth import HTTPBasicAuth
try:
    from hashlib import md5
except ImportError:
    # Python 2.4 compatibility
    from md5 import md5
from openerp.tools.translate import _
_logger = logging.getLogger(__name__)


dsns = \
    ('ds',
     'http://www.w3.org/2000/09/xmldsig#')
wssens = \
    ('wsse',
     'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd')
wsuns = \
    ('wsu',
     'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd')
wsencns = \
    ('wsenc',
     'http://www.w3.org/2001/04/xmlenc#')


class mySecurity(Security):
    """
    WS-Security object.
    @ivar tokens: A list of security tokens
    @type tokens: [L{Token},...]
    @ivar signatures: A list of signatures.
    @type signatures: TBD
    @ivar references: A list of references.
    @type references: TBD
    @ivar keys: A list of encryption keys.
    @type keys: TBD
    """

    def __init__(self):
        """ """
        Security.__init__(self)
        self.mustUnderstand = True
        self.tokens = []
        self.signatures = []
        self.references = []
        self.keys = []

    def xml(self):
        """
        Get xml representation of the object.
        @return: The root node.
        @rtype: L{Element}
        """
        root = Element('Security', ns=wssens)
        root.set('mustUnderstand', str(self.mustUnderstand).lower())
        for t in self.tokens:
            root.append(t.xml())
        return root


class myToken(Token):
    """ I{Abstract} security token. """

    @classmethod
    def now(cls):
        return datetime.now()

    @classmethod
    def utc(cls):
        return datetime.utcnow()

    @classmethod
    def sysdate(cls):
        utc = UTC()
        return str(utc)

    def __init__(self):
            Token.__init__(self)


class myUsernameToken(myToken):
    """
    Represents a basic I{UsernameToken} WS-Secuirty token.
    @ivar username: A username.
    @type username: str
    @ivar password: A password.
    @type password: str
    @ivar nonce: A set of bytes to prevent reply attacks.
    @type nonce: str
    @ivar created: The token created.
    @type created: L{datetime}
    """

    def __init__(self, username=None, password=None):
        """
        @param username: A username.
        @type username: str
        @param password: A password.
        @type password: str
        """
        myToken.__init__(self)
        self.username = username
        self.password = password
        self.nonce = None
        self.created = None

    def setnonce(self, text=None):
        """
        Set I{nonce} which is arbitraty set of bytes to prevent
        reply attacks.
        @param text: The nonce text value.
            Generated when I{None}.
        @type text: str
        """
        if text is None:
            s = []
            s.append(self.username)
            s.append(self.password)
            s.append(myToken.sysdate())
            m = md5()
            m.update(':'.join(s))
            self.nonce = m.hexdigest()
        else:
            self.nonce = text

    def setcreated(self, dt=None):
        """
        Set I{created}.
        @param dt: The created date & time.
            Set as datetime.utc() when I{None}.
        @type dt: L{datetime}
        """
        if dt is None:
            self.created = Token.utc()
        else:
            self.created = dt


    def xml(self):
        """
        Get xml representation of the object.
        @return: The root node.
        @rtype: L{Element}
        """
        root = Element('UsernameToken', ns=wssens)
        IncludeToken=Attribute('IncludeToken').setValue("http://docs.oasis-open.org/ws-sx/ws-securitypolicy/200702/IncludeToken/AlwaysToRecipient")
        root.attributes.append(IncludeToken)
 
        u = Element('Username', ns=wssens)
        u.setText(self.username)
        root.append(u)
        p = Element('Password', ns=wssens)
        p.setText(self.password)
        Type=Attribute('Type').setValue('http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText')
        p.attributes.append(Type)
        root.append(p)
        if self.nonce is not None:
            n = Element('Nonce', ns=wssens)
            n.setText(self.nonce)
            root.append(n)
        if self.created is not None:
            n = Element('Created', ns=wsuns)
            n.setText(str(UTC(self.created)))
            root.append(n)
        return root


class Timestamp(myToken):
    """
    Represents the I{Timestamp} WS-Secuirty token.
    @ivar created: The token created.
    @type created: L{datetime}
    @ivar expires: The token expires.
    @type expires: L{datetime}
    """

    def __init__(self, validity=90):
        """
        @param validity: The time in seconds.
        @type validity: int
        """
        myToken.__init__(self)
        self.created = myToken.utc()
        self.expires = self.created + timedelta(seconds=validity)

    def xml(self):
        root = Element("Timestamp", ns=wsuns)
        created = Element('Created', ns=wsuns)
        created.setText(str(UTC(self.created)))
        expires = Element('Expires', ns=wsuns)
        expires.setText(str(UTC(self.expires)))
        root.append(created)
        root.append(expires)
        return root

class FatturaPAAttachment_in(orm.Model):
    #_inherits = {'ir.attachment': 'ir_attachment_id','ir.attachment': 'ir_attachment_signed_id'}    
    _inherit = "fatturapa.attachment.in"

    def _get_default_url(self, cr, uid, ids, context=None):
            fatturapa_url_obj=self.pool.get('fatturapa.url')
            fatturapa_url_ids=fatturapa_url_obj.search(cr,uid,[('id','>',0)],order='sequence desc,id desc',context=context)
            
            if  fatturapa_url_ids:     
                return fatturapa_url_ids[0]
            else:
                return None

    def _get_fat(self, cr, uid, ids, name, arg, context=None):
         res = dict([(i, {}) for i in ids])
         #res = dict.fromkeys(ids, {})
         print 'attach_id_ids',ids,res
         for attach_id in self.browse(cr, uid, ids, context=context):
            print 'attach_id',attach_id.id
            res[attach_id.id]['num_fat']=''
            res[attach_id.id]['data_fat']=''
            res[attach_id.id]['fornitore']=''
            if attach_id.in_invoice_ids:
                print  'in_invoice_ids',attach_id.in_invoice_ids[0].id
                res[attach_id.id]['num_fat'] = attach_id.in_invoice_ids[0].supplier_invoice_number or None
                res[attach_id.id]['data_fat'] =    attach_id.in_invoice_ids[0].date_invoice[8:10]+"/"+attach_id.in_invoice_ids[0].date_invoice[5:7]+"/"+attach_id.in_invoice_ids[0].date_invoice[0:4] or None
                res[attach_id.id]['fornitore'] =    attach_id.in_invoice_ids[0].partner_id.name or None
                break   
         
         return res

    _columns = {
        'ir_attachment_id': fields.many2one(
            'ir.attachment', 'Attachment', required=True, ondelete="cascade"),
        'in_invoice_ids': fields.one2many(
            'account.invoice', 'fatturapa_attachment_in_id',
            string="In Invoices", readonly=True),

        'stato_rx': fields.text('Stato ricezione'),  
        'url_id': fields.many2one('fatturapa.url', 'URl tramissione', required=False ),
        'log': fields.text('Dettaglio'),  
        'id_soap': fields.char(string='Id soap',size=20),  
        'id_sdi': fields.char(string='Id Agenzia entrate',size=20),
        'json_fatForSDIId':fields.char(string='Id fatForSDIId',size=20),
        'json_chiusa':fields.boolean('Chiusa', required=False),
        'json_fatForSDISezionale':fields.char(string='Sezionale',size=20),
        'num_fat' : fields.function(_get_fat, type="char",size=20,multi="dati fatt", string="numero"),
        'data_fat' : fields.function(_get_fat, type="char",size=20,multi="dati fatt", string="data"),
        'fornitore' : fields.function(_get_fat, type="char",size=30,multi="dati fatt", string="Fornitore"),

    }
    _defaults = {  
            'url_id': _get_default_url,  
            }    
                            
    def chiudi_fatturapa(self,cr,uid,ids,context=None):
                    if hasattr(ids, '__iter__'):
                        ids=ids
                    else:
                        ids=[ids]
                    for attach in self.browse(cr,uid,ids,context=context):
                        if attach.url_id.type=="json":
                            self.json_update_request(cr,uid,[attach.id],escludi=True,metadata={},context=context)
    def apri_fatturapa(self,cr,uid,ids,context=None):
                    if hasattr(ids, '__iter__'):
                        ids=ids
                    else:
                        ids=[ids]
                    for attach in self.browse(cr,uid,ids,context=context):
                        if attach.url_id.type=="json":
                            self.json_update_request(cr,uid,[attach.id],escludi=False,metadata={},context=context)
                
    def json_update_request(self,cr,uid,ids,escludi=True,metadata={},context=None):
                attach_obj=self.pool.get('ir.attachment')
                url_obj=self.pool.get('fatturapa.url')
                import_fpa_obj=self.pool.get('wizard.import.fatturapa')
                invoice_obj=self.pool.get('account.invoice')
                partner_obj=self.pool.get('res.partner')
                url_ids=url_obj.search(cr,uid,[('id','>',0)],order='sequence desc ,id desc',context=context)
                url_id_obj=url_obj.browse(cr,uid,url_ids[0],context=context)
                date_today=datetime.today()
                cert_file=date_today.strftime('%d-%m-%Y_%h_%m_%s')+'_.crt'
                user_password=base64.b64encode(url_id_obj.json_username+':'+url_id_obj.json_password )
                user_password='Basic '+user_password
                filepath='/media/disco2/ship_sda_doc/collaudo-ws.sda.it.crt'
                if url_id_obj.json_url_update:
                    if hasattr(ids, '__iter__'):
                        ids=ids
                    else:
                        ids=[ids]
                    for attach in self.browse(cr,uid,ids,context=context):
                          
                       http = httplib2.Http()
                       #body = {'USERNAME': 'foo', 'PASSWORD': 'bar'}..
                       body = {}
                       #invoice='PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0ibGF0aW4xIj8+PG5zMTpGYXR0dXJhRWxldHRyb25pY2EgdmVyc2lvbmU9IkZQUjEyIiB4bWxuczpuczE9Imh0dHA6Ly9pdmFzZXJ2aXppLmFnZW56aWFlbnRyYXRlLmdvdi5pdC9kb2NzL3hzZC9mYXR0dXJlL3YxLjIiPjxGYXR0dXJhRWxldHRyb25pY2FIZWFkZXI+PERhdGlUcmFzbWlzc2lvbmU+PElkVHJhc21pdHRlbnRlPjxJZFBhZXNlPklUPC9JZFBhZXNlPjxJZENvZGljZT4wMTQ3NzQzMDQ0OTwvSWRDb2RpY2U+PC9JZFRyYXNtaXR0ZW50ZT48UHJvZ3Jlc3Npdm9JbnZpbz4wMDAwNzwvUHJvZ3Jlc3Npdm9JbnZpbz48Rm9ybWF0b1RyYXNtaXNzaW9uZT5GUFIxMjwvRm9ybWF0b1RyYXNtaXNzaW9uZT48Q29kaWNlRGVzdGluYXRhcmlvPjAwMDAwMDA8L0NvZGljZURlc3RpbmF0YXJpbz48Q29udGF0dGlUcmFzbWl0dGVudGU+PFRlbGVmb25vPjA3MzQ5NjIzNzY8L1RlbGVmb25vPjxFbWFpbD5pbmZvQHRhbWFudGlub2xlZ2dpLml0PC9FbWFpbD48L0NvbnRhdHRpVHJhc21pdHRlbnRlPjxQRUNEZXN0aW5hdGFyaW8+YW1taW5pc3RyYXppb25lQHBlYy50b21hcy5pdDwvUEVDRGVzdGluYXRhcmlvPjwvRGF0aVRyYXNtaXNzaW9uZT48Q2VkZW50ZVByZXN0YXRvcmU+PERhdGlBbmFncmFmaWNpPjxJZEZpc2NhbGVJVkE+PElkUGFlc2U+SVQ8L0lkUGFlc2U+PElkQ29kaWNlPjAxNDc3NDMwNDQ5PC9JZENvZGljZT48L0lkRmlzY2FsZUlWQT48QW5hZ3JhZmljYT48RGVub21pbmF6aW9uZT5UQU1BTlRJIEdJVUxJQU5PPC9EZW5vbWluYXppb25lPjwvQW5hZ3JhZmljYT48UmVnaW1lRmlzY2FsZT5SRjAxPC9SZWdpbWVGaXNjYWxlPjwvRGF0aUFuYWdyYWZpY2k+PFNlZGU+PEluZGlyaXp6bz5TT0NDT1JTTyAyNjwvSW5kaXJpenpvPjxDQVA+NjM4MzM8L0NBUD48Q29tdW5lPk1PTlRFR0lPUkdJTzwvQ29tdW5lPjxQcm92aW5jaWE+Rk08L1Byb3ZpbmNpYT48TmF6aW9uZT5JVDwvTmF6aW9uZT48L1NlZGU+PENvbnRhdHRpPjxUZWxlZm9ubz4wNzM0OTYyMzc2PC9UZWxlZm9ubz48RW1haWw+aW5mb0B0YW1hbnRpbm9sZWdnaS5pdDwvRW1haWw+PC9Db250YXR0aT48L0NlZGVudGVQcmVzdGF0b3JlPjxDZXNzaW9uYXJpb0NvbW1pdHRlbnRlPjxEYXRpQW5hZ3JhZmljaT48SWRGaXNjYWxlSVZBPjxJZFBhZXNlPklUPC9JZFBhZXNlPjxJZENvZGljZT4wMDE3OTIxMDQ0ODwvSWRDb2RpY2U+PC9JZEZpc2NhbGVJVkE+PEFuYWdyYWZpY2E+PERlbm9taW5hemlvbmU+TUFHTElGSUNJTyBUT01BUyBTUkwgPC9EZW5vbWluYXppb25lPjwvQW5hZ3JhZmljYT48L0RhdGlBbmFncmFmaWNpPjxTZWRlPjxJbmRpcml6em8+VklBIFNBQ0NPTkkgTicxPC9JbmRpcml6em8+PENBUD42MzkwMDwvQ0FQPjxDb211bmU+RkVSTU88L0NvbXVuZT48UHJvdmluY2lhPkZNPC9Qcm92aW5jaWE+PE5hemlvbmU+SVQ8L05hemlvbmU+PC9TZWRlPjwvQ2Vzc2lvbmFyaW9Db21taXR0ZW50ZT48L0ZhdHR1cmFFbGV0dHJvbmljYUhlYWRlcj48RmF0dHVyYUVsZXR0cm9uaWNhQm9keT48RGF0aUdlbmVyYWxpPjxEYXRpR2VuZXJhbGlEb2N1bWVudG8+PFRpcG9Eb2N1bWVudG8+VEQwMTwvVGlwb0RvY3VtZW50bz48RGl2aXNhPkVVUjwvRGl2aXNhPjxEYXRhPjIwMTgtMDYtMjA8L0RhdGE+PE51bWVybz5GREovMjAxOC8wMjcwPC9OdW1lcm8+PEltcG9ydG9Ub3RhbGVEb2N1bWVudG8+OTUuMDA8L0ltcG9ydG9Ub3RhbGVEb2N1bWVudG8+PC9EYXRpR2VuZXJhbGlEb2N1bWVudG8+PC9EYXRpR2VuZXJhbGk+PERhdGlCZW5pU2Vydml6aT48RGV0dGFnbGlvTGluZWU+PE51bWVyb0xpbmVhPjE8L051bWVyb0xpbmVhPjxEZXNjcml6aW9uZT5OT0xFR0dJTyBPUEVMIFZJVkFSTyBFWjIzNFdEPC9EZXNjcml6aW9uZT48UXVhbnRpdGE+MS4wMDwvUXVhbnRpdGE+PFVuaXRhTWlzdXJhPlVuaXRhPC9Vbml0YU1pc3VyYT48UHJlenpvVW5pdGFyaW8+OTUuMDA8L1ByZXp6b1VuaXRhcmlvPjxQcmV6em9Ub3RhbGU+NzcuODc8L1ByZXp6b1RvdGFsZT48QWxpcXVvdGFJVkE+MjIuMDA8L0FsaXF1b3RhSVZBPjwvRGV0dGFnbGlvTGluZWU+PERhdGlSaWVwaWxvZ28+PEFsaXF1b3RhSVZBPjIyLjAwPC9BbGlxdW90YUlWQT48SW1wb25pYmlsZUltcG9ydG8+NzcuODc8L0ltcG9uaWJpbGVJbXBvcnRvPjxJbXBvc3RhPjE3LjEzPC9JbXBvc3RhPjwvRGF0aVJpZXBpbG9nbz48L0RhdGlCZW5pU2Vydml6aT48RGF0aVBhZ2FtZW50bz48Q29uZGl6aW9uaVBhZ2FtZW50bz5UUDAzPC9Db25kaXppb25pUGFnYW1lbnRvPjxEZXR0YWdsaW9QYWdhbWVudG8+PE1vZGFsaXRhUGFnYW1lbnRvPk1QMDI8L01vZGFsaXRhUGFnYW1lbnRvPjxEYXRhU2NhZGVuemFQYWdhbWVudG8+MjAxOC0wNi0yMDwvRGF0YVNjYWRlbnphUGFnYW1lbnRvPjxJbXBvcnRvUGFnYW1lbnRvPjk1LjAwPC9JbXBvcnRvUGFnYW1lbnRvPjxJc3RpdHV0b0ZpbmFuemlhcmlvPkJBTkNBIERFTExFIE1BUkNIRTwvSXN0aXR1dG9GaW5hbnppYXJpbz48L0RldHRhZ2xpb1BhZ2FtZW50bz48L0RhdGlQYWdhbWVudG8+PC9GYXR0dXJhRWxldHRyb25pY2FCb2R5PjwvbnMxOkZhdHR1cmFFbGV0dHJvbmljYT4='
                       metadata=[{"olv:escludi":escludi}]                      
                       if  attach.in_invoice_ids:
                            if  attach.in_invoice_ids[0].move_id:
                               len_id=len(str(attach.in_invoice_ids[0].id))
                               if len_id>5:
                                   len_id=5
                               proto=attach.in_invoice_ids[0].move_id.date[2:4]+str(attach.in_invoice_ids[0].id)[len(str(attach.in_invoice_ids[0].id))-len_id:len(str(attach.in_invoice_ids[0].id))]
                               #proto=str(attach.in_invoice_ids[0].id)[len(str(attach.in_invoice_ids[0].id))-len_id:len(str(attach.in_invoice_ids[0].id))]
                               metadata= [{"olv:escludi":escludi},
                                        {"olv:fatForSDISezionale":attach.in_invoice_ids[0].journal_id.id},
                                        {"olv:fatForSDINumProtocollo":proto},
                                        {"olv:fatForSDIDataRegistrazione":attach.in_invoice_ids[0].move_id.date},
                                        #"olv:fatForSDIStato":'HDO02' if metadata.get('olv:fatForSDINote',None) else 'HDO01'
                                        ]                      
                            else:
                               metadata= [{"olv:escludi":escludi,
                                        }]                      
                                
                       if attach.json_fatForSDIId:
                            keys=[{"olv:fatForSDIId":attach.json_fatForSDIId}]
                            """
                            keys={
                               "olv:fatForSDIPivaCodFisc":attach.in_invoice_ids[0].partner_id.vat[2:13] or attach.in_invoice_ids[0].partner_id.fiscalcode ,
                               "olv:fatForSDINumFattura":attach.in_invoice_ids[0].supplier_invoice_number,
                               "olv:fatForSDIAnno":int(attach.in_invoice_ids[0].date_invoice[0:4]),
                               }
                            """
                       else:
                           vat_code=""
                           if attach.in_invoice_ids:
                                   if attach.in_invoice_ids[0].partner_id.vat:
                                       vat_code=attach.in_invoice_ids[0].partner_id.vat#[2:13]
                                   elif  attach.in_invoice_ids[0].partner_id.fiscalcode:
                                       vat_code=attach.in_invoice_ids[0].partner_id.fiscalcode
                                   else:
                                       vat_code=""
                                 
                                       
                                   keys=[
                                       {"olv:fatForSDIPivaCodFisc": vat_code} ,
                                       {"olv:fatForSDINumFattura":attach.in_invoice_ids[0].supplier_invoice_number},
                                       {"olv:fatForSDIAnno":attach.in_invoice_ids[0].date_invoice[0:4]},
                                       ]
                           else:
                                keys={}

                       params = {
                           "site":str(url_id_obj.json_sito),
                           "class":"olv:fatForSDI",                    
                           "items":
                                [
                                    {
                                        "keys": keys,
                                        "metadata": metadata
                                    }   
                                ]                
                           }
                       
                       headers ={'Content-Type':'application/json','Authorization':user_password}
                       #headers ={'Authorization':user_password}
                       #try: 
                       print 'url',url_id_obj.json_url_update
                       print 'user,password-->',url_id_obj.json_username,url_id_obj.json_password
                       print 'body-->',body
                       print 'headers-->',headers
                       print 'params-->',params
                       print 'auth',HTTPBasicAuth(url_id_obj.json_username,url_id_obj.json_password)
                       print 'data',json.dumps(body)
                       jsonString = json.dumps(params)
                       print 'jsonString',jsonString #get string with all double quotes 
                       if str(url_id_obj.json_url_update).find('https')>=0:
                            if url_id_obj.json_usa_cert==False:
                                req = requests.post(url_id_obj.json_url_update, 
                                                    data=jsonString,
                                                    headers=headers,
                                                    ) 
                                response=req.text
                                print 'response_json_send_request',response
                                print 'req',req
                            else:
                                req = requests.post(url_id_obj.json_url_update, 
                                                    data=jsonString,
                                                    headers=headers,
                                                    verify=True,
                                                    cert=filepath,
                                                    ) 
                                response=req.text
                       else:
                                req = requests.post(url_id_obj.json_url_update, 
                                                    data=jsonString,
                                                    headers=headers,
                                                    verify=False,
                                                    ) 
                                response=req.text
                                print 'response',response
                       if response:
                            try:
                                fatture=json.loads(response)
                            except:
                                raise orm.except_orm(
                        _("Avviso"), _("Il server non è disponibile, riprovare più tardi"))
                            if fatture['returnCode']=='0000':    
                                for ret_meta in fatture['message']:
                                    ret=ret_meta['message']
                                    print 'ret',ret
                                    stato_rx={
                                                'stato_rx':fatture['returnCode'],
                                                'log':fatture['description']+'-'+fatture['message'][0]['message']
                                                }

                            else:
                                    if fatture['message']:
                                        message_rx=fatture['message'][0]['message']
                                    else:
                                        message_rx=''
                                    stato_rx={
                                                'stato_rx':fatture['returnCode'],
                                                'log':fatture['description']+'-'+message_rx
                                                }
                                
                            self.write(cr,uid,attach.id,stato_rx)
                            return True
                       else:
                            return True        
    def json_imp_request(self,cr,uid,ids=[],processid='1',context=None):
                    attach_obj=self.pool.get('ir.attachment')
                    url_obj=self.pool.get('fatturapa.url')
                    import_fpa_obj=self.pool.get('wizard.import.fatturapa')
                    invoice_obj=self.pool.get('account.invoice')
                    partner_obj=self.pool.get('res.partner')
                    url_ids=url_obj.search(cr,uid,[('id','>',0)],order='sequence desc ,id desc',context=context)
                    url_id_obj=url_obj.browse(cr,uid,url_ids[0],context=context)
                    date_today=datetime.today()
                    cert_file=date_today.strftime('%d-%m-%Y_%h_%m_%s')+'_.crt'
                    user_password=base64.b64encode(url_id_obj.json_username+':'+url_id_obj.json_password )
                    #user_password=sda_obj.user+':'+sda_obj.password..
                    user_password='Basic '+user_password
                    filepath='/media/disco2/ship_sda_doc/collaudo-ws.sda.it.crt'
                    if url_id_obj.json_url_import:
                       http = httplib2.Http()
                        #body = {'USERNAME': 'foo', 'PASSWORD': 'bar'}..
                       body = {}
                       #invoice='PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0ibGF0aW4xIj8+PG5zMTpGYXR0dXJhRWxldHRyb25pY2EgdmVyc2lvbmU9IkZQUjEyIiB4bWxuczpuczE9Imh0dHA6Ly9pdmFzZXJ2aXppLmFnZW56aWFlbnRyYXRlLmdvdi5pdC9kb2NzL3hzZC9mYXR0dXJlL3YxLjIiPjxGYXR0dXJhRWxldHRyb25pY2FIZWFkZXI+PERhdGlUcmFzbWlzc2lvbmU+PElkVHJhc21pdHRlbnRlPjxJZFBhZXNlPklUPC9JZFBhZXNlPjxJZENvZGljZT4wMTQ3NzQzMDQ0OTwvSWRDb2RpY2U+PC9JZFRyYXNtaXR0ZW50ZT48UHJvZ3Jlc3Npdm9JbnZpbz4wMDAwNzwvUHJvZ3Jlc3Npdm9JbnZpbz48Rm9ybWF0b1RyYXNtaXNzaW9uZT5GUFIxMjwvRm9ybWF0b1RyYXNtaXNzaW9uZT48Q29kaWNlRGVzdGluYXRhcmlvPjAwMDAwMDA8L0NvZGljZURlc3RpbmF0YXJpbz48Q29udGF0dGlUcmFzbWl0dGVudGU+PFRlbGVmb25vPjA3MzQ5NjIzNzY8L1RlbGVmb25vPjxFbWFpbD5pbmZvQHRhbWFudGlub2xlZ2dpLml0PC9FbWFpbD48L0NvbnRhdHRpVHJhc21pdHRlbnRlPjxQRUNEZXN0aW5hdGFyaW8+YW1taW5pc3RyYXppb25lQHBlYy50b21hcy5pdDwvUEVDRGVzdGluYXRhcmlvPjwvRGF0aVRyYXNtaXNzaW9uZT48Q2VkZW50ZVByZXN0YXRvcmU+PERhdGlBbmFncmFmaWNpPjxJZEZpc2NhbGVJVkE+PElkUGFlc2U+SVQ8L0lkUGFlc2U+PElkQ29kaWNlPjAxNDc3NDMwNDQ5PC9JZENvZGljZT48L0lkRmlzY2FsZUlWQT48QW5hZ3JhZmljYT48RGVub21pbmF6aW9uZT5UQU1BTlRJIEdJVUxJQU5PPC9EZW5vbWluYXppb25lPjwvQW5hZ3JhZmljYT48UmVnaW1lRmlzY2FsZT5SRjAxPC9SZWdpbWVGaXNjYWxlPjwvRGF0aUFuYWdyYWZpY2k+PFNlZGU+PEluZGlyaXp6bz5TT0NDT1JTTyAyNjwvSW5kaXJpenpvPjxDQVA+NjM4MzM8L0NBUD48Q29tdW5lPk1PTlRFR0lPUkdJTzwvQ29tdW5lPjxQcm92aW5jaWE+Rk08L1Byb3ZpbmNpYT48TmF6aW9uZT5JVDwvTmF6aW9uZT48L1NlZGU+PENvbnRhdHRpPjxUZWxlZm9ubz4wNzM0OTYyMzc2PC9UZWxlZm9ubz48RW1haWw+aW5mb0B0YW1hbnRpbm9sZWdnaS5pdDwvRW1haWw+PC9Db250YXR0aT48L0NlZGVudGVQcmVzdGF0b3JlPjxDZXNzaW9uYXJpb0NvbW1pdHRlbnRlPjxEYXRpQW5hZ3JhZmljaT48SWRGaXNjYWxlSVZBPjxJZFBhZXNlPklUPC9JZFBhZXNlPjxJZENvZGljZT4wMDE3OTIxMDQ0ODwvSWRDb2RpY2U+PC9JZEZpc2NhbGVJVkE+PEFuYWdyYWZpY2E+PERlbm9taW5hemlvbmU+TUFHTElGSUNJTyBUT01BUyBTUkwgPC9EZW5vbWluYXppb25lPjwvQW5hZ3JhZmljYT48L0RhdGlBbmFncmFmaWNpPjxTZWRlPjxJbmRpcml6em8+VklBIFNBQ0NPTkkgTicxPC9JbmRpcml6em8+PENBUD42MzkwMDwvQ0FQPjxDb211bmU+RkVSTU88L0NvbXVuZT48UHJvdmluY2lhPkZNPC9Qcm92aW5jaWE+PE5hemlvbmU+SVQ8L05hemlvbmU+PC9TZWRlPjwvQ2Vzc2lvbmFyaW9Db21taXR0ZW50ZT48L0ZhdHR1cmFFbGV0dHJvbmljYUhlYWRlcj48RmF0dHVyYUVsZXR0cm9uaWNhQm9keT48RGF0aUdlbmVyYWxpPjxEYXRpR2VuZXJhbGlEb2N1bWVudG8+PFRpcG9Eb2N1bWVudG8+VEQwMTwvVGlwb0RvY3VtZW50bz48RGl2aXNhPkVVUjwvRGl2aXNhPjxEYXRhPjIwMTgtMDYtMjA8L0RhdGE+PE51bWVybz5GREovMjAxOC8wMjcwPC9OdW1lcm8+PEltcG9ydG9Ub3RhbGVEb2N1bWVudG8+OTUuMDA8L0ltcG9ydG9Ub3RhbGVEb2N1bWVudG8+PC9EYXRpR2VuZXJhbGlEb2N1bWVudG8+PC9EYXRpR2VuZXJhbGk+PERhdGlCZW5pU2Vydml6aT48RGV0dGFnbGlvTGluZWU+PE51bWVyb0xpbmVhPjE8L051bWVyb0xpbmVhPjxEZXNjcml6aW9uZT5OT0xFR0dJTyBPUEVMIFZJVkFSTyBFWjIzNFdEPC9EZXNjcml6aW9uZT48UXVhbnRpdGE+MS4wMDwvUXVhbnRpdGE+PFVuaXRhTWlzdXJhPlVuaXRhPC9Vbml0YU1pc3VyYT48UHJlenpvVW5pdGFyaW8+OTUuMDA8L1ByZXp6b1VuaXRhcmlvPjxQcmV6em9Ub3RhbGU+NzcuODc8L1ByZXp6b1RvdGFsZT48QWxpcXVvdGFJVkE+MjIuMDA8L0FsaXF1b3RhSVZBPjwvRGV0dGFnbGlvTGluZWU+PERhdGlSaWVwaWxvZ28+PEFsaXF1b3RhSVZBPjIyLjAwPC9BbGlxdW90YUlWQT48SW1wb25pYmlsZUltcG9ydG8+NzcuODc8L0ltcG9uaWJpbGVJbXBvcnRvPjxJbXBvc3RhPjE3LjEzPC9JbXBvc3RhPjwvRGF0aVJpZXBpbG9nbz48L0RhdGlCZW5pU2Vydml6aT48RGF0aVBhZ2FtZW50bz48Q29uZGl6aW9uaVBhZ2FtZW50bz5UUDAzPC9Db25kaXppb25pUGFnYW1lbnRvPjxEZXR0YWdsaW9QYWdhbWVudG8+PE1vZGFsaXRhUGFnYW1lbnRvPk1QMDI8L01vZGFsaXRhUGFnYW1lbnRvPjxEYXRhU2NhZGVuemFQYWdhbWVudG8+MjAxOC0wNi0yMDwvRGF0YVNjYWRlbnphUGFnYW1lbnRvPjxJbXBvcnRvUGFnYW1lbnRvPjk1LjAwPC9JbXBvcnRvUGFnYW1lbnRvPjxJc3RpdHV0b0ZpbmFuemlhcmlvPkJBTkNBIERFTExFIE1BUkNIRTwvSXN0aXR1dG9GaW5hbnppYXJpbz48L0RldHRhZ2xpb1BhZ2FtZW50bz48L0RhdGlQYWdhbWVudG8+PC9GYXR0dXJhRWxldHRyb25pY2FCb2R5PjwvbnMxOkZhdHR1cmFFbGV0dHJvbmljYT4='
                       params = {
                           "site":str(url_id_obj.json_sito),
                           "class":"olv:fatForSDI",
                           "xmlFile": True                          
                           }
                       
                       headers ={'Content-Type':'application/json','Authorization':user_password}
                       #headers ={'Authorization':user_password}
                       #try: 
                       print 'url',url_id_obj.json_url_import
                       print 'user,password-->',url_id_obj.json_username,url_id_obj.json_password
                       print 'body-->',body
                       print 'headers-->',headers
                       print 'params-->',params
                       print 'auth',HTTPBasicAuth(url_id_obj.json_username,url_id_obj.json_password)
                       print 'data',json.dumps(body)
                       jsonString = json.dumps(params)
                       print 'jsonString',jsonString #get string with all double quotes 
                       conta_fatt=0
                       if str(url_id_obj.json_url_import).find('https')>=0:
                            if url_id_obj.json_usa_cert==False:
                                req = requests.post(url_id_obj.json_url_import, 
                                                    data=jsonString,
                                                    headers=headers,
                                                    ) 
                                response=req.text
                                #print 'response_json_send_request',response
                                #print 'req',req
                            else:
                                req = requests.post(url_id_obj.json_url_import, 
                                                    data=jsonString,
                                                    headers=headers,
                                                    verify=True,
                                                    cert=filepath
                                                    ) 
                                """"
                                s = Session()
                                req = Request('POST',  url,
                                    data=json.dumps(body),
                                    headers=headers,
                                    auth=HTTPBasicAuth(sda_obj.user,sda_obj.password)
                                )
                                """
                                response=req.text
                       else:
                                req = requests.post(url_id_obj.json_url_import, 
                                                    data=jsonString,
                                                    headers=headers,verify=False) 
                                response=req.text
                       #print 'response',response
                       import_ids=[]
                       if response:
                            try:
                                fatture=json.loads(response)
                            except:
                                raise orm.except_orm(
                        _("Avviso"), _("Il server non è disponibile, riprovare più tardi"))
                            if fatture['returnCode']=='0000':    
                                for ret_meta in fatture['message']:
                                    ret=ret_meta['metadata']
                                    #print 'ret',ret
                                    partner_ids=partner_obj.search(cr,uid,[('vat','=',ret[2]['olv:fatForSDIPivaCodFisc'])],context=context)
                                    if ret[2]['olv:fatForSDIPivaCodFisc']=='IT03863660167':
                                        print 'ret_IT03863660167',ret,partner_ids
                                    if partner_ids:
                                        data_invoice = str(ret[6]['olv:fatForSDIDataEmissione'])

                                        invoice_ids_obj=invoice_obj.search(cr,uid,[
                                                                            ('supplier_invoice_number','=',ret[5]['olv:fatForSDINumFattura']),
                                                                            ('date_invoice','=',data_invoice),
                                                                            ('partner_id','=',partner_ids[0]),
                                                                             ],context=context)
                                    
                                        if invoice_ids_obj:
                                            ok=True
                                        else:
                                            invoice_ids_obj=None
                                    else:
                                        invoice_ids_obj=None
                                    conta_fatt+=1
                                    print 'Fatt_sca',conta_fatt,ret[5]['olv:fatForSDINumFattura'],ret[6]['olv:fatForSDIDataEmissione'],ret[7]['olv:fatForSDIId']
                                    if invoice_ids_obj==None:
                                            invoice = b64decode(ret_meta['file'])
                                            #invoice = b64encode(str(invoice))
                                            stato_rx={'type':'json',
                                                'olv:fatForSDINumFattura':ret[5]['olv:fatForSDINumFattura'],
                                                'olv:fatForSDIDataEmissione':str(ret[6]['olv:fatForSDIDataEmissione']),
                                                'olv:fatForSDIId':ret[7]['olv:fatForSDIId'],
                                                'returnCode':fatture['returnCode'],
                                                'description':fatture['description']
                                                }
                                            atttach_id=import_fpa_obj.saveAttachment(cr, uid,stato_rx , invoice, context)
                                            if context is None:
                                                context={}
                                            context['active_ids']=[atttach_id]
                                            #import_id=import_fpa_obj.create(cr,uid,{},context=context)
                                            import_ids.append(atttach_id)
                                            #print 'stato_rx',stato_rx['olv:fatForSDIDataEmissione'],stato_rx['olv:fatForSDINumFattura'],stato_rx['olv:fatForSDIDataEmissione'],ret[7]['olv:fatForSDIId']

                                #if import_ids:
                                    #res_fpa= import_fpa_obj.importFatturaPA(cr,uid,import_ids,context=context)
                            
                            fatture.update({'import_ids':import_ids})
                            return fatture
                       else:
                            return {'message': [], 'returnCode': '0100', 'description': 'generic error','import_ids':[]}

    def soap_imp_request(self, cr, uid, ids, context=None):
            import_fpa_obj=self.pool.get('wizard.import.fatturapa')
            invoice_obj=self.pool.get('account.invoice')
            partner_obj=self.pool.get('res.partner')
            url_obj=self.pool.get('fatturapa.url')
            attach_in_obj=self.pool.get('fatturapa.attachment.in')
            attach_out_obj=self.pool.get('fatturapa.attachment.out')
            ids_in=attach_in_obj.search(cr,uid,[('id_soap','>',0)],order='id_soap desc',context=context)
            ids_out=attach_out_obj.search(cr,uid,[('id_soap','>',0)],order='id_soap desc',context=context)
            ids_in_obj=None
            ids_out_obj=None
            if ids_in:
                id_in_obj=attach_in_obj(cr,uid,ids_in[0],context=context)
                soap_in_id=id_in_obj.id_soap
            else:
                soap_in_id=0
            if ids_out:
                id_out_obj=attach_out_obj(cr,uid,ids_out[0],context=context)
                soap_out_id=id_out_obj.id_soap
            else:
                soap_out_id=0
            if soap_in_id>=soap_out_id:
                 soap_id=soap_in_id
            else:
                 soap_id=soap_out_id
                
                
            url_ids=url_obj.search(cr,uid,[('id','>',0)],order='sequence desc ,id desc',context=context)
            url_id_obj=url_obj.browse(cr,uid,url_ids[0],context=context)
            if url_id_obj:
                pp = PrettyPrinter(indent=4)
                    
                CUST = url_id_obj.soap_customerName
                USER = url_id_obj.soap_username
                A='1234567890qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM'
                PASS=''
                for a in url_id_obj.soap_password:
                        if A.find(a):
                            PASS+=a

                #PASS = url_id_obj.soap_password[0:len-1]
                #PASS = b64encode(url_id_obj.soap_password)
                #PASS = b64encode(PASS)
                    
                print PASS
                ZONE = 'a-zone-in-my-account.com'
                    
                # The path to the Dynect API WSDL file
                base_url = url_id_obj.soap_wsdl
                base_endpoint = url_id_obj.soap_endpoint
                    
                    # Create a client instance
                client = suds.client.Client(base_url)
                client.options.location = base_endpoint
                security=mySecurity()
                token=myUsernameToken(username=USER,password=PASS)
                security.tokens.append(token)
                print token  ,  security
                client.set_options(wsse=security)                    
                
                #client.set_options(
                #soapheaders=security
                #)

                #for method in client.wsdl.services[0].ports[0].methods.values():
                #    print '%s(%s)' % (method.name, ', '.join('%s: %s' % (part.type, part.name) for part in method.soap.input.body.parts))            
                Filter = Element('Filter')
                compare = Element('compare')
                op=Attribute('op').setValue('>')
                compare.attributes.append(op)
                #compare.op=">"
                col = Element('column')
                col.name="ID"
                compare.append(col)
                const = Element('const')
                const.type="long"
                const.value=soap_id
                compare.append(const)
                Filter.append(compare)
                """
                compareElement = client.factory.create('compareElement')
                filterElement = client.factory.create('filterElement')
                
                compareElement.op='>'
                compareElement['column'].name="ID"
                compareElement.const.type="long"
                compareElement.const.value=soap_id
                filterElement.compare=compareElement 
                """
                response = client.service.InvoiceEnum(
                        Filter = Filter,
                        FromIndex = 100000,
                        FetchLimit=100
                    )
                    
                    
                print 'response',response
                    
                if response.ErrorCode not in ('0',None):
                        return {'returnCode':response.ErrorCode,
                                'description':response.ErrorMessage,
                                                                'stato_rx':'%s - %s' % (response.ErrorCode,response.ErrorMessage,),
                                                                }
                else:
                    if response.RowCount==0:
                        return {'message': [], 
                                'returnCode': 'YYY', 
                                'description': 'Nessuna fattura da importare','import_ids':[]}

                    list_invoice=json.loads(response.InvoiceProperties)
                    import_ids=[]
                    fatture= {'message': [], 'returnCode': response.ErrorCode, 'description': response.ErrorMessage,'import_ids':[]}
                    for row_invoice in list_invoice:
                        ids_in=attach_in_obj.search(cr,uid,[('soap_id','>',row_invoice['ID'])],order='id_soap desc',context=context)
                        ids_out=attach_out_obj.search(cr,uid,[('soap_id','>',row_invoice['ID'])],order='id_soap desc',context=context)
                        ids_in_obj=None
                        ids_out_obj=None
                        if ids_in or ids_out:
                                continue
                        res=self.soap_get_request(cr,uid,url_id_obj.id,row_invoice['ID'],context=context)
                        numfat=row_invoice.FatturaElettronicaBody.Numero
                        stato_rx={'type':'soap',
                                  'id_soap':row_invoice['ID'],
                                  'soap_numfat':numfat,
                                  'stato_rx':res['stato_rx'],
                                                }
                        atttach_id=import_fpa_obj.saveAttachment(cr, uid,stato_rx , res['invoice'], context)
                        import_ids.append(atttach_id)
                        fatture.update({'import_ids':import_ids})

            return {'message': [], 'returnCode': 'xxxx', 'description': 'generic error','import_ids':[]}
                   
    def soap_get_request(self, cr, uid, url_id,soap_id, context=None):
            url_obj=self.pool.get('fatturapa.url')
            if soap_id:
                    url_id_obj=url_obj.browse(cr,uid,url_id,context=context)
                    pp = PrettyPrinter(indent=4)
                    
                    CUST = url_id_obj.soap_customerName
                    USER = url_id_obj.soap_username
                    A='1234567890qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM'
                    PASS=''
                    for a in url_id_obj.soap_password:
                        if A.find(a):
                            PASS+=a

                    #PASS = url_id_obj.soap_password[0:len-1]
                    #PASS = b64encode(url_id_obj.soap_password)
                    #PASS = b64encode(PASS)
                    
                    print PASS
                    ZONE = 'a-zone-in-my-account.com'
                    
                    # The path to the Dynect API WSDL file
                    base_url = url_id_obj.soap_wsdl
                    base_endpoint = url_id_obj.soap_endpoint
                    
                    # Create a client instance
                    client = suds.client.Client(base_url)
                    client.options.location = base_endpoint
                    security=mySecurity()
                    token=myUsernameToken(username=USER,password=PASS)
                    security.tokens.append(token)
                    
                    client.set_options(wsse=security)                    
                    #client.set_options(
                    #soapheaders=security
                    #)

                    #for method in client.wsdl.services[0].ports[0].methods.values():
                    #    print '%s(%s)' % (method.name, ', '.join('%s: %s' % (part.type, part.name) for part in method.soap.input.body.parts))            
                    response = client.service.InvoiceGet(
                        ID = soap_id,
                        contentType = 'auto',
                    )
                    
                    print 'response',response
                    if response.ErrorCode not in ('0',None):
                        return  {
                                    'invoice':None,
                                    'stato_rx':'%s - %s' % (response.ErrorCode,response.ErrorMessage,),
                                }
                    else:
                        print 'response.Invoice[0:4]',response.Invoice[0:4]
                        if  response.Invoice[0:4] == 'MIAG':
                                           """cades"""
                                           extenz='xml.7pm'
                                           
                        else:
                                          """ xcades """
                                          extenz='.xml'
                        invoice_dec = b64decode(response.Invoice)
                                          #invoice = b64encode(response.Invoice)
                                          #handle, filepath = tempfile.mkstemp()
                                          #fileobj = os.fdopen(handle,'w+')  # convert raw handle to file object        try:
                        invoice=base64.encodestring(invoice_dec)
                                          #fileobj.write(base64.decodestring(invoice))
                                          #fileobj.close()
                            
                                        #invoice = response.Invoice
                        return  {
                                        'invoice':invoice_dec,
                                        'stato_rx':'%s - %s' % (response.ErrorCode,response.ErrorMessage,),
                                    }
            return {}
class FatturaPAAttachment(orm.Model):
    #_inherits = {'ir.attachment': 'ir_attachment_id','ir.attachment': 'ir_attachment_signed_id'}    
    _inherit = "fatturapa.attachment.out"
    def _get_default_url(self, cr, uid, ids, context=None):
            fatturapa_url_obj=self.pool.get('fatturapa.url')
            fatturapa_url_ids=fatturapa_url_obj.search(cr,uid,[('id','>',0)],order='sequence desc,id desc',context=context)
            
            if  fatturapa_url_ids:     
                return fatturapa_url_ids[0]
            else:
                return None
    def _get_default_processid(self, cr, uid, ids, context=None):
            fatturapa_url_obj=self.pool.get('fatturapa.url')
            fatturapa_url_ids=fatturapa_url_obj.search(cr,uid,[('id','>',0)],order='sequence desc,id desc',context=context)
            
            if  fatturapa_url_ids:     
                fatturapa_url_id_obj=fatturapa_url_obj.browse(cr,uid,fatturapa_url_ids[0],context=context)
                return fatturapa_url_id_obj.processid
            else:
                return None

    def _get_ir_attachment(self, cr, uid, ids, name, args, context=None):
        
        res = {}
        for inv_pa in self.browse(cr, uid, ids, context=context):
            id = inv_pa.id
            res[id] = []
            ir_attach_obj=self.pool.get('ir.attachment')
            if inv_pa.url_id.type=="json":
                if inv_pa.json_fatCliSDIStato in ('HDO01','HDO05'):
                        res[id] = True
                        if inv_pa.firmata==False:
                                    self.write(cr, uid, id, {'firmata':True}, context)
                else: 
                        res[id] = False
                        if inv_pa.firmata==True:
                            self.write(cr, uid, id, {'firmata':False}, context)
            else:
                    
                if inv_pa.ir_attachment_signed_id:
                    ir_attach_ids=ir_attach_obj.search(cr,uid,[('id','=',inv_pa.ir_attachment_signed_id.id)],context=context)
                    if ir_attach_ids:
                        res[id] = True
                        if inv_pa.firmata==False:
                            self.write(cr, uid, id, {'firmata':True}, context)
                    else:
                        res[id] = False
                else:
                        res[id] = False
                        if inv_pa.firmata==True:
                            self.write(cr, uid, id, {'firmata':False}, context)
                    
        return res
    def _get_trasmix(self, cr, uid, ids, name, args, context=None):
        
        res = {}
        for inv_pa in self.browse(cr, uid, ids, context=context):
            id = inv_pa.id
            res[id] = []
            if inv_pa.stato_tx:
                res[id] = True
                if inv_pa.trasmessa==False:
                    self.write(cr, uid, id, {'trasmessa':True}, context)
            else:
                res[id] = False
                if inv_pa.trasmessa==True:
                    self.write(cr, uid, id, {'trasmessa':False}, context)
        return res
    def _get_fat(self, cr, uid, ids, name, arg, context=None):
         res = dict([(i, {}) for i in ids])
         for attach_id in self.browse(cr, uid, ids, context=context):
            if attach_id.out_invoice_ids:
                res[attach_id.id]['num_fat'] = attach_id.out_invoice_ids[0].number
                res[attach_id.id]['data_fat'] =    attach_id.out_invoice_ids[0].date_invoice[8:10]+"/"+attach_id.out_invoice_ids[0].date_invoice[5:7]+"/"+attach_id.out_invoice_ids[0].date_invoice[0:4]
                res[attach_id.id]['cliente'] =    attach_id.out_invoice_ids[0].partner_id.name
         return res

    _columns = {
        'ir_attachment_id': fields.many2one(
            'ir.attachment', 'Attachment', required=True, ondelete="cascade"),
        'out_invoice_ids': fields.one2many(
            'account.invoice', 'fatturapa_attachment_out_id',
            string="Out Invoices", readonly=True),
        
        'ir_attachment_signed_id': fields.many2one(
            'ir.attachment', 'Signed', required=False, ondelete="cascade"),
                
        'fun_firmata': fields.function(_get_ir_attachment, string='Funz.fatt.firmata',type='boolean'),
        'fun_tramessa': fields.function(_get_trasmix, string='Funz.fatt.trasmessa',type='boolean'),
        'firmata':fields.boolean('Firmata', required=False),
        'trasmessa':fields.boolean('Trasmessa', required=False),
        'stato_tx': fields.text('Stato trasmissione'),  
        'stato_rx': fields.text('Stato ricezione'),  
        'url_id': fields.many2one('fatturapa.url', 'URl tramissione', required=False ),
        'log': fields.text('Dettaglio'),  
        'id_soap': fields.char(string='Id soap',size=20),  
        'id_sdi': fields.char(string='Id Agenzia entrate',size=20),  
        'processid': fields.selection([('1','tramessa'), ('sap02','Tramessa,Firmata e Inviata'),
                                  ], 'Workflow Trasmissione', size=10, required=False, help="Modalità di connessione"),

        'json_fatclisdiid':fields.char(string='Id fatcliSDIId',size=20, required=False),
        'json_chiusa':fields.boolean('Chiusa', required=False),
        'json_fatCliSDIStato': fields.selection([
            ('HDO00','In attesa di risposta da SDI'),
            ('HDO01', 'Accettata'),
            ('HDO02', 'Rifiutata'),
            ('HDO03', 'Decorrenza termini'),
            ('HDO05', 'Consegnata'),
            ('HDO06', 'Non consegnata'),  
            ('HDO07', 'Scartata da SDI'),
                                  ], 'Stato conservazione', size=10, required=False, help="Stato conservazione"),
        'json_fatCliSDISezionale':fields.char(string='Sezionale',size=20),
        'num_fat' : fields.function(_get_fat, type="char",size=20,multi="dati fatt", string="numero"),
        'data_fat' : fields.function(_get_fat, type="char",size=20,multi="dati fatt", string="data"),
        'cliente' : fields.function(_get_fat, type="char",size=30,multi="dati fatt", string="Cliente"),
    
    }
    _defaults = {  
            'url_id': _get_default_url,  
            'processid': _get_default_processid,  
            }
    def send_fatturapa(self,cr,uid,ids,processid='1',context=None):
        if context==None:
            context={}
        if context.get('active_model',None)=='account.invoice':
            active_ids=context.get('active_ids',[])
            fatturapa_out=[]
            for invoice_id_obj in self.pool.get('account.invoice').browse(cr,uid,active_ids,context=context):
                if invoice_id_obj.fatturapa_attachment_out_id:
                    if invoice_id_obj.fatturapa_attachment_out_id.trasmessa==False:
                        fatturapa_out.append(invoice_id_obj.fatturapa_attachment_out_id.id)
            
            ids=fatturapa_out
        else:
            active_ids=context.get('active_ids',[])
            if active_ids:
                ids=active_ids
            
        if hasattr(ids, '__iter__'):
            ids=ids
        else:
            ids=[ids]
            
        for attach_id_obj in self.browse(cr,uid,ids,context=context):
            if attach_id_obj.url_id.type=='soap':
                res=self.soap_send_suds(cr,uid,[attach_id_obj.id],processid=processid,context=context)
            elif attach_id_obj.url_id.type=='json':
                res=self.json_send_request(cr,uid,[attach_id_obj.id],processid=processid,context=context)
        return {}
    def ric_fatturapa(self,cr,uid,ids,context=None):
        print 'context',context
        if context==None:
            context={}
        if context.get('active_model',None)=='account.invoice':
                active_ids=context.get('active_ids',[])
                fatturapa_out=[]
                for invoice_id_obj in self.pool.get('account.invoice').browse(cr,uid,active_ids,context=context):
                    if invoice_id_obj.fatturapa_attachment_out_id:
                            fatturapa_out.append(invoice_id_obj.fatturapa_attachment_out_id.id)
                ids=fatturapa_out
        else:
                active_ids=context.get('active_ids',[])
                fatturapa_out=[]
                for fatturapa_attachment_out_id in self.browse(cr,uid,active_ids,context=context):
                             fatturapa_out.append(fatturapa_attachment_out_id.id)
                if fatturapa_out:
                    ids=fatturapa_out
            
        print 'ids',ids
        print 'active_model',context.get('active_model','account.invoice')
        print 'active_ids',context.get('active_ids',[])
        if hasattr(ids, '__iter__'):
            ids=ids
        else:
            ids=[ids]
            
        for attach_id_obj in self.browse(cr,uid,ids,context=context):
            if attach_id_obj.url_id.type=='soap':
                res=self.soap_ric_suds(cr,uid,[attach_id_obj.id],context=context)
            elif attach_id_obj.url_id.type=='json':
                res=self.json_imp_request(cr,uid,[attach_id_obj.id],context=context)
        return {}
    def show_fatturapa(self, cr, uid, ids,stile='PA',context=None):
        if context==None:
            context={}
        if context.get('active_model',None)=='account.invoice':
            active_ids=context.get('active_ids',[])
            fatturapa_out=[]
            fatturapa_in=[]
            for invoice_id_obj in self.pool.get('account.invoice').browse(cr,uid,active_ids,context=context):
                if invoice_id_obj.fatturapa_attachment_out_id:
                        fatturapa_out.append(invoice_id_obj.fatturapa_attachment_out_id.id)
                        continue
                if invoice_id_obj.fatturapa_attachment_in_id:
                        fatturapa_in.append(invoice_id_obj.fatturapa_attachment_in_id.id)
            
            if fatturapa_out:
                ids=fatturapa_out
                attach_obj=self.browse(cr,uid,ids,context=context)
            elif fatturapa_in:
                ids=fatturapa_in
                attach_obj=self.pool.get('fatturapa.attachment.in').browse(cr,uid,ids,context=context)
            else:
                ids=ids
        if hasattr(ids, '__iter__'):
            ids=ids
        else:
            ids=[ids]
            

        for attach_id_obj in attach_obj:
            data = attach_id_obj.ir_attachment_id.datas
            datas_name = attach_id_obj.ir_attachment_id.datas_fname
            if data:
                        out = data.decode('base64')
            else:
                        out = ''
            if stile=="PA":
                stile_pa="http://www.fatturapa.gov.it/export/fatturazione/sdi/fatturapa/v1.2.1/fatturaPA_v1.2.1.xsl"
            else:
                stile_pa="http://www.ideawork.it/joomla2/check_module/FoglioStileAssoSoftware.xsl"
                #stile_pa="http://www.fatturapa.gov.it/export/fatturazione/sdi/fatturapa/v1.2.1/fatturaordinaria_v1.2.1.xsl"
            values={}
            data=urllib.urlencode(values)
            headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
           'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
           'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
           'Accept-Encoding': 'none',
           'Accept-Language': 'en-US,en;q=0.8',
           'Connection': 'keep-alive'
            }
            recovering_parser = XET.XMLParser(recover=True)
            xml_tree = XET.XML(out, parser=recovering_parser)

            #xml_tree = XET.fromstring(root)
            xml_root = xml_tree
            #dom = ET.parse(out)
            req = urllib2.Request(stile_pa, data=data, headers=headers)
            xslt = XET.parse(urllib2.urlopen(req)).getroot()
            print 'soup',xslt
            #xslt = ET.fromstring(soup)
            transform = XET.XSLT(xslt)
            newdom = transform(xml_tree)
            print(XET.tostring(newdom, pretty_print=True))
        
            invoice=base64.encodestring(str(newdom))
            
            print 'invoice',invoice
        
        show_obj = self.pool['wizard.show.fatturapa']
        show_id=show_obj.create(cr,uid,{'fatturapa_html':str(newdom),'fatturapa':invoice,'fatturapa_name':datas_name.replace('xml','html')},context=context)
        model_data_obj = self.pool['ir.model.data']
        view_rec = model_data_obj.get_object_reference(
                cr, uid, 'prof_fatturapa_out',
                'wizard_show_fatturapa_form_view')
        if view_rec:
                view_id = view_rec and view_rec[1] or False

        return {
           #'domain': "[('id','in',["+','.join(map(str, [show_id]))+"])]",
            'name': "Vista FatturaPA",
            'view_id': view_id,
            'res_id': show_id, #inv_pa[0] if len(inv_pa)<2 else None,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.show.fatturapa',
            'type': 'ir.actions.act_window',
            'context': context,
            'target':'new'
            }

    def soap_send_suds(self, cr, uid, ids,processid='1', context=None):
            for attach_id_obj in self.browse(cr,uid,ids,context=context):
                    if attach_id_obj.processid:
                        processid=attach_id_obj.processid
                    else:
                        processid=processid
                    data = attach_id_obj.ir_attachment_id.datas
                    """
                    if data:
                        out = data.decode('base64')
                    else:
                        out = ''
                    """
                    out="data:;base64,%s"  %  (data,)  
                    url_obj=self.pool.get('fatturapa.url')
                    if attach_id_obj.url_id:
                        url_id_obj=attach_id_obj.url_id
                    else:
                        url_ids=url_obj.search(cr,uid,[('id','>',0)],context=context)
                        url_id_obj=url_obj.browse(cr,uid,url_ids[0],context=context)
                    pp = PrettyPrinter(indent=4)
                    
                    CUST = url_id_obj.soap_customerName
                    USER = url_id_obj.soap_username
                    A='1234567890qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM'
                    PASS=''
                    for a in url_id_obj.soap_password:
                        if A.find(a):
                            PASS+=a

                    #PASS = url_id_obj.soap_password[0:len-1]
                    #PASS = b64encode(url_id_obj.soap_password)
                    #PASS = b64encode(PASS)
                    
                    print PASS
                    ZONE = 'a-zone-in-my-account.com'
                    
                    # The path to the Dynect API WSDL file
                    base_url = url_id_obj.soap_wsdl
                    base_endpoint = url_id_obj.soap_endpoint
                    
                    # Create a client instance
                    client = suds.client.Client(base_url)
                    client.options.location = base_endpoint
                    security=mySecurity()
                    token=myUsernameToken(username=USER,password=PASS)
                    print 'token',token
                    security.tokens.append(token)
                    
                    client.set_options(wsse=security)                    
                    #client.set_options(
                    #soapheaders=security
                    #)

                    #for method in client.wsdl.services[0].ports[0].methods.values():
                    #    print '%s(%s)' % (method.name, ', '.join('%s: %s' % (part.type, part.name) for part in method.soap.input.body.parts))            
                    response = client.service.InvoicePut(
                        CustomerName = CUST,
                        ProcessID = processid,
                        InvoiceDocumentID = attach_id_obj.name,
                        Invoice = out,
                        FileName = attach_id_obj.name,attributes={'Type':'http://docs.oasis-open.org/wss/2001/01/oasis-200401-wss-username-token-profile-1.0#PasswordText'}
                    )
                    
                    print 'response',response.ID,response
                    if response.ErrorCode not in ('0',None):
                        trasmessa=False
                        self.write(cr,uid,attach_id_obj.id,{
                                                                'trasmessa':trasmessa,
                                                                'stato_tx':'%s - %s' % (response.ErrorCode,response.ErrorMessage,),
                                                                'processid':processid,
                                                                'url_id':url_id_obj.id
                                                                },context=context)
                    else:
                        trasmessa=True
                        self.write(cr,uid,attach_id_obj.id,{
                                                                'trasmessa':trasmessa,
                                                                'stato_tx':'%s - %s' % (response.ErrorCode,response.ErrorMessage,),
                                                                'log':'log - %s' % (response.Log or None,),
                                                                'id_soap':response.ID or None,
                                                                'processid':processid,
                                                                'url_id':url_id_obj.id
                                                                },context=context)
                        
            return {}

    def soap_ric_suds(self, cr, uid, ids, context=None):
            attach_obj=self.pool.get('ir.attachment')
            for attach_id_obj in self.browse(cr,uid,ids,context=context):
                    url_obj=self.pool.get('fatturapa.url')
                    url_id_obj=attach_id_obj.url_id
                    pp = PrettyPrinter(indent=4)
                    
                    CUST = url_id_obj.soap_customerName
                    USER = url_id_obj.soap_username
                    A='1234567890qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM'
                    PASS=''
                    for a in url_id_obj.soap_password:
                        if A.find(a):
                            PASS+=a

                    #PASS = url_id_obj.soap_password[0:len-1]
                    #PASS = b64encode(url_id_obj.soap_password)
                    #PASS = b64encode(PASS)
                    
                    print PASS
                    ZONE = 'a-zone-in-my-account.com'
                    
                    # The path to the Dynect API WSDL file
                    base_url = url_id_obj.soap_wsdl
                    base_endpoint = url_id_obj.soap_endpoint
                    
                    # Create a client instance
                    client = suds.client.Client(base_url)
                    client.options.location = base_endpoint
                    security=mySecurity()
                    token=myUsernameToken(username=USER,password=PASS)
                    security.tokens.append(token)
                    
                    client.set_options(wsse=security)                    
                    #client.set_options(
                    #soapheaders=security
                    #)

                    #for method in client.wsdl.services[0].ports[0].methods.values():
                    #    print '%s(%s)' % (method.name, ', '.join('%s: %s' % (part.type, part.name) for part in method.soap.input.body.parts))            
                    response = client.service.InvoiceGet(
                        ID = attach_id_obj.id_soap,
                        contentType = 'auto',
                    )
                    
                    print 'response',response
                    if response.ErrorCode not in ('0',None):
                        self.write(cr,uid,attach_id_obj.id,{
                                                                'stato_rx':'%s - %s' % (response.ErrorCode,response.ErrorMessage,),
                                                                },context=context)
                    else:
                        print 'response.Invoice[0:4]',response.Invoice[0:4]
                        if  response.Invoice[0:4] == 'MIAG':
                                           """cades"""
                                           extenz='xml.7pm'
                                           
                        else:
                                          """ xcades """
                                          extenz='.xml'
                        invoice = b64decode(response.Invoice)
                        #invoice = b64encode(response.Invoice)
                        #handle, filepath = tempfile.mkstemp()
                        #fileobj = os.fdopen(handle,'w+')  # convert raw handle to file object        try:
                        invoice=base64.encodestring(invoice)
                        #fileobj.write(base64.decodestring(invoice))
                        #fileobj.close()
                        
                        #invoice = response.Invoice
                        print 'invoice',invoice
                        new_attach_id=attach_obj.create(cr,uid,{'datas':invoice,'res_model':'account.invoice','res_id':attach_id_obj.out_invoice_ids[0].id,'name':attach_id_obj.out_invoice_ids[0].number,'datas_fname':attach_id_obj.out_invoice_ids[0].number + extenz})
                        new_attach_id=attach_obj.create(cr,uid,{'datas':invoice,'res_model':'fatturapa.attachment.out','res_id':attach_id_obj.id,'name':attach_id_obj.out_invoice_ids[0].number,'datas_fname':attach_id_obj.out_invoice_ids[0].number+extenz})
                        self.write(cr,uid,attach_id_obj.id,{
                                                                'stato_rx':'%s - %s' % (response.ErrorCode,response.ErrorMessage,),
                                                                'ir_attachment_signed_id':new_attach_id
                                                                },context=context)
                        
            return {}

    def json_send_request(self,cr,uid,ids,processid='1',context=None):
            for attach_id_obj in self.browse(cr,uid,ids,context=context):
                    if attach_id_obj.ir_attachment_id.datas==None:
                        continue
                    if attach_id_obj.processid:
                        processid=attach_id_obj.processid
                    else:
                        processid=processid
                    data = attach_id_obj.ir_attachment_id.datas
                    invoice = b64decode(data)
                    print 'json_send_request_data',data
                    print 'json_send_request_invoice_decode',invoice
                    invoice = b64encode(str(invoice))
                    print 'json_send_request_invoice_encode',invoice
                    """
                    if data:
                        out = data.decode('base64')
                    else:
                        out = ''
                    """
                    out='%s'  %  (data,)  
                    url_obj=self.pool.get('fatturapa.url')
                    if attach_id_obj.url_id:
                        url_id_obj=attach_id_obj.url_id
                    else:
                        url_ids=url_obj.search(cr,uid,[('id','>',0)],context=context)
                        url_id_obj=url_obj.browse(cr,uid,url_ids[0],context=context)
                    date_today=datetime.today()
                    cert_file=date_today.strftime('%d-%m-%Y_%h_%m_%s')+'_.crt'
                    user_password=base64.b64encode(url_id_obj.json_username+':'+url_id_obj.json_password )
                    #user_password=sda_obj.user+':'+sda_obj.password..
                    user_password='Basic '+user_password
                    filepath='/media/disco2/ship_sda_doc/collaudo-ws.sda.it.crt'
                    if url_id_obj.json_url:
                       http = httplib2.Http()
                        #body = {'USERNAME': 'foo', 'PASSWORD': 'bar'}..
                       body = {}
                       #invoice='PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0ibGF0aW4xIj8+PG5zMTpGYXR0dXJhRWxldHRyb25pY2EgdmVyc2lvbmU9IkZQUjEyIiB4bWxuczpuczE9Imh0dHA6Ly9pdmFzZXJ2aXppLmFnZW56aWFlbnRyYXRlLmdvdi5pdC9kb2NzL3hzZC9mYXR0dXJlL3YxLjIiPjxGYXR0dXJhRWxldHRyb25pY2FIZWFkZXI+PERhdGlUcmFzbWlzc2lvbmU+PElkVHJhc21pdHRlbnRlPjxJZFBhZXNlPklUPC9JZFBhZXNlPjxJZENvZGljZT4wMTQ3NzQzMDQ0OTwvSWRDb2RpY2U+PC9JZFRyYXNtaXR0ZW50ZT48UHJvZ3Jlc3Npdm9JbnZpbz4wMDAwNzwvUHJvZ3Jlc3Npdm9JbnZpbz48Rm9ybWF0b1RyYXNtaXNzaW9uZT5GUFIxMjwvRm9ybWF0b1RyYXNtaXNzaW9uZT48Q29kaWNlRGVzdGluYXRhcmlvPjAwMDAwMDA8L0NvZGljZURlc3RpbmF0YXJpbz48Q29udGF0dGlUcmFzbWl0dGVudGU+PFRlbGVmb25vPjA3MzQ5NjIzNzY8L1RlbGVmb25vPjxFbWFpbD5pbmZvQHRhbWFudGlub2xlZ2dpLml0PC9FbWFpbD48L0NvbnRhdHRpVHJhc21pdHRlbnRlPjxQRUNEZXN0aW5hdGFyaW8+YW1taW5pc3RyYXppb25lQHBlYy50b21hcy5pdDwvUEVDRGVzdGluYXRhcmlvPjwvRGF0aVRyYXNtaXNzaW9uZT48Q2VkZW50ZVByZXN0YXRvcmU+PERhdGlBbmFncmFmaWNpPjxJZEZpc2NhbGVJVkE+PElkUGFlc2U+SVQ8L0lkUGFlc2U+PElkQ29kaWNlPjAxNDc3NDMwNDQ5PC9JZENvZGljZT48L0lkRmlzY2FsZUlWQT48QW5hZ3JhZmljYT48RGVub21pbmF6aW9uZT5UQU1BTlRJIEdJVUxJQU5PPC9EZW5vbWluYXppb25lPjwvQW5hZ3JhZmljYT48UmVnaW1lRmlzY2FsZT5SRjAxPC9SZWdpbWVGaXNjYWxlPjwvRGF0aUFuYWdyYWZpY2k+PFNlZGU+PEluZGlyaXp6bz5TT0NDT1JTTyAyNjwvSW5kaXJpenpvPjxDQVA+NjM4MzM8L0NBUD48Q29tdW5lPk1PTlRFR0lPUkdJTzwvQ29tdW5lPjxQcm92aW5jaWE+Rk08L1Byb3ZpbmNpYT48TmF6aW9uZT5JVDwvTmF6aW9uZT48L1NlZGU+PENvbnRhdHRpPjxUZWxlZm9ubz4wNzM0OTYyMzc2PC9UZWxlZm9ubz48RW1haWw+aW5mb0B0YW1hbnRpbm9sZWdnaS5pdDwvRW1haWw+PC9Db250YXR0aT48L0NlZGVudGVQcmVzdGF0b3JlPjxDZXNzaW9uYXJpb0NvbW1pdHRlbnRlPjxEYXRpQW5hZ3JhZmljaT48SWRGaXNjYWxlSVZBPjxJZFBhZXNlPklUPC9JZFBhZXNlPjxJZENvZGljZT4wMDE3OTIxMDQ0ODwvSWRDb2RpY2U+PC9JZEZpc2NhbGVJVkE+PEFuYWdyYWZpY2E+PERlbm9taW5hemlvbmU+TUFHTElGSUNJTyBUT01BUyBTUkwgPC9EZW5vbWluYXppb25lPjwvQW5hZ3JhZmljYT48L0RhdGlBbmFncmFmaWNpPjxTZWRlPjxJbmRpcml6em8+VklBIFNBQ0NPTkkgTicxPC9JbmRpcml6em8+PENBUD42MzkwMDwvQ0FQPjxDb211bmU+RkVSTU88L0NvbXVuZT48UHJvdmluY2lhPkZNPC9Qcm92aW5jaWE+PE5hemlvbmU+SVQ8L05hemlvbmU+PC9TZWRlPjwvQ2Vzc2lvbmFyaW9Db21taXR0ZW50ZT48L0ZhdHR1cmFFbGV0dHJvbmljYUhlYWRlcj48RmF0dHVyYUVsZXR0cm9uaWNhQm9keT48RGF0aUdlbmVyYWxpPjxEYXRpR2VuZXJhbGlEb2N1bWVudG8+PFRpcG9Eb2N1bWVudG8+VEQwMTwvVGlwb0RvY3VtZW50bz48RGl2aXNhPkVVUjwvRGl2aXNhPjxEYXRhPjIwMTgtMDYtMjA8L0RhdGE+PE51bWVybz5GREovMjAxOC8wMjcwPC9OdW1lcm8+PEltcG9ydG9Ub3RhbGVEb2N1bWVudG8+OTUuMDA8L0ltcG9ydG9Ub3RhbGVEb2N1bWVudG8+PC9EYXRpR2VuZXJhbGlEb2N1bWVudG8+PC9EYXRpR2VuZXJhbGk+PERhdGlCZW5pU2Vydml6aT48RGV0dGFnbGlvTGluZWU+PE51bWVyb0xpbmVhPjE8L051bWVyb0xpbmVhPjxEZXNjcml6aW9uZT5OT0xFR0dJTyBPUEVMIFZJVkFSTyBFWjIzNFdEPC9EZXNjcml6aW9uZT48UXVhbnRpdGE+MS4wMDwvUXVhbnRpdGE+PFVuaXRhTWlzdXJhPlVuaXRhPC9Vbml0YU1pc3VyYT48UHJlenpvVW5pdGFyaW8+OTUuMDA8L1ByZXp6b1VuaXRhcmlvPjxQcmV6em9Ub3RhbGU+NzcuODc8L1ByZXp6b1RvdGFsZT48QWxpcXVvdGFJVkE+MjIuMDA8L0FsaXF1b3RhSVZBPjwvRGV0dGFnbGlvTGluZWU+PERhdGlSaWVwaWxvZ28+PEFsaXF1b3RhSVZBPjIyLjAwPC9BbGlxdW90YUlWQT48SW1wb25pYmlsZUltcG9ydG8+NzcuODc8L0ltcG9uaWJpbGVJbXBvcnRvPjxJbXBvc3RhPjE3LjEzPC9JbXBvc3RhPjwvRGF0aVJpZXBpbG9nbz48L0RhdGlCZW5pU2Vydml6aT48RGF0aVBhZ2FtZW50bz48Q29uZGl6aW9uaVBhZ2FtZW50bz5UUDAzPC9Db25kaXppb25pUGFnYW1lbnRvPjxEZXR0YWdsaW9QYWdhbWVudG8+PE1vZGFsaXRhUGFnYW1lbnRvPk1QMDI8L01vZGFsaXRhUGFnYW1lbnRvPjxEYXRhU2NhZGVuemFQYWdhbWVudG8+MjAxOC0wNi0yMDwvRGF0YVNjYWRlbnphUGFnYW1lbnRvPjxJbXBvcnRvUGFnYW1lbnRvPjk1LjAwPC9JbXBvcnRvUGFnYW1lbnRvPjxJc3RpdHV0b0ZpbmFuemlhcmlvPkJBTkNBIERFTExFIE1BUkNIRTwvSXN0aXR1dG9GaW5hbnppYXJpbz48L0RldHRhZ2xpb1BhZ2FtZW50bz48L0RhdGlQYWdhbWVudG8+PC9GYXR0dXJhRWxldHRyb25pY2FCb2R5PjwvbnMxOkZhdHR1cmFFbGV0dHJvbmljYT4='
                       params = {'filetosend':invoice}
                       
                       headers ={'Content-Type':'application/x-www-form-urlencoded','Authorization':user_password}
                       #headers ={'Content-Type':'multipart/form-data','Authorization':user_password}
                       #headers ={'Content-Type':mp_encoder.content_type,'Authorization':user_password}
                       #headers ={'Content-Type':'application/json','Authorization':user_password}
                       #headers ={'Authorization':user_password}
                       #try: 
                       print 'url',url_id_obj.json_url
                       print 'user,password-->',url_id_obj.json_username,url_id_obj.json_password
                       print 'body-->',body
                       print 'headers-->',headers
                       print 'params-->',params
                       if str(url_id_obj.json_url).find('https')>=0:
                            if url_id_obj.json_usa_cert==False:
                                #req = requests.post(url_id_obj.json_url, params=params, data=json.dumps(body),headers=headers,verify=False,auth=HTTPBasicAuth(url_id_obj.json_username,url_id_obj.json_password)) 
                                req = requests.post(url_id_obj.json_url, data=params,headers=headers,verify=False,auth=HTTPBasicAuth(url_id_obj.json_username,url_id_obj.json_password)) 
                                response=req.text
                                print 'response_json_send_request',response
                            else:
                                req = requests.post(url_id_obj.json_url, data=params,
                                                    headers=headers,verify=True,
                                                    cert=filepath,
                                                    auth=HTTPBasicAuth(url_id_obj.json_username,url_id_obj.json_password)) 
                                """"
                                s = Session()
                                req = Request('POST',  url,
                                    data=json.dumps(body),
                                    headers=headers,
                                    auth=HTTPBasicAuth(sda_obj.user,sda_obj.password)
                                )
                                """
                                response=req.text
                       else:
                                #req = requests.post(url_id_obj.json_url, data=json.dumps(body),headers=headers,verify=False,auth=HTTPBasicAuth(url_id_obj.json_username,url_id_obj.json_password)) 
                                req = requests.post(url_id_obj.json_url, data=params,headers=headers,verify=False,auth=HTTPBasicAuth(url_id_obj.json_username,url_id_obj.json_password)) 
                                response=req.text
                                print 'response',response
                       if response:
                            try:
                                ret=json.loads(response)
                            except:
                                raise orm.except_orm(
                        _("Avviso"), _("Il server non è disponibile, riprovare più tardi"))
                            if ret:
                                if ret['returnCode']!=0:
                                    trasmessa=False
                                    self.write(cr,uid,attach_id_obj.id,{
                                                                        'trasmessa':trasmessa,
                                                                        'stato_tx':'%s - %s' % (ret['returnCode'],ret['description'],),
                                                                        'processid':processid,
                                                                        'url_id':url_id_obj.id
                                                                        },context=context)
    
                                else:
                                    trasmessa=True
                                    self.write(cr,uid,attach_id_obj.id,{
                                                                        'trasmessa':trasmessa,
                                                                        'stato_tx':'%s - %s' % (ret['returnCode'],ret['description'],),
                                                                        'processid':processid,
                                                                        'url_id':url_id_obj.id
                                                                        },context=context)
                                    
                            return   {}             
                        
                       else:
                                    return  {}             
    def json_imp_request(self,cr,uid,ids=[],context=None):
                    attach_obj=self.pool.get('fatturapa.attachment.out')
                    url_obj=self.pool.get('fatturapa.url')
                    import_fpa_obj=self.pool.get('wizard.import.fatturapa')
                    invoice_obj=self.pool.get('account.invoice')
                    partner_obj=self.pool.get('res.partner')
                    url_ids=url_obj.search(cr,uid,[('id','>',0)],order='sequence desc ,id desc',context=context)
                    url_id_obj=url_obj.browse(cr,uid,url_ids[0],context=context)
                    date_today=datetime.today()
                    cert_file=date_today.strftime('%d-%m-%Y_%h_%m_%s')+'_.crt'
                    user_password=base64.b64encode(url_id_obj.json_username+':'+url_id_obj.json_password )
                    #user_password=sda_obj.user+':'+sda_obj.password..
                    user_password='Basic '+user_password
                    filepath='/media/disco2/ship_sda_doc/collaudo-ws.sda.it.crt'
                    if url_id_obj.json_url_import:
                       http = httplib2.Http()
                        #body = {'USERNAME': 'foo', 'PASSWORD': 'bar'}..
                       body = {}
                       #invoice='PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0ibGF0aW4xIj8+PG5zMTpGYXR0dXJhRWxldHRyb25pY2EgdmVyc2lvbmU9IkZQUjEyIiB4bWxuczpuczE9Imh0dHA6Ly9pdmFzZXJ2aXppLmFnZW56aWFlbnRyYXRlLmdvdi5pdC9kb2NzL3hzZC9mYXR0dXJlL3YxLjIiPjxGYXR0dXJhRWxldHRyb25pY2FIZWFkZXI+PERhdGlUcmFzbWlzc2lvbmU+PElkVHJhc21pdHRlbnRlPjxJZFBhZXNlPklUPC9JZFBhZXNlPjxJZENvZGljZT4wMTQ3NzQzMDQ0OTwvSWRDb2RpY2U+PC9JZFRyYXNtaXR0ZW50ZT48UHJvZ3Jlc3Npdm9JbnZpbz4wMDAwNzwvUHJvZ3Jlc3Npdm9JbnZpbz48Rm9ybWF0b1RyYXNtaXNzaW9uZT5GUFIxMjwvRm9ybWF0b1RyYXNtaXNzaW9uZT48Q29kaWNlRGVzdGluYXRhcmlvPjAwMDAwMDA8L0NvZGljZURlc3RpbmF0YXJpbz48Q29udGF0dGlUcmFzbWl0dGVudGU+PFRlbGVmb25vPjA3MzQ5NjIzNzY8L1RlbGVmb25vPjxFbWFpbD5pbmZvQHRhbWFudGlub2xlZ2dpLml0PC9FbWFpbD48L0NvbnRhdHRpVHJhc21pdHRlbnRlPjxQRUNEZXN0aW5hdGFyaW8+YW1taW5pc3RyYXppb25lQHBlYy50b21hcy5pdDwvUEVDRGVzdGluYXRhcmlvPjwvRGF0aVRyYXNtaXNzaW9uZT48Q2VkZW50ZVByZXN0YXRvcmU+PERhdGlBbmFncmFmaWNpPjxJZEZpc2NhbGVJVkE+PElkUGFlc2U+SVQ8L0lkUGFlc2U+PElkQ29kaWNlPjAxNDc3NDMwNDQ5PC9JZENvZGljZT48L0lkRmlzY2FsZUlWQT48QW5hZ3JhZmljYT48RGVub21pbmF6aW9uZT5UQU1BTlRJIEdJVUxJQU5PPC9EZW5vbWluYXppb25lPjwvQW5hZ3JhZmljYT48UmVnaW1lRmlzY2FsZT5SRjAxPC9SZWdpbWVGaXNjYWxlPjwvRGF0aUFuYWdyYWZpY2k+PFNlZGU+PEluZGlyaXp6bz5TT0NDT1JTTyAyNjwvSW5kaXJpenpvPjxDQVA+NjM4MzM8L0NBUD48Q29tdW5lPk1PTlRFR0lPUkdJTzwvQ29tdW5lPjxQcm92aW5jaWE+Rk08L1Byb3ZpbmNpYT48TmF6aW9uZT5JVDwvTmF6aW9uZT48L1NlZGU+PENvbnRhdHRpPjxUZWxlZm9ubz4wNzM0OTYyMzc2PC9UZWxlZm9ubz48RW1haWw+aW5mb0B0YW1hbnRpbm9sZWdnaS5pdDwvRW1haWw+PC9Db250YXR0aT48L0NlZGVudGVQcmVzdGF0b3JlPjxDZXNzaW9uYXJpb0NvbW1pdHRlbnRlPjxEYXRpQW5hZ3JhZmljaT48SWRGaXNjYWxlSVZBPjxJZFBhZXNlPklUPC9JZFBhZXNlPjxJZENvZGljZT4wMDE3OTIxMDQ0ODwvSWRDb2RpY2U+PC9JZEZpc2NhbGVJVkE+PEFuYWdyYWZpY2E+PERlbm9taW5hemlvbmU+TUFHTElGSUNJTyBUT01BUyBTUkwgPC9EZW5vbWluYXppb25lPjwvQW5hZ3JhZmljYT48L0RhdGlBbmFncmFmaWNpPjxTZWRlPjxJbmRpcml6em8+VklBIFNBQ0NPTkkgTicxPC9JbmRpcml6em8+PENBUD42MzkwMDwvQ0FQPjxDb211bmU+RkVSTU88L0NvbXVuZT48UHJvdmluY2lhPkZNPC9Qcm92aW5jaWE+PE5hemlvbmU+SVQ8L05hemlvbmU+PC9TZWRlPjwvQ2Vzc2lvbmFyaW9Db21taXR0ZW50ZT48L0ZhdHR1cmFFbGV0dHJvbmljYUhlYWRlcj48RmF0dHVyYUVsZXR0cm9uaWNhQm9keT48RGF0aUdlbmVyYWxpPjxEYXRpR2VuZXJhbGlEb2N1bWVudG8+PFRpcG9Eb2N1bWVudG8+VEQwMTwvVGlwb0RvY3VtZW50bz48RGl2aXNhPkVVUjwvRGl2aXNhPjxEYXRhPjIwMTgtMDYtMjA8L0RhdGE+PE51bWVybz5GREovMjAxOC8wMjcwPC9OdW1lcm8+PEltcG9ydG9Ub3RhbGVEb2N1bWVudG8+OTUuMDA8L0ltcG9ydG9Ub3RhbGVEb2N1bWVudG8+PC9EYXRpR2VuZXJhbGlEb2N1bWVudG8+PC9EYXRpR2VuZXJhbGk+PERhdGlCZW5pU2Vydml6aT48RGV0dGFnbGlvTGluZWU+PE51bWVyb0xpbmVhPjE8L051bWVyb0xpbmVhPjxEZXNjcml6aW9uZT5OT0xFR0dJTyBPUEVMIFZJVkFSTyBFWjIzNFdEPC9EZXNjcml6aW9uZT48UXVhbnRpdGE+MS4wMDwvUXVhbnRpdGE+PFVuaXRhTWlzdXJhPlVuaXRhPC9Vbml0YU1pc3VyYT48UHJlenpvVW5pdGFyaW8+OTUuMDA8L1ByZXp6b1VuaXRhcmlvPjxQcmV6em9Ub3RhbGU+NzcuODc8L1ByZXp6b1RvdGFsZT48QWxpcXVvdGFJVkE+MjIuMDA8L0FsaXF1b3RhSVZBPjwvRGV0dGFnbGlvTGluZWU+PERhdGlSaWVwaWxvZ28+PEFsaXF1b3RhSVZBPjIyLjAwPC9BbGlxdW90YUlWQT48SW1wb25pYmlsZUltcG9ydG8+NzcuODc8L0ltcG9uaWJpbGVJbXBvcnRvPjxJbXBvc3RhPjE3LjEzPC9JbXBvc3RhPjwvRGF0aVJpZXBpbG9nbz48L0RhdGlCZW5pU2Vydml6aT48RGF0aVBhZ2FtZW50bz48Q29uZGl6aW9uaVBhZ2FtZW50bz5UUDAzPC9Db25kaXppb25pUGFnYW1lbnRvPjxEZXR0YWdsaW9QYWdhbWVudG8+PE1vZGFsaXRhUGFnYW1lbnRvPk1QMDI8L01vZGFsaXRhUGFnYW1lbnRvPjxEYXRhU2NhZGVuemFQYWdhbWVudG8+MjAxOC0wNi0yMDwvRGF0YVNjYWRlbnphUGFnYW1lbnRvPjxJbXBvcnRvUGFnYW1lbnRvPjk1LjAwPC9JbXBvcnRvUGFnYW1lbnRvPjxJc3RpdHV0b0ZpbmFuemlhcmlvPkJBTkNBIERFTExFIE1BUkNIRTwvSXN0aXR1dG9GaW5hbnppYXJpbz48L0RldHRhZ2xpb1BhZ2FtZW50bz48L0RhdGlQYWdhbWVudG8+PC9GYXR0dXJhRWxldHRyb25pY2FCb2R5PjwvbnMxOkZhdHR1cmFFbGV0dHJvbmljYT4='
                       params = {
                           "site":str(url_id_obj.json_sito),
                           "class":"olv:fatCliSDI",
                           "xmlFile": False                          
                           }
                       
                       headers ={'Content-Type':'application/json','Authorization':user_password}
                       jsonString = json.dumps(params)
                       print 'jsonString',jsonString #get string with all double quotes 
                       print 'headers',headers #get string with all double quotes 
                       if str(url_id_obj.json_url_import).find('https')>=0:
                            if url_id_obj.json_usa_cert==False:
                                req = requests.post(url_id_obj.json_url_import, 
                                                    data=jsonString,
                                                    headers=headers,
                                                    ) 
                                response=req.text
                                print 'response_json_send_request',response
                                print 'req',req
                            else:
                                req = requests.post(url_id_obj.json_url_import, 
                                                    data=jsonString,
                                                    headers=headers,
                                                    verify=True,
                                                    cert=filepath
                                                    ) 
                                response=req.text
                       else:
                                req = requests.post(url_id_obj.json_url_import, 
                                                    data=jsonString,
                                                    headers=headers,verify=False) 
                                response=req.text
                                print 'response',response
                       import_ids=[]
                       if response:
                            try:
                                fatture=json.loads(response)
                            except:
                                raise orm.except_orm(
                        _("Avviso"), _("Il server non è disponibile, riprovare più tardi"))
                            for ret_meta in fatture['message']:
                                #if fatture['returnCode']=='0000':    
                                    ret=ret_meta['metadata']
                                    print 'ret',ret
                                    
                                    data_invoice = ret[3]['olv:fatCliSDIDataFattura']
                            
                                    invoice_ids_obj=invoice_obj.search(cr,uid,[
                                                                            ('number','=',ret[2]['olv:fatCliSDINumFattura']),
                                                                            ('date_invoice','=',data_invoice),
                                                                             ],context=context)
                                    
                                    for invoice_id_rm in invoice_ids_obj:
                                            invoice_id_obj=invoice_obj.browse(cr,uid,invoice_id_rm,context=context)
                                            if invoice_id_obj.fatturapa_attachment_out_id.json_fatCliSDIStato in ('HDO01','HDO05','HDO06'):
                                                invoice_ids_obj.remove(invoice_id_rm)
                                    if invoice_ids_obj:
                                        
                                            stato_rx={
                                                 'json_fatCliSDIStato':ret[5]['olv:fatCliSDIStato'],
                                                'stato_rx':fatture['returnCode'],
                                                'log':fatture['description']+'***'+fatture['returnCode'],
                                                }
                                            if ret[1]['olv:fatCliSDISezionale']:
                                                stato_rx.update({'json_fatCliSDISezionale':ret[1]['olv:fatCliSDISezionale']})
                                            if ret[4]['olv:fatCliSDIId']:
                                                stato_rx.update({'json_fatclisdiid':ret[4]['olv:fatCliSDIId']})
                                            if ret[5]['olv:fatCliSDIStato']=='HDO01' or ret[5]['olv:fatCliSDIStato']=='HDO05':
                                                stato_rx.update({'firmata':True})
                                            invoice_id_obj=invoice_obj.browse(cr,uid,invoice_ids_obj[0],context=context)
                                            attach_id=invoice_id_obj.fatturapa_attachment_out_id.id
                                            print 'attach_id',attach_id,'stato_rx',stato_rx
                                            if invoice_id_obj.fatturapa_attachment_out_id.json_fatCliSDIStato not in ('HDO01','HDO05','HDO06'):
                                                attach_obj.write(cr,uid,attach_id,stato_rx,context=context)
                                            if ret[5]['olv:fatCliSDIStato']=='HDO01' or ret[5]['olv:fatCliSDIStato']=='HDO05':
                                                attach_obj.chiudi_fatturapa(cr,uid,attach_id,context=context)
                                    """ rocco 07/02/2019
                                    else:
                                        if ids:
                                            for id in ids:
                                                myattach_id_obj=self.browse(cr,uid,id,context=context)
                                                
                                                self.write(cr,uid,id,{'log':myattach_id_obj.log or '' +'-'+fatture['returnCode']+'-'+fatture['description']+'-'+ret[2]['olv:fatCliSDINumFattura']})
                            
                                    """
                            """ rocco 07/02/2019
                            if ids:
                                for id in ids:
                                                myattach_id_obj=self.browse(cr,uid,id,context=context)
                                                
                                                self.write(cr,uid,id,{'log':myattach_id_obj.log or '' +'-'+fatture['returnCode']+'-'+fatture['description']+'-'+ret[2]['olv:fatCliSDINumFattura']})
                            """
                            return True
                       else:
                            return {'message': [], 'returnCode': '0100', 'description': 'generic error','import_ids':[]}

    def chiudi_fatturapa(self,cr,uid,ids,context=None):
                    if hasattr(ids, '__iter__'):
                        ids=ids
                    else:
                        ids=[ids]
                    for attach in self.browse(cr,uid,ids,context=context):
                        if attach.url_id.type=="json":
                            self.json_update_request(cr,uid,attach.id,escludi=True,context=None)
    def apri_fatturapa(self,cr,uid,ids,context=None):
                    if hasattr(ids, '__iter__'):
                        ids=ids
                    else:
                        ids=[ids]
                    for attach in self.browse(cr,uid,ids,context=context):
                        if attach.url_id.type=="json":
                            self.json_update_request(cr,uid,attach.id,False,context=None)
                
    def apri_fatturapa_active_ids(self,cr,uid,ids=[],context=None):
                    if context==None:
                        context={}
                    if context.get('active_model',None)=='account.invoice':
                            active_ids=context.get('active_ids',[])
                            fatturapa_out=[]
                            for invoice_id_obj in self.pool.get('account.invoice').browse(cr,uid,active_ids,context=context):
                                if invoice_id_obj.fatturapa_attachment_out_id:
                                        fatturapa_out.append(invoice_id_obj.fatturapa_attachment_out_id.id)
                            ids=fatturapa_out
                    else:
                            active_ids=context.get('active_ids',[])
                            fatturapa_out=[]
                            for fatturapa_attachment_out_id in self.browse(cr,uid,active_ids,context=context):
                                         fatturapa_out.append(fatturapa_attachment_out_id.id)
                            if fatturapa_out:
                                ids=fatturapa_out
                    if hasattr(ids, '__iter__'):
                        ids=ids
                    else:
                        ids=[ids]
                    for attach in self.browse(cr,uid,ids,context=context):
                        if attach.url_id.type=="json":
                            self.json_update_request(cr,uid,attach.id,False,context=None)
                
    def json_update_request(self,cr,uid,ids,escludi=True,context=None):
                url_obj=self.pool.get('fatturapa.url')
                import_fpa_obj=self.pool.get('wizard.import.fatturapa')
                invoice_obj=self.pool.get('account.invoice')
                partner_obj=self.pool.get('res.partner')
                url_ids=url_obj.search(cr,uid,[('id','>',0)],order='sequence desc ,id desc',context=context)
                url_id_obj=url_obj.browse(cr,uid,url_ids[0],context=context)
                date_today=datetime.today()
                cert_file=date_today.strftime('%d-%m-%Y_%h_%m_%s')+'_.crt'
                user_password=base64.b64encode(url_id_obj.json_username+':'+url_id_obj.json_password )
                user_password='Basic '+user_password
                filepath='/media/disco2/ship_sda_doc/collaudo-ws.sda.it.crt'
                if url_id_obj.json_url_update:
                    if hasattr(ids, '__iter__'):
                        ids=ids
                    else:
                        ids=[ids]
                    for attach in self.browse(cr,uid,ids,context=context):
                          
                       http = httplib2.Http()
                       #body = {'USERNAME': 'foo', 'PASSWORD': 'bar'}..
                       body = {}
                       #invoice='PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0ibGF0aW4xIj8+PG5zMTpGYXR0dXJhRWxldHRyb25pY2EgdmVyc2lvbmU9IkZQUjEyIiB4bWxuczpuczE9Imh0dHA6Ly9pdmFzZXJ2aXppLmFnZW56aWFlbnRyYXRlLmdvdi5pdC9kb2NzL3hzZC9mYXR0dXJlL3YxLjIiPjxGYXR0dXJhRWxldHRyb25pY2FIZWFkZXI+PERhdGlUcmFzbWlzc2lvbmU+PElkVHJhc21pdHRlbnRlPjxJZFBhZXNlPklUPC9JZFBhZXNlPjxJZENvZGljZT4wMTQ3NzQzMDQ0OTwvSWRDb2RpY2U+PC9JZFRyYXNtaXR0ZW50ZT48UHJvZ3Jlc3Npdm9JbnZpbz4wMDAwNzwvUHJvZ3Jlc3Npdm9JbnZpbz48Rm9ybWF0b1RyYXNtaXNzaW9uZT5GUFIxMjwvRm9ybWF0b1RyYXNtaXNzaW9uZT48Q29kaWNlRGVzdGluYXRhcmlvPjAwMDAwMDA8L0NvZGljZURlc3RpbmF0YXJpbz48Q29udGF0dGlUcmFzbWl0dGVudGU+PFRlbGVmb25vPjA3MzQ5NjIzNzY8L1RlbGVmb25vPjxFbWFpbD5pbmZvQHRhbWFudGlub2xlZ2dpLml0PC9FbWFpbD48L0NvbnRhdHRpVHJhc21pdHRlbnRlPjxQRUNEZXN0aW5hdGFyaW8+YW1taW5pc3RyYXppb25lQHBlYy50b21hcy5pdDwvUEVDRGVzdGluYXRhcmlvPjwvRGF0aVRyYXNtaXNzaW9uZT48Q2VkZW50ZVByZXN0YXRvcmU+PERhdGlBbmFncmFmaWNpPjxJZEZpc2NhbGVJVkE+PElkUGFlc2U+SVQ8L0lkUGFlc2U+PElkQ29kaWNlPjAxNDc3NDMwNDQ5PC9JZENvZGljZT48L0lkRmlzY2FsZUlWQT48QW5hZ3JhZmljYT48RGVub21pbmF6aW9uZT5UQU1BTlRJIEdJVUxJQU5PPC9EZW5vbWluYXppb25lPjwvQW5hZ3JhZmljYT48UmVnaW1lRmlzY2FsZT5SRjAxPC9SZWdpbWVGaXNjYWxlPjwvRGF0aUFuYWdyYWZpY2k+PFNlZGU+PEluZGlyaXp6bz5TT0NDT1JTTyAyNjwvSW5kaXJpenpvPjxDQVA+NjM4MzM8L0NBUD48Q29tdW5lPk1PTlRFR0lPUkdJTzwvQ29tdW5lPjxQcm92aW5jaWE+Rk08L1Byb3ZpbmNpYT48TmF6aW9uZT5JVDwvTmF6aW9uZT48L1NlZGU+PENvbnRhdHRpPjxUZWxlZm9ubz4wNzM0OTYyMzc2PC9UZWxlZm9ubz48RW1haWw+aW5mb0B0YW1hbnRpbm9sZWdnaS5pdDwvRW1haWw+PC9Db250YXR0aT48L0NlZGVudGVQcmVzdGF0b3JlPjxDZXNzaW9uYXJpb0NvbW1pdHRlbnRlPjxEYXRpQW5hZ3JhZmljaT48SWRGaXNjYWxlSVZBPjxJZFBhZXNlPklUPC9JZFBhZXNlPjxJZENvZGljZT4wMDE3OTIxMDQ0ODwvSWRDb2RpY2U+PC9JZEZpc2NhbGVJVkE+PEFuYWdyYWZpY2E+PERlbm9taW5hemlvbmU+TUFHTElGSUNJTyBUT01BUyBTUkwgPC9EZW5vbWluYXppb25lPjwvQW5hZ3JhZmljYT48L0RhdGlBbmFncmFmaWNpPjxTZWRlPjxJbmRpcml6em8+VklBIFNBQ0NPTkkgTicxPC9JbmRpcml6em8+PENBUD42MzkwMDwvQ0FQPjxDb211bmU+RkVSTU88L0NvbXVuZT48UHJvdmluY2lhPkZNPC9Qcm92aW5jaWE+PE5hemlvbmU+SVQ8L05hemlvbmU+PC9TZWRlPjwvQ2Vzc2lvbmFyaW9Db21taXR0ZW50ZT48L0ZhdHR1cmFFbGV0dHJvbmljYUhlYWRlcj48RmF0dHVyYUVsZXR0cm9uaWNhQm9keT48RGF0aUdlbmVyYWxpPjxEYXRpR2VuZXJhbGlEb2N1bWVudG8+PFRpcG9Eb2N1bWVudG8+VEQwMTwvVGlwb0RvY3VtZW50bz48RGl2aXNhPkVVUjwvRGl2aXNhPjxEYXRhPjIwMTgtMDYtMjA8L0RhdGE+PE51bWVybz5GREovMjAxOC8wMjcwPC9OdW1lcm8+PEltcG9ydG9Ub3RhbGVEb2N1bWVudG8+OTUuMDA8L0ltcG9ydG9Ub3RhbGVEb2N1bWVudG8+PC9EYXRpR2VuZXJhbGlEb2N1bWVudG8+PC9EYXRpR2VuZXJhbGk+PERhdGlCZW5pU2Vydml6aT48RGV0dGFnbGlvTGluZWU+PE51bWVyb0xpbmVhPjE8L051bWVyb0xpbmVhPjxEZXNjcml6aW9uZT5OT0xFR0dJTyBPUEVMIFZJVkFSTyBFWjIzNFdEPC9EZXNjcml6aW9uZT48UXVhbnRpdGE+MS4wMDwvUXVhbnRpdGE+PFVuaXRhTWlzdXJhPlVuaXRhPC9Vbml0YU1pc3VyYT48UHJlenpvVW5pdGFyaW8+OTUuMDA8L1ByZXp6b1VuaXRhcmlvPjxQcmV6em9Ub3RhbGU+NzcuODc8L1ByZXp6b1RvdGFsZT48QWxpcXVvdGFJVkE+MjIuMDA8L0FsaXF1b3RhSVZBPjwvRGV0dGFnbGlvTGluZWU+PERhdGlSaWVwaWxvZ28+PEFsaXF1b3RhSVZBPjIyLjAwPC9BbGlxdW90YUlWQT48SW1wb25pYmlsZUltcG9ydG8+NzcuODc8L0ltcG9uaWJpbGVJbXBvcnRvPjxJbXBvc3RhPjE3LjEzPC9JbXBvc3RhPjwvRGF0aVJpZXBpbG9nbz48L0RhdGlCZW5pU2Vydml6aT48RGF0aVBhZ2FtZW50bz48Q29uZGl6aW9uaVBhZ2FtZW50bz5UUDAzPC9Db25kaXppb25pUGFnYW1lbnRvPjxEZXR0YWdsaW9QYWdhbWVudG8+PE1vZGFsaXRhUGFnYW1lbnRvPk1QMDI8L01vZGFsaXRhUGFnYW1lbnRvPjxEYXRhU2NhZGVuemFQYWdhbWVudG8+MjAxOC0wNi0yMDwvRGF0YVNjYWRlbnphUGFnYW1lbnRvPjxJbXBvcnRvUGFnYW1lbnRvPjk1LjAwPC9JbXBvcnRvUGFnYW1lbnRvPjxJc3RpdHV0b0ZpbmFuemlhcmlvPkJBTkNBIERFTExFIE1BUkNIRTwvSXN0aXR1dG9GaW5hbnppYXJpbz48L0RldHRhZ2xpb1BhZ2FtZW50bz48L0RhdGlQYWdhbWVudG8+PC9GYXR0dXJhRWxldHRyb25pY2FCb2R5PjwvbnMxOkZhdHR1cmFFbGV0dHJvbmljYT4='
                       metadata = [{"olv:escludi":escludi}]                      
                       if  attach.out_invoice_ids:
                            if  attach.out_invoice_ids[0].move_id:
                               len_id=len(str(attach.out_invoice_ids[0].id))
                               if len_id>5:
                                   len_id=5
                               proto=attach.out_invoice_ids[0].move_id.date[2:4]+str(attach.out_invoice_ids[0].id)[len(str(attach.out_invoice_ids[0].id))-len_id:len(str(attach.out_invoice_ids[0].id))]
                               metadata= [{"olv:escludi":escludi},
                                        {"olv:fatCliSDISezionale":attach.out_invoice_ids[0].journal_id.name},
                                        {"olv:fatForSDINumProtocollo":proto},
                                         {"olv:fatCliSDIDataRegistrazione":attach.out_invoice_ids[0].move_id.date},
                                        ]                      
                       if attach.json_fatclisdiid:
                           keys=[{"olv:fatCliSDIId":attach.json_fatclisdiid}]
                       else:
                           keys=[
                               {"olv:fatCliSDISezionale":attach.json_fatCliSDISezionale},
                               {"olv:fatCliSDINumFattura":attach.out_invoice_ids[0].number},
                               {"olv:fatCliSDIDataFattura":attach.out_invoice_ids[0].date_invoice[0:4]},
                               ]
                            
                       params = {
                           "site":str(url_id_obj.json_sito),
                           "class":"olv:fatCliSDI",                    
                           "items":
                                [
                                    {
                                        "keys": keys,
                                        "metadata": metadata
                                    }   
                                ]                
                           }
                       
                       headers ={'Content-Type':'application/json','Authorization':user_password}
                       #headers ={'Authorization':user_password}
                       #try: 
                       print 'url',url_id_obj.json_url_update
                       print 'user,password-->',url_id_obj.json_username,url_id_obj.json_password
                       print 'body-->',body
                       print 'headers-->',headers
                       print 'params-->',params
                       print 'auth',HTTPBasicAuth(url_id_obj.json_username,url_id_obj.json_password)
                       print 'data',json.dumps(body)
                       jsonString = json.dumps(params)
                       print 'jsonString',jsonString #get string with all double quotes 
                       if str(url_id_obj.json_url_update).find('https')>=0:
                            if url_id_obj.json_usa_cert==False:
                                req = requests.post(url_id_obj.json_url_update, 
                                                    data=jsonString,
                                                    headers=headers,
                                                    ) 
                                response=req.text
                                print 'response_json_send_request',response
                                print 'req',req
                            else:
                                req = requests.post(url_id_obj.json_url_update, 
                                                    data=jsonString,
                                                    headers=headers,
                                                    verify=True,
                                                    cert=filepath,
                                                    ) 
                                response=req.text
                       else:
                                req = requests.post(url_id_obj.json_url_update, 
                                                    data=jsonString,
                                                    headers=headers,
                                                    verify=False,
                                                    ) 
                                response=req.text
                                print 'response',response
                       if response:
                            fatture=json.loads(response)
                            if fatture['returnCode']=='0000':    
                                for ret_meta in fatture['message']:
                                    ret=ret_meta['message']
                                    print 'ret',ret
                                    stato_rx={
                                                'stato_rx':fatture['returnCode'],
                                                'log':fatture['description']+'-'+fatture['message'][0]['message']
                                                }

                            else:
                                    stato_rx={
                                                'stato_rx':fatture['returnCode'],
                                                'log':fatture['description']+'-'+fatture['message'][0]['message']
                                                }
                                
                            self.write(cr,uid,attach.id,stato_rx)
                            return True
                       else:
                            return True
            
    def signe_fatturapa(self, cr, uid, ids, context=None):
            url="http://wsf.cdyne.com/WeatherWS/Weather.asmx?WSDL"
            #headers = {'content-type': 'application/soap+xml'}
            headers = {'content-type': 'text/xml'}
            body = """<?xml version="1.0" encoding="UTF-8"?>
                         <SOAP-ENV:Envelope xmlns:ns0="http://ws.cdyne.com/WeatherWS/" xmlns:ns1="http://schemas.xmlsoap.org/soap/envelope/" 
                             xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
                             <SOAP-ENV:Header/>
                               <ns1:Body><ns0:GetWeatherInformation/></ns1:Body>
                         </SOAP-ENV:Envelope>"""
            
            response = requests.post(url,data=body,headers=headers)
            print response.content        
            return {}
    def trasmx_fatturapa(self, cr, uid, ids,url_id, context=None):
            pp = PrettyPrinter(indent=4)
            
            CUST = '<my customer name>'
            USER = '<my api username>'
            PASS = '<my api password>'
            
            ZONE = 'a-zone-in-my-account.com'
            
            # The path to the Dynect API WSDL file
            base_url = 'https://api2.dynect.net/wsdl/current/Dynect.wsdl'
            
            # Create a client instance
            client = suds.client.Client(base_url)
            
            # Logging in
            response = client.service.SessionLogin(
                customer_name = CUST,
                user_name = USER,
                password = PASS,
                fault_incompat = 1,
            )
            
            if response.status != 'success':
                print "Login request failed!"
                pp.pprint(response)
                raise SystemExit
            
            token = response.data.token
            
            print "Token: %s" % token
            
            # Get all records from the root node of a zone
            response = client.service.GetANYRecords(
                token = token,
                zone = ZONE,
                fqdn = ZONE,
                fault_incompat = 1,
            )
            
            print "Response: %s" % pp.pformat(response)
            
            if response.status != 'success':
                print "Record request failed!"
                pp.pprint(response)
                raise SystemExit
            
            
            # Log out
            response = client.service.SessionLogout(
                token = token,
                fault_incompat = 1,
            )
            
            if response.status != 'success':
                print "Logout request failed!"
                pp.pprint(response)
                raise SystemExit
            
            print "Successfully logged out"
            return {}
class fatturapa_url(orm.Model):
    _name = "fatturapa.url"
    _description = "FatturaPA Export File"
    _inherit = ['mail.thread']
    _columns = {
        'name':fields.char('Nome', size=64, required=False, readonly=False),
        'sequence': fields.integer('Sequenza',help='Per difetto prende la sequenza più alta') ,
        'type': fields.selection([('soap','Request Soap'), ('json','Request post json'),
                                  ], 'Type', size=10, required=True, help="Modalità di connessione"),
        'soap_wsdl':fields.char('wsdl', size=256, required=False, readonly=False),
        'soap_endpoint':fields.char('Endpoint', size=256, required=False, readonly=False),
        'soap_username':fields.char('Username', size=64, required=False, readonly=False),
        'soap_password':fields.char('Password', size=64, required=False, readonly=False),
        'soap_customerName':fields.char('CustomerName', size=64, required=False, readonly=False),
        'processid': fields.selection([('1','tramessa'), ('sap02','Tramessa,Firmata e Inviata'),
                                  ], 'Workflow Trasmissione', size=10, required=True, help="Modalità di connessione"),
        
        'json_sito':fields.char('Json sito', size=256, required=False, readonly=False),
        'json_url':fields.char('Json url', size=256, required=False, readonly=False),
        'json_username':fields.char('json Username', size=64, required=False, readonly=False),
        'json_password':fields.char('json Password', size=64, required=False, readonly=False),
        'json_certificato':fields.binary('Certificato', filters=None), 
        'json_usa_cert':fields.boolean('Usa Certificato', required=False), 
        'json_url_import':fields.char('Json url ciclo passivo', size=256, required=False, readonly=False),
        'json_url_update':fields.char('Json url update', size=256, required=False, readonly=False),
        'json_ver_trust': fields.selection([('1','Versione 1'), ('2','Versione 2'),
                                  ], 'Versione', size=1, required=False, help="Modalità di connessione"),
        
    }
    _defaults = {  
        'json_ver_trust': '2',  
        }
    _order = 'sequence desc,id desc'
    def soap_login_requests(self, cr, uid, ids, context=None):
        url_id_obj=self.browse(cr,uid,ids,context=context)
        
        url=url_id_obj.soap_endpoint
        CUST = url_id_obj.soap_customerName
        USER = url_id_obj.soap_username
        PASS = url_id_obj.soap_password
        #headers = {'content-type': 'application/soap+xml'}
        headers = {'content-type': 'text/xml'}
        body = """<?xml version="1.0" encoding="UTF-8"?>
                     <SOAP-ENV:Envelope xmlns:soapenv="http://shemas.xmlsoap.org.soap/envelope/"
                      xmlns:fe="uri://comped.it/fe" 
                      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                      xmlns:wsse="http://docs.oasis-open.org/wss/2001/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
                      xmlns:fe="uri://comped.it/fe" 

                         <SOAP-ENV:Header>
                         <wsse:Security>
                             <wsse:UsernameToken>
                             <wsse:Username>%s</wsse:Username>
                             <wsse:Password Type="http://docs.oasis-open.org/wss/2001/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">
                             %s
                             </wsse:Password>
                         
                             </wsse:UsernameToken>                         
                         </wsse:Security>
                         </SOAP-ENV:Header>
                           <ns1:Body><ns0:GetWeatherInformation/></ns1:Body>
                     </SOAP-ENV:Envelope>""" % (USER,PASS)
        
        response = requests.post(url,data=body,headers=headers)
        print response.content
        return {}
fatturapa_url()      
class fatturapa_config(orm.Model):
    _name = "fatturapa.config"
    _description = "FatturaPA Export File"
    _inherits = {'ir.attachment': 'ir_attachment_id'}
    _inherit = ['mail.thread']
    def _get_ir_attachment(self, cr, uid, ids, name, args, context=None):
        
        res = {}
        for inv_pa in self.browse(cr, uid, ids, context=context):
            id = inv_pa.id
            res[id] = []
            ir_attach_obj=self.pool.get('ir.attachment')
            ir_attach_ids=ir_attach_obj.search(cr,uid,[('id','=',inv_pa.ir_attachment_signed_id)],context=context)
            if ir_attach_ids:
                res[id] = True
                if inv_pa.firmata==False:
                    self.write(cr, uid, id, {'firmata':True}, context)
            else:
                res[id] = False
                if inv_pa.firmata==True:
                    self.write(cr, uid, id, {'firmata':False}, context)
        return res

    _columns = {
        'ir_attachment_id': fields.many2one(
            'ir.attachment', 'Attachment', required=True, ondelete="cascade"),
        'out_invoice_ids': fields.one2many(
            'account.invoice', 'fatturapa_attachment_out_id',
            string="Out Invoices", readonly=True),
        
        'ir_attachment_signed_id': fields.many2one(
            'ir.attachment', 'Signed', required=False, ondelete="cascade"),
                
        'fun_firmata': fields.function(_get_ir_attachment, string='Funz.fatt.firmata',type='boolean'),
        'firmata':fields.boolean('Firmata', required=False),
        'trasmessa':fields.boolean('Trasmessa', required=False),
        'stato_tx': fields.text('Stato trasmissione'),  
        'stato_rx': fields.text('Stato ricezione'),  
    }
class account_invoice(orm.Model):
    #_inherits = {'ir.attachment': 'ir_attachment_id','ir.attachment': 'ir_attachment_signed_id'}    
    _inherit = "account.invoice"
    def invoice_validate(self, cr, uid, ids, context=None):
        res=super(account_invoice, self).invoice_validate(cr, uid, ids, context=context)
        attach_out_obj=self.pool.get('fatturapa.attachment.out')
        attach_in_obj=self.pool.get('fatturapa.attachment.in')
        if res:
            for invoice in self.browse(cr,uid,ids,context=context):
                                    if invoice.type in ('out_invoice','out_refund'):    
                                        if invoice.fatturapa_attachment_out_id:
                                            attach_id=invoice.fatturapa_attachment_out_id.id
                                            attach_out_obj.chiudi_fatturapa(cr,uid,attach_id,context=context)
                                    else:
                                        if invoice.fatturapa_attachment_in_id:
                                            attach_id=invoice.fatturapa_attachment_in_id.id
                                            attach_in_obj.chiudi_fatturapa(cr,uid,attach_id,context=context)
                                        
        return res
    

 