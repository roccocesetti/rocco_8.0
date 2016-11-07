# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 solutions2use (<http://www.solutions2use.com>).
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

from openerp.osv import osv, fields
from openerp.tools.translate import _
import openerp.netsvc as netsvc
from pamfax import PamFax
import time, datetime
import logging
import base64
import re
import os.path
import json, urllib2
import xml.etree.ElementTree as ET
import urllib
import httplib2

from xml.etree.ElementTree import parse
import openerp.pooler as pooler
logger = logging.getLogger('faxsend')

class news_feed(osv.osv):
    _name = 'rocco.news.feed'
    _columns = {
        'name': fields.char('Search_mail', size=256, required=True),
        'url': fields.char('url', size=256, required=True),
        'cartella': fields.char('Cartella download', size=256, required=True),
        'livello': fields.integer('Livello scanner sottolink',help="Numero di links da trovare all'interno del link in elaborazione"),
        'max_link': fields.integer('Numero massimo di link da scannerizzare',help="Numero massimo di links da elaborare"),
        'no_link': fields.integer('Link non elaborati'),
        'mass_mail_id':fields.many2one('mail.mass_mailing.list', 'Mailing list', required=True), 
        'x_mail_ids':fields.one2many('mail.mass_mailing.contact.x_mail', 'x_search_mail_id', 'Dettaglio_ricerca', required=False),
                    }
    _defaults = {  
        'cartella': 'tmp',  
        'livello': 10,  
        'max_link': 1000,  
        'no_link': 0,  
        }
    def process_url(self, cr, uid, ids, context=None):
            def add_link(my_link,my_hdr,my_link_ids=None,my_mail_ids=None,my_tel_ids=None,my_fax_ids=None,my_conta={'link_con':0,'link_max':20},no_links=[],context=context):
                my_cursor=0
                my_fine=0
                my_cont=0
                my_conta['link_con']=0                  
                print 'add_link_my_link',my_link
                try:
                    urequest = urllib2.Request(my_link,headers=my_hdr)
                    uopen = urllib2.urlopen(urequest)
                    if my_link_ids==None:
                            my_link_ids=[]
                    if my_mail_ids==None:
                            my_mail_ids=[]
                    if my_fax_ids==None:
                            my_fax_ids=[]
                    if my_tel_ids==None:
                            my_tel_ids=[]
                    my_resp = uopen.read()
                except:
                    my_resp=''
                while str(my_resp).find('http://',my_cursor):
                    my_inizio=str(my_resp).find('http://',my_cursor)
                    if my_inizio>=0:
                        my_fines=[]
                        my_fines.append(str(my_resp).find('"',my_inizio+len('http://')))
                        my_fines.append(str(my_resp).find("'",my_inizio+len('http://')))
                        my_fines.append(str(my_resp).find('</a>',my_inizio+len('http://')))
                        my_fines.append(str(my_resp).find('</p>',my_inizio+len('http://')))
                        my_fines.append(str(my_resp).find('>',my_inizio+len('http://')))
                        my_fines.sort()
                        my_fine=0
                        for my_fin in my_fines:
                            if my_fin>=0:
                                my_fine=my_fin
                                break
                        if my_fine<=my_cursor:
                                my_fine+=my_inizio+len('http://')
                        my_cursor=my_fine+1
                        #my_fine-=1
                        my_link_res=str(my_resp)[my_inizio:my_fine]
                        si_link=True
                        for no_link in no_links:
                            if my_link_res.find(no_link)>=0:
                                    si_link=False
                                    break
                        if si_link:
                            if my_link_res not in my_link_ids:
                                    my_conta['link_con']+=1                    
                                    if my_conta['link_con']<my_conta['link_max']:
                                        my_link_ids.append(my_link_res)
                                        my_cont+=1
                                        print 'my_link_res',my_link_res
                    else:
                        break
                my_cursor=0
                my_fine=0
                while str(my_resp).find('mailto:',my_cursor):
                    print 'my_cursor',my_cursor
                    my_inizio=str(my_resp).find('mailto:',my_cursor)
                    if my_inizio>=0:                        
                        my_fines=[]
                        my_fines.append(str(my_resp).find('"',my_inizio+len('mailto:')))
                        my_fines.append(str(my_resp).find("'",my_inizio+len('mailto:')))
                        my_fines.append(str(my_resp).find('</a>',my_inizio+len('mailto:')))
                        my_fines.append(str(my_resp).find('</p>',my_inizio+len('mailto:')))
                        my_fines.append(str(my_resp).find('>',my_inizio+len('mailto:')))
                        my_fines.sort()
                        my_fine=0
                        for my_fin in my_fines:
                            if my_fin>=0:
                                my_fine=my_fin
                                break
                        if my_fine<=my_cursor:
                                my_fine+=my_inizio+len('mailto:')
                        my_cursor=my_fine+1
                        my_mail_res=str(my_resp)[my_inizio+len('mailto:'):my_fine]
                        if my_mail_res:
                            if my_mail_res not in my_mail_ids and my_mail_res.find('@')>=0:
                                my_mail_ids.append({'name':my_link,'mail':my_mail_res.strip()})
                    else:
                        break
                my_cursor=0
                my_fine=0
                while str(my_resp).find('mail',my_cursor):
                        print 'my_cursor',my_cursor
                        my_inizio=str(my_resp).find('mail',my_cursor)
                        if my_inizio>=0:                        
                            my_fines=[]
                            my_fines.append(str(my_resp).find('"',my_inizio+len('mail')))
                            my_fines.append(str(my_resp).find("'",my_inizio+len('mail')))
                            my_fines.append(str(my_resp).find('>',my_inizio+len('mail')))
                            my_fines.append(str(my_resp).find('</a>',my_inizio+len('mail')))
                            my_fines.append(str(my_resp).find('</p>',my_inizio+len('mail')))
                            my_fines.sort()
                            my_fine=0
                            for my_fin in my_fines:
                                if my_fin>=0:
                                    my_fine=my_fin
                                    break
                            if my_fine<=my_cursor:
                                    my_fine+=my_inizio+len('mail')
                            my_cursor=my_fine+1
                            my_mail_res=str(my_resp)[my_inizio+len('mail'):my_fine]
                            if my_mail_res:
                                if my_mail_res not in my_mail_ids and my_mail_res.find('@')>=0:
                                    my_mail_ids.append({'name':my_link,'mail':my_mail_res.strip()})
                        else:
                            break
                my_cursor=0
                my_fine=0
                while str(my_resp).find('email',my_cursor):
                        print 'my_cursor',my_cursor
                        my_inizio=str(my_resp).find('email',my_cursor)
                        if my_inizio>=0:                        
                            my_fines=[]
                            my_fines.append(str(my_resp).find('"',my_inizio+len('email')))
                            my_fines.append(str(my_resp).find("'",my_inizio+len('email')))
                            my_fines.append(str(my_resp).find('>',my_inizio+len('email')))
                            my_fines.append(str(my_resp).find('</a>',my_inizio+len('email')))
                            my_fines.append(str(my_resp).find('</p>',my_inizio+len('email')))
                            my_fines.sort()
                            my_fine=0
                            for my_fin in my_fines:
                                if my_fin>=0:
                                    my_fine=my_fin
                                    break
                            if my_fine<=my_cursor:
                                    my_fine+=my_inizio+len('email')
                            my_cursor=my_fine+1
                            my_mail_res=str(my_resp)[my_inizio+len('email'):my_fine]
                            if my_mail_res:
                                if my_mail_res not in my_mail_ids and my_mail_res.find('@')>=0:
                                    my_mail_ids.append({'name':my_link,'mail':my_mail_res.strip()})
                        else:
                            break
                my_cursor=0
                my_fine=0
                while str(my_resp).find('e-mail',my_cursor):
                        print 'my_cursor',my_cursor
                        my_inizio=str(my_resp).find('e-mail',my_cursor)
                        if my_inizio>=0:                        
                            my_fines=[]
                            my_fines.append(str(my_resp).find('"',my_inizio+len('e-mail')))
                            my_fines.append(str(my_resp).find("'",my_inizio+len('e-mail')))
                            my_fines.append(str(my_resp).find('>',my_inizio+len('e-mail')))
                            my_fines.append(str(my_resp).find('</a>',my_inizio+len('e-mail')))
                            my_fines.append(str(my_resp).find('</p>',my_inizio+len('e-mail')))
                            my_fines.sort()
                            my_fine=0
                            for my_fin in my_fines:
                                if my_fin>=0:
                                    my_fine=my_fin
                                    break
                            if my_fine<=my_cursor:
                                    my_fine+=my_inizio+len('e-mail:')
                            my_cursor=my_fine+1
                            my_mail_res=str(my_resp)[my_inizio+len('e-mail'):my_fine]
                            if my_mail_res:
                                if my_mail_res not in my_mail_ids and my_mail_res.find('@')>=0:
                                        my_mail_ids.append({'name':my_link,'mail':my_mail_res.strip()})
                        else:
                            break
                my_cursor=0
                my_fine=0
                while str(my_resp).lower().find('tel',my_cursor):
                        print 'my_cursor_tel',my_cursor
                        my_inizio=str(my_resp).find('tel',my_cursor)
                        if my_inizio>=0:                        
                            my_fines=[]
                            my_fines.append(str(my_resp).find('"',my_inizio+len('tel')))
                            my_fines.append(str(my_resp).find("'",my_inizio+len('tel')))
                            my_fines.append(str(my_resp).find('>',my_inizio+len('tel')))
                            my_fines.append(str(my_resp).find('</a>',my_inizio+len('tel')))
                            my_fines.append(str(my_resp).find('</p>',my_inizio+len('tel')))
                            my_fines.sort()
                            my_fine=0
                            for my_fin in my_fines:
                                if my_fin>=0:
                                    my_fine=my_fin
                                    break
                            if my_fine<=my_cursor:
                                    my_fine+=my_inizio+len('tel')
                            my_cursor=my_fine+1
                            my_tel_res=str(my_resp)[my_inizio+len('tel'):my_fine]
                            if my_tel_res not in my_tel_ids and my_tel_res.strip().isdigit():
                                    my_tel_ids.append({'name':my_link,'tel':my_tel_res})
                        else:
                            break
                my_cursor=0
                my_fine=0
                while str(my_resp).lower().find('fax',my_cursor):
                        print 'my_cursor_fax',my_cursor
                        my_inizio=str(my_resp).lower().find('fax',my_cursor)
                        print 'my_fax',my_inizio
                        if my_inizio>=0:                        
                            my_fines=[]
                            my_fines.append(str(my_resp).find('"',my_inizio+len('fax')))
                            my_fines.append(str(my_resp).find("'",my_inizio+len('fax')))
                            my_fines.append(str(my_resp).find('>',my_inizio+len('fax')))
                            my_fines.append(str(my_resp).find('</a>',my_inizio+len('fax')))
                            my_fines.append(str(my_resp).find('</p>',my_inizio+len('fax')))
                            my_fines.sort()
                            my_fine=0
                            for my_fin in my_fines:
                                if my_fin>=0:
                                    my_fine=my_fin
                                    break
                            if my_fine<=my_cursor:
                                    my_fine+=my_inizio+len('fax')
                            my_cursor=my_fine+1
                            print 'my_fax_fine',my_fine
                            my_fax_res=str(my_resp)[my_inizio+len('fax'):my_fine]
                            print 'my_fax_res',my_fax_res,my_fax_res.strip().isdigit()
                            print 'my_fax_ids',my_fax_ids
                            if my_fax_res not in my_fax_ids and my_fax_res.strip().isdigit():
                                    my_fax_ids.append({'name':my_link,'fax':my_fax_res})
                                    print 'my_fax_ids',my_fax_ids
                        else:
                            break
                return {'cont':my_cont,'links':my_link_ids,'mail':my_mail_ids,'tel':my_tel_ids,'fax':my_fax_ids,'my_conta':my_conta}
            if hasattr(ids, '__iter__'):
                ids=ids
            else:
                ids=[ids]
            no_links=['w3.org','wikipedia','schema.org','dishdash.com','purl.org','example.com','iana.org']
            for x_url_id in ids:
                    x_url_mail_id_obj=self.browse(cr, uid, x_url_id, context=context)
                    x_url_x_contact_mail_obj=self.pool.get('mail.mass_mailing.contact.x_mail')
                    url = str(x_url_mail_id_obj.url)
                    cartella=x_url_mail_id_obj.cartella
                    livello=x_url_mail_id_obj.livello
                    max_link=x_url_mail_id_obj.max_link
                    http = httplib2.Http()
                    x_POST={}
                    x_POST['request']=""
                    body = {'$_POST': x_POST}
                    headers = {'Content-type': 'application/x-www-form-urlencoded'}
                    hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
               'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
               'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
               'Accept-Encoding': 'none',
               'Accept-Language': 'en-US,en;q=0.8;it-IT,it',
               'Connection': 'keep-alive'}
        
                    #urequest = urllib2.Request(url+"?request="+request,headers=hdr)
                    #import pdb; pdb.set_trace()
                    my_link_ids=[]
                    my_mail_ids=[]
                    my_tel_ids=[]
                    my_fax_ids=[]
                    my_link_ids.append(url)
                    no_links.append(url)
                    res=add_link(url,hdr,my_link_ids,my_mail_ids,my_tel_ids,my_fax_ids,{'link_con':0,'link_max':livello},no_links,context)
                    num_link=0
                    for link in res['links']:
                            #import pdb; pdb.set_trace()
                            num_link+=1
                            if num_link<=max_link:
                                print 'link',link,res['my_conta']
                                res=add_link(link,hdr,res['links'],res['mail'],res['tel'],res['fax'],res['my_conta'],no_links,context)
                            else:
                                self.write(cr, uid, ids,{'no_link':max_link-num_link}, context=context)
                                break
                    for mail in res['mail']:
                         x_contact_ids=x_url_x_contact_mail_obj.search(cr,uid,[('email','ilike',mail['mail']),('x_search_mail_id','=',x_url_id)])
                         if x_contact_ids==[]:
                            x_url_x_contact_mail_obj.create(cr,uid,{'name':mail['name'],'email':mail['mail'],'x_search_mail_id':x_url_id,'fax':None})    
                    for fax in res['fax']:
                         x_contact_ids=x_url_x_contact_mail_obj.search(cr,uid,[('fax','ilike',fax['fax']),('x_search_mail_id','=',x_url_id)])
                         if x_contact_ids==[]:
                            x_url_x_contact_mail_obj.create(cr,uid,{'name':fax['name'],'fax':fax['fax'],'email':None,'x_search_mail_id':x_url_id})    
                    for tel in res['tel']:
                         x_contact_ids=x_url_x_contact_mail_obj.search(cr,uid,[('tel','ilike',tel['tel']),('x_search_mail_id','=',x_url_id)])
                         if x_contact_ids==[]:
                            x_url_x_contact_mail_obj.create(cr,uid,{'name':fax['name'],'tel':tel['tel'],'email':None,'x_search_mail_id':x_url_id})    
    def process_mass_mail(self, cr, uid, ids, context=None):
            x_url_mail_id_obj=self.browse(cr, uid, ids, context=context)
            x_url_x_contact_mail_obj=self.pool.get('mail.mass_mailing.contact.x_mail')
            mail_mass_mailing_contact_obj=self.pool.get('mail.mass_mailing.contact')
            for x_contact in x_url_mail_id_obj.x_mail_ids:
                    mail_mass_mailing_contact_obj.create(cr,uid,{'name':x_contact.name,'email':str(x_contact.email).strip() or None,'list_id':x_contact.x_search_mail_id.mass_mail_id.id,'fax':x_contact.fax or None},context=context)
class mail_mass_mailing_contact_x_mail(osv.osv):
    _name = 'mail.mass_mailing.contact.x_mail' 
    _columns = {
        'x_search_mail_id': fields.many2one('mail.mass_mailing.contact.x_url_mail', 'Rif-ricerca', required=False), 
        'name': fields.char('Contatto', size=256, required=True),
        'email': fields.char('Mail', size=256, required=False),
        'fax': fields.char('Fax', size=256, required=False),
        'tel': fields.char('Tel', size=256, required=False),

                    }

class faxsend_account(osv.osv):    
    
    _name = 'faxsend.account'
    _columns = {
        'name': fields.char('Account', size=50, required=True),
        'username': fields.char('Username', size=50, required=True),
        'password': fields.char('password', size=50, required=True),
        'apikey': fields.char('apikey', size=128, required=True),        
        'apisecret': fields.char('apisecret', size=128, required=True),        
        'host': fields.char('host', size=256, required=True),        
        'mailing_list_id':fields.many2one('mail.mass_mailing.list', 'Mailing list', required=True), 
        'filename': fields.char('filename', size=256, required=True),
    }
    _defaults = {  
        'host': 'api.pamfax.biz',        
        }    
    _sql_constraints = [
        ('pu-key', 'UNIQUE (name)',  'Account already exists in database!'),                
    ]
    
class faxsend_queue(osv.osv):
    
    def _get_name(self, cr, uid, ids, field_name, arg, context):
        
        res = {}
        
        for r in self.browse(cr, uid, ids):            
            res[r.id] = r.report + '/' + r.subject + '/' + str(r.obj_id)
            
        return res
    
    def _process_faxes(self, cr, uid, ids=False, context=None):
        if not ids:
            ids = self.search(cr, uid, [('state','=','wait')])
        return self.process_faxes(cr, uid, ids, context=context)
        
    _name = 'faxsend.queue'   
    _order = 'queue_date desc, id desc' 
    _columns = {
       'name': fields.function(_get_name, method=True, type='char', size=50, string='Queue'),
       'report': fields.char('Report/Model', size=50, required=True, readonly=True, states={'draft': [('readonly', False)]}),
       'object_type': fields.selection([
            ('report', 'Report'),                                                      
            ('attachment', 'Attachment'),                                                                
            ], 'Obj type', required=True, select=True, readonly=True, states={'draft': [('readonly', False)]}),
       'obj_id': fields.integer('Obj. ID', required=True, readonly=True, states={'draft': [('readonly', False)]}),
       'state': fields.selection([
            ('draft', 'Draft'),                                                      
            ('wait', 'Waiting'),                    
            ('send', 'Sending'),
            ('error', 'Error'),
            ('ok', 'Send ok'),
            ('cancel', 'Cancelled'),                                    
            ], 'Fax State', readonly=True, help="Gives the state of the fax.", select=True),
       'faxno': fields.char('Fax No.', size=50, required=True, readonly=True, states={'draft': [('readonly', False)]}),
       'job_no': fields.char('Job', size=50, select=True, readonly=True, states={'draft': [('readonly', False)]}),
       'pages': fields.integer('Pages', readonly=True),
       'duration': fields.integer('Duration (sec.)', readonly=True),
       'subject': fields.char('Subject', size=50, required=True, readonly=True, states={'draft': [('readonly', False)]}),
       'account_id': fields.many2one('faxsend.account', 'Account', select=True, required=True, readonly=True, states={'draft': [('readonly', False)]}),
       'queue_date': fields.date('Date of entry'),
       'trigger_model': fields.char('Trigger model', size=50, readonly=True, states={'draft': [('readonly', False)]}),       
       'trigger_method': fields.char('Trigger method', size=50, readonly=True, states={'draft': [('readonly', False)]}),
       'trigger_method_args': fields.char('Method args', size=50, readonly=True, states={'draft': [('readonly', False)]}),
       
    }
    
    _defaults = {          
        'object_type': 'report',                  
        'state': 'draft', 
        'queue_date': lambda *a: time.strftime('%Y-%m-%d'),
        'trigger_method_args': '()',           
    }
    
    def send_report_by_fax(self, cr, uid, obj_id, account, subject, report, faxno, triggerModel=None, triggerMethod=None, triggerArgs=None):
        
        account_pool = self.pool.get('faxsend.account')        
        list = account_pool.search(cr, uid, [('name', '=', account)])
        
        if len(list) != 1:                        
            raise osv.except_osv(_('Error :'), _('Account \'%s\' for send fax not found.') % account)
        
        a = account_pool.browse(cr,uid, list[0])                        
        id = self.create(cr, uid, {'report': report, 
                                   'obj_id': obj_id, 
                                   'faxno': faxno, 
                                   'subject': subject, 
                                   'account_id': a.id, 
                                   'object_type':'report',
                                   'trigger_model': triggerModel,
                                   'trigger_method': triggerMethod,
                                   'trigger_method_args': triggerArgs})
        # change state from 'draft' to 'wait' so that fax is send by the the next call from the scheduler  
        self.write(cr, uid, id, { 'state' : 'wait' })  
        
    def send_attachment_by_fax(self, cr, uid, obj_id, account, subject, model, faxno, triggerModel=None, triggerMethod=None, triggerArgs=None):
        
        account_pool = self.pool.get('faxsend.account')        
        list = account_pool.search(cr, uid, [('name', '=', account)])
        
        if len(list) != 1:                        
            raise osv.except_osv(_('Error :'), _('Account \'%s\' for send fax not found.') % account)
        
        a = account_pool.browse(cr,uid, list[0])                        
        id = self.create(cr, uid, {'report': model, 
                                   'obj_id': obj_id, 
                                   'faxno': faxno, 
                                   'subject': subject, 
                                   'account_id': a.id, 
                                   'object_type':'attachment',
                                   'trigger_model': triggerModel,
                                   'trigger_method': triggerMethod,
                                   'trigger_method_args': triggerArgs})
        # change state from 'draft' to 'wait' so that fax is send by the the next call from the scheduler  
        self.write(cr, uid, id, { 'state' : 'wait' })
    
    def action_send_fax(self, cr, uid, ids, *args):
        
        for o in self.browse(cr, uid, ids):               
            self.write(cr, uid, o.id, { 'state' : 'wait' })
            
    def action_send_fax_again(self, cr, uid, ids, *args):
        
        if not len(ids):
            return False
                
        # set state='draft' gives user chance to change data before sending fax
        self.write(cr, uid, ids, {'state': 'draft', 'job_no':'' })        
        wf_service = netsvc.LocalService("workflow")
        for id in ids:
            # Deleting the existing instance of workflow for faxsend.queue
            wf_service.trg_delete(uid, 'faxsend.queue', id, cr)
            wf_service.trg_create(uid, 'faxsend.queue', id, cr)                        
                                                                                                                                     
        return True            
        
    def action_cancel_send_fax(self, cr, uid, ids, *args):             
                       
        for o in self.browse(cr, uid, ids):               
            self.write(cr, uid, o.id, { 'state' : 'cancel' })                    
             
        return True
    
    def process_faxes(self, cr, uid, ids, context=None):
        """WARNING: meant for cron usage only - will commit() after each fax!"""                                
        # first let us check the status of faxes previous send by the scheduler
        contact_obj=self.pool.get('mail.mass_mailing.contact')
        list = self.search(cr, uid, [('state', '=', 'send')], order='job_no desc', context=context)
        if len(list) > 0:            
            try:
                o = self.browse(cr, uid, list[0])                            
                pamfax = PamFax(o.username, o.password, host=o.host, apikey=o.apikey, apisecret=o.apisecret)
                pamfax.create()
                response = pamfax.list_available_covers()                
                pamfax.set_cover(response['Covers']['content'][1]['id'], 'My test fax with PamFax using Python')
                for item in o.mailing_list_id.item_ids:                    
                    pamfax.add_recipient(item.fax)
                pamfax.add_file(o.filename, origin=None)
                while True:
                 fax_state = pamfax.get_state()
                 if fax_state['FaxContainer']['state'] == 'ready_to_send':
                  break
                 time.sleep(2)
                 
                pamfax.send()
                if fax_state['FaxContainer']['state']:
                                    self.write(cr, uid, list, { 'state': 'ok', 'pages': i[6], 'duration': i[8]})
                else:
                                    self.write(cr, uid, list, { 'state': 'error' })
            except Exception:
                logger.error('failed retrieving fax-status from interfax.net')
           