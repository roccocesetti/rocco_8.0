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
#from tools.translate import _
import base64
from tempfile import TemporaryFile
import csv
import openerp.pooler as pooler
import time
import openerp.addons.decimal_precision as dp
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp
from contextlib import contextmanager
import logging
_logger = logging.getLogger(__name__)


class partner_import(osv.osv):
    """ partner Import """

    _name = "res.partner.import"
    _description = "partner Import"
    _columns = {
        'name': fields.char('identificativo di  Importazione', size=64 , required=True),
        'data': fields.binary('File', required=True),
        'overwrite': fields.boolean('Sovrascrivi i codici esistenti',
                                    help=" i codici esistenti,  "
                                         "saranno sostituiti  "),

     }

    def import_partner(self, cr, uid, ids, context=None):
        this = self.browse(cr, uid, ids[0])
        fileobj = TemporaryFile('w+')
        this = self.browse(cr, uid, ids[0])
        try:
            fileobj.write(base64.decodestring(this.data))
    
            # now we determine the file format
            fileobj.seek(0)
            first_line = fileobj.readline().strip().replace('"', '').replace(' ', '')
            fileformat = first_line.endswith("codice,nome,cognome,email,"#3 
            "password,ragionesociale,blocco,codicefiscale,partitaiva,tipo,"#9 
            ",telefono,"#10
            "indirizzo,null,citta,"#13
            "localita,cap,altro"#15
            ) and 'csv' or 'csv'#46
            
            fileobj.seek(0)
            
            self.load_data( cr, uid, ids ,fileobj, fileformat, context=context)
        finally:
            fileobj.close()
        return True
	
    def load_data(self, cr, uid, ids, fileobj, fileformat,  context=None):
        db_name = cr.dbname
        pool = pooler.get_pool(db_name)
        state_obj = pool.get('res.country.state')
        partner_obj = pool.get('res.partner')
        user_obj = pool.get('res.users')
 
        
        this = self.browse(cr, uid, ids[0])
        try:
           # now, the serious things: we read the language file
            """leggo l'intestazione"""
            fileobj.seek(0)
            if fileformat == 'csv':
                reader = csv.reader(fileobj, quotechar='"', delimiter=',')
                # read the first line of the file (it contains columns titles)
                for row in reader:
                    f = row
                    break

            else:
                raise osv.except_osv(('Bad file format: %s'), (fileformat))
                raise Exception(_('Bad file format'))
    
            # read the rest of the file
            line = 1   
            for row in reader:
                line +=1
                
                """creo la provincia"""
                state_ids = state_obj.search(cr, uid, [('name','=', row[14])])    
                if not state_ids:
                            state_id=state_obj.create(cr, uid, {'name': row[14],'code': row[14],'country_id':110}, context=context)
                else:
                            state_id=state_ids[0]
                """creo il cliente"""
                partner_ids = partner_obj.search(cr, uid, [('name','=', row[5])])    
                vals={
                     'name':row[5],
                     'customer':True,
                     'supplier':False,
                     'zip':row[15],
                     'state_id':state_id,
                     'city':row[13],
                     'street':row[11],
                     #'vat':row[8],
                     'ref':row[7],
                     'email':row[3],
                     'active':True,
                     'is_company':True,
                     
                }# skip empty rows and rows where the translation field (=last fiefd) is empty
                if not partner_ids:
             # lets create the language with locale information
                     partner_ids_id=partner_obj.create(cr, uid, vals, context=context)
                else:
                     partner_ids_id=partner_ids[0]
                     if this.overwrite==True: 
                        partner_obj.write(cr, uid, partner_ids_id, vals, context)  
                """creo utente"""
                user_partner_ids = partner_obj.search(cr, uid, [('name','=', row[1]+row[2])])    
                if not user_partner_ids:
             # lets create the language with locale information
                     if vals.get('name',False):
                         vals={
                             'name':row[1]+row[2],
                             'customer':False,
                             'supplier':False,
                             'zip':row[15],
                             'state_id':state_id,
                             'city':row[13],
                             'street':row[11],
                             'email':row[3],
                             'active':True,
                             'parent_id':partner_ids_id,
                         }# skip empty rows and rows where the translation field (=last fiefd) is empty

                         user_partner_ids_id=partner_obj.create(cr, uid, vals, context=context)
                else:
                     vals={
                         'name':row[1]+row[2],
                         'customer':False,
                         'supplier':False,
                         'zip':row[15],
                         'state_id':state_id,
                         'city':row[13],
                         'street':row[11],
                         'email':row[3],
                         'active':True,
                         }

                     user_partner_ids_id=user_partner_ids[0]
                     if this.overwrite==True: 
                         if vals.get('name',False):
                             partner_obj.write(cr, uid, user_partner_ids_id, vals, context)  

                user_ids = user_obj.search(cr, uid, [('login','=', row[3])])    
                vals={
                     'login':row[3],
                     'password':row[4],
                     #'new_password':row[4],
                     'active':True,
                     'partner_id':partner_ids_id,
                     'group_id':1,
                }# skip empty rows and rows where the translation field (=last fiefd) is empty
                if not user_ids:
             # lets create the language with locale information
                         if vals.get('login',False):
                                user_ids_id=user_obj.create(cr, uid, vals, context=context)
                else:
                     user_ids_id=user_ids[0]
                     if this.overwrite==True: 
                         if vals.get('login',False):
                                user_obj.write(cr, uid, user_ids_id, vals, context)  
                
                #_logger.info("importazione effettuata con successo")
        except IOError:
            filename = '[lang: %s][format: %s]' % (iso_lang or 'new', fileformat)
            raise osv.except_osv(_("Impossibile leggere ilfile %s"), _(filename))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
