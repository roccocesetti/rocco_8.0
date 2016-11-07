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
from openerp.tools.translate import _
import base64
from tempfile import TemporaryFile
from openerp import tools
from openerp.osv import osv, fields
from lxml import etree
import openerp.pooler as pooler
import openerp.sql_db as sql_db
from datetime import datetime, timedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
from openerp import netsvc
import openerp.addons.decimal_precision as dp
import xxsubtype
import itertools
from lxml import etree
from openerp import api

class rc_mrp_rtl_machine_tools(osv.osv):
    """ configurazione utensile"""

    _name = "rc.mrp.machine_tools"
    _description = "machine tools"
    _columns = {
        'name': fields.char('Nome Utenzile', size=64 , required=True),
        'speed_rm': fields.float('Velacita di rotazione del mandrino in giri al minuto'),
        'forward_tool_mg': fields.float('Avanzamento utenzile mellimetri/giro'),
        'active': fields.boolean('Attiva', required=False), 
     }
class rc_mrp_rtl_machine_tools_forwars(osv.osv):
    """ configurazione utensile"""

    _name = "rc.mrp.machine_tools.forwards"
    _description = "Parametri medi Avanzamento utenzile "
    _columns = {
        'name': fields.char('Avanzamento', size=64 , required=True),
        'out_sgrossa_min': fields.float('Esterna sgrossa min'),
        'out_sgrossa_max': fields.float('Esterna sgrossa max'),
        'out_finisce_min': fields.float('Esterna finisce min'),
        'out_finisce_max': fields.float('Esterna finisce max'),
        'in_sgrossa_min': fields.float('Interna sgrossa min'),
        'in_sgrossa_max': fields.float('Interna sgrossa max'),
        'in_finisce_min': fields.float('Interna  finisce min'),
        'in_finisce_max': fields.float('Interna  finisce max'),
        'formare_min': fields.float('Formare min'),
        'formare_max': fields.float('Formare max'),
        'troncare_min': fields.float('Troncare min'),
        'troncare_max': fields.float('Troncare  max'),
        'active': fields.boolean('Attiva', required=False), 
     }
    _defaults = {  
        'active': True,  
        }
class rc_mrp_rtl_machine_tools_centered(osv.osv):
    """ configurazione centrinatura utensile"""

    _name = "rc.mrp.machine_tools.centered"
    _description = "Parametri  Centrinatura utenzile "
    _columns = {
        'name': fields.char('Centrinatura', size=64 , required=True),
        'pezzo_diametro_min': fields.float('Diametro prezzo min'),
        'pezzo_diametro_max': fields.float('Diametro prezzo max'),
        'D_diametro': fields.float('Diametro centrino'),
        'L_centrino_A': fields.float('Profondità Centrino A'),
        'L_centrino_B': fields.float('Profondità Centrino B'),
        'active': fields.boolean('Attiva', required=False), 
     }
    _defaults = {  
        'active': True,  
        }
class rc_mrp_rtl_head(osv.osv):
    """ unione dei file plc per la rilevazione tempi delle macchine utenzili """

    _name = "rc.mrp.rtl.head"
    _description = "head rtl"
    _columns = {
        'name': fields.char('lavorazione', size=64 , required=True),
        'product_id':fields.many2one('product.product', 'Articolo', required=False), 
        'tool_id':fields.many2one('rc.mrp.machine_tools', 'macchina Utensile', required=True), 
        'forward_id':fields.many2one('rc.mrp.machine_tools.forwards', 'Avanzamento', required=True), 
        'centered_id':fields.many2one('rc.mrp.machine_tools.centered', 'Centratura', required=False), 
        'speed_rm': fields.float('Velocità di rotazione del mandrino in giri al minuto'),
        'forward_tool_mg': fields.float('Avanzamento utenzile mellimetri/giro'),
        'D_pezzo': fields.float('Diametro iniziale in mm'),
        'boby_ids':fields.one2many('rc.mrp.rtl.body', 'head_id', 'Dettaglio file plc', required=False),
        'format': fields.selection([('txt','txt File'),
                                        
                                       ], 'File Format', required=False),
         'state': fields.selection([('choose', 'choose'),   # choose language
                                       ('get', 'get')]),  
        #TODO : import time required to get currect datetime
        'datetime': fields.datetime('Data esecuzione'),       # get the file
        'data': fields.binary('File file plc', required=False),

     }
    _defaults = {  
        'name':'lav_'+str(datetime.today().strftime('%Y-%m-%d_%H:%M:%S')),
        'datetime': lambda *a: datetime.today().strftime('%Y-%m-%d %H:%M:%S'),  
        }
    def onchange_tool_id(self,cr, uid, ids, tool_id, context=None):
        tool_obj=self.pool.get('rc.mrp.machine_tools')
        if tool_id:
            tool_id_obj=tool_obj.browse(cr,uid,tool_id,context=context)
            return {'value':{'speed_rm': tool_id_obj.speed_rm,'forward_tool_mg': tool_id_obj.forward_tool_mg}}
        return {}
    def calc_diametro(self, cr, uid, ids, context=None):
        #TODO: process before updating resource
        body_obj=self.pool.get('rc.mrp.rtl.body')
        if hasattr(ids, '__iter__'):
             ids=ids
        else:
            ids[ids]
        for head_id_obj in self.browse(cr, uid, arg, context):
            for body_id_obj in boby_ids:
                    body_obj.import_file_plc
        
        return res 

class rc_mrp_rtl_body(osv.osv):
    """ rilevazione tempi macchine utensili"""

    _name = "rc.mrp.rtl.body"
    _description = "Dettaglio plc rilevazione tempi"
    _columns = {
        'name': fields.char('identificativo di  importazione', size=64 , required=True),
        'head_id':fields.many2one('rc.mrp.rtl.head', 'macchine Utensile', required=True), 
        'data': fields.binary('File plc', required=True),
        'text': fields.text('Nota Sostitutiva'),
        'time_rtl': fields.float('Tempo di lavorazione', digits_compute=dp.get_precision('Product Unit of Measure')), 
     }
    _defaults = {  
        'name': 'plc_'+str(datetime.today().strftime('%Y-%m-%d_%H:%M:%S')),  
        }
    def import_file_plc(self, cr, uid, ids, context=None):
        fileobj = TemporaryFile('w+')
        this = self.browse(cr, uid, ids[0])
        try:
            fileobj.write(base64.decodestring(this.data))
    
            # now we determine the file format
            self.load_data( cr, uid, ids ,fileobj, context=context)
        finally:
            fileobj.close()
        return True
	
    def load_data(self, cr, uid, ids, fileobj, fileformat,  context=None):
        cod_GS=['G0','G1','G2','G3','G4','G9'
               ,'G00','G01','G02','G03','G04','G09','G16','G17'
               ,'G18','G19','G27','G28','G29','G33','G40','G41','G42','G70'
               ,'G71','G72','G73','G74','G79','G80','G81','G82','G83','G84'
               ,'G85','G86','G89','G90','G91','G92','G93','G94','G95','G96','G97','G99']
        db_name = cr.dbname
        pool = pooler.get_pool(db_name)
        this = self.browse(cr, uid, ids[0])
        body_plc_obj=self.pool.get('rc.mrp.rtl.body.plc')
        date_today=datetime.today()
        try:
            fileobj.seek(0)
            line_str = fileobj.readline().strip()
            index=0
            fileobj.seek(index)
            lav_mandrino=[]
            while str(line_str).find("M30")<=0:
                        index+=1
                        fileobj.seek(index)
                        line_str = fileobj.readline().strip()
                        tipo_GS=[]
                        if str(line_str).find("G")>0:
                            for cod_G in cod_GS:
                                if str(line_str).find(cod_G)>0:
                                    tipo_GS.append(cod_G)
                 #posizionamento rapido degli assi
                        XX=None
                        YY=None
                        ZZ=None
                        FF=None
                        if str(line_str).find("X")>0:
                            XX=str(line_str).find("X")
                        if str(line_str).find("Y")>0:
                            YY=str(line_str).find("Y")
                        if str(line_str).find("Z")>0:
                            ZZ=str(line_str).find("Z")
                        if str(line_str).find("F")>0:
                            FF=str(line_str).find("F")
                        """ X """
                        if XX and YY:
                                X1=YY-XX
                        elif XX and ZZ:
                                X1=ZZ-XX
                        elif XX and FF:
                                X1=FF-XX
                        elif XX and (not YY and not ZZ and not FF):
                                X1=len(line_str)-XX
                        else:
                            X1=None
                        """ Y """
                        if YY and ZZ:
                                Y1=YY-ZZ
                        elif YY and FF:
                                Y1=FF-YY
                        elif YY and (not FF and not ZZ ):
                                Y1=len(line_str)-YY
                        else:
                            Y1=None
                        """ Z """
                        if ZZ and FF:
                                Z1=ZZ-FF
                        elif ZZ and not FF:
                                Z1=len(line_str)-ZZ
                        else:
                            Z1=None
                        """ F """
                        if FF:
                                F1=len(line_str)-FF
                        XYZF=[X1,Y1,Z1,F1]
                        vals={'body_id':ids[0],
                              'codes_ids':[[6, 0, tipo_GS]],
                              'XYZF':XYZF}
                        body_plc_obj.create(cr,uid,vals,context=context)
                #_logger.info("importazione effettuata con successo")
        except IOError:
            raise osv.except_osv(_("Impossibile leggere ilfile "), _(""))
class rc_mrp_rtl_body_plc_codes(osv.osv):
    """ rilevazione tempi macchine utensili codici"""

    _name = "rc.mrp.rtl.body.plc.codes"
    _description = "Dettaglio plc rilevazione tempi codici"
    _columns = {
        'name': fields.char('identificativo di  importazione', size=64 , required=True),
        'code': fields.char('codice', size=64 ),
                    }
    @api.model
    @api.returns('self', lambda value:value.id)
    def create(self, vals):
        if vals.get('code',None):
            vals['code']=vals['name']
        return osv.osv.create(self, vals)
class rc_mrp_rtl_body_plc_coodinate(osv.osv):
    """ rilevazione tempi macchine utensili codici"""

    _name = "rc.mrp.rtl.body.plc.assi"
    _description = "Dettaglio plc rilevazione tempi assi"
    _columns = {
        'name': fields.char('identificativo di  importazione', size=64 , required=True),
        'asse': fields.char('asse', size=64 ),
        'valore': fields.float('Valore', digits_compute=dp.get_precision('Product Unit of Measure')), 
                    }
    @api.model
    @api.returns('self', lambda value:value.id)
    def create(self, vals):
        if vals.get('asse',None):
            vals['asse']=vals['name']
        return osv.osv.create(self, vals)
class rc_mrp_rtl_body_plc(osv.osv):
    """ rilevazione tempi macchine utensili"""

    _name = "rc.mrp.rtl.body.plc"
    _description = "Dettaglio plc rilevazione tempi"
    _columns = {
        'name': fields.char('identificativo di  importazione', size=64 , required=True),
        'body_id':fields.many2one('rc.mrp.rtl.body', 'body referense'), 
        'codes_ids': fields.many2many('rc.mrp.rtl.body.plc.codes', id1='plc_id', id2='cod_id', string='Variants', readonly=True),
        'coordinate_ids': fields.many2one('rc.mrp.rtl.body.plc.assi', 'Coordinate'),
        'ascissa_x': fields.float('ascissa X', digits_compute=dp.get_precision('Product Unit of Measure')), 
        'ordinata_y': fields.float('ordinata Y', digits_compute=dp.get_precision('Product Unit of Measure')), 
        'profondita_z': fields.float('profondita Z', digits_compute=dp.get_precision('Product Unit of Measure')), 
        'asse_B': fields.float('Asse B', digits_compute=dp.get_precision('Product Unit of Measure')), 
        'asse_C': fields.float('Asse C', digits_compute=dp.get_precision('Product Unit of Measure')), 
        'Velocita': fields.float('velocita A', digits_compute=dp.get_precision('Product Unit of Measure')), 
        'lunghezza': fields.float('Lunghezza L', digits_compute=dp.get_precision('Product Unit of Measure')), 
     }
    _defaults = {  
        'name': 'plc_'+str(datetime.today().strftime('%Y-%m-%d_%H:%M:%S')),  
        }

class rc_mrp_rtl_key(osv.osv):
    """ api key  prodotti da logistica"""

    _name = "rc.mrp.rtl.key"
    _description = "chiavi utilizzo calcolo del tempo di lavorazione"
    _columns = {
        'name': fields.char('name', size=128 , required=True),
        'apiuser': fields.char('apyuser', size=128 , required=True),
        'apikey': fields.char('apykey', size=128 , required=True),
        'apiconta': fields.integer('Contatotore'), 
        'data_key': fields.date('Data'), 
     }
    _defaults = {  
        'name': 'Ricevi apikey_apiuser',  
        'apiuser': '[-------------]',  
        'apikey': '[--------------]',  
        'data_key': lambda *a: time.strftime('%Y-%m-%d'),  
        }
    def key_active_call(self, cr, uid, ids=None,context=None):
        #import pdb; pdb.set_trace()
        if ids==None:
            ids=self.search(cr,uid,[('id','>',0)],context=context)
        if hasattr(ids, '__iter__'):
            ids=ids
        else:
            ids=[ids]
        fl_user=False
        fl_key=False
        apimsg=None
        for key_active_obj in self.browse(cr, uid, ids, context=context):
            try:
                    url = str('http://www.ideawork.it/check_module/apiserver.php')
                    http = httplib2.Http()
                    hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
           'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
           'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
           'Accept-Encoding': 'none',
           'Accept-Language': 'en-US,en;q=0.8',
           'Connection': 'keep-alive'}
                    #import pdb; pdb.set_trace()
                    request ='<customers><customer><apiuser>'+key_active_obj.apiuser+'</apiuser><apikey>'+key_active_obj.apikey+'</apikey></customer></customers>'
                    urequest = urllib2.Request(url+"?request="+request,headers=hdr)
                    uopen = urllib2.urlopen(urequest)
                    resp = uopen.read()

                    if resp:
                        root = ET.fromstring(resp)
                        fl_user=False
                        fl_key=False
                        for nodes in root.getchildren():
                            if nodes.tag!='customer':
                                continue
                            apikey=None
                            apiuser=None
                            apimsg=None
                            apidata=None
                            apiconta=None
                            for node in nodes.getchildren():
                                if node.tag=='apiuser':
                                   apiuser=node.text
                                if node.tag=='apikey':
                                   apikey=node.text
                                if node.tag=='apiconta':
                                   apiconta=int(node.text)
                                if node.tag=='apimsg':
                                   apimsg=node.text
                                if node.tag=='apidata':
                                   apidata=datetime.strptime(node.text,"%d/%m/%Y").strftime("%Y-%m-%d")
                                   data_today=str(datetime.today().date())
                                   if apiuser==key_active_obj.apiuser:
                                         #import pdb; pdb.set_trace()
                                         if apikey==key_active_obj.apikey:
                                             if apiconta==1:
                                                    fl_key=True
                                                    break
                                             else:
                                                if apidata>=data_today:
                                                    fl_key=True
                                                    break
                                                    
                                                else:
                                                    fl_key=False
                                                    break
                        if fl_key==False:
                            return {'apiflag':False,'apimsg':apimsg}
                            #raise osv.except_osv(_("Attenzione impossibile continuare il servizio è scaduto %s"), _("contattare l'amministratore"))
            except:
                        return {'apiflag':True,'apimsg':apimsg}                   
            #print 'fl_key--->',fl_key,apimsg
            #import pdb; pdb.set_trace()
            return {'apiflag':fl_key,'apimsg':apimsg}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
