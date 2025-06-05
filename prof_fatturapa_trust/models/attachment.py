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
from requests_toolbelt.multipart.encoder import MultipartEncoder
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
    def json_update_request(self,cr,uid,ids,escludi=True,metadata={},context=None):
                attach_obj=self.pool.get('ir.attachment')
                url_obj=self.pool.get('fatturapa.url')
                import_fpa_obj=self.pool.get('wizard.import.fatturapa')
                invoice_obj=self.pool.get('account.invoice')
                partner_obj=self.pool.get('res.partner')
                url_ids=url_obj.search(cr,uid,[('id','>',0)],order='sequence desc ,id desc',context=context)
                url_id_obj=url_obj.browse(cr,uid,url_ids[0],context=context)
                if url_id_obj.json_ver_trust=='1':
                        return super(FatturaPAAttachment_in, self).json_update_request(cr,uid,ids,escludi=escludi,metadata=metadata,context=context)
                
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
                                metadata= [{"olv:escludi":escludi},
                                        {"olv:fatForSDISezionale":attach.in_invoice_ids[0].journal_id.id},
                                        {"olv:fatForSDINumProtocollo":proto},
                                        {"olv:fatForSDIDataRegistrazione":attach.in_invoice_ids[0].move_id.date,
                                        }]                      
                            else:
                               metadata= [{"olv:escludi":escludi}]
                                                             
                                
                       if attach.json_fatForSDIId:
                            keys={"olv:fatForSDIId":attach.json_fatForSDIId}
                       else:
                           keys={
                               "olv:fatForSDIPivaCodFisc":attach.in_invoice_ids[0].partner_id.vat[2:13] or attach.in_invoice_ids[0].partner_id.fiscalcode ,
                               "olv:fatForSDINumFattura":attach.in_invoice_ids[0].supplier_invoice_number,
                               "olv:fatForSDIAnno":int(attach.in_invoice_ids[0].date_invoice[0:4]),
                               }

                       params = {
                           "site":str(url_id_obj.json_sito),
                           "class":"olv:fatForSDI",                    
                           "items":
                                [
                                    {
                                        "keys": [keys],
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
                                                    verify=False,
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
                                    #ret=ret_meta['message']
                                    ret=ret_meta['keys'][2]['message']
                                    print 'ret',ret
                                    stato_rx={
                                                'stato_rx':fatture['returnCode'],
                                                'log':fatture['description']+'-'+ret
                                                }

                            else:
                                    stato_rx={
                                                'stato_rx':fatture['returnCode'],
                                                'log':fatture['description']+'-'
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
                    if url_id_obj.json_ver_trust=='1':
                        return super(FatturaPAAttachment_in, self).json_imp_request(cr,uid,ids,processid=processid,context=context)


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
                           "xmlFile": True,
                           #"escludi":False                          
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
                       if str(url_id_obj.json_url_import).find('https')>=0:
                            if url_id_obj.json_usa_cert==False:
                                req = requests.post(url_id_obj.json_url_import, 
                                                    data=jsonString,
                                                    headers=headers,
                                                    verify=False
                                                    ) 
                                response=req.text
                                """
                                _logger.info(_(
                                    "json_imp_request %s: %s "
                                ) % (response, req))
                                """
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
                                    rets=ret_meta['metadata']
                                    num_fat=None
                                    data_invoice=None
                                    trust_stato=None
                                    trust_sezionale=None
                                    trust_sdi=None
                                    trust_fatForSDIDataEmissione=None
                                    trust_fatForSDIPivaCodFisc=None
                                    for ret in rets:
                                        if 'olv:fatForSDIDataFattura' in ret.keys():
                                            data_invoice = ret['olv:fatForSDIDataFattura']
                                        elif 'olv:fatForSDINumFattura' in ret.keys():
                                            num_fat = ret['olv:fatForSDINumFattura']
                                        elif 'olv:fatCliSDIStato' in ret.keys():
                                            trust_stato = ret['olv:fatCliSDIStato']
                                        elif 'olv:fatCliSDISezionale' in ret.keys():
                                            trust_sezionale = ret['olv:fatCliSDISezionale']
                                        elif 'olv:fatForSDIId' in ret.keys():
                                            trust_sdi = ret['olv:fatForSDIId']
                                        elif 'olv:fatForSDIPivaCodFisc' in ret.keys():
                                            trust_fatForSDIPivaCodFisc = ret['olv:fatForSDIPivaCodFisc']
                                        elif 'olv:fatForSDIDataEmissione' in ret.keys():
                                            trust_fatForSDIDataEmissione = ret['olv:fatForSDIDataEmissione']
                                        else:
                                            continue
                            
                                    #print 'ret',ret
                                    partner_ids=partner_obj.search(cr,uid,[('vat','=',trust_fatForSDIPivaCodFisc)],context=context)
                                    if trust_fatForSDIPivaCodFisc=='IT02984480166':
                                        print 'ret_IT02984480166',ret,partner_ids
                                    if partner_ids:
                                        partner_id_obj=partner_obj.browse(cr,uid,partner_ids[0],context=context)
                                        data_invoice = str(trust_fatForSDIDataEmissione)

                                        invoice_ids_obj=invoice_obj.search(cr,uid,[
                                                                            ('supplier_invoice_number','=',num_fat),
                                                                            ('date_invoice','=',data_invoice),
                                                                            ('partner_id','=',partner_ids[0]),
                                                                             ],context=context)
                                    
                                        if invoice_ids_obj:
                                            ok=True
                                        else:
                                            invoice_ids_obj=None
                                            """verifico se è un autofattura """
                                            invoice_ids_obj=invoice_obj.search(cr,uid,[
                                                                                ('number','=',num_fat),
                                                                                ('date_invoice','=',data_invoice),
                                                                                ('partner_id','=',partner_id_obj.company_id.partner_id.id),
                                                                                 ],context=context)

                                             
                                    else:
                                        invoice_ids_obj=None
                                    
                                    _logger.info(_("json_imp_request 1 %s:%s:%s") % (trust_sdi, num_fat,str(trust_fatForSDIDataEmissione)))
                                    if invoice_ids_obj==None or invoice_ids_obj==[]:
                                            invoice = b64decode(ret_meta['file'])
                                            #invoice = b64encode(str(invoice))
                                            stato_rx={'type':'json',
                                                'olv:fatForSDINumFattura':num_fat,
                                                'olv:fatForSDIDataEmissione':str(trust_fatForSDIDataEmissione),
                                                'olv:fatForSDIId':trust_sdi,
                                                'returnCode':fatture['returnCode'],
                                                'description':fatture['description']
                                                }
                                            atttach_id=import_fpa_obj.saveAttachment(cr, uid,stato_rx , invoice, context)
                                            if context is None:
                                                context={}
                                            context['active_ids']=[atttach_id]
                                            #import_id=import_fpa_obj.create(cr,uid,{},context=context)
                                            import_ids.append(atttach_id)
                                            _logger.info(_("json_imp_request 2 %s:") % (str(atttach_id),))

                                    else:
                                            
                                            invoice = b64decode(ret_meta['file'])
                                            #invoice = b64encode(str(invoice))
                                            stato_rx={'type':'json',
                                                'olv:fatForSDINumFattura':num_fat,
                                                'olv:fatForSDIDataEmissione':str(trust_fatForSDIDataEmissione),
                                                'olv:fatForSDIId':trust_sdi,
                                                'returnCode':fatture['returnCode'],
                                                'description':fatture['description']
                                                }
                                            atttach_id=import_fpa_obj.saveAttachment(cr, uid,stato_rx , invoice, context)
                                            invoice_id_obj=invoice_obj.browse(cr,uid,invoice_ids_obj[0],context)
                                            if invoice_id_obj.type in ('out_invoice','out_refund'):
                                                resp=self.json_update_request(cr, uid, [atttach_id], True, {}, context=context) 
                                            _logger.info(_("json_imp_request 2 %s:%s") % (str(atttach_id),invoice_id_obj.type))
                                            
                                #if import_ids:
                                    #res_fpa= import_fpa_obj.importFatturaPA(cr,uid,import_ids,context=context)
                            
                            fatture.update({'import_ids':import_ids})
                            return fatture
                       else:
                            return {'message': [], 'returnCode': '0100', 'description': 'generic error','import_ids':[]}
class FatturaPAAttachment(orm.Model):
    #_inherits = {'ir.attachment': 'ir_attachment_id','ir.attachment': 'ir_attachment_signed_id'}    
    _inherit = "fatturapa.attachment.out"
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
                    if url_id_obj.json_ver_trust=='1':
                        return super(FatturaPAAttachment, self).json_send_request(cr,uid,ids,processid=processid,context=context)
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
                       mp_encoder = MultipartEncoder(params)
                       
                       headers ={'Content-Type':'application/x-www-form-urlencoded','Authorization':user_password}
                       #headers ={'Content-Type':'multipart/form-data','Authorization':user_password}
                       headers ={'Content-Type':mp_encoder.content_type,'Authorization':user_password}
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
                                req = requests.post(url_id_obj.json_url, data=mp_encoder,headers=headers,verify=False,auth=HTTPBasicAuth(url_id_obj.json_username,url_id_obj.json_password)) 
                                response=req.text
                                print 'response_json_send_request',response
                            else:
                                req = requests.post(url_id_obj.json_url, data=mp_encoder,
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
                                req = requests.post(url_id_obj.json_url, data=mp_encoder,headers=headers,verify=False,auth=HTTPBasicAuth(url_id_obj.json_username,url_id_obj.json_password)) 
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
                    if url_id_obj.json_ver_trust=='1':
                        return super(FatturaPAAttachment, self).json_imp_request(cr,uid,ids,context=context)

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
                                                    verify=False
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
                                _logger.info(_(
                                    "_logger_json_imp_request %s: %s "
                                ) % (url_id_obj.json_url_import, headers))

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
                            _logger.info("json %s" % fatture)
                            for ret_meta in fatture['message']:
                                #if fatture['returnCode']=='0000':    
                                    
                                    rets=ret_meta['metadata']
                                    print 'rets',rets
                                    num_fat=None
                                    data_invoice=None
                                    trust_stato=None
                                    trust_sezionale=None
                                    trust_sdi=None
                                    for ret in rets:
                                        if 'olv:fatCliSDIDataFattura' in ret.keys():
                                            data_invoice = ret['olv:fatCliSDIDataFattura']
                                        elif 'olv:fatCliSDINumFattura' in ret.keys():
                                            num_fat = ret['olv:fatCliSDINumFattura']
                                        elif 'olv:fatCliSDIStato' in ret.keys():
                                            trust_stato = ret['olv:fatCliSDIStato']
                                        elif 'olv:fatCliSDISezionale' in ret.keys():
                                            trust_sezionale = ret['olv:fatCliSDISezionale']
                                        elif 'olv:fatCliSDIId' in ret.keys():
                                            trust_sdi = ret['olv:fatCliSDIId']
                                        else:
                                            continue
                            
                                    invoice_ids_obj=invoice_obj.search(cr,uid,[
                                                                            ('number','=',num_fat),
                                                                            ('date_invoice','=',data_invoice),
                                                                             ],context=context)
                                    
                                    for invoice_id_rm in invoice_ids_obj:
                                            invoice_id_obj=invoice_obj.browse(cr,uid,invoice_id_rm,context=context)
                                            if invoice_id_obj.fatturapa_attachment_out_id.json_fatCliSDIStato in ('HDO01','HDO05','HDO06'):
                                                invoice_ids_obj.remove(invoice_id_rm)
                                    if invoice_ids_obj:
                                        
                                            stato_rx={
                                                 'json_fatCliSDIStato':trust_stato,
                                                'stato_rx':fatture['returnCode'],
                                                'log':fatture['description']+'***'+fatture['returnCode'],
                                                }
                                            if trust_sezionale:
                                                stato_rx.update({'json_fatCliSDISezionale':trust_sezionale})
                                            if trust_sdi:
                                                stato_rx.update({'json_fatclisdiid':trust_sdi})
                                            if trust_stato=='HDO01' or trust_stato=='HDO05':
                                                stato_rx.update({'firmata':True})
                                            invoice_id_obj=invoice_obj.browse(cr,uid,invoice_ids_obj[0],context=context)
                                            attach_id=invoice_id_obj.fatturapa_attachment_out_id.id
                                            print 'attach_id',attach_id,'stato_rx',stato_rx
                                            if invoice_id_obj.fatturapa_attachment_out_id.json_fatCliSDIStato not in ('HDO01','HDO05','HDO06'):
                                                attach_obj.write(cr,uid,attach_id,stato_rx,context=context)
                                            if trust_stato=='HDO01' or trust_stato=='HDO05':
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

    def json_update_request(self,cr,uid,ids,escludi=True,context=None):
                url_obj=self.pool.get('fatturapa.url')
                import_fpa_obj=self.pool.get('wizard.import.fatturapa')
                invoice_obj=self.pool.get('account.invoice')
                partner_obj=self.pool.get('res.partner')
                url_ids=url_obj.search(cr,uid,[('id','>',0)],order='sequence desc ,id desc',context=context)
                url_id_obj=url_obj.browse(cr,uid,url_ids[0],context=context)
                if url_id_obj.json_ver_trust=='1':
                        return super(FatturaPAAttachment, self).json_update_request(cr,uid,ids,escludi=escludi,context=context)

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
                                        {"olv:fatCliSDIDataRegistrazione":attach.out_invoice_ids[0].move_id.date}
                                        ]                      
                       if attach.json_fatclisdiid:
                           keys=[{"olv:fatCliSDIId":attach.json_fatclisdiid}]
                       else:
                           keys=[
                               {"olv:fatCliSDISezionale":attach.json_fatCliSDISezionale},
                               {"olv:fatCliSDINumFattura":attach.out_invoice_ids[0].number},
                               {"olv:fatCliSDIDataFattura":str(attach.out_invoice_ids[0].date_invoice[0:4])},
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
                       _logger.info("jsonString %s" % jsonString)

                       if str(url_id_obj.json_url_update).find('https')>=0:
                            if url_id_obj.json_usa_cert==False:
                                req = requests.post(url_id_obj.json_url_update, 
                                                    data=jsonString,
                                                    headers=headers,
                                                    verify=False

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
                            _logger.info("jsonString %s" % fatture)
                            if fatture['returnCode']=='0000':    
                                for ret_meta in fatture['message']:
                                    ret=ret_meta['keys'][2]['message']
                                    print 'ret',ret
                                    stato_rx={
                                                'stato_rx':fatture['returnCode'],
                                                'log':fatture['description']+'-'+ret
                                                }

                            else:
                                    ret=''
                                    stato_rx={
                                                'stato_rx':fatture['returnCode'],
                                                'log':fatture['description']+'-'+ret
                                                }
                                
                            self.write(cr,uid,attach.id,stato_rx)
                            return True
                       else:
                            return True
            
class fatturapa_url(orm.Model):
    _inherit = 'fatturapa.url'
    _columns = {
        'json_ver_trust': fields.selection([('1','Versione 1'), ('2','Versione 2'),
                                  ], 'Versione', size=1, required=False, help="Versione trust"),
        
    }
    _defaults = {  
        'json_ver_trust': '1',  
        }
fatturapa_url()      

 