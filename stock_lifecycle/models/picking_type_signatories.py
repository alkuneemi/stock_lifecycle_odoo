from odoo import models, fields, api
from odoo.exceptions import ValidationError


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    has_transfer_lifecycle = fields.Boolean(string='يتضمن دورة حياة التحويل')

    manager_user_id = fields.Many2one('res.users', string='المدير الافتراضي')
    warehouse_manager_user_id = fields.Many2one('res.users', string='مدير المخازن الافتراضي')
    shipping_manager_user_id = fields.Many2one('res.users', string='مدير الشحن الافتراضي')

    def _validate_lifecycle_required_fields(self):
        """Python-only: enforce required fields when lifecycle is enabled."""
        for rec in self:
            if rec.has_transfer_lifecycle:
                missing = []
                if not rec.manager_user_id:
                    missing.append('المدير الافتراضي')
                if not rec.warehouse_manager_user_id:
                    missing.append('مدير المخازن الافتراضي')
                if not rec.shipping_manager_user_id:
                    missing.append('مدير الشحن الافتراضي')

                if missing:
                    raise ValidationError(
                        "عند تفعيل دورة حياة التحويل يجب تعبئة الحقول التالية:\n- "
                        + "\n- ".join(missing)
                    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._validate_lifecycle_required_fields()
        return records

    def write(self, vals):
        res = super().write(vals)
        self._validate_lifecycle_required_fields()
        return res

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.onchange('picking_type_id')
    def _onchange_picking_type_set_signatories(self):
        for rec in self:
            pt = rec.picking_type_id
            if not pt:
                continue
            # try to set manager fields if they exist
            # manager_id
            if 'manager_id' in rec._fields:
                f = rec._fields.get('manager_id')
                if f and f.comodel_name == 'res.users' and pt.manager_user_id:
                    rec.manager_id = pt.manager_user_id.id
                elif f and f.comodel_name == 'stock_lifecycle.signatory' and pt.manager_user_id:
                    # find signatory linked to that user
                    sign = self.env['stock_lifecycle.signatory'].search([('user_id','=',pt.manager_user_id.id)], limit=1)
                    if sign:
                        rec.manager_id = sign.id
            # warehouse_manager_id
            if 'warehouse_manager_id' in rec._fields:
                f = rec._fields.get('warehouse_manager_id')
                if f and f.comodel_name == 'res.users' and pt.warehouse_manager_user_id:
                    rec.warehouse_manager_id = pt.warehouse_manager_user_id.id
                elif f and f.comodel_name == 'stock_lifecycle.signatory' and pt.warehouse_manager_user_id:
                    sign = self.env['stock_lifecycle.signatory'].search([('user_id','=',pt.warehouse_manager_user_id.id)], limit=1)
                    if sign:
                        rec.warehouse_manager_id = sign.id
            # shipping_manager_id
            if 'shipping_manager_id' in rec._fields:
                f = rec._fields.get('shipping_manager_id')
                if f and f.comodel_name == 'res.users' and pt.shipping_manager_user_id:
                    rec.shipping_manager_id = pt.shipping_manager_user_id.id
                elif f and f.comodel_name == 'stock_lifecycle.signatory' and pt.shipping_manager_user_id:
                    sign = self.env['stock_lifecycle.signatory'].search([('user_id','=',pt.shipping_manager_user_id.id)], limit=1)
                    if sign:
                        rec.shipping_manager_id = sign.id
