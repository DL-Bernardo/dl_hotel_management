from odoo import models, fields, api

class HotelLaundryOrder(models.Model):
    _name = 'hotel.laundry.order'
    _description = 'Pedido de Lavanderia'

    name = fields.Char(string='Referência', default='Novo', readonly=True)
    room_id = fields.Many2one('hotel.room', string='Quarto', required=True)
    booking_id = fields.Many2one('hotel.booking', string='Reserva', ondelete='restrict')
    company_id = fields.Many2one('res.company', string='Hotel/Empresa', default=lambda self: self.env.company, required=True)
    date = fields.Date(string='Data', default=fields.Date.context_today)
    status = fields.Selection([
        ('draft', 'Rascunho'), ('confirmed', 'Confirmado'), 
        ('pickup', 'Recolha'), ('in_process', 'Em Processo'), ('delivered', 'Entregue')
    ], string='Status', default='draft')

    @api.onchange('room_id')
    def _onchange_room_id_find_booking(self):
        if self.room_id:
            booking = self.env['hotel.booking'].search([
                ('room_line_ids.room_id', '=', self.room_id.id),
                ('status', '=', 'checked_in')
            ], limit=1)
            self.booking_id = booking.id if booking else False
        else:
            self.booking_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('room_id') and not vals.get('booking_id'):
                booking = self.env['hotel.booking'].search([
                    ('room_line_ids.room_id', '=', vals['room_id']),
                    ('status', '=', 'checked_in')
                ], limit=1)
                if booking:
                    vals['booking_id'] = booking.id
        return super(HotelLaundryOrder, self).create(vals_list)

    def write(self, vals):
        if 'room_id' in vals and not vals.get('booking_id'):
            booking = self.env['hotel.booking'].search([
                ('room_line_ids.room_id', '=', vals['room_id']),
                ('status', '=', 'checked_in')
            ], limit=1)
            if booking:
                vals['booking_id'] = booking.id
        return super(HotelLaundryOrder, self).write(vals)
    
    line_ids = fields.One2many('hotel.laundry.line', 'order_id', string='Itens')
    total_amount = fields.Float(string='Total', compute='_compute_total', store=True)

    @api.depends('line_ids.subtotal')
    def _compute_total(self):
        for order in self:
            order.total_amount = sum(line.subtotal for line in order.line_ids)

class HotelLaundryLine(models.Model):
    _name = 'hotel.laundry.line'
    _description = 'Linha de Lavanderia'

    order_id = fields.Many2one('hotel.laundry.order')
    name = fields.Char(string='Item (Ex: Camisa, Vestido)', required=True)
    qty = fields.Integer(string='Qtd', default=1)
    price = fields.Float(string='Preço')
    subtotal = fields.Float(string='Subtotal', compute='_compute_subtotal', store=True)

    @api.depends('qty', 'price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.qty * line.price

class HotelRestaurantOrder(models.Model):
    _name = 'hotel.restaurant.order'
    _description = 'Pedido de Restaurante'

    name = fields.Char(string='Referência', default='Novo', readonly=True)
    room_id = fields.Many2one('hotel.room', string='Quarto', required=True)
    booking_id = fields.Many2one('hotel.booking', string='Reserva', ondelete='restrict')
    company_id = fields.Many2one('res.company', string='Hotel/Empresa', default=lambda self: self.env.company, required=True)
    date = fields.Date(string='Data', default=fields.Date.context_today)
    status = fields.Selection([
        ('draft', 'Rascunho'), ('confirmed', 'Confirmado'), 
        ('in_prep', 'Em Preparação'), ('delivered', 'Entregue')
    ], string='Status', default='draft')

    @api.onchange('room_id')
    def _onchange_room_id_find_booking(self):
        if self.room_id:
            booking = self.env['hotel.booking'].search([
                ('room_line_ids.room_id', '=', self.room_id.id),
                ('status', '=', 'checked_in')
            ], limit=1)
            self.booking_id = booking.id if booking else False
        else:
            self.booking_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('room_id') and not vals.get('booking_id'):
                booking = self.env['hotel.booking'].search([
                    ('room_line_ids.room_id', '=', vals['room_id']),
                    ('status', '=', 'checked_in')
                ], limit=1)
                if booking:
                    vals['booking_id'] = booking.id
        return super(HotelRestaurantOrder, self).create(vals_list)

    def write(self, vals):
        if 'room_id' in vals and not vals.get('booking_id'):
            booking = self.env['hotel.booking'].search([
                ('room_line_ids.room_id', '=', vals['room_id']),
                ('status', '=', 'checked_in')
            ], limit=1)
            if booking:
                vals['booking_id'] = booking.id
        return super(HotelRestaurantOrder, self).write(vals)
    
    line_ids = fields.One2many('hotel.restaurant.line', 'order_id', string='Itens')
    total_amount = fields.Float(string='Total', compute='_compute_total', store=True)

    @api.depends('line_ids.subtotal')
    def _compute_total(self):
        for order in self:
            order.total_amount = sum(line.subtotal for line in order.line_ids)

class HotelRestaurantLine(models.Model):
    _name = 'hotel.restaurant.line'
    _description = 'Linha de Restaurante'

    order_id = fields.Many2one('hotel.restaurant.order')
    name = fields.Char(string='Item (Ex: Sopa, Bife)', required=True)
    qty = fields.Integer(string='Qtd', default=1)
    price = fields.Float(string='Preço')
    subtotal = fields.Float(string='Subtotal', compute='_compute_subtotal', store=True)

    @api.depends('qty', 'price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.qty * line.price

class HotelTransportRequest(models.Model):
    _name = 'hotel.transport.request'
    _description = 'Pedido de Transporte'

    name = fields.Char(string='Referência', default='Novo', readonly=True)
    booking_id = fields.Many2one('hotel.booking', string='Reserva', ondelete='restrict')
    company_id = fields.Many2one('res.company', string='Hotel/Empresa', default=lambda self: self.env.company, required=True)
    guest_name = fields.Char(string='Hóspede', required=True)
    type = fields.Selection([('pickup', 'Pickup (Buscar)'), ('drop', 'Drop (Levar)'), ('round', 'Ida e Volta')], string='Tipo', required=True)
    status = fields.Selection([
        ('draft', 'Rascunho'), ('confirmed', 'Confirmado'), 
        ('in_progress', 'Em Progresso'), ('completed', 'Concluído')
    ], string='Status', default='draft')

    @api.onchange('booking_id')
    def _onchange_booking_id_fill_guest(self):
        if self.booking_id and self.booking_id.partner_id:
            self.guest_name = self.booking_id.partner_id.name

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('booking_id') and not vals.get('guest_name'):
                booking = self.env['hotel.booking'].browse(vals['booking_id'])
                if booking.partner_id:
                    vals['guest_name'] = booking.partner_id.name
        return super(HotelTransportRequest, self).create(vals_list)

    def write(self, vals):
        if 'booking_id' in vals and not vals.get('guest_name'):
            booking = self.env['hotel.booking'].browse(vals['booking_id'])
            if booking.partner_id:
                vals['guest_name'] = booking.partner_id.name
        return super(HotelTransportRequest, self).write(vals)
    
    pickup_from = fields.Char(string='Origem')
    drop_at = fields.Char(string='Destino')
    distance = fields.Float(string='Distância (KM)')
    vehicle = fields.Char(string='Veículo')
    driver = fields.Char(string='Motorista')
    charge = fields.Float(string='Custo Total')