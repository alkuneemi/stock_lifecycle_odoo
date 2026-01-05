# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import secrets


class StockPicking(models.Model):
    _inherit = "stock.picking"

    review_state = fields.Selection([
        ('draft', 'مسودة'),
        ('waiting_manager', 'بانتظار موافقة المدير'),
        ('waiting_warehouse', 'بانتظار موافقة مدير المخازن'),
        ('waiting_shipping', 'بانتظار تأكيد مدير الشحن'),
        ('in_transit', 'تم الشحن - قيد النقل'),
        ('confirmed', 'مصادق عليها'),
    ], default='draft', tracking=True,store=True)

    # Tokens per approval stage
    approve_token = fields.Char(copy=False, readonly=True)
    warehouse_approve_token = fields.Char(copy=False, readonly=True)
    shipping_token = fields.Char(copy=False, readonly=True)
    final_confirm_token = fields.Char(copy=False, readonly=True)

    manager_id = fields.Many2one('res.users', string='المدير المباشر')
    warehouse_manager_id = fields.Many2one('res.users', string='مدير المخازن')
    shipping_manager_id = fields.Many2one('res.users', string='مدير الشحن')

    # Timestamps for auditing the approval flow
    sent_to_manager_datetime = fields.Datetime(string='تم الإرسال للمدير في')
    manager_approved_datetime = fields.Datetime(string='وافق المدير في')
    warehouse_approved_datetime = fields.Datetime(string='وافق مدير المخازن في')
    shipping_confirmed_datetime = fields.Datetime(string='أكد مدير الشحن في')
    creator_confirmed_datetime = fields.Datetime(string='مصادقة المنشئ في')

    def action_send_to_manager_for_approval(self):
        for picking in self:
            if not picking.manager_id:
                raise UserError("لا يوجد مدير مباشر (manager_id) لهذا السجل.")

            if not picking.approve_token:
                picking.approve_token = secrets.token_urlsafe(24)

            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            record_url = f"{base_url}/web#id={picking.id}&model=stock.picking&view_type=form"

            approve_url = f"{base_url}/picking/approve/{picking.id}?token={picking.approve_token}"
            reject_url = f"{base_url}/picking/reject/{picking.id}?token={picking.approve_token}"

            lines_html = ""
            for ml in picking.move_line_ids_without_package:
                quantity = getattr(ml, 'quantity', getattr(ml, 'quantity', 0.0))
                lines_html += f"""
                    <tr>
                        <td>{ml.product_id.display_name or ''}</td>
                        <td style="text-align:center;">{(ml.product_uom_id.name or '') if ml.product_uom_id else ''}</td>
                        <td style="text-align:center;">{quantity or 0.0}</td>
                        <td>{ml.location_id.display_name or ''}</td>
                        <td>{ml.location_dest_id.display_name or ''}</td>
                    </tr>
                """

            requester = picking.create_uid
            requester_info = "%s (%s)" % (requester.name, requester.email or "بدون بريد")

            scheduled = getattr(picking, 'scheduled_date', getattr(picking, 'scheduled_date', ''))

            body = f"""
                <p>تم إنشاء طلب تحويل داخلي ويحتاج موافقتكم على الكميات المطلوبة:</p>
                <ul>
                    <li><strong>رقم التحويل:</strong> {picking.name or ''}</li>
                    <li><strong>التاريخ المجدول:</strong> {scheduled or ''}</li>
                    <li><strong>نوع العملية:</strong> {picking.picking_type_id.name or ''}</li>
                    <li><strong>من:</strong> {picking.location_id.display_name or ''}</li>
                    <li><strong>إلى:</strong> {picking.location_dest_id.display_name or ''}</li>
                </ul>

                <table border="1" cellpadding="6" cellspacing="0" width="100%">
                    <tr style="background-color:#f0f0f0;">
                        <th>المنتج</th>
                        <th>الوحدة</th>
                        <th>الكمية المطلوبة</th>
                        <th>الموقع المصدر</th>
                        <th>الموقع الوجهة</th>
                    </tr>
                    {lines_html}
                </table>

                <br/>

                <div style="margin-top:14px;">
                    <a href="{record_url}"
                       style="background:#1f6feb;color:#fff;padding:10px 14px;text-decoration:none;border-radius:6px;display:inline-block;">
                        فتح السجل للمراجعة
                    </a>

                    <a href="{approve_url}"
                       style="background:#2da44e;color:#fff;padding:10px 14px;text-decoration:none;border-radius:6px;display:inline-block;margin-left:8px;">
                        موافقة
                    </a>

                    <a href="{reject_url}"
                       style="background:#cf222e;color:#fff;padding:10px 14px;text-decoration:none;border-radius:6px;display:inline-block;margin-left:8px;">
                        رفض
                    </a>
                </div>

                <br/>
                <p><strong>منشئ السجل:</strong> {requester_info}</p>
            """

            # record timestamp for send action
            picking.sent_to_manager_datetime = fields.Datetime.now()

            mail = self.env['mail.mail'].sudo().create({
                'subject': f'طلب موافقة تحويل داخلي {picking.name or ""}',
                'body_html': body,
                'email_to': picking.manager_id.email or '',
            })
            mail.sudo().send()

            picking.review_state = 'waiting_manager'

    def action_manager_approve(self):
        for picking in self:
            # سجل وقت موافقة المدير، ثم أرسل لمدير المخازن
            picking.manager_approved_datetime = fields.Datetime.now()

            # بعد موافقة المدير الأولية، نرسل لمدير المخازن
            if not picking.warehouse_manager_id:
                raise UserError("لا يوجد مدير مخازن (warehouse_manager_id) لهذا السجل.")

            if not picking.warehouse_approve_token:
                picking.warehouse_approve_token = secrets.token_urlsafe(24)

            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            approve_url = f"{base_url}/picking/warehouse_approve/{picking.id}?token={picking.warehouse_approve_token}"

            body = f"""
                <p>طلب تحويل داخلي ينتظر موافقتكم كمراجع (مدير المخازن):</p>
                <ul>
                    <li><strong>التحويل:</strong> {picking.name or ''}</li>
                </ul>
                <div style="margin-top:14px;">
                    <a href="{approve_url}"
                       style="background:#2da44e;color:#fff;padding:10px 14px;text-decoration:none;border-radius:6px;display:inline-block;">
                        موافقة مدير المخازن
                    </a>
                </div>
            """

            mail = self.env['mail.mail'].sudo().create({
                'subject': f'طلب مراجعة من مدير المخازن {picking.name or ""}',
                'body_html': body,
                'email_to': picking.warehouse_manager_id.email or '',
            })
            mail.sudo().send()

            picking.review_state = 'waiting_warehouse'

    def action_manager_reject(self):
        for picking in self:
            picking.review_state = 'draft'

    def action_warehouse_approve(self):
        for picking in self:
            # سجل وقت موافقة مدير المخازن، ثم أرسل لمدير الشحن
            picking.warehouse_approved_datetime = fields.Datetime.now()

            # بعد موافقة مدير المخازن، نرسل لمدير الشحن
            if not picking.shipping_manager_id:
                raise UserError("لا يوجد مدير شحن (shipping_manager_id) لهذا السجل.")

            if not picking.shipping_token:
                picking.shipping_token = secrets.token_urlsafe(24)

            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            shipping_url = f"{base_url}/picking/shipping_confirm/{picking.id}?token={picking.shipping_token}"

            body = f"""
                <p>طلب تحويل داخلي مُعَدّ للتحميل ويحتاج تأكيد مدير الشحن:</p>
                <ul>
                    <li><strong>التحويل:</strong> {picking.name or ''}</li>
                </ul>
                <div style="margin-top:14px;">
                    <a href="{shipping_url}"
                       style="background:#1f6feb;color:#fff;padding:10px 14px;text-decoration:none;border-radius:6px;display:inline-block;">
                        تأكيد استلام الشحنة (مدير الشحن)
                    </a>
                </div>
            """

            mail = self.env['mail.mail'].sudo().create({
                'subject': f'تأكيد تحميل - طلب شحن {picking.name or ""}',
                'body_html': body,
                'email_to': picking.shipping_manager_id.email or '',
            })
            mail.sudo().send()

            picking.review_state = 'waiting_shipping'

    def action_warehouse_reject(self):
        for picking in self:
            picking.review_state = 'draft'

    def action_shipping_confirm(self):
        for picking in self:
            # عند تأكيد مدير الشحن، نسجل الوقت ونُعلم منشئ السجل بأن الشحنة في الطريق
            picking.shipping_confirmed_datetime = fields.Datetime.now()

            if not picking.final_confirm_token:
                picking.final_confirm_token = secrets.token_urlsafe(24)

            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            confirm_url = f"{base_url}/picking/final_confirm/{picking.id}?token={picking.final_confirm_token}"

            body = f"""
                <p>تم تأكيد استلام الشحنة من قبل مدير الشحن، الشحنة في الطريق.</p>
                <p>يرجى مراجعة الكميات وتصديق الشحنة:</p>
                <div style="margin-top:14px;">
                    <a href="{confirm_url}"
                    style="background:#2da44e;color:#fff;padding:10px 14px;text-decoration:none;border-radius:6px;display:inline-block;">
                        تصديق الشحنة ومراجعة الكميات
                    </a>
                </div>
            """

            mail = self.env['mail.mail'].sudo().create({
                'subject': f'الشحنة في الطريق - تحقق وصادق {picking.name or ""}',
                'body_html': body,
                'email_to': picking.create_uid.email or '',
            })
            mail.sudo().send()

            picking.review_state = 'in_transit'

            # ✅ طباعة/فتح PDF مباشرة بعد التأكيد
            return self.env.ref('stock_lifecycle.action_report_transfer_order').report_action(picking)

    def action_shipping_reject(self):
        for picking in self:
            picking.review_state = 'draft'

    def action_final_confirm(self):
        for picking in self:
            # سجل وقت مصادقة المنشئ
            picking.creator_confirmed_datetime = fields.Datetime.now()
            picking.review_state = 'confirmed'
    
    def action_open_workflow(self):
            self.ensure_one()
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = f"{base_url}/stock_lifecycle/workflow/{self.id}"
            return {
                'type': 'ir.actions.act_url',
                'url': url,
                'target': 'new',
            }

