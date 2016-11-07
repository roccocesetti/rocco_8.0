
{
    'name': 'Public Cloud',
    'category': 'Website',
    'summary': 'Publish Your Public Cloud',
    'version': '1.0',
    'description': """
Portal Servizi cloud 
================

        """,
    'author': 'Rocco Cesetti',
    'depends': ['website','website_mail', 'rc_Cloudonthecloud','base'],
    'data': [
        'views/website_cloud.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
}
