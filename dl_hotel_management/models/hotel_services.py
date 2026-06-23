from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class HotelLavanderiaServico(models.Model):
    _name = 'hotel.lavanderia.servico'
    _description = 'Serviço de Lavandaria'

    name = fields.Char(string='Serviço', required=True)
    preco = fields.Float(string='Preço', required=True)
    imposto_id = fields.Many2one('account.tax', string='Imposto', domain=[('type_tax_use', '=', 'sale')])


class HotelLaundryOrder(models.Model):
    _name = 'hotel.laundry.order'
    _description = 'Pedido de Lavanderia'

    name = fields.Char(string='Referência', default='Novo', readonly=True)
    room_id = fields.Many2one('hotel.room', string='Quarto', required=True)
    booking_id = fields.Many2one('hotel.booking', string='Reserva', ondelete='restrict')
    company_id = fields.Many2one('res.company', string='Hotel/Empresa', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Moeda', readonly=True)
    date = fields.Date(string='Data', default=fields.Date.context_today)
    status = fields.Selection([
        ('draft', 'Rascunho'), ('confirmed', 'Confirmado'), 
        ('pickup', 'Recolha'), ('in_process', 'Em Processo'), ('delivered', 'Entregue')
    ], string='Status', default='draft')

    @api.onchange('booking_id')
    def _onchange_booking_id(self):
        if self.booking_id:
            room_line = self.booking_id.room_line_ids[:1]
            self.room_id = room_line.room_id.id if room_line else False
        else:
            self.room_id = False

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
            if vals.get('name', 'Novo') == 'Novo':
                vals['name'] = self.env['ir.sequence'].next_by_code('hotel.laundry.order.seq') or 'Novo'
            if vals.get('booking_id') and not vals.get('room_id'):
                booking = self.env['hotel.booking'].browse(vals['booking_id'])
                room_line = booking.room_line_ids[:1]
                if room_line:
                    vals['room_id'] = room_line.room_id.id
            if vals.get('room_id') and not vals.get('booking_id'):
                booking = self.env['hotel.booking'].search([
                    ('room_line_ids.room_id', '=', vals['room_id']),
                    ('status', '=', 'checked_in')
                ], limit=1)
                if booking:
                    vals['booking_id'] = booking.id
        return super(HotelLaundryOrder, self).create(vals_list)

    def write(self, vals):
        for record in self:
            if record.status != 'draft' and not self.env.context.get('bypass_status_check'):
                protected_fields = ['room_id', 'booking_id', 'date', 'line_ids']
                if any(f in vals for f in protected_fields):
                    raise ValidationError(_("Não é permitido alterar um pedido de lavanderia que já não esteja em rascunho."))
        if 'booking_id' in vals and 'room_id' not in vals:
            booking = self.env['hotel.booking'].browse(vals['booking_id'])
            room_line = booking.room_line_ids[:1]
            if room_line:
                vals['room_id'] = room_line.room_id.id
        if 'room_id' in vals and not vals.get('booking_id'):
            booking = self.env['hotel.booking'].search([
                ('room_line_ids.room_id', '=', vals['room_id']),
                ('status', '=', 'checked_in')
            ], limit=1)
            if booking:
                vals['booking_id'] = booking.id
        return super(HotelLaundryOrder, self).write(vals)

    def action_confirm(self):
        for record in self:
            record.status = 'confirmed'

    def action_pickup(self):
        for record in self:
            record.status = 'pickup'

    def action_process(self):
        for record in self:
            record.status = 'in_process'

    def action_deliver(self):
        for record in self:
            record.status = 'delivered'
    
    def action_print_lavandaria(self):
        return self.env.ref('dl_hotel_management.action_report_hotel_laundry').report_action(self)
    
    line_ids = fields.One2many('hotel.laundry.line', 'order_id', string='Itens')
    total_amount = fields.Float(string='Total', compute='_compute_total', store=True)
    total_imposto = fields.Float(string='Total de Imposto', compute='_compute_total', store=True)
    total_geral = fields.Float(string='Total com Imposto', compute='_compute_total', store=True)

    @api.depends('line_ids.subtotal', 'line_ids.price_tax', 'line_ids.price_total')
    def _compute_total(self):
        for order in self:
            order.total_amount = sum(line.subtotal for line in order.line_ids)
            order.total_imposto = sum(line.price_tax for line in order.line_ids)
            order.total_geral = sum(line.price_total for line in order.line_ids)


class HotelLaundryLine(models.Model):
    _name = 'hotel.laundry.line'
    _description = 'Linha de Lavanderia'

    order_id = fields.Many2one('hotel.laundry.order')
    date = fields.Date(related='order_id.date', store=True, string='Data', readonly=True)
    servico_id = fields.Many2one('hotel.lavanderia.servico', string='Serviço', required=True)
    name = fields.Char(related='servico_id.name', store=True, string='Item')
    qty = fields.Integer(string='Qtd', default=1)
    price = fields.Float(string='Preço')
    tax_id = fields.Many2one('account.tax', string='Imposto', required=True, domain=[('type_tax_use', '=', 'sale')])
    subtotal = fields.Float(string='Subtotal', compute='_compute_subtotal', store=True)
    price_tax = fields.Float(string='Valor do Imposto', compute='_compute_subtotal', store=True)
    price_total = fields.Float(string='Total com Imposto', compute='_compute_subtotal', store=True)

    @api.onchange('servico_id')
    def _onchange_servico_id(self):
        if self.servico_id:
            self.price = self.servico_id.preco
            self.tax_id = self.servico_id.imposto_id

    @api.depends('qty', 'price', 'tax_id')
    def _compute_subtotal(self):
        for line in self:
            if line.tax_id:
                currency = line.order_id.company_id.currency_id or self.env.company.currency_id
                taxes = line.tax_id.compute_all(
                    line.price,
                    currency,
                    line.qty,
                    partner=line.order_id.booking_id.partner_id
                )
                line.subtotal = taxes['total_excluded']
                line.price_total = taxes['total_included']
                line.price_tax = taxes['total_included'] - taxes['total_excluded']
            else:
                line.subtotal = line.qty * line.price
                line.price_total = line.subtotal
                line.price_tax = 0.0

    def action_print_bi_report(self):
        domain = self.env.context.get('active_domain', [])
        records = self.search(domain)
        if not records:
            records = self.search([])
        return self.env.ref('dl_hotel_management.action_report_bi_lavanderia').report_action(records)

class HotelRestauranteServico(models.Model):
    _name = 'hotel.restaurante.servico'
    _description = 'Serviço de Restaurante'

    name = fields.Char(string='Prato/Bebida', required=True)
    preco = fields.Float(string='Preço', required=True)
    imposto_id = fields.Many2one('account.tax', string='Imposto', domain=[('type_tax_use', '=', 'sale')])
    product_id = fields.Many2one('product.product', string='Produto Relacionado no POS', ondelete='set null')

    @api.model_create_multi
    def create(self, vals_list):
        records = super(HotelRestauranteServico, self).create(vals_list)
        for record in records:
            if not record.product_id:
                product_vals = record._prepare_product_values()
                product = self.env['product.product'].create(product_vals)
                record.write({'product_id': product.id})
        return records

    def write(self, vals):
        res = super(HotelRestauranteServico, self).write(vals)
        for record in self:
            if record.product_id:
                product_vals = {}
                if 'name' in vals:
                    product_vals['name'] = vals['name']
                if 'preco' in vals:
                    product_vals['list_price'] = vals['preco']
                if 'imposto_id' in vals:
                    product_vals['taxes_id'] = [(6, 0, [vals['imposto_id']])] if vals['imposto_id'] else [(5, 0, 0)]
                if product_vals:
                    record.product_id.write(product_vals)
            else:
                product_vals = record._prepare_product_values()
                product = self.env['product.product'].create(product_vals)
                record.write({'product_id': product.id})
        return res

    def unlink(self):
        for record in self:
            if record.product_id:
                record.product_id.write({'available_in_pos': False, 'active': False})
        return super(HotelRestauranteServico, self).unlink()

    def _prepare_product_values(self):
        self.ensure_one()
        pos_categ = self.env['pos.category'].search([('name', 'ilike', 'Restaurante')], limit=1)
        if not pos_categ:
            pos_categ = self.env['pos.category'].create({'name': 'Restaurante'})
            
        return {
            'name': self.name,
            'list_price': self.preco,
            'available_in_pos': True,
            'pos_categ_ids': [(6, 0, [pos_categ.id])] if pos_categ else [],
            'detailed_type': 'consu',
            'taxes_id': [(6, 0, [self.imposto_id.id])] if self.imposto_id else [],
        }

    def _register_hook(self):
        super(HotelRestauranteServico, self)._register_hook()
        # Encontrar registos sem product_id e criá-los
        services_without_product = self.search([('product_id', '=', False)])
        for service in services_without_product:
            product_vals = service._prepare_product_values()
            product = self.env['product.product'].create(product_vals)
            service.write({'product_id': product.id})


class HotelRestaurantOrder(models.Model):
    _name = 'hotel.restaurant.order'
    _description = 'Pedido de Restaurante'

    name = fields.Char(string='Referência', default='Novo', readonly=True)
    room_id = fields.Many2one('hotel.room', string='Quarto', required=True)
    booking_id = fields.Many2one('hotel.booking', string='Reserva', ondelete='restrict')
    company_id = fields.Many2one('res.company', string='Hotel/Empresa', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Moeda', readonly=True)
    date = fields.Date(string='Data', default=fields.Date.context_today)
    status = fields.Selection([
        ('draft', 'Rascunho'), ('confirmed', 'Confirmado'), 
        ('in_prep', 'Em Preparação'), ('delivered', 'Entregue')
    ], string='Status', default='draft')

    @api.onchange('booking_id')
    def _onchange_booking_id(self):
        if self.booking_id:
            room_line = self.booking_id.room_line_ids[:1]
            self.room_id = room_line.room_id.id if room_line else False
        else:
            self.room_id = False

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
            if vals.get('name', 'Novo') == 'Novo':
                vals['name'] = self.env['ir.sequence'].next_by_code('hotel.restaurant.order.seq') or 'Novo'
            if vals.get('booking_id') and not vals.get('room_id'):
                booking = self.env['hotel.booking'].browse(vals['booking_id'])
                room_line = booking.room_line_ids[:1]
                if room_line:
                    vals['room_id'] = room_line.room_id.id
            if vals.get('room_id') and not vals.get('booking_id'):
                booking = self.env['hotel.booking'].search([
                    ('room_line_ids.room_id', '=', vals['room_id']),
                    ('status', '=', 'checked_in')
                ], limit=1)
                if booking:
                    vals['booking_id'] = booking.id
        return super(HotelRestaurantOrder, self).create(vals_list)

    def write(self, vals):
        for record in self:
            if record.status != 'draft' and not self.env.context.get('bypass_status_check'):
                protected_fields = ['room_id', 'booking_id', 'date', 'line_ids']
                if any(f in vals for f in protected_fields):
                    raise ValidationError(_("Não é permitido alterar um pedido de restaurante que já não esteja em rascunho."))
        if 'booking_id' in vals and 'room_id' not in vals:
            booking = self.env['hotel.booking'].browse(vals['booking_id'])
            room_line = booking.room_line_ids[:1]
            if room_line:
                vals['room_id'] = room_line.room_id.id
        if 'room_id' in vals and not vals.get('booking_id'):
            booking = self.env['hotel.booking'].search([
                ('room_line_ids.room_id', '=', vals['room_id']),
                ('status', '=', 'checked_in')
            ], limit=1)
            if booking:
                vals['booking_id'] = booking.id
        return super(HotelRestaurantOrder, self).write(vals)

    def action_confirm(self):
        for record in self:
            record.status = 'confirmed'

    def action_in_prep(self):
        for record in self:
            record.status = 'in_prep'

    def action_deliver(self):
        for record in self:
            record.status = 'delivered'
    
    def action_print_restaurante(self):
        return self.env.ref('dl_hotel_management.action_report_hotel_restaurant').report_action(self)
    
    line_ids = fields.One2many('hotel.restaurant.line', 'order_id', string='Itens')
    total_amount = fields.Float(string='Total', compute='_compute_total', store=True)
    total_imposto = fields.Float(string='Total de Imposto', compute='_compute_total', store=True)
    total_geral = fields.Float(string='Total com Imposto', compute='_compute_total', store=True)

    @api.depends('line_ids.subtotal', 'line_ids.price_tax', 'line_ids.price_total')
    def _compute_total(self):
        for order in self:
            order.total_amount = sum(line.subtotal for line in order.line_ids)
            order.total_imposto = sum(line.price_tax for line in order.line_ids)
            order.total_geral = sum(line.price_total for line in order.line_ids)


class HotelRestaurantLine(models.Model):
    _name = 'hotel.restaurant.line'
    _description = 'Linha de Restaurante'

    order_id = fields.Many2one('hotel.restaurant.order')
    date = fields.Date(related='order_id.date', store=True, string='Data', readonly=True)
    servico_id = fields.Many2one('hotel.restaurante.servico', string='Serviço', required=True)
    name = fields.Char(related='servico_id.name', store=True, string='Item')
    qty = fields.Integer(string='Qtd', default=1)
    price = fields.Float(string='Preço')
    tax_id = fields.Many2one('account.tax', string='Imposto', required=True, domain=[('type_tax_use', '=', 'sale')])
    subtotal = fields.Float(string='Subtotal', compute='_compute_subtotal', store=True)
    price_tax = fields.Float(string='Valor do Imposto', compute='_compute_subtotal', store=True)
    price_total = fields.Float(string='Total com Imposto', compute='_compute_subtotal', store=True)

    @api.onchange('servico_id')
    def _onchange_servico_id(self):
        if self.servico_id:
            self.price = self.servico_id.preco
            self.tax_id = self.servico_id.imposto_id

    @api.depends('qty', 'price', 'tax_id')
    def _compute_subtotal(self):
        for line in self:
            if line.tax_id:
                currency = line.order_id.company_id.currency_id or self.env.company.currency_id
                taxes = line.tax_id.compute_all(
                    line.price,
                    currency,
                    line.qty,
                    partner=line.order_id.booking_id.partner_id
                )
                line.subtotal = taxes['total_excluded']
                line.price_total = taxes['total_included']
                line.price_tax = taxes['total_included'] - taxes['total_excluded']
            else:
                line.subtotal = line.qty * line.price
                line.price_total = line.subtotal
                line.price_tax = 0.0

    def action_print_bi_report(self):
        domain = self.env.context.get('active_domain', [])
        records = self.search(domain)
        if not records:
            records = self.search([])
        return self.env.ref('dl_hotel_management.action_report_bi_restaurante').report_action(records)

class HotelTransporteServico(models.Model):
    _name = 'hotel.transporte.servico'
    _description = 'Serviço de Transporte'

    name = fields.Char(string='Serviço de Transporte', required=True)
    preco = fields.Float(string='Preço Base', required=True)
    imposto_id = fields.Many2one('account.tax', string='Imposto', domain=[('type_tax_use', '=', 'sale')])


class HotelTransportRequest(models.Model):
    _name = 'hotel.transport.request'
    _description = 'Pedido de Transporte'

    name = fields.Char(string='Referência', default='Novo', readonly=True)
    booking_id = fields.Many2one('hotel.booking', string='Reserva', ondelete='restrict')
    room_id = fields.Many2one('hotel.room', string='Quarto', required=True)
    company_id = fields.Many2one('res.company', string='Hotel/Empresa', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Moeda', readonly=True)
    guest_name = fields.Char(string='Hóspede', required=True)
    
    status = fields.Selection([
        ('draft', 'Rascunho'), ('confirmed', 'Confirmado'), 
        ('in_progress', 'Em Progresso'), ('completed', 'Concluído')
    ], string='Status', default='draft')

    @api.onchange('booking_id')
    def _onchange_booking_id(self):
        if self.booking_id:
            room_line = self.booking_id.room_line_ids[:1]
            self.room_id = room_line.room_id.id if room_line else False
            if self.booking_id.partner_id:
                self.guest_name = self.booking_id.partner_id.name
        else:
            self.room_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Novo') == 'Novo':
                vals['name'] = self.env['ir.sequence'].next_by_code('hotel.transport.request.seq') or 'Novo'
            if vals.get('booking_id') and not vals.get('room_id'):
                booking = self.env['hotel.booking'].browse(vals['booking_id'])
                room_line = booking.room_line_ids[:1]
                if room_line:
                    vals['room_id'] = room_line.room_id.id
            if vals.get('booking_id') and not vals.get('guest_name'):
                booking = self.env['hotel.booking'].browse(vals['booking_id'])
                if booking.partner_id:
                    vals['guest_name'] = booking.partner_id.name
        return super(HotelTransportRequest, self).create(vals_list)

    def write(self, vals):
        for record in self:
            if record.status != 'draft' and not self.env.context.get('bypass_status_check'):
                protected_fields = [
                    'booking_id', 'room_id', 'guest_name', 'servico_id', 'tipo_trajeto', 
                    'local_origem', 'local_destino', 'data_hora_viagem', 'num_passageiros', 
                    'notas_voo', 'preco_base', 'imposto_id', 'subtotal', 'imposto', 'total_geral'
                ]
                if any(f in vals for f in protected_fields):
                    raise ValidationError(_("Não é permitido alterar um pedido de transporte que já não esteja em rascunho."))
        if 'booking_id' in vals and 'room_id' not in vals:
            booking = self.env['hotel.booking'].browse(vals['booking_id'])
            room_line = booking.room_line_ids[:1]
            if room_line:
                vals['room_id'] = room_line.room_id.id
        if 'booking_id' in vals and not vals.get('guest_name'):
            booking = self.env['hotel.booking'].browse(vals['booking_id'])
            if booking.partner_id:
                vals['guest_name'] = booking.partner_id.name
        return super(HotelTransportRequest, self).write(vals)

    def action_confirm(self):
        for record in self:
            record.status = 'confirmed'

    def action_in_progress(self):
        for record in self:
            record.status = 'in_progress'

    def action_complete(self):
        for record in self:
            record.status = 'completed'
    
    def action_print_transporte(self):
        return self.env.ref('dl_hotel_management.action_report_hotel_transport').report_action(self)
    
    def action_print_bi_report(self):
        domain = self.env.context.get('active_domain', [])
        records = self.search(domain)
        if not records:
            records = self.search([])
        return self.env.ref('dl_hotel_management.action_report_bi_transporte').report_action(records)
    
    # Novos Campos Reestruturados
    servico_id = fields.Many2one('hotel.transporte.servico', string='Serviço', required=True)
    tipo_trajeto = fields.Selection([
        ('pickup', 'Ida / Chegada'), 
        ('dropoff', 'Volta / Partida'), 
        ('tour', 'Passeio / Outro')
    ], string='Tipo de Trajeto', required=True)
    local_origem = fields.Char(string='Local de Origem', required=True)
    local_destino = fields.Char(string='Local de Destino', required=True)
    data_hora_viagem = fields.Datetime(string='Data/Hora da Viagem', required=True)
    num_passageiros = fields.Integer(string='Nº de Passageiros', default=1, required=True)
    notas_voo = fields.Char(string='Notas de Voo')
    
    # Novos Campos de Totais / Preços
    preco_base = fields.Float(string='Preço Base', required=True)
    imposto_id = fields.Many2one('account.tax', string='Imposto', required=True, domain=[('type_tax_use', '=', 'sale')])
    subtotal = fields.Float(string='Subtotal', compute='_compute_totais', store=True)
    imposto = fields.Float(string='Imposto', compute='_compute_totais', store=True)
    total_geral = fields.Float(string='Total com Imposto', compute='_compute_totais', store=True)

    # Compatibilidade com Folio Faturação
    charge = fields.Float(related='subtotal', string='Preço Sem Imposto', store=True)
    tax_id = fields.Many2one(related='imposto_id', string='Imposto Folio', store=True)

    @api.onchange('servico_id')
    def _onchange_servico_id(self):
        if self.servico_id:
            self.preco_base = self.servico_id.preco
            self.imposto_id = self.servico_id.imposto_id

    @api.depends('preco_base', 'imposto_id')
    def _compute_totais(self):
        for reg in self:
            reg.subtotal = reg.preco_base or 0.0
            
            valor_iva = 0.0
            if reg.imposto_id and reg.preco_base:
                taxas = reg.imposto_id.compute_all(reg.preco_base, quantity=1, product=None, partner=None)
                valor_iva = sum(t['amount'] for t in taxas['taxes'])
            
            reg.imposto = valor_iva
            reg.total_geral = reg.subtotal + reg.imposto