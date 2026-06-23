from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta

class HotelBooking(models.Model):
    _name = 'hotel.booking'
    _description = 'Reserva de Hotel'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    # Referência da Reserva (Ex: BK/2026/0001)
    name = fields.Char(string='Referência', required=True, copy=False, readonly=True, default='/')
    company_id = fields.Many2one('res.company', string='Hotel/Empresa', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', string='Moeda', default=lambda self: self.env.company.currency_id)
    
    # Informações do Hóspede
    partner_id = fields.Many2one('res.partner', string='Nome do Hóspede Principal', required=True, tracking=True)
    phone = fields.Char(related='partner_id.phone', string='Telefone', readonly=True)
    email = fields.Char(related='partner_id.email', string='Email', readonly=True)
    
    # Datas com hora incluída
    check_in = fields.Datetime(string='Data/Hora de Check-In', required=True, tracking=True)
    check_out = fields.Datetime(string='Data/Hora de Check-Out', required=True, tracking=True)
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
    early_checkout_reason = fields.Text(string='Motivo de Saída Antecipada', tracking=True)

    # Linhas de Quartos e Hóspedes Registrados
    room_line_ids = fields.One2many('hotel.booking.room.line', 'booking_id', string='Quartos na Reserva')
    guest_line_ids = fields.One2many('hotel.booking.guest.line', 'booking_id', string='Hóspedes Registrados')
    laundry_order_ids = fields.One2many('hotel.laundry.order', 'booking_id', string='Pedidos de Lavanderia')
    restaurant_order_ids = fields.One2many('hotel.restaurant.order', 'booking_id', string='Pedidos de Restaurante')
    transport_request_ids = fields.One2many('hotel.transport.request', 'booking_id', string='Pedidos de Transporte')
    pos_order_ids = fields.One2many('pos.order', 'booking_id', string='Pedidos do Ponto de Venda (POS)')
    
    # Novos Campos para Inteligência de Negócio Hoteleira
    quarto_id = fields.Many2one('hotel.room', string='Quarto')
    preco_quarto = fields.Monetary(
        string="Preço do Quarto", 
        compute="_compute_preco_quarto", 
        store=True, 
        readonly=False
    )
    numero_noites = fields.Integer(string='Número de Noites', compute='_compute_numero_noites', store=True)
    subtotal_hospedagem = fields.Float(string='Subtotal da Estadia', compute='_compute_subtotal_hospedagem', store=True)

    # Campos Computados para Extrato de Consumo Geral
    total_lavandaria = fields.Float(string='Total Lavandaria', compute='_compute_total_servicos', store=True)
    total_restaurante = fields.Float(string='Total Restaurante', compute='_compute_total_servicos', store=True)
    total_transporte = fields.Float(string='Total Transporte', compute='_compute_total_servicos', store=True)
    total_pos = fields.Float(string='Total POS', compute='_compute_total_servicos', store=True)
    total_fatura_quarto = fields.Float(string='Total Geral da Conta', compute='_compute_total_servicos', store=True)

    # Campo para contagem no Smart Button
    consumos_count = fields.Integer(string='Consumos', compute='_compute_consumos_count')

    # Totais
    total_amount = fields.Float(string='Total Sem Imposto', compute='_compute_total', store=True)
    total_tax = fields.Float(string='Imposto', compute='_compute_total', store=True)
    total_amount_with_tax = fields.Float(string='Total com Imposto', compute='_compute_total', store=True)

    @api.depends('check_in', 'check_out')
    def _compute_numero_noites(self):
        for record in self:
            if record.check_in and record.check_out:
                delta = record.check_out.date() - record.check_in.date()
                record.numero_noites = delta.days if delta.days > 0 else 0
            else:
                record.numero_noites = 0

    @api.depends('quarto_id')
    def _compute_preco_quarto(self):
        for reg in self:
            if reg.quarto_id:
                try:
                    reg.preco_quarto = reg.quarto_id.room_type_id.base_price or getattr(reg.quarto_id, 'list_price', 0.0) or 0.0
                except:
                    reg.preco_quarto = getattr(reg.quarto_id, 'list_price', 0.0) or 0.0
            else:
                reg.preco_quarto = 0.0

    @api.onchange('quarto_id')
    def _onchange_quarto_id(self):
        if self.quarto_id:
            try:
                self.preco_quarto = self.quarto_id.room_type_id.base_price or getattr(self.quarto_id, 'list_price', 0.0) or 0.0
            except:
                self.preco_quarto = getattr(self.quarto_id, 'list_price', 0.0) or 0.0
            
            # Sincroniza com room_line_ids
            if not self.room_line_ids:
                self.room_line_ids = [(0, 0, {
                    'room_id': self.quarto_id.id,
                    'price_unit': self.preco_quarto,
                })]
            else:
                self.room_line_ids[0].room_id = self.quarto_id.id
                self.room_line_ids[0].price_unit = self.preco_quarto

    @api.onchange('room_line_ids')
    def _onchange_room_line_ids(self):
        if self.room_line_ids:
            line = self.room_line_ids[0]
            if line.room_id and line.room_id != self.quarto_id:
                self.quarto_id = line.room_id
                self.preco_quarto = line.price_unit

    @api.depends('preco_quarto', 'numero_noites')
    def _compute_subtotal_hospedagem(self):
        for record in self:
            record.subtotal_hospedagem = (record.preco_quarto or 0.0) * (record.numero_noites or 0)

    @api.depends(
        'laundry_order_ids.total_geral', 
        'restaurant_order_ids.total_geral', 
        'transport_request_ids.total_geral',
        'pos_order_ids.amount_total',
        'subtotal_hospedagem'
    )
    def _compute_total_servicos(self):
        for record in self:
            record.total_lavandaria = sum(order.total_geral for order in record.laundry_order_ids)
            record.total_restaurante = sum(order.total_geral for order in record.restaurant_order_ids)
            record.total_transporte = sum(request.total_geral for request in record.transport_request_ids)
            record.total_pos = sum(order.amount_total for order in record.pos_order_ids)
            record.total_fatura_quarto = (
                (record.subtotal_hospedagem or 0.0) +
                record.total_lavandaria +
                record.total_restaurante +
                record.total_transporte +
                record.total_pos
            )

    @api.depends('laundry_order_ids', 'restaurant_order_ids', 'transport_request_ids', 'pos_order_ids')
    def _compute_consumos_count(self):
        for record in self:
            laundry_count = len(record.laundry_order_ids)
            restaurant_count = len(record.restaurant_order_ids)
            transport_count = len(record.transport_request_ids)
            pos_count = len(record.pos_order_ids)
            record.consumos_count = laundry_count + restaurant_count + transport_count + pos_count

    def action_view_consumos(self):
        self.ensure_one()
        folio = self.env['hotel.folio'].search([('booking_id', '=', self.id)], limit=1)
        if not folio:
            folio = self.env['hotel.folio'].create({
                'name': f"FOL/{self.name.split('/')[-1]}" if '/' in self.name else f"FOL/{self.name}",
                'booking_id': self.id,
            })
        return {
            'name': _('Consumos / Fólio'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.folio',
            'res_id': folio.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.depends('check_in', 'check_out')
    def _compute_nights(self):
        for record in self:
            if record.check_in and record.check_out:
                delta = record.check_out.date() - record.check_in.date()
                record.nights = delta.days if delta.days > 0 else 1
            else:
                record.nights = 1

    @api.depends('room_line_ids.subtotal', 'room_line_ids.price_tax', 'room_line_ids.price_total')
    def _compute_total(self):
        for record in self:
            record.total_amount = sum(line.subtotal for line in record.room_line_ids)
            record.total_tax = sum(line.price_tax for line in record.room_line_ids)
            record.total_amount_with_tax = sum(line.price_total for line in record.room_line_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('hotel.booking') or '/'
        return super(HotelBooking, self).create(vals_list)

    def write(self, vals):
        for record in self:
            if record.status in ('checked_out', 'cancelled', 'no_show') and not self.env.context.get('bypass_status_check'):
                raise ValidationError(_("Não é permitido alterar uma reserva já concluída, cancelada ou registada como No Show."))
            if record.status in ('confirmed', 'checked_in') and not self.env.context.get('bypass_status_check'):
                if 'partner_id' in vals:
                    raise ValidationError(_("Não é permitido alterar o hóspede principal de uma reserva já confirmada ou ativa."))
        return super(HotelBooking, self).write(vals)

    @api.constrains('check_in', 'check_out')
    def _check_dates(self):
        for record in self:
            if record.check_in and record.check_out and record.check_out <= record.check_in:
                raise ValidationError(_("A data e hora de Check-Out deve ser posterior à data e hora de Check-In."))

    @api.constrains('check_in', 'check_out', 'partner_id', 'status')
    def _check_partner_overlapping_bookings(self):
        for booking in self:
            if not booking.partner_id or not booking.check_in or not booking.check_out:
                continue
            if booking.status not in ('confirmed', 'checked_in'):
                continue
            overlapping = self.search([
                ('id', '!=', booking.id),
                ('partner_id', '=', booking.partner_id.id),
                ('status', 'in', ('confirmed', 'checked_in')),
                ('check_in', '<', booking.check_out),
                ('check_out', '>', booking.check_in),
            ])
            if overlapping:
                raise ValidationError(_("O hóspede %s já possui uma reserva ativa (%s) no mesmo período (de %s a %s).") % (
                    booking.partner_id.name,
                    overlapping[0].name,
                    overlapping[0].check_in,
                    overlapping[0].check_out
                ))

    @api.constrains('quarto_id', 'adults', 'children')
    @api.onchange('quarto_id', 'adults', 'children')
    def _check_occupants_capacity(self):
        for record in self:
            if record.quarto_id and (record.adults + record.children) > record.quarto_id.capacity:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Informação sobre Capacidade'),
                        'message': _('O quarto selecionado não permite este número de ocupantes. Por favor, verifique a capacidade máxima do quarto.'),
                        'type': 'info',
                        'sticky': False,
                    }
                }

    @api.constrains('check_in', 'check_out', 'room_line_ids', 'status')
    def _check_room_availability(self):
        for booking in self:
            if booking.status not in ('confirmed', 'checked_in'):
                continue
            for line in booking.room_line_ids:
                if not line.room_id or not booking.check_in or not booking.check_out:
                    continue
                overlapping = self.env['hotel.booking.room.line'].search([
                    ('id', '!=', line.id),
                    ('room_id', '=', line.room_id.id),
                    ('booking_id.status', 'in', ['confirmed', 'checked_in']),
                    ('booking_id.check_in', '<', booking.check_out),
                    ('booking_id.check_out', '>', booking.check_in),
                ])
                if overlapping:
                    raise ValidationError(_("O quarto %s já está reservado ou ocupado no período selecionado pela reserva %s.") % (
                        line.room_id.name, overlapping[0].booking_id.name
                    ))

    def action_confirm(self):
        for record in self:
            record.status = 'confirmed'
            # Enviar e-mail de confirmação automaticamente ao hóspede
            template = self.env.ref('dl_hotel_management.email_template_hotel_booking_confirmation', raise_if_not_found=False)
            if template and record.partner_id.email:
                template.send_mail(record.id, force_send=False)
        self._update_related_rooms_status()

    def action_send_booking_confirmation_email(self):
        self.ensure_one()
        template = self.env.ref('dl_hotel_management.email_template_hotel_booking_confirmation', raise_if_not_found=False)
        if template and self.partner_id.email:
            template.send_mail(self.id, force_send=True)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Sucesso'),
                    'message': _('E-mail de confirmação de reserva enviado com sucesso para %s.') % self.partner_id.email,
                    'sticky': False,
                    'type': 'success',
                }
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Aviso'),
                'message': _('Não foi possível enviar o e-mail. Verifique se o hóspede possui um endereço de e-mail válido registado.'),
                'sticky': False,
                'type': 'warning',
            }
        }

    def action_check_in(self):
        today = fields.Date.context_today(self)
        for record in self:
            if fields.Date.to_date(record.check_in) > today:
                from odoo.tools import format_date
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Informação sobre Check-In'),
                        'message': _('Não é possível realizar o Check-In hoje. Este hóspede tem entrada agendada apenas para o dia %s.') % format_date(self.env, record.check_in),
                        'type': 'info',
                        'sticky': False,
                    }
                }
            
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
        today = fields.Date.context_today(self)
        for record in self:
            if fields.Date.to_date(record.check_out) > today:
                if not record.early_checkout_reason:
                    from odoo.tools import format_date
                    raise UserError(_("Não é possível realizar o Check-Out antes da data agendada (%s). Em caso de saída antecipada/desistência, por favor preencha o campo 'Motivo de Saída Antecipada' antes de proceder.") % format_date(self.env, record.check_out))
            
            record.status = 'checked_out'
            # Marcar quartos associados como Sujos (dirty) para limpeza
            for line in record.room_line_ids:
                line.room_id.housekeeping_status = 'dirty'
            # Auto-finalizar os serviços associados que ainda não estão concluídos
            if record.laundry_order_ids:
                record.laundry_order_ids.filtered(lambda l: l.status != 'delivered').write({'status': 'delivered'})
            if record.restaurant_order_ids:
                record.restaurant_order_ids.filtered(lambda r: r.status != 'delivered').write({'status': 'delivered'})
            if record.transport_request_ids:
                record.transport_request_ids.filtered(lambda t: t.status != 'completed').write({'status': 'completed'})
            
            # Enviar e-mail de agradecimento (Check-out/Consumos)
            template = self.env.ref('dl_hotel_management.email_template_hotel_checkout_thank_you', raise_if_not_found=False)
            if template and record.partner_id.email:
                template.send_mail(record.id, force_send=False)
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

    def action_print_reserva(self):
        self.ensure_one()
        return self.env.ref('dl_hotel_management.action_report_hotel_booking').report_action(self)

    def action_print_bi_report(self):
        domain = self.env.context.get('active_domain', [])
        records = self.search(domain)
        if not records:
            records = self.search([])
        return self.env.ref('dl_hotel_management.action_report_bi_ocupacao').report_action(records)

    @api.model
    def cron_auto_checkin(self):
        """
        Cron job to automatically check-in confirmed bookings that have reached their check-in time.
        """
        now = fields.Datetime.now()
        bookings_to_checkin = self.search([
            ('status', '=', 'confirmed'),
            ('check_in', '<=', now)
        ])
        for booking in bookings_to_checkin:
            booking.action_check_in()



class HotelBookingRoomLine(models.Model):
    _name = 'hotel.booking.room.line'
    _description = 'Linha de Quarto na Reserva'

    booking_id = fields.Many2one('hotel.booking', string='Reserva')
    company_id = fields.Many2one('res.company', related='booking_id.company_id', string='Hotel/Empresa', store=True, readonly=True)
    room_id = fields.Many2one('hotel.room', string='Quarto', required=True)
    room_type_id = fields.Many2one(related='room_id.room_type_id', string='Tipo')
    check_in = fields.Datetime(related='booking_id.check_in', string='Check-In')
    nights = fields.Integer(related='booking_id.nights', string='Noites')
    price_unit = fields.Float(string='Taxa/Noite', required=True, compute='_compute_price_unit', readonly=False, store=True)
    tax_id = fields.Many2one('account.tax', string='Imposto', required=True, compute='_compute_tax_id', readonly=False, store=True)
    subtotal = fields.Float(string='Subtotal', compute='_compute_subtotal', store=True)
    price_tax = fields.Float(string='Valor do Imposto', compute='_compute_subtotal', store=True)
    price_total = fields.Float(string='Total com Imposto', compute='_compute_subtotal', store=True)

    @api.depends('room_id')
    def _compute_price_unit(self):
        for line in self:
            if line.room_id and line.room_id.room_type_id:
                line.price_unit = line.room_id.room_type_id.base_price
            else:
                line.price_unit = 0.0

    @api.depends('room_id')
    def _compute_tax_id(self):
        for line in self:
            if line.room_id and line.room_id.room_type_id and line.room_id.room_type_id.tax_id:
                line.tax_id = line.room_id.room_type_id.tax_id
            else:
                line.tax_id = False

    @api.depends('nights', 'price_unit', 'tax_id')
    def _compute_subtotal(self):
        for line in self:
            if line.tax_id:
                currency = line.booking_id.currency_id or line.company_id.currency_id or self.env.company.currency_id
                taxes = line.tax_id.compute_all(
                    line.price_unit,
                    currency,
                    line.nights,
                    partner=line.booking_id.partner_id
                )
                line.subtotal = taxes['total_excluded']
                line.price_total = taxes['total_included']
                line.price_tax = taxes['total_included'] - taxes['total_excluded']
            else:
                line.subtotal = line.nights * line.price_unit
                line.price_total = line.subtotal
                line.price_tax = 0.0


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