# -*- coding: utf-8 -*-
# Copyright 2016 Avanzosc (<http://www.avanzosc.es>)
# Copyright 2016 Tecnativa (<http://www.tecnativa.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, exceptions, fields, models, _


class StockInventory(models.Model):
    _inherit = "stock.inventory"

    @api.model
    def _selection_filter(self):
        res_filter = super(StockInventory, self)._selection_filter()
        res_filter.append(('file', _('By File')))
        return res_filter

    @api.depends('import_lines')
    def _file_lines_processed(self):
        processed = True
        if self.import_lines:
            processed = any((not line.fail or
                             (line.fail and
                              line.fail_reason != _('No processed')))
                            for line in self.import_lines)
        self.processed = processed

    imported = fields.Boolean('Imported')
    import_lines = fields.One2many('stock.inventory.import.line',
                                   'inventory_id', string='Imported Lines')
    filter = fields.Selection(_selection_filter,
                              string='Selection Filter',
                              required=True)
    processed = fields.Boolean(string='Has been processed at least once?',
                               compute='_file_lines_processed')

    @api.multi
    def process_import_lines(self):
        """Process Inventory Load lines."""
        self.ensure_one()
        if not self.import_lines:
            raise exceptions.Warning(_("There must be one line at least to "
                                       "process"))
        inventory_line_obj = self.env['stock.inventory.line']
        stk_lot_obj = self.env['stock.production.lot']
        product_obj = self.env['product.product']
        for line in self.import_lines:
            if line.fail:
                if not line.product:
                    prod_lst = product_obj.search([('default_code', '=',
                                                    line.code)])
                    if prod_lst:
                        product = prod_lst[0]
                    else:
                        line.fail_reason = _('No product code found')
                    continue
                else:
                    product = line.product
                lot_id = None
                if line.lot:
                    lot_lst = stk_lot_obj.search([('name', '=', line.lot)])
                    if lot_lst:
                        lot_id = lot_lst[0].id
                    else:
                        lot = stk_lot_obj.create({'name': line.lot,
                                                  'product_id': product.id})
                        lot_id = lot.id
                inventory_line_obj.create({'product_id': product.id,
                                           'product_uom_id': product.uom_id.id,
                                           'product_qty': line.quantity,
                                           'inventory_id': self.id,
                                           'location_id': line.location_id.id,
                                           'prod_lot_id': lot_id})
                line.write({'fail': False, 'fail_reason': _('Processed')})
        return True

    @api.multi
    def action_done(self):
        for inventory in self:
            if not inventory.processed:
                raise exceptions.Warning(
                    _("Loaded lines must be processed at least one time for "
                      "inventory : %s") % (inventory.name))
        return super(StockInventory, self).action_done()
