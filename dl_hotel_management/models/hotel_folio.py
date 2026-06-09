from odoo import models, fields, api, _
from odoo.exceptions import UserError

class HotelFolio(models.Model):
    _name = 'hotel.folio'
    _description = 'Folio do Hotel (Fatura)'

    name = fields.Char(string='Referência', default='Novo', readonly=True)
    booking_id = fields.Many2one('hotel.booking', string='Reserva', required=True)
    partner_id = fields.Many2one(related='booking_id.partner_id', string='Hóspede')
    status = fields.Selection([('open', 'Aberto'), ('closed', 'Fechado')], string='Status', default='open')
    
    # Relações com serviços herdadas da Reserva
    laundry_order_ids = fields.One2many(related='booking_id.laundry_order_ids', string='Pedidos de Lavanderia', readonly=True)
    restaurant_order_ids = fields.One2many(related='booking_id.restaurant_order_ids', string='Pedidos de Restaurante', readonly=True)
    transport_request_ids = fields.One2many(related='booking_id.transport_request_ids', string='Pedidos de Transporte', readonly=True)
    
    # Ligação com a fatura nativa do Odoo
    invoice_id = fields.Many2one('account.move', string='Fatura Odoo', ondelete='restrict', readonly=True, copy=False)
    company_id = fields.Many2one('res.company', related='booking_id.company_id', string='Hotel/Empresa', store=True, readonly=True)
    
    # Em um cenário real, estas linhas seriam auto-calculadas. Para o protótipo, criamos ligações textuais simples.
    room_charge_total = fields.Float(related='booking_id.total_amount', string='Total do Quarto')
    
    grand_total = fields.Float(string='Total Geral', compute='_compute_grand_total', store=True)

    @api.depends('room_charge_total', 'booking_id.laundry_order_ids.total_amount', 'booking_id.restaurant_order_ids.total_amount', 'booking_id.transport_request_ids.charge')
    def _compute_grand_total(self):
        for folio in self:
            laundry_total = sum(order.total_amount for order in folio.laundry_order_ids)
            restaurant_total = sum(order.total_amount for order in folio.restaurant_order_ids)
            transport_total = sum(request.charge for request in folio.transport_request_ids)
            folio.grand_total = folio.room_charge_total + laundry_total + restaurant_total + transport_total

    def action_create_invoice(self):
        self.ensure_one()
        if self.invoice_id:
            raise UserError(_("Já existe uma fatura criada para este Folio."))
        if not self.partner_id:
            raise UserError(_("A reserva não possui um Hóspede associado."))
        
        invoice_lines = []
        
        # 1. Hospedagem
        if self.room_charge_total > 0:
            invoice_lines.append((0, 0, {
                'name': f"Hospedagem - Reserva {self.booking_id.name}",
                'quantity': 1.0,
                'price_unit': self.room_charge_total,
            }))
        
        # 2. Lavanderia
        for order in self.laundry_order_ids:
            if order.total_amount > 0:
                invoice_lines.append((0, 0, {
                    'name': f"Serviço de Lavanderia - Pedido {order.name}",
                    'quantity': 1.0,
                    'price_unit': order.total_amount,
                }))
                
        # 3. Restaurante
        for order in self.restaurant_order_ids:
            if order.total_amount > 0:
                invoice_lines.append((0, 0, {
                    'name': f"Consumo de Restaurante - Pedido {order.name}",
                    'quantity': 1.0,
                    'price_unit': order.total_amount,
                }))
                
        # 4. Transporte
        for request in self.transport_request_ids:
            if request.charge > 0:
                invoice_lines.append((0, 0, {
                    'name': f"Serviço de Transporte - {request.name} ({request.type})",
                    'quantity': 1.0,
                    'price_unit': request.charge,
                }))
                
        if not invoice_lines:
            raise UserError(_("Não existem consumos a faturar neste Folio."))
            
        # Criar a fatura Odoo (account.move)
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_origin': self.name,
            'invoice_line_ids': invoice_lines,
        })
        
        self.write({
            'invoice_id': invoice.id,
            'status': 'closed',
        })
        
        # Redirecionar para a fatura recém-criada
        return {
            'name': _('Fatura Criada'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_invoice(self):
        self.ensure_one()
        if self.invoice_id:
            return {
                'name': _('Fatura Odoo'),
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': self.invoice_id.id,
                'view_mode': 'form',
                'target': 'current',
            }