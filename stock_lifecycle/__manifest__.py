# -*- coding: utf-8 -*-
{
    'name': 'دورة حياة المخزون',
    'version': '1.0.0',
    'summary': 'سير موافقات التحويلات الداخلية (إرسال للموافقة، قبول/رفض عبر رابط)',
    'description': 'Adds an approval workflow for internal stock pickings with email links for manager approval.',
    'category': 'Inventory',
    'author': 'Generated',
    'license': 'LGPL-3',
    'depends': ['stock', 'mail'],
    'data': [
        'views/stock_picking_view.xml',
         'views/workflow_templates.xml',
          'views/picking_type_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
