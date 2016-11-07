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

import time
from openerp.report import report_sxw
from openerp import pooler
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
from openerp import SUPERUSER_ID
import curses.ascii
import string
from datetime import datetime, timedelta
from operator import itemgetter
from itertools import groupby
from openerp import tools
csp=[]
csp=[curses.ascii.ACK,curses.ascii.BEL,curses.ascii.BS,curses.ascii.CAN,curses.ascii.CR,curses.ascii.DC1,curses.ascii.DC2,
             curses.ascii.DC3,curses.ascii.DC4,curses.ascii.DEL,curses.ascii.DLE,curses.ascii.EM,curses.ascii.ENQ,curses.ascii.EOT,
             curses.ascii.ESC,curses.ascii.ETB,curses.ascii.ETX,curses.ascii.FF,curses.ascii.GS,curses.ascii.HT,curses.ascii.LF,
             curses.ascii.NAK,curses.ascii.NL,curses.ascii.NUL,curses.ascii.RS,curses.ascii.SI,curses.ascii.SO,curses.ascii.SOH,
             curses.ascii.SP,curses.ascii.STX,curses.ascii.SUB,curses.ascii.SYN,curses.ascii.TAB,curses.ascii.US,curses.ascii.VT]

   #Do not touch _name it must be same as _inherit
    #_name = 'stock.picking.out' cr        

class distinta_bancaria_print(report_sxw.rml_parse):
    def get_righe(self,stringa):
            righe=[]
            miocampo=''
            for  landa in stringa:
                    if landa!='#'.decode('utf-8').encode('cp1250') or  (landa in csp):
                            miocampo=miocampo+landa
                    else:    
                            if miocampo:
                                righe.append(miocampo)
                                miocampo=''
            
            if miocampo!='':
                if len(miocampo)<=22:
                  righe.append(miocampo)
                else:
                    my_i=0
                    while  my_i<  len(miocampo.strip()): 
                    
                        myriga= miocampo[my_i:my_i+22]
                        righe.append(myriga)
                        my_i+=22
            return righe
    def get_num_effetti(self,stringa):
            righe=[]
            miocampo=''
            for  landa in stringa:
                    if landa!='#'.decode('utf-8').encode('cp1250') or  (landa in csp):
                            miocampo=miocampo+landa
                    else:    
                            if miocampo:
                                righe.append(miocampo)
                                miocampo=''
            
            if miocampo!='':
                if len(miocampo)<=14:
                  righe.append(miocampo)
                else:
                    my_i=0
                    while  my_i<  len(miocampo): 
                    
                        myriga= miocampo[my_i:my_i+14]
                        righe.append(myriga)
                        my_i+=14
            return righe
    def get_data_fatt(self,stringa):
            righe=[]
            miocampo=''
            for  landa in stringa:
                    if landa!='#'.decode('utf-8').encode('cp1250') or  (landa in csp):
                            miocampo=miocampo+landa
                    else:    
                            if miocampo:
                                righe.append(miocampo)
                                miocampo=''
            
            if miocampo!='':
                if len(miocampo)<=10:
                  righe.append(miocampo)
                else:
                    my_i=0
                    while  my_i<  len(miocampo): 
                    
                        myriga= miocampo[my_i:my_i+10]
                        righe.append(myriga)
                        my_i+=10
            return righe
    def get_line_eff(self,line_ids):
            res={}
            for line in line_ids:
                res[str(line.due_date)+'-'+str(line.sequence)]=line
            
            res=sorted(res.items(), key=lambda(k,v):(k,v))
            return res
    def get_righe_piede(self,stringa):
            righe=[]
            miocampo=''
            for  landa in stringa:
                    if landa!='#'.decode('utf-8').encode('cp1250') or  (landa in csp):
                            miocampo=miocampo+landa
                    else:    
                            if miocampo:
                                righe.append(miocampo)
                                miocampo=''
            
            if miocampo!='':
                if len(miocampo)<=25:
                  righe.append(miocampo)
                else:
                    my_i=0
                    while  my_i<  len(miocampo): 
                    
                        myriga= miocampo[my_i:my_i+22]
                        righe.append(myriga)
                        my_i+=22
            return righe

    def _get_conta(self,conta=0):
            conta+1
            if conta>60:
                conta=1
                
            return conta
    def _get_data(self,data=None):
        try:
            return datetime.strptime(str(data),"%Y-%m-%d").strftime("%d/%m/%Y")            
        except:
            try:
                 return datetime.strptime(str(data),"%m/%d/%Y").strftime("%d/%m/%Y")            
            except:
                 return data           

        

    def __init__(self, cr, uid, name, context):
        super(distinta_bancaria_print, self).__init__(cr, uid, name, context=context)
        db_name = cr.dbname
        pool = pooler.get_pool(db_name)
        partner_obj=pool.get('res.partner')
        user_obj=pool.get('res.users')
        user_ids_obj=user_obj.browse(cr, uid, uid,context=context) 
        if user_ids_obj:
            if user_ids_obj.company_id:
                   partner_ids_obj=partner_obj.browse(cr, uid, user_ids_obj.company_id.partner_id.id,context=context)
                   partner_ids_id=partner_ids_obj.id
            else:    
                   partner_ids_id=0
        else:
               partner_ids_id=0
        riba_obj=pool.get('riba.distinta')
        if context.get('active_ids',None):
           riba_ids_obj = riba_obj.browse(cr, uid, context['active_ids'],context=context)
           data_oggi=datetime.today()
           time.tzset()
           
           cons_ora_mm_ss=datetime.strptime(str(data_oggi),"%Y-%m-%d %H:%M:%S.%f").strftime("%H:%M:%S")
           cons_HH=int(datetime.strptime(str(data_oggi),"%Y-%m-%d %H:%M:%S.%f").strftime("%H"))
           if cons_HH>23:
               cons_HH=23
           cons_mm=int(datetime.strptime(str(data_oggi),"%Y-%m-%d %H:%M:%S.%f").strftime("%M"))
           cons_ss=int(datetime.strptime(str(data_oggi),"%Y-%m-%d %H:%M:%S.%f").strftime("%S"))
           cons_ora=str(cons_HH)+":"+str(cons_mm)+":"+str(cons_ss)
           riba_ids_obj=riba_obj.browse(cr,uid,context['active_ids'],context=context)
               
        self.localcontext.update({
            'time': time,
            'cr':cr,
            'uid': uid,
            'nome_report':'fattura',
            'conta':60,
            'get_conta': self._get_conta,
            'partner_ids_id':partner_ids_id,
            'get_righe': self.get_righe,           
            'get_numeff': self.get_num_effetti,           
            'cons_ora':  cons_ora,
            'get_line_eff':self.get_line_eff,
            'get_data':self._get_data,
            'get_data_fatt':self.get_data_fatt,
            'cons_data':   datetime.strptime(str(data_oggi),"%Y-%m-%d %H:%M:%S.%f").strftime("%d/%m/%Y")

        })
        
report_sxw.report_sxw('report.rocco_ext_banca.distinta.bancaria.print',
                       'riba.distinta', 
                       'addons/rocco_ext_banca/report/distinta_bancaria.mako',
                       parser=distinta_bancaria_print)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
