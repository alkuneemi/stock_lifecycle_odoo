# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError


class PickingApprovalController(http.Controller):

    @http.route('/picking/approve/<int:picking_id>', type='http', auth='user', website=False)
    def picking_approve(self, picking_id, token=None, **kwargs):
        picking = request.env['stock.picking'].sudo().browse(picking_id)
        if not picking.exists():
            return request.not_found()

        if not token or token != (picking.approve_token or ''):
            raise AccessError("Invalid token")

        if picking.manager_id and request.env.user.id != picking.manager_id.id:
            raise AccessError("You are not allowed to approve this request.")

        picking.action_manager_approve()

        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return request.redirect(f"{base_url}/web#id={picking.id}&model=stock.picking&view_type=form")
    
    @http.route('/stock_lifecycle/workflow/<int:picking_id>', type='http', auth='user', website=False)
    def workflow_page(self, picking_id, **kwargs):
        picking = request.env['stock.picking'].sudo().browse(picking_id)
        if not picking.exists():
            return request.not_found()

        # تحديد المراحل حسب review_state (عدّل القيم حسب نظامك)
        state = picking.review_state or 'draft'
        stages = {
            'sent_to_manager': state in ('waiting_manager','waiting_warehouse','waiting_shipping','in_transit','confirmed'),
            'manager_approved': state in ('waiting_warehouse','waiting_shipping','in_transit','confirmed'),
            'warehouse_approved': state in ('waiting_shipping','in_transit','confirmed'),
            'shipping_confirmed': state in ('in_transit','confirmed'),
            'creator_confirmed': state == 'confirmed',
        }

        # قائمة التحاويل للسايدبار (اختر الدومين المناسب لك)
        pickings = request.env['stock.picking'].sudo().search(
            [('picking_type_code', '=', 'internal')],
            order='id desc',
            limit=200
        )

        return request.render('stock_lifecycle.workflow_template', {
            'picking': picking,
            'stages': stages,
            'pickings': pickings,
        })
    @http.route('/picking/reject/<int:picking_id>', type='http', auth='user', website=False)
    def picking_reject(self, picking_id, token=None, **kwargs):
        picking = request.env['stock.picking'].sudo().browse(picking_id)
        if not picking.exists():
            return request.not_found()

        if not token or token != (picking.approve_token or ''):
            raise AccessError("Invalid token")

        if picking.manager_id and request.env.user.id != picking.manager_id.id:
            raise AccessError("You are not allowed to reject this request.")

        picking.action_manager_reject()

        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return request.redirect(f"{base_url}/web#id={picking.id}&model=stock.picking&view_type=form")
    
    @http.route('/stock_lifecycle/validate/<int:picking_id>', type='http', auth='user', website=False)
    def stock_lifecycle_validate(self, picking_id, **kw):
        picking = request.env['stock.picking'].sudo().browse(picking_id)
        if not picking.exists():
            return request.not_found()

        # شرط: لا يظهر إلا بعد تصديق المنشئ
        # نفس منطق stages: creator_confirmed_datetime موجود = تم التصديق
        if not picking.creator_confirmed_datetime:
            return request.redirect(f"/stock_lifecycle/workflow/{picking_id}")

        # (اختياري) تحقق أن المستخدم مدير عام/مسموح له
        # مثال بسيط: فقط مدير النوع الافتراضي أو مجموعة stock manager
        user = request.env.user
        if not (user.has_group('stock.group_stock_manager') or user == picking.picking_type_id.manager_user_id):
            raise AccessError("ليس لديك صلاحية للتصديق النهائي.")

        # تنفيذ الترحيل
        try:
            if picking.state not in ('done', 'cancel'):
                # تأكيد/تخصيص إذا لزم
                if picking.state == 'draft':
                    picking.action_confirm()
                if picking.state in ('confirmed', 'waiting'):
                    picking.action_assign()

                picking.button_validate()
        except (UserError, Exception):
            # إذا فشل لأي سبب رجّع لنفس الصفحة
            return request.redirect(f"/stock_lifecycle/workflow/{picking_id}")

        return request.redirect(f"/stock_lifecycle/workflow/{picking_id}")