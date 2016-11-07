# coding: utf-8
import time
import datetime
import openerp
from openerp.addons import web
from openerp.addons.web import http
#from openerp.addons.web.http import request
from openerp.http import request #as req_2
import xml.etree.ElementTree as ET
import base64
try:
    import simplejson as json
except ImportError:
    import json
import logging
import pprint
import urllib2
import werkzeug
import openerp.addons.decimal_precision as dp
from openerp.modules import get_module_resource
from cStringIO import StringIO
from openerp.addons.web.controllers.main import WebClient
from openerp.http import request, STATIC_CACHE
from openerp.tools import image_save_for_web
from openerp import api
from openerp.addons.website.models import website
from openerp import tools
from openerp.modules import get_module_resource
import functools
MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT = IMAGE_LIMITS = (1024, 768)
LOC_PER_BLOG_RSS = 45000
BLOG_RSS_CACHE_TIME = datetime.timedelta(minutes=1)
_logger = logging.getLogger(__name__)


class WebsiteBlogProduct(http.Controller):
    def create_product_rss(self, url, content):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        ira = request.registry['ir.attachment']
        #mimetype = 'application/xml;charset=utf-8'
        mimetype = 'application/xml'
        ira.create(cr, uid, dict(
            datas=content.encode('base64'),
            mimetype=mimetype,
            type='binary',
            name=url,
            url=url,
        ), context=context)

    # TODO Rewrite this method to be generic and innheritable for any model
    @http.route(['/product_rss_ru_RU_1.xml', "/blog/<model('blog.blog'):blog>/rss.xml"],
                type='http', auth="public", website=True)
    def rss_xml_index(self, blog=False):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        ira = request.registry['ir.attachment']
        iuv = request.registry['ir.ui.view']
        user_obj = request.registry['res.users']
        blog_obj = request.registry['blog.blog']
        config_obj = request.registry['ir.config_parameter']
        try:
            blog_ids = blog.ids
        except AttributeError:
            blog_ids = blog_obj.search(cr, uid, [], context=context)

        user_brw = user_obj.browse(cr, uid, [uid], context=context)
        blog_post_obj = request.registry['blog.post']
        #mimetype = 'application/xml;charset=utf-8'
        mimetype = 'application/xml'
        content = None
        blog_rss = ira.search_read(cr, uid, [
            ('name', '=', '/product_rss.xml'),
            ('type', '=', 'binary')],
            ('datas', 'create_date'), context=context)
        if blog_rss:
            # Check if stored version is still valid
            server_format = openerp.tools.misc.DEFAULT_SERVER_DATETIME_FORMAT
            create_date = datetime.datetime.strptime(
                blog_rss[0]['create_date'], server_format)
            delta = datetime.datetime.now() - create_date
            if delta < BLOG_RSS_CACHE_TIME:
                content = blog_rss[0]['datas'].decode('base64')

        if not content:
            # Remove all RSS in ir.attachments as we're going to regenerate
            product_rss_ids = ira.search(cr, uid, [
                ('name', '=like', '/prodcut_rss%.xml'),
                ('type', '=', 'binary')], context=context)
            if blog_rss_ids:
                ira.unlink(cr, uid, blog_rss_ids, context=context)

            pages = 0
            first_page = None
            values = {}
            post_domain = [('website_published', '=', True)]
            if blog_ids:
                post_domain += [("blog_id", "in", blog_ids)]
            post_ids = blog_post_obj.search(cr, uid, post_domain)
            values['posts'] = blog_post_obj.browse(cr, uid, post_ids, context)
            if blog_ids:
                blog = blog_obj.browse(cr, uid, blog_ids, context=context)[0]
                values['blog'] = blog
            values['company'] = user_brw[0].company_id
            values['website_url'] = config_obj.get_param(
                cr,
                uid,
                'web.base.url')
            values['url_root'] = request.httprequest.url_root
            urls = iuv.render(cr, uid, 'rocco_blog_rss.product_rss_locs',
                              values, context=context)
            if urls:
                page = iuv.render(cr, uid, 'rocco_blog_rss.product_rss_xml',
                                  dict(content=urls), context=context)
                if not first_page:
                    first_page = page
                pages += 1
                self.create_product_rss('/product_rss-%d.xml' % pages, page)
            if not pages:
                return request.not_found()
            elif pages == 1:
                content = first_page
        return request.make_response(content, [('Content-Type', mimetype)])

    @http.route('/blog/product/get', type='http', auth='none', methods=['GET'])
    def domain_product_get(self, **get):
        """ product get """
        _logger.info('product %s', pprint.pformat(get))  # debug
        new_get = dict(get)
        return self.rss_product(new_get)
    @http.route('/blog/product/post', type='http', auth='public', methods=['POST'])
    def domain_product_post(self, **post):
        """ product post """
        _logger.info('product %s', pprint.pformat(post))  # debug
        new_post = dict(post)
        return self.rss_product(new_post)
    def get_price(self, pricelist_id, product_id):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        uid=openerp.SUPERUSER_ID
        price_digits = dp.get_precision('Product Price')
        pricelist = request.registry.get('product.pricelist').browse(cr, uid, [pricelist_id], context=context)[0]
        price_dict = request.registry.get('product.pricelist').price_get(cr, uid, [pricelist_id], product_id, 0.0,partner=None, context=context)
        return price_dict[pricelist_id]

    def rss_product(self, new_get={'lang':None,'partner_id':None,'page_id':0}):
        cr, uid, context = request.cr, request.uid, request.context
        uid=openerp.SUPERUSER_ID
        lang=new_get.get('lang','it_IT').decode('utf-8').encode('utf-8')
        partner_id=int(new_get.get('partner_id',1))#.decode('utf-8').encode('utf-8'))
        page_id=int(new_get.get('page_id',1))#.decode('utf-8').encode('utf-8'))
        print 'entrata_mia_logistica',uid,openerp.SUPERUSER_ID,lang,partner_id,page_id,context

        if context==None:
            context={}
        context['lang']=lang
        print 'context',context
        date_today=time.strftime('%Y-%m-%d')
        db_name = cr.dbname
        product_obj = request.registry.get('product.product')
        warehouse_obj = request.registry.get('stock.warehouse')
        stock_move_obj = request.registry.get('stock.move')
        product_site_export_obj = request.registry.get('product.site.export')                
        pricelist_obj = request.registry.get('product.pricelist')
        pricelist_version_obj = request.registry.get('product.pricelist.version')
        pricelist_item_obj = request.registry.get('product.pricelist.item')
        partner_obj = request.registry.get('res.partner')
        user_obj = request.registry.get('res.users')
        user_id_obj=user_obj.browse(cr,uid,uid,context=context)
        partner_company_id=user_id_obj.company_id.partner_id.id
        prod_ids=None
        warehouse_ids=None
        partner_id_obj=partner_obj.browse(cr,uid,partner_id,context=context)
        request_xml ='<?xml version="1.0" encoding="utf-8" ?><root><pagine><CurPage>'+ str(page_id) +'</CurPage><LastPage>1</LastPage><PageSize>100</PageSize><TotSize>6</TotSize><customer>'+str(partner_id)+'</customer></pagine><Products>'
        warehouse_id=True
        if warehouse_id:
                product_ids = product_obj.search(cr, uid, [('active','=', True)])    
                
                conta=0
                
                for product_id in product_ids:
                            conta+=1
                            if page_id==1:
                                if conta>100:
                                    continue
                            elif page_id==2:
                                if conta<=100 and conta>200:
                                    continue
                            elif page_id==3:
                                if conta<=200 and conta>300:
                                    continue
                            elif page_id==4:
                                if conta<=300 and conta>400:
                                    continue
                            elif page_id==5:
                                if conta<=400 and conta>500:
                                    continue
                            elif page_id>5:
                                if conta<500:
                                    continue
                                
                    
                            product_id_obj=product_obj.browse(cr,uid,product_id,context=context)
                            if product_id_obj.default_code:
                                prod_ids_rec=product_id_obj
                                #price_surcharge = pricelist_obj.price_get(cr, uid, [partner_id_obj.property_product_pricelist.id],prod_ids_rec.id, 1.0, partner_id, {'uom': prod_ids_rec.uom_id.id,'date': date_today}) [partner_id_obj.property_product_pricelist.id]
                                price_surcharge = self.get_price(partner_id_obj.property_product_pricelist[0].id,prod_ids_rec.id)
    
                                try:
                                            codice=str(prod_ids_rec.default_code).replace("è", "e'").replace("à", "a'").replace("ù", "u'").replace("É", "E").replace("È", "E").replace("À", "A").replace("Ù", "U")
                                            nome=str(prod_ids_rec.name).replace("è", "e'").replace("à", "a'").replace("ù", "u'").replace("É", "E").replace("È", "E").replace("À", "A").replace("Ù", "U")
                                            codice=codice.decode('ascii', 'ignore').encode('utf-8')
                                            nome=nome.decode('ascii', 'ignore').encode('utf-8')
                                except:
                                            #nome='Errore codifica unicode'
                                            nome=u'{string}'.format(string=nome or '')
                                            #codice=str(prod_ids_rec.default_code).decode('ascii', 'ignore').encode('utf-8')
                                            codice=u'{string}'.format(string=codice or '')
                                try:
                                    categoria=prod_ids_rec.categ_id.name
                                    if prod_ids_rec.categ_id:
                                            categoria=str(prod_ids_rec.categ_id.name).decode('ascii', 'ignore').encode('utf-8')
                                    else:
                                            categoria=''.decode('ascii', 'ignore').encode('utf-8')
                                except:
                                    categoria=u'{string}'.format(string=categoria or '')
                                    #categoria='errore unicode'
                                try:
                                    Categoria_padre=prod_ids_rec.categ_id.parent_id.name
                                    if prod_ids_rec.categ_id.parent_id:
                                            Categoria_padre=str(prod_ids_rec.categ_id.parent_id.name).decode('ascii', 'ignore').encode('utf-8')
                                    else:
                                            Categoria_padre=''.decode('ascii', 'ignore').encode('utf-8')
                                except:
                                    Categoria_padre=u'{string}'.format(string=Categoria_padre or '')
                                    #Categoria_padre='errore unicode'
                                attributo=''
                                for attribute_values_id in prod_ids_rec.attribute_value_ids:
                                    attributo+=attribute_values_id.name
                                #"'data:image/png;base64,%s' % get_image(p['id'])"
                                try:
                                    attributo=attributo.decode('utf-8')
                                    attributo=attributo.decode('ascii', 'ignore')
                                    #attributo=attributo.replace("è", "e'").replace("à", "a'").replace("ù", "u'").replace("É", "E").replace("È", "E").replace("À", "A").replace("Ù", "U")
                                except:
                                    attributo=u'{string}'.format(string=attributo or '')
                                    attributo='-'
                                request_xml =request_xml+"<Product><Code>"+codice.replace("&", "")+"</Code><AvailableQty>"+str(str(prod_ids_rec.virtual_available)).decode('ascii', 'ignore').encode('utf-8')+"</AvailableQty><Nome-Brand-Variante>"+nome.replace("&" or "ù" or "®", "")+"</Nome-Brand-Variante><category>"+categoria+"</category><manufacturer>"+Categoria_padre+"</manufacturer><Price>"+str(price_surcharge)+"</Price><attibute>" + attributo + "</attibute><binary>" + str(prod_ids_rec.image) + "</binary></Product>" 
        request_xml =request_xml+"</Products></root>"            
        #print request
        """
        request.decode('utf-8')
        request.decode('ascii', 'ignore')
        """
        #request.encode('utf-8')
        """
        xml_root = ET.fromstring(request)
        """
        #send_request(site_ids.name_site,request,context)
        #print request
        #mimetype = 'application/xml;charset=utf-8'
        mimetype = 'application/xml'
        return request.make_response(request_xml, [('Content-Type', mimetype)])

class Binary(http.Controller):
            #Do not touch _name it must be same as _inherit
            #_name = 'Binary'
    @http.route([
        '/logo_2.png',
        '/logo_2',
        '/page/site_mm/logo_2.png',
    ], type='http', auth="none", cors="*", methods=['get'])
    def company_logo_get(self, dbname=None, **kw):
        #res=super(Binary, self).company_logo( dbname=dbname, kw=kw)
        #print 'company_logo_mm'#,self.context
        wiew_obj=request.registry['ir.ui.view']
        if not request.uid:
                wiew_obj._auth_method_public()

        _logger.info('company_logo_get %s', pprint.pformat(kw))  # debug

        new_get = dict(kw)
        imgname = 'logo.png'
        placeholder = functools.partial(get_module_resource, 'web', 'static', 'src', 'img')
        uid = None
        if request.session.db:
            dbname = request.session.db
            uid = request.session.uid
        elif dbname is None:
            dbname = db_monodb()

        if not uid:
            uid = openerp.SUPERUSER_ID

        if new_get.get('company_id',None):
            company_id=new_get.get('company_id',None)
        else:
            user_obj=request.registry['res.users'].browse(request.cr, uid,uid,context=request.context)
            company_id=user_obj.company_id.id
        if not dbname:
            response = http.send_file(placeholder(imgname))
        else:
            try:
                # create an empty registry
                registry = openerp.modules.registry.Registry(dbname)
                with registry.cursor() as cr:
                    cr.execute("""SELECT c.logo_web, c.write_date
                                    FROM res_users u
                               LEFT JOIN res_company c
                                      ON c.id = %s
                                   WHERE u.id = %s 
                               """, (company_id,uid))
                    row = cr.fetchone()
                    if row and row[0]:
                        image_data = StringIO(str(row[0]).decode('base64'))
                        response = http.send_file(image_data, filename=imgname, mtime=row[1])
                    else:
                        response = http.send_file(placeholder('nologo.png'))
            except Exception:
                response = http.send_file(placeholder(imgname))

        return response

    @http.route([
        '/logo_2.png',
        '/logo_2',
        '/page/site_mm/logo_2.png',
    ], type='http', auth="none", cors="*", methods=['POST'])
    def company_logo_post(self, dbname=None, **kw):
        #res=super(Binary, self).company_logo( dbname=dbname, kw=kw)
        #print 'company_logo_mm'#,self.context
        _logger.info('get %s', pprint.pformat(kw))  # debug

        new_get = dict(kw)
        imgname = 'logo.png'
        placeholder = functools.partial(get_module_resource, 'web', 'static', 'src', 'img')
        uid = None
        if request.session.db:
            dbname = request.session.db
            uid = request.session.uid
        elif dbname is None:
            dbname = db_monodb()

        if not uid:
            uid = openerp.SUPERUSER_ID

        if new_get.get('company_id',None):
            company_id=new_get.get('company_id',None)
        else:
            user_obj=request.registry['res.users'].browse(request.cr, uid,uid,context=request.context)
            company_id=user_obj.company_id.id
        if not dbname:
            response = http.send_file(placeholder(imgname))
        else:
            try:
                # create an empty registry
                registry = openerp.modules.registry.Registry(dbname)
                with registry.cursor() as cr:
                    cr.execute("""SELECT c.logo_web, c.write_date
                                    FROM res_users u
                               LEFT JOIN res_company c
                                      ON c.id = %s
                                   WHERE u.id = %s 
                               """, (company_id,uid))
                    row = cr.fetchone()
                    if row and row[0]:
                        image_data = StringIO(str(row[0]).decode('base64'))
                        response = http.send_file(image_data, filename=imgname, mtime=row[1])
                    else:
                        response = http.send_file(placeholder('nologo.png'))
            except Exception:
                response = http.send_file(placeholder(imgname))

        return response

    @http.route([
        '/page/site_mm/logo_mm.png',
        '/logo_mm',
        '/logo_mm.png',
    ], type='http', auth="none", cors="*")
    def company_logo_mm(self, dbname=None, **kw):
        #res=super(Binary, self).company_logo( dbname=dbname, kw=kw)
        #print 'company_logo_mm'#,self.context
        imgname = 'logo.png'
        placeholder = functools.partial(get_module_resource, 'web', 'static', 'src', 'img')
        uid = None
        if request.session.db:
            dbname = request.session.db
            uid = request.session.uid
        elif dbname is None:
            dbname = db_monodb()

        if not uid:
            uid = openerp.SUPERUSER_ID

        if request.context.get('company_id',None):
            company_id=request.context.get('company_id',None)
        else:
            user_obj=request.registry['res.users'].browse(request.cr, uid,uid,context=request.context)
            company_id=user_obj.company_id.child_ids[0].id
        if not dbname:
            response = http.send_file(placeholder(imgname))
        else:
            try:
                # create an empty registry
                registry = openerp.modules.registry.Registry(dbname)
                with registry.cursor() as cr:
                    cr.execute("""SELECT c.logo_web, c.write_date
                                    FROM res_users u
                               LEFT JOIN res_company c
                                      ON c.id = %s
                                   WHERE u.id = %s 
                               """, (company_id,uid))
                    row = cr.fetchone()
                    if row and row[0]:
                        image_data = StringIO(str(row[0]).decode('base64'))
                        response = http.send_file(image_data, filename=imgname, mtime=row[1])
                    else:
                        response = http.send_file(placeholder('nologo.png'))
            except Exception:
                response = http.send_file(placeholder(imgname))

        return response


class website_site_mm(openerp.addons.web.controllers.main.Home):
    
    @http.route(['/page/site_mm','/page/site_mm/homepage'], type='http', auth='public', website=True)
    def site_mm_index(self, **kw):
        _logger.info('site_mm_index %s', pprint.pformat(kw))  # debug
        page='homepage'
        iuv = request.registry['ir.ui.view']
        try:
            main_menu = request.registry['ir.model.data'].get_object(request.cr, request.uid, 'rocco_blog_rss', 'main_menu_mm')
            company_id=main_menu.website_id.company_id.id
            res_company=main_menu.website_id.company_id
            request.context['company_id'] = company_id
            request.context['res_company'] = res_company
        except Exception:
            pass
        else:
            first_menu = main_menu.child_id and main_menu.child_id[0]
        #'website.layout'
        
        resp=iuv.x_render(request.cr,request.uid,'rocco_blog_rss.homepage_mm',
                     values=
                     {'company_id':company_id,'res_company':res_company,
        },engine='ir.qweb',context=request.context)
        #resp=self.page([page,company_id,res_company])                    
        return resp
        #return http.request.render('rocco_blog_rss.homepage_site_mm_1', {'context':request.context,
        #    'Contatti': ["Alberto Carducci", "Marina Venturi", "Luca Carducci"],
        #})

    @http.route('/page/site_mm_old', type='http', auth="public", website=True)
    def site_mm_index_old(self, **kw):
        iuv = request.registry['ir.ui.view']
        page = 'homepage_site_mm_1'
        try:
            main_menu = request.registry['ir.model.data'].get_object(request.cr, request.uid, 'rocco_blog_rss', 'main_menu_mm')
            company_id=main_menu.website_id.company_id.id
            res_company=main_menu.website_id.company_id
            request.context['company_id'] = company_id
            request.context['res_company'] = res_company
        except Exception:
            pass
        else:
            first_menu = main_menu.child_id and main_menu.child_id[0]
            if first_menu:
                if first_menu.url and (not (first_menu.url.startswith(('/page/site_mm/', '/?', '/#')) or (first_menu.url == '/'))):
                            context=request.context
                            #return iuv.x_render(request.cr,request.uid,'website.homepage',values={},engine='ir.qweb',context=context)
                            request.context
                            resp=request.redirect(first_menu.url)
                            pprint.pformat(resp)
                            resp.qcontext['company_id'] = company_id
                            resp.qcontext['res_company'] = res_company
                            resp.qcontext.templates('rocco_blog_rss.homepage_site_mm')

                            return resp
                if first_menu.url and first_menu.url.startswith('/site_mm/page/'):
                    context=request.context
                    context['company_id']=company_id
                    #return iuv.x_render(request.cr,request.uid,'website.homepage',values={},engine='ir.qweb',context=context)
                    
                    resp=request.registry['ir.http'].reroute(first_menu.url)
                    resp.qcontext['company_id'] = company_id
                    resp.qcontext['res_company'] = res_company
                    pprint.pformat(resp)
                    return resp
        #self.context = self.params.pop('context', dict(self.session.context))
        resp=self.page([page,company_id,res_company])
        return resp
    #@http.route('/page/site_mm_test/<page:page>', type='http', auth="public", website=True)
    def page_old(self, page, **opt):
        #qcontext = self.get_auth_signup_qcontext()
        #qcontext['company_id'] = opt['company_id']
        #qcontext['res_company'] = opt['res_company']
        if hasattr(page, '__iter__'):
            page=page
        else:
            uid = openerp.SUPERUSER_ID
            user_obj=request.registry['res.users'].browse(request.cr, uid,uid,context=request.context)
            company_id=user_obj.company_id.id
            page=[page]
            page.append(company_id)
            page.append(user_obj.company_id)
 
        #super(website_site_mm, self).page(page, **opt)
        values = {
            'path': page[0],
            'company_id':page[1],
            'res_company':page[2]
        }
        # /page/website.XXX --> /page/XXX
        if page[0].startswith('website.'):
            return request.redirect('/page/' + page[0][8:], code=301)
        elif '.' not in page[0]:
            page[0] = 'website.%s' % page[0]

        try:
            request.website.get_template(page[0])
        except ValueError, e:
            # page not found
            if request.website.is_publisher():
                page[0] = 'website.page_404'
            else:
                return request.registry['ir.http']._handle_exception(e, 404)

        request.context['company_id']=page[1]
        request.context['res_company']=page[2]
        return request.render(page[0], values)
from openerp.addons import website_sale

PPG = 20 # Products Per Page
PPR = 4  # Products Per Row
class table_compute(openerp.addons.website_sale.controllers.main.table_compute):
    def test(self):
        self.table = {}

class QueryURL(openerp.addons.website_sale.controllers.main.QueryURL):
    def test(self, test='', **args):
        self.test = test
        self.args = args
def get_pricelist():
    cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
    sale_order = context.get('sale_order')
    if sale_order:
        pricelist = sale_order.pricelist_id
    else:
        partner = pool['res.users'].browse(cr, SUPERUSER_ID, uid, context=context).partner_id
        pricelist = partner.property_product_pricelist
    if not pricelist:
        _logger.error('Fail to find pricelist for partner "%s" (id %s)', partner.name, partner.id)
    return pricelist
    

class website_sale(openerp.addons.website_sale.controllers.main.website_sale):

    @http.route([
        '/page/site_mm/shop',
        '/page/site_mm/shop/page/<int:page>',
        '/page/site_mm/shop/category/<model("product.public.category"):category>',
        '/page/site_mm/shop/category/<model("product.public.category"):category>/page/<int:page>'
    ], type='http', auth="public", website=True)
    def site_mm_shop(self, page=0, category=None, search='', **post):
        _logger.info('site_mm_shop_post %s', pprint.pformat(post))  # debug
        _logger.info('site_mm_shop %s', pprint.pformat(request.website.company_id.name))  # debug
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        try:
            main_menu = request.registry['ir.model.data'].get_object(request.cr, request.uid, 'rocco_blog_rss', 'main_menu_mm')
            company_id=main_menu.website_id.company_id.id
            res_company=main_menu.website_id.company_id
            request.context['company_id'] = company_id
            request.context['res_company'] = res_company
            post['company_id']=company_id
            post['res_company']=res_company
        except Exception:
            pass
        

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [map(int, v.split("-")) for v in attrib_list if v]
        attrib_set = set([v[1] for v in attrib_values])

        domain = self._get_search_domain(search, category, attrib_values)

        keep = QueryURL('/shop', category=category and int(category), search=search, attrib=attrib_list)

        if not context.get('pricelist'):
            pricelist = self.get_pricelist()
            context['pricelist'] = int(pricelist)
        else:
            pricelist = pool.get('product.pricelist').browse(cr, uid, context['pricelist'], context)

        product_obj = pool.get('product.template')

        url = "/shop"
        product_count = product_obj.search_count(cr, uid, domain, context=context)
        if search:
            post["search"] = search
        if category:
            category = pool['product.public.category'].browse(cr, uid, int(category), context=context)
            url = "/shop/category/%s" % slug(category)
        if attrib_list:
            post['attrib'] = attrib_list
        pager = request.website.pager(url=url, total=product_count, page=page, step=PPG, scope=7, url_args=post)
        product_ids = product_obj.search(cr, uid, domain, limit=PPG, offset=pager['offset'], order='website_published desc, website_sequence desc', context=context)
        products = product_obj.browse(cr, uid, product_ids, context=context)

        style_obj = pool['product.style']
        style_ids = style_obj.search(cr, uid, [], context=context)
        styles = style_obj.browse(cr, uid, style_ids, context=context)

        category_obj = pool['product.public.category']
        category_ids = category_obj.search(cr, uid, [('parent_id', '=', False)], context=context)
        categs = category_obj.browse(cr, uid, category_ids, context=context)

        attributes_obj = request.registry['product.attribute']
        attributes_ids = attributes_obj.search(cr, uid, [], context=context)
        attributes = attributes_obj.browse(cr, uid, attributes_ids, context=context)

        from_currency = pool.get('product.price.type')._get_field_currency(cr, uid, 'list_price', context)
        to_currency = pricelist.currency_id
        compute_currency = lambda price: pool['res.currency']._compute(cr, uid, from_currency, to_currency, price, context=context)

        values = {
            'company_id': company_id,
            'res_company': res_company,
            'search': search,
            'category': category,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'pager': pager,
            'pricelist': pricelist,
            'products': products,
            'bins': table_compute().process(products),
            'rows': PPR,
            'styles': styles,
            'categories': categs,
            'attributes': attributes,
            'compute_currency': compute_currency,
            'keep': keep,
            'style_in_product': lambda style, product: style.id in [s.id for s in product.website_style_ids],
            'attrib_encode': lambda attribs: werkzeug.url_encode([('attrib',i) for i in attribs]),
        }
        return request.website.render("website_sale.products", values)

    @http.route(['/page/site_mm/shop/product/<model("product.template"):product>'], type='http', auth="public", website=True)
    def site_mm_product(self, product, category='', search='', **kwargs):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        try:
            main_menu = request.registry['ir.model.data'].get_object(request.cr, request.uid, 'rocco_blog_rss', 'main_menu_mm')
            company_id=main_menu.website_id.company_id.id
            res_company=main_menu.website_id.company_id
            request.context['company_id'] = company_id
            request.context['res_company'] = res_company
            kwargs['company_id']=company_id
            kwargs['res_company']=res_company
        except Exception:
            pass

        category_obj = pool['product.public.category']
        template_obj = pool['product.template']

        context.update(active_id=product.id)

        if category:
            category = category_obj.browse(cr, uid, int(category), context=context)
            category = category if category.exists() else False

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [map(int,v.split("-")) for v in attrib_list if v]
        attrib_set = set([v[1] for v in attrib_values])

        keep = QueryURL('/shop', category=category and category.id, search=search, attrib=attrib_list)

        category_ids = category_obj.search(cr, uid, [], context=context)
        category_list = category_obj.name_get(cr, uid, category_ids, context=context)
        category_list = sorted(category_list, key=lambda category: category[1])

        pricelist = self.get_pricelist()

        from_currency = pool.get('product.price.type')._get_field_currency(cr, uid, 'list_price', context)
        to_currency = pricelist.currency_id
        compute_currency = lambda price: pool['res.currency']._compute(cr, uid, from_currency, to_currency, price, context=context)

        if not context.get('pricelist'):
            context['pricelist'] = int(self.get_pricelist())
            product = template_obj.browse(cr, uid, int(product), context=context)

        values = {
            'company_id': company_id,
            'res_company': res_company,
            'search': search,
            'category': category,
            'pricelist': pricelist,
            'attrib_values': attrib_values,
            'compute_currency': compute_currency,
            'attrib_set': attrib_set,
            'keep': keep,
            'category_list': category_list,
            'main_object': product,
            'product': product,
            'get_attribute_value_ids': self.get_attribute_value_ids
        }
        return request.website.render("website_sale.product", values)

    @http.route(['/page/site_mm/shop/product/comment/<int:product_template_id>'], type='http', auth="public", website=True)
    def site_mm_product_comment(self, product_template_id, **post):
        if not request.session.uid:
            return login_redirect()
        cr, uid, context = request.cr, request.uid, request.context
        try:
            main_menu = request.registry['ir.model.data'].get_object(request.cr, request.uid, 'rocco_blog_rss', 'main_menu_mm')
            company_id=main_menu.website_id.company_id.id
            res_company=main_menu.website_id.company_id
            context['company_id']=company_id
            context['res_company']=res_company
        except Exception:
            pass
        if post.get('comment'):
            request.registry['product.template'].message_post(
                cr, uid, product_template_id,
                body=post.get('comment'),
                type='comment',
                subtype='mt_comment',
                context=dict(context, mail_create_nosubscribe=True))
        return werkzeug.utils.redirect('/page/site_mm/shop/product/%s#comments' % product_template_id)

    @http.route(['/page/site_mm/shop/pricelist'], type='http', auth="public", website=True)
    def site_mm_pricelist(self, promo, **post):
        cr, uid, context = request.cr, request.uid, request.context
        request.website.sale_get_order(code=promo, context=context)
        return request.redirect("/page/site_mm/shop/cart")

from openerp.addons import website_crm
class website_crm(openerp.addons.website_crm.controllers.main.contactus):
    @http.route(['/page/site_mm/website.contactus', '/page/site_mm/contactus'], type='http', auth="public", website=True)
    def site_mm_contact(self, **kwargs):
        _logger.info('site_mm_contact %s', pprint.pformat(kwargs))  # debug
        page='contactus_mm'
        iuv = request.registry['ir.ui.view']
        try:
            main_menu = request.registry['ir.model.data'].get_object(request.cr, request.uid, 'rocco_blog_rss', 'main_menu_mm')
            company_id=main_menu.website_id.company_id.id
            res_company=main_menu.website_id.company_id
            request.context['company_id'] = company_id
            request.context['res_company'] = res_company
        except Exception:
            pass
        else:
            first_menu = main_menu.child_id and main_menu.child_id[0]
        #'website.layout'
        """
        resp=iuv.x_render(request.cr,request.uid,'rocco_blog_rss.contactus_mm',
                     values=
                     {'company_id':company_id,'res_company':res_company,
        },engine='ir.qweb',context=request.context)
        """
        values = {}
        for field in ['description', 'partner_name', 'phone', 'contact_name', 'email_from', 'name']:
            if kwargs.get(field):
                values[field] = kwargs.pop(field)
        values.update(kwargs=kwargs.items())
        values['company_id']=company_id
        values['res_company']=res_company
        return request.website.render("rocco_blog_rss.contactus_mm", values)
        #return super(website_crm, self).contact(kwargs=kwargs)
    def get_contactus_response_mm(self, values, kwargs):
        values = self.preRenderThanks(values, kwargs)
        """ inizio id site_mm """
        try:
            main_menu = request.registry['ir.model.data'].get_object(request.cr, request.uid, 'rocco_blog_rss', 'main_menu_mm')
            company_id=main_menu.website_id.company_id.id
            res_company=main_menu.website_id.company_id
            request.context['company_id'] = company_id
            request.context['res_company'] = res_company
            values['company_id']=company_id
            values['res_company']=res_company
        except Exception:
            pass
        """ fine  id site mm """
        return request.website.render(kwargs.get("view_callback", "rocco_blog_rss.contactus_thanks_mm"), values)
    @http.route(['/page/site_mm/crm/contactus'], type='http', auth="public", website=True)
    def contactus_mm(self, **kwargs):
        def dict_to_str(title, dictvar):
            ret = "\n\n%s" % title
            for field in dictvar:
                ret += "\n%s" % field
            return ret

        _TECHNICAL = ['show_info', 'view_from', 'view_callback']  # Only use for behavior, don't stock it
        _BLACKLIST = ['id', 'create_uid', 'create_date', 'write_uid', 'write_date', 'user_id', 'active']  # Allow in description
        _REQUIRED = ['name', 'contact_name', 'email_from', 'description']  # Could be improved including required from model

        post_file = []  # List of file to add to ir_attachment once we have the ID
        post_description = []  # Info to add after the message
        values = {}

        values['medium_id'] = request.registry['ir.model.data'].xmlid_to_res_id(request.cr, SUPERUSER_ID, 'crm.crm_medium_website')
        values['section_id'] = request.registry['ir.model.data'].xmlid_to_res_id(request.cr, SUPERUSER_ID, 'website.salesteam_website_sales')
        for field_name, field_value in kwargs.items():
            if hasattr(field_value, 'filename'):
                post_file.append(field_value)
            elif field_name in request.registry['crm.lead']._fields and field_name not in _BLACKLIST:
                values[field_name] = field_value
            elif field_name not in _TECHNICAL:  # allow to add some free fields or blacklisted field like ID
                post_description.append("%s: %s" % (field_name, field_value))

        if "name" not in kwargs and values.get("contact_name"):  # if kwarg.name is empty, it's an error, we cannot copy the contact_name
            values["name"] = values.get("contact_name")
        # fields validation : Check that required field from model crm_lead exists
        error = set(field for field in _REQUIRED if not values.get(field))

        if error:
            values = dict(values, error=error, kwargs=kwargs.items())
            return request.website.render(kwargs.get("view_from", "rocco_blog_rss.contactus_mm"), values)

        # description is required, so it is always already initialized
        if post_description:
            values['description'] += dict_to_str(_("Custom Fields: "), post_description)

        if kwargs.get("show_info"):
            post_description = []
            environ = request.httprequest.headers.environ
            post_description.append("%s: %s" % ("IP", environ.get("REMOTE_ADDR")))
            post_description.append("%s: %s" % ("USER_AGENT", environ.get("HTTP_USER_AGENT")))
            post_description.append("%s: %s" % ("ACCEPT_LANGUAGE", environ.get("HTTP_ACCEPT_LANGUAGE")))
            post_description.append("%s: %s" % ("REFERER", environ.get("HTTP_REFERER")))
            values['description'] += dict_to_str(_("Environ Fields: "), post_description)

        lead_id = self.create_lead(request, dict(values, user_id=False), kwargs)
        values.update(lead_id=lead_id)
        if lead_id:
            for field_value in post_file:
                attachment_value = {
                    'name': field_value.filename,
                    'res_name': field_value.filename,
                    'res_model': 'crm.lead',
                    'res_id': lead_id,
                    'datas': base64.encodestring(field_value.read()),
                    'datas_fname': field_value.filename,
                }
                request.registry['ir.attachment'].create(request.cr, SUPERUSER_ID, attachment_value, context=request.context)

        return self.get_contactus_response_mm(values, kwargs)    