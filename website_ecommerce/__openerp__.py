# -*- coding: utf-8 -*-
# Copyright (C) Kanak Infosystems LLP.

{
    'name': 'Tangy Ecommerce Theme',
    'version': '1.0',
    'summary': 'Tangy Ecommerce Theme',
    'description': """
Tangy Ecommerce Theme
=====================
    """,
    'author': 'Kanak Infosystems LLP.',
    'images': ['static/description/main_screenshot.png'],
    'category': 'Theme/Ecommerce',
    'depends': ['website', 'website_sale', 'website_blog', 'theme_common'],
    'data': [
        'views/website_ecommerce_template_views.xml',
        'views/template.xml',
        'views/shop_product_template.xml',
        'views/contactus_template.xml',
        'views/shop_template.xml',
        'views/login_template.xml',
        'views/signup_template.xml',
        'views/blog_templates.xml',
        'views/ecommerce_snippest.xml',
        'data/data.xml',
        'views/product_image_demo.xml',
        'views/ecommerce_snippest_extra.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': True,
    'price': 0.0,
    'currency': 'EUR',
}
