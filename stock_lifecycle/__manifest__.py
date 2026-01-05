# -*- coding: utf-8 -*-
{
    "name": "Internal Transfer & Shipment Tracking Workflow",
    "summary": "End-to-end tracking and approval workflow for internal stock transfers",
    "description": """
Internal Transfer & Shipment Tracking Workflow
==============================================

A professional governance and tracking module for internal stock transfers.
It provides full visibility over shipment lifecycle, approvals, signatories,
and a visual timeline with audit trail.

Key Features
------------
• Multi-stage approval workflow (Manager, Warehouse, Shipping, Receiver)
• Shipment timeline with avatars and timestamps
• Configurable signatories per picking type
• Internal transfer log with quick search
• Clear accountability and audit trail
• Designed for environments with high operational risk
• Fully bilingual (Arabic / English)

Ideal for companies that require strict control over internal movements
between main sites and warehouses.
""",

    "version": "1.0.0",
    "author": "ADEX",
    "website": "https://www.odoo.com",
    "license": "LGPL-3",

    "category": "Inventory",
    "depends": [
        "stock",
        "mail",
        "web",
    ],

    "data": [
        "security/ir.model.access.csv",
        "views/stock_picking_type_view.xml",
        "views/stock_picking_view.xml",
        "views/workflow_templates.xml",
    ],

    "assets": {
        "web.assets_backend": [
            # إذا عندك JS أو CSS إضافي مستقبلاً
        ],
    },

    # ===== Odoo Apps Store =====
    "price": 199.0,          # ✅ بين 120 و 300
    "currency": "USD",

    "images": [
        "static/description/hero.png",
        "static/description/timeline.png",
        "static/description/sidebar.png",
    ],

    "installable": True,
    "application": True,
    "auto_install": False,

    # دعم الإصدارات
    "odoo_version": "18.0",
}

