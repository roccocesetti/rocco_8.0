# coding: utf-8
{
    'name': 'website_blog_RSS_Product',
    'category': 'website',
    'summary': 'This module enables RSS on product',
    'website': 'http://ideawork.it',
    'version': '8.0.0.2.0',
    'author': 'Rocco Cesetti, Ideawork.it',
    'license': 'AGPL-3',
    'depends': [
        'website_blog','website_sale','website_sale_variant_pictures',
    ],
    'data': [
        'views/website_templates.xml',
        'new_site/website.xml',
        #'new_site/template.xml',

    ],
    'demo': [

    ],
    'qweb': [

    ],
    'installable': True,
    'application': True,
}
