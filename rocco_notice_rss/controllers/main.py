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
from xml.etree.ElementTree import parse
import urllib
import feedparser
from openerp.osv.orm import browse_record
from openerp.addons.website.models.website import slug
from openerp import tools
import httplib2
import requests
MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT = IMAGE_LIMITS = (1024, 768)
LOC_PER_BLOG_RSS = 45000
BLOG_RSS_CACHE_TIME = datetime.timedelta(minutes=1)
_logger = logging.getLogger(__name__)

class QueryURL(object):
    def __init__(self, path='', path_args=None, **args):
        self.path = path
        self.args = args
        self.path_args = set(path_args or [])

    def __call__(self, path=None, path_args=None, **kw):
        path = path or self.path
        for k, v in self.args.items():
            kw.setdefault(k, v)
        path_args = set(path_args or []).union(self.path_args)
        paths, fragments = [], []
        for key, value in kw.items():
            if value and key in path_args:
                if isinstance(value, browse_record):
                    paths.append((key, slug(value)))
                else:
                    paths.append((key, value))
            elif value:
                if isinstance(value, list) or isinstance(value, set):
                    fragments.append(werkzeug.url_encode([(key, item) for item in value]))
                else:
                    fragments.append(werkzeug.url_encode([(key, value)]))
        for key, value in paths:
            path += '/' + key + '/%s' % value
        if fragments:
            path += '?' + '&'.join(fragments)
        return path



class WebsiteBlogNotice(http.Controller):
    _blog_post_per_page = 20
    _post_comment_per_page = 10
    def nav_list(self):
        blog_post_obj = request.registry['blog.post']
        groups = blog_post_obj.read_group(
            request.cr, request.uid, [], ['name', 'create_date'],
            groupby="create_date", orderby="create_date desc", context=request.context)
        for group in groups:
            begin_date = datetime.datetime.strptime(group['__domain'][0][2], tools.DEFAULT_SERVER_DATETIME_FORMAT).date()
            end_date = datetime.datetime.strptime(group['__domain'][1][2], tools.DEFAULT_SERVER_DATETIME_FORMAT).date()
            group['date_begin'] = '%s' % datetime.date.strftime(begin_date, tools.DEFAULT_SERVER_DATE_FORMAT)
            group['date_end'] = '%s' % datetime.date.strftime(end_date, tools.DEFAULT_SERVER_DATE_FORMAT)
        return groups
    @http.route([
        '/blog/<model("blog.blog"):blog>',
        '/blog/<model("blog.blog"):blog>/page/<int:page>',
        '/blog/<model("blog.blog"):blog>/tag/<model("blog.tag"):tag>',
        '/blog/<model("blog.blog"):blog>/tag/<model("blog.tag"):tag>/page/<int:page>',
    ], type='http', auth="public", website=True)
    def blog(self, blog=None, tag=None, page=1, **opt):
        """ Prepare all values to display the blog.

        :return dict values: values for the templates, containing

         - 'blog': current blog
         - 'blogs': all blogs for navigation
         - 'pager': pager of posts
         - 'tag': current tag
         - 'tags': all tags, for navigation
         - 'nav_list': a dict [year][month] for archives navigation
         - 'date': date_begin optional parameter, used in archives navigation
         - 'blog_url': help object to create URLs
        """
        date_begin, date_end = opt.get('date_begin'), opt.get('date_end')
        print 'blog',blog,'tag',tag,'opt',opt
        cr, uid, context = request.cr, request.uid, request.context
        uid=openerp.SUPERUSER_ID
        blog_post_obj = request.registry['blog.post']
        blog_obj = request.registry['blog.blog']
        blog_ids = blog_obj.search(cr, uid, [], order="create_date asc", context=context)
        blogs = blog_obj.browse(cr, uid, blog_ids, context=context)
        
        domain = []
        if blog:
            blog_sport_ids = blog_obj.search(cr, uid, [('x_rss_channel','<>',None)],context=context)
            if blog.id in blog_sport_ids:
                blog_post_ids = blog_post_obj.search(cr, uid, domain, order="create_date desc", context=context)
                if blog.x_elimina_art:
                    blog_post_obj.unlink(cr,uid,blog.id,context=context)
                root=feedparser.parse(blog.x_rss_channel)
                line=0
                if root:
                    for item in root.entries:
                      if blog.x_elimina_art==False:
                          #domain=[('blog_id', '=', blog.id),('name','=',item.title)]
                          blog_post_ids = blog_post_obj.search(cr, uid, [('blog_id', '=', blog.id),('name','=',item.title)], order="create_date desc", context=context)
                          if blog_post_ids:
                              continue
                          ok_tag=False
                          for tag_ctrl_id in blog.x_tag_ids:
                              if item.title.find(tag_ctrl_id.name):
                                   ok_tag=True
                                   break
                              if item.description.find(tag_ctrl_id.name):
                                   ok_tag=True
                                   break
                          if ok_tag==False:
                             if blog.x_tag_ids:
                                ok_tag=False
                             else: 
                                 ok_tag=True
                               
                      content='<section class="mt16 mb16 readable">'               
                      content+='<ul><li><a href='+item.link+'>'+item.title+'</a></li></ul>'
                      f = requests.get(item.link)
                      il_fatto=False
                      if blog.x_image_tag:
                          if  (f.text).find(blog.x_image_tag):
                              img_ini=(f.text).find(blog.x_image_tag)-len(blog.x_image_tag)*2
                          else:
                              img_ini=0
                      else:
                          img_ini=0
                      print 'img_ini->',img_ini
                      while (f.text)[img_ini:len(f.text)].find('<img'):
                          img_ini=f.text.find('<img')
                          img_fin=f.text[img_ini:len(f.text)].find('>')
                          myimg= f.text[img_ini:img_ini+img_fin+1]
                          mysrc_ini=myimg.find('src="')
                          mysrc_fin=myimg[mysrc_ini+5:len(myimg)].find('"')
                          mysrc= myimg[mysrc_ini+5:mysrc_ini+5+mysrc_fin]
                          if img_ini>0:
                            if blog.x_image_tag:
                                  if mysrc.find(blog.x_image_tag):
                                      content+='<ul><li><img src="%s%s"></li></ul>' % (blog.x_image_tag or '',mysrc)
                                      break
                                  else:
                                      content+='<ul><li><img src="%s%s"></li></ul>' % (blog.x_site_channel_image or '',mysrc)
                                      break                                   
                            else:
                                      content+='<ul><li><img src="%s%s"></li></ul>' % (blog.x_site_channel_image or '',mysrc)
                                      break                                   
                                
                          else:
                             img_ini+=img_fin
                             continue     
                      content+='<ul><li>'+item.description+'</li></ul>'
                      line+=1
                      if line>blog.x_rss_number:
                          #continue
                          break
                      """ get url """
                      if item.link: 
                          f = urllib.urlopen(item.link)
                          myfile = f.read()                          
                          #myfile=''
                          #print 'myfile',myfile
                          ini=myfile.find('<div itemprop="articleBody" class="news-txt">')
                          if ini>0:
                              myfile_2=myfile[ini+len('<div itemprop="articleBody" class="news-txt">')+1:len(myfile)]
                              fini=myfile_2.find('</div>')
                              my_art=myfile_2[0:fini-1]
                              print 'my_art',my_art
                              content+='<ul><li>'+my_art.decode('utf-8')+'</li></ul>'
                      """ fine get url """
                      content+='</section>'
                      #view_id = request.registry['ir.model.data'].get_object_reference(cr, uid, 'blog.tag', 'blog_tag_rocco_sport')
                      vals={'name':item.title,
                                 'subtitle':item.description,
                                 'content':content,
                                 'blog_id':blog.id,
                                 'website_published':ok_tag,
                                 'website_meta_title':item.title,
                                 'website_meta_description':item.description,
                                 'website_noindex':blog.website_noindex or True
                                 #'website_meta_keywords':item.title.replace(',',' ').replace('.',' '),
                                 #'tag_ids': [(6, 0 ,[ id for id in blog.x_tag_ids] ) ],
                                #'tag_ids': [(6, 0, [view_id])]
                                 }
                      blog_post_obj.create(cr,uid,vals)
       
            domain += [('blog_id', '=', blog.id)]
        if tag:
            domain += [('tag_ids', 'in', tag.id)]
        if date_begin and date_end:
            domain += [("create_date", ">=", date_begin), ("create_date", "<=", date_end)]

        blog_url = QueryURL('', ['blog', 'tag'], blog=blog, tag=tag, date_begin=date_begin, date_end=date_end)
        post_url = QueryURL('', ['blogpost'], tag_id=tag and tag.id or None, date_begin=date_begin, date_end=date_end)

        blog_post_ids = blog_post_obj.search(cr, uid, domain, order="create_date desc", context=context)
        blog_posts = blog_post_obj.browse(cr, uid, blog_post_ids, context=context)

        pager = request.website.pager(
            url=blog_url(),
            total=len(blog_posts),
            page=page,
            step=self._blog_post_per_page,
        )
        pager_begin = (page - 1) * self._blog_post_per_page
        pager_end = page * self._blog_post_per_page
        blog_posts = blog_posts[pager_begin:pager_end]

        tags = blog.all_tags()[blog.id]

        values = {
            'blog': blog,
            'blogs': blogs,
            'main_object': blog,
            'tags': tags,
            'tag': tag,
            'blog_posts': blog_posts,
            'pager': pager,
            'nav_list': self.nav_list(),
            'blog_url': blog_url,
            'post_url': post_url,
            'date': date_begin,
        }
        response = request.website.render("website_blog.blog_post_short", values)
        return response

    