from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta

class HotelBooking(models.Model):
    _name = 'hotel.booking'
    _description = 'Reserva de Hotel'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    # Referência da Reserva (Ex: BK/2026/0001)
    name = fields.Char(string='Referência', required=True, copy=False, readonly=True, default=lambda self: 'Nova')
    company_id = fields.Many2one('res.company', string='Hotel/Empresa', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', string='Moeda', default=lambda self: self.env.company.currency_id)
    
    # Informações do Hóspede
    partner_id = fields.Many2one('res.partner', string='Nome do Hóspede Principal', required=True, tracking=True)
    phone = fields.Char(related='partner_id.phone', string='Telefone', readonly=True)
    email = fields.Char(related='partner_id.email', string='Email', readonly=True)
    
    # Datas
    check_in = fields.Date(string='Data de Check-In', required=True, tracking=True)
    check_out = fields.Date(string='Data de Check-Out', required=True, tracking=True)
    nights = fields.Integer(string='Noites', compute='_compute_nights', store=True)
    
    # Capacidade
    adults = fields.Integer(string='Adultos', default=1, required=True)
    children = fields.Integer(string='Crianças', default=0)
    
    # Status (Barra superior verde/vermelha/cinza)
    status = fields.Selection([
        ('draft', 'Rascunho'),
        ('confirmed', 'Confirmado'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('cancelled', 'Cancelado'),
        ('no_show', 'No Show')
    ], string='Status', default='draft', tracking=True)

    # Linhas de Quartos e Hóspedes Registrados
    room_line_ids = fields.One2many('hotel.booking.room.line', 'booking_id', string='Quartos na Reserva')
    guest_line_ids = fields.One2many('hotel.booking.guest.line', 'booking_id', string='Hóspedes Registrados')
    laundry_order_ids = fields.One2many('hotel.laundry.order', 'booking_id', string='Pedidos de Lavanderia')
    restaurant_order_ids = fields.One2many('hotel.restaurant.order', 'booking_id', string='Pedidos de Restaurante')
    transport_request_ids = fields.One2many('hotel.transport.request', 'booking_id', string='Pedidos de Transporte')
    
    # Totais
    total_amount = fields.Float(string='Total', compute='_compute_total', store=True)

    @api.depends('check_in', 'check_out')
    def _compute_nights(self):
        for record in self:
            if record.check_in and record.check_out:
                delta = record.check_out - record.check_in
                record.nights = delta.days if delta.days > 0 else 1
            else:
                record.nights = 1

    @api.depends('room_line_ids.subtotal')
    def _compute_total(self):
        for record in self:
            record.total_amount = sum(line.subtotal for line in record.room_line_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nova') == 'Nova':
                vals['name'] = self.env['ir.sequence'].next_by_code('hotel.booking.seq') or 'Nova'
        return super(HotelBooking, self).create(vals_list)

    @api.constrains('check_in', 'check_out')
    def _check_dates(self):
        for record in self:
            if record.check_in and record.check_out and record.check_out <= record.check_in:
                raise ValidationError(_("A data de Check-Out deve ser posterior à data de Check-In."))

    def action_confirm(self):
        for record in self:
            record.status = 'confirmed'
        self._update_related_rooms_status()

    def action_check_in(self):
        for record in self:
            record.status = 'checked_in'
            # Auto-gerar Folio se não existir
            existing_folio = self.env['hotel.folio'].search([('booking_id', '=', record.id)], limit=1)
            if not existing_folio:
                self.env['hotel.folio'].create({
                    'name': f"FOL/{record.name.split('/')[-1]}" if '/' in record.name else f"FOL/{record.name}",
                    'booking_id': record.id,
                })
        self._update_related_rooms_status()

    def action_check_out(self):
        for record in self:
            record.status = 'checked_out'
        self._update_related_rooms_status()

    def action_cancel(self):
        for record in self:
            record.status = 'cancelled'
        self._update_related_rooms_status()

    def _update_related_rooms_status(self):
        for record in self:
            rooms = record.room_line_ids.mapped('room_id')
            if rooms:
                rooms.action_update_room_statuses()


class HotelBookingRoomLine(models.Model):
    _name = 'hotel.booking.room.line'
    _description = 'Linha de Quarto na Reserva'

    booking_id = fields.Many2one('hotel.booking', string='Reserva')
    company_id = fields.Many2one('res.company', related='booking_id.company_id', string='Hotel/Empresa', store=True, readonly=True)
    room_id = fields.Many2one('hotel.room', string='Quarto', required=True)
    room_type_id = fields.Many2one(related='room_id.room_type_id', string='Tipo')
    check_in = fields.Date(related='booking_id.check_in', string='Check-In')
    nights = fields.Integer(related='booking_id.nights', string='Noites')
    price_unit = fields.Float(string='Taxa/Noite', required=True, compute='_compute_price_unit', readonly=False, store=True)
    subtotal = fields.Float(string='Subtotal', compute='_compute_subtotal', store=True)

    @api.depends('room_id')
    def _compute_price_unit(self):
        for line in self:
            if line.room_id and line.room_id.room_type_id:
                line.price_unit = line.room_id.room_type_id.base_price
            else:
                line.price_unit = 0.0

    @api.constrains('room_id', 'booking_id.check_in', 'booking_id.check_out', 'booking_id.status')
    def _check_room_availability(self):
        for line in self:
            if not line.room_id or not line.booking_id.check_in or not line.booking_id.check_out:
                continue
            if line.booking_id.status not in ('confirmed', 'checked_in'):
                continue
            # Procurar conflitos de reservas ativas para o mesmo quarto
            overlapping = self.env['hotel.booking.room.line'].search([
                ('id', '!=', line.id),
                ('room_id', '=', line.room_id.id),
                ('booking_id.status', 'in', ['confirmed', 'checked_in']),
                ('booking_id.check_in', '<', line.booking_id.check_out),
                ('booking_id.check_out', '>', line.booking_id.check_in),
            ])
            if overlapping:
                raise ValidationError(_("O quarto %s já está reservado ou ocupado no período selecionado pela reserva %s.") % (
                    line.room_id.name, overlapping[0].booking_id.name
                ))

    @api.depends('nights', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.nights * line.price_unit


class HotelBookingGuestLine(models.Model):
    _name = 'hotel.booking.guest.line'
    _description = 'Hóspede Registrado'

    booking_id = fields.Many2one('hotel.booking', string='Reserva')
    company_id = fields.Many2one('res.company', related='booking_id.company_id', string='Hotel/Empresa', store=True, readonly=True)
    name = fields.Char(string='Nome do Hóspede', required=True)
    room_id = fields.Many2one('hotel.room', string='Quarto Alocado')
    document_type = fields.Selection([
        ('passport', 'Passaporte'),
        ('national_id', 'Bilhete de Identidade / RG'),
        ('driver_license', 'Carta de Condução')
    ], string='Tipo de Documento', required=True)
    document_number = fields.Char(string='Nº do Documento', required=True)