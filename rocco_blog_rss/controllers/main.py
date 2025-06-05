# coding: utf-8
import time
import datetime
import openerp
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.http import request as req_2
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
from itertools import islice
from openerp.addons.web.controllers.main import WebClient
from openerp.http import request, STATIC_CACHE
from openerp.tools import image_save_for_web
import functools
from openerp.modules import get_module_resource
from openerp import tools
from cStringIO import StringIO
MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT = IMAGE_LIMITS = (1024, 768)
LOC_PER_BLOG_RSS = 45000
BLOG_RSS_CACHE_TIME = datetime.timedelta(minutes=1)
_logger = logging.getLogger(__name__)
SITEMAP_CACHE_TIME = datetime.timedelta(hours=12)
LOC_PER_SITEMAP = 45000
PPG = 20 # Products Per Page
PPR = 4  # Products Per Row

from openerp.addons.website_sale.controllers.main import table_compute
from openerp.addons.website_sale.controllers.main import QueryURL
from openerp.addons.website.models.website import slug
from openerp.addons.web.controllers.main import login_redirect

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
        cr, uid, context = req_2.cr, openerp.SUPERUSER_ID, req_2.context
        uid = openerp.SUPERUSER_ID 
        price_digits = dp.get_precision('Product Price')
        pricelist = req_2.registry.get('product.pricelist').browse(cr, uid, [pricelist_id], context=context)[0]
        price_dict = req_2.registry.get('product.pricelist').price_get(cr, uid, [pricelist_id], product_id, 0.0,partner=None, context=context)
        return price_dict[pricelist_id]

    def rss_product(self, new_get={'lang':None,'partner_id':None,'page_id':0}):
        cr, uid, context = req_2.cr, req_2.uid, req_2.context
        uid=openerp.SUPERUSER_ID
        lang=new_get.get('lang','it_IT').decode('utf-8').encode('utf-8')
        partner_id=int(new_get.get('partner_id',1))#.decode('utf-8').encode('utf-8'))
        page_id=int(new_get.get('page_id',1))#.decode('utf-8').encode('utf-8'))
        print 'entrata_mia_logistica',uid,openerp.SUPERUSER_ID,lang,partner_id,page_id,context

        if context is None:
            context={}
        context['lang']=lang
        print 'context',context
        date_today=time.strftime('%Y-%m-%d')
        db_name = cr.dbname
        product_obj = req_2.registry.get('product.product')
        warehouse_obj = req_2.registry.get('stock.warehouse')
        stock_move_obj = req_2.registry.get('stock.move')
        product_site_export_obj = req_2.registry.get('product.site.export')                
        pricelist_obj = req_2.registry.get('product.pricelist')
        pricelist_version_obj = req_2.registry.get('product.pricelist.version')
        pricelist_item_obj = req_2.registry.get('product.pricelist.item')
        partner_obj = req_2.registry.get('res.partner')
        user_obj = req_2.registry.get('res.users')
        user_id_obj=user_obj.browse(cr,uid,uid,context=context)
        partner_company_id=user_id_obj.company_id.partner_id.id
        prod_ids=None
        warehouse_ids=None
        partner_id_obj=partner_obj.browse(cr,uid,partner_id,context=context)
        request ='<?xml version="1.0" encoding="utf-8" ?><root><pagine><CurPage>'+ str(page_id) +'</CurPage><LastPage>1</LastPage><PageSize>100</PageSize><TotSize>6</TotSize><customer>'+str(partner_id)+'</customer></pagine><Products>'
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
                                request =request+"<Product><Code>"+codice.replace("&", "")+"</Code><AvailableQty>"+str(str(prod_ids_rec.virtual_available)).decode('ascii', 'ignore').encode('utf-8')+"</AvailableQty><Nome-Brand-Variante>"+nome.replace("&" or "ù" or "®", "")+"</Nome-Brand-Variante><category>"+categoria+"</category><manufacturer>"+Categoria_padre+"</manufacturer><Price>"+str(price_surcharge)+"</Price><attibute>" + attributo + "</attibute><binary>" + str('prod_ids_rec.image') + "</binary></Product>" 
        request =request+"</Products></root>"            
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
        return req_2.make_response(request, [('Content-Type', mimetype)])


class Binary(openerp.addons.web.controllers.main.Binary):
    @http.route([
        '/web/binary/company_logo',
        '/logo',
        '/logo.png',
    ], type='http', auth="none", cors="*")
    def company_logo(self, dbname=None, **kw):
        res=super(Binary, self).company_logo(dbname=dbname, kw=kw)
        imgname = 'logo.png'
        placeholder = functools.partial(get_module_resource, 'web', 'static', 'src', 'img')
        wiew_obj=req_2.registry['ir.http']
        uid = None
        if not request.uid:
                wiew_obj._auth_method_public()
                if request.uid:
                    request.session.uid=request.uid
        if request.session.db:
            dbname = request.session.db
            uid = request.session.uid
        elif dbname is None:
            dbname = db_monodb()

        if not uid:
            uid = openerp.SUPERUSER_ID

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
                                      ON c.id = u.company_id
                                   WHERE u.id = %s
                               """, (uid,))
                    row = cr.fetchone()
                    if row and row[0]:
                        image_data = StringIO(str(row[0]).decode('base64'))
                        response = http.send_file(image_data, filename=imgname, mtime=row[1])
                    else:
                        response = http.send_file(placeholder('nologo.png'))
            except Exception:
                response = http.send_file(placeholder(imgname))

        return response

class Website_site_mm(openerp.addons.web.controllers.main.Home):
    @http.route('/sitemap.xml', type='http', auth="public", website=True)
    def sitemap_xml_index(self):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        ira = request.registry['ir.attachment']
        iuv = request.registry['ir.ui.view']
        mimetype ='application/xml;charset=utf-8'
        content = None

        def create_sitemap(url, content,company_id):
            ira.create(cr, uid, dict(
                datas=content.encode('base64'),
                mimetype=mimetype,
                type='binary',
                name=url,
                url=url,
                company_id=company_id
            ), context=context)

        """ rocco 08-11-2016 """
        request.website = request.registry['website'].get_current_website(request.cr, request.uid, context=request.context)
        """ rocco fine """
        sitemap = ira.search_read(cr, uid, [('url', '=', '/sitemap.xml'), ('type', '=', 'binary'), ('company_id', '=', request.website.company_id.id)], ('datas', 'create_date'), context=context)
        if sitemap:
            # Check if stored version is still valid
            server_format = openerp.tools.misc.DEFAULT_SERVER_DATETIME_FORMAT
            create_date = datetime.datetime.strptime(sitemap[0]['create_date'], server_format)
            delta = datetime.datetime.now() - create_date
            if delta < SITEMAP_CACHE_TIME:
                content = sitemap[0]['datas'].decode('base64')

        if not content:
            # Remove all sitemaps in ir.attachments as we're going to regenerated them
            sitemap_ids = ira.search(cr, uid, [('url', '=like', '/sitemap%.xml'), ('type', '=', 'binary'), ('company_id', '=', request.website.company_id.id)], context=context)
            if sitemap_ids:
                ira.unlink(cr, uid, sitemap_ids, context=context)

            pages = 0
            first_page = None
            locs = request.website.sudo(user=request.website.user_id.id).enumerate_pages()
            while True:
                values = {
                    'locs': islice(locs, 0, LOC_PER_SITEMAP),
                    'url_root': request.httprequest.url_root[:-1],
                }
                urls = iuv.render(cr, uid, 'website.sitemap_locs', values, context=context)
                if urls.strip():
                    page = iuv.render(cr, uid, 'website.sitemap_xml', dict(content=urls), context=context)
                    if not first_page:
                        first_page = page
                    pages += 1
                    create_sitemap('/sitemap-%d.xml' % pages, page,request.website.company_id.id)
                else:
                    break
            if not pages:
                return request.not_found()
            elif pages == 1:
                content = first_page
            else:
                # Sitemaps must be split in several smaller files with a sitemap index
                content = iuv.render(cr, uid, 'website.sitemap_index_xml', dict(
                    pages=range(1, pages + 1),
                    url_root=request.httprequest.url_root,
                ), context=context)
            create_sitemap('/sitemap.xml', content,request.website.company_id.id)

        return request.make_response(content, [('Content-Type', mimetype)])


    @http.route('/site_mm', type='http', auth="public", website=True)
    def site_mm_index(self, **kw):
        page = 'homepage'
        try:
            main_menu = request.registry['ir.model.data'].get_object(request.cr, request.uid, 'rocco_blog_rss', 'main_menu_mm')
        except Exception:
            pass
        else:
            first_menu = main_menu.child_id and main_menu.child_id[0]
            if first_menu:
                if first_menu.url and (not (first_menu.url.startswith(('/site_mm/page/', '/?', '/#')) or (first_menu.url == '/'))):
                    return request.redirect(first_menu.url)
                if first_menu.url and first_menu.url.startswith('/site_mm/page/'):
                    return request.registry['ir.http'].reroute(first_menu.url)
        return self.page(page)
    @http.route([
        '/site_mm/shop',
        '/site_mm/shop/page/<int:page>',
        '/site_mm/shop/category/<model("product.public.category"):category>',
        '/site_mm/shop/category/<model("product.public.category"):category>/page/<int:page>'
    ], type='http', auth="public", website=True)
    def site_mm_shop(self, page=0, category=None, search='', **post):
        return super(WebsiteBlogProduct, self).site_mm_shop(page=page, category=category, search=search, post=post)


class website_sale(openerp.addons.website_sale.controllers.main.website_sale):

    def _get_search_domain(self, search, category, attrib_values):
        domain = request.website.sale_product_domain()

        if search:
            for srch in search.split(" "):
                domain += [
                    '|', '|', '|', ('name', 'ilike', srch), ('description', 'ilike', srch),
                    ('description_sale', 'ilike', srch), ('product_variant_ids.default_code', 'ilike', srch)]

        if category:
            domain += [('public_categ_ids', 'child_of', int(category))]

        if attrib_values:
            attrib = None
            ids = []
            for value in attrib_values:
                if not attrib:
                    attrib = value[0]
                    ids.append(value[1])
                elif value[0] == attrib:
                    ids.append(value[1])
                else:
                    domain += [('attribute_line_ids.value_ids', 'in', ids)]
                    attrib = value[0]
                    ids = [value[1]]
            if attrib:
                domain += [('attribute_line_ids.value_ids', 'in', ids)]

        return domain

    @http.route([
        '/shop',
        '/shop/page/<int:page>',
        '/shop/category/<model("product.public.category"):category>',
        '/shop/category/<model("product.public.category"):category>/page/<int:page>'
    ], type='http', auth="public", website=True)

    def shop(self, page=0, category=None, search='',**post):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [map(int, v.split("-")) for v in attrib_list if v]
        attrib_set = set([v[1] for v in attrib_values])
        tes_category=post.get('tes_category',None)
        domain = self._get_search_domain(search, category, attrib_values)

        keep = QueryURL('/shop', category=category and int(category), search=search, attrib=attrib_list)

        if not context.get('pricelist'):##
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
        product_ids = product_obj.search(cr, uid, domain, limit=PPG, offset=pager['offset'], order=self._get_search_order(post), context=context)
        products = product_obj.browse(cr, uid, product_ids, context=context)

        style_obj = pool['product.style']
        style_ids = style_obj.search(cr, uid, [], context=context)
        styles = style_obj.browse(cr, uid, style_ids, context=context)

        category_obj = pool['product.public.category']
        if category==None:
            category_ids = category_obj.search(cr, uid, [('parent_id', '=', False)], context=context)
        else:
            category_ids = category_obj.search(cr, uid, [('parent_id', '=', int(category))], context=context)
            if category_ids==[]:
                        category_ids = category_obj.search(cr, uid, [('parent_id', '=', category.parent_id.id)], context=context)
    
        categs = category_obj.browse(cr, uid, category_ids, context=context)

        attributes_obj = request.registry['product.attribute']
        attributes_ids = attributes_obj.search(cr, uid, [], context=context)
        attributes = attributes_obj.browse(cr, uid, attributes_ids, context=context)

        from_currency = pool.get('product.price.type')._get_field_currency(cr, uid, 'list_price', context)
        to_currency = pricelist.currency_id
        compute_currency = lambda price: pool['res.currency']._compute(cr, uid, from_currency, to_currency, price, context=context)

        values = {
            'search': search,
            'category': category,
            'tes_category': tes_category,
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

    @http.route(['/shop/product/<model("product.template"):product>'], type='http', auth="public", website=True)
    def product(self, product, category='', search='', **kwargs):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        category_obj = pool['product.public.category']
        template_obj = pool['product.template']
        tes_category=kwargs.get('tes_category',None)
        context.update(active_id=product.id)

        if category:
            category = category_obj.browse(cr, uid, int(category), context=context)
            category = category if category.exists() else False

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [map(int,v.split("-")) for v in attrib_list if v]
        attrib_set = set([v[1] for v in attrib_values])

        keep = QueryURL('/shop', category=category and category.id, search=search, attrib=attrib_list)

        if tes_category==None:
            category_ids = category_obj.search(cr, uid, [], context=context)
        else:
            category_ids = category_obj.search(cr, uid, [('parent_id','=',tes_category)], context=context)
            
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
            'search': search,
            'category': category,
            'tes_category': tes_category,
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

        