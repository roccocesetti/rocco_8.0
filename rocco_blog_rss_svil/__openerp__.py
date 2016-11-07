# coding: utf-8
{
    'name': 'website_blog_RSS_Product',
    'category': 'website',
    'summary': 'This module enables RSS on product',
    'website': 'http://ideawork.it',
    'version': '8.0.0.2.0',
    'author': 'Rocco Cesetti, Ideawork.it',
    'license': 'AGPL-3',
    'depends': ['base','web', 'share', 'mail','website',
        'website_blog','website_sale','website_sale_variant_pictures','website_crm',
    ],
    'data': [
        'views/website_templates.xml',
       'views/website_crm.xml'
       #'views/templates.xml'

    ],
    'demo': [

    ],
    'qweb': [

    ],
    'installable': True,
    'application': True,
}
