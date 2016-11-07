# coding: utf-8
{
    'name': 'website_notice_RSS_',
    'category': 'website',
    'summary': 'This module enables RSS on notice',
    'website': 'http://ideawork.it',
    'version': '8.0.0.2.0',
    'author': 'Rocco Cesetti, Ideawork.it',
    'license': 'AGPL-3',
    'depends': [
        'website_blog','website_blog_rss',
    ],
    'data': [
        'views/website_templates.xml',
        #'new_site/website.xml',
        #'new_site/template.xml',

    ],
    'demo': [

    ],
    'qweb': [

    ],
    'installable': True,
    'application': True,
}
