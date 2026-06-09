from odoo import models, fields, api

class HotelFloor(models.Model):
    _name = 'hotel.floor'
    _description = 'Andar do Hotel'
    _order = 'sequence, name'

    name = fields.Char(string='Nome do Andar', required=True)
    sequence = fields.Integer(string='Sequência', default=10)
    company_id = fields.Many2one('res.company', string='Hotel/Empresa', default=lambda self: self.env.company, required=True)


class HotelRoomType(models.Model):
    _name = 'hotel.room.type'
    _description = 'Tipo de Quarto'

    name = fields.Char(string='Tipo (Ex: Standard, Deluxe)', required=True)
    base_price = fields.Float(string='Preço Base por Noite', required=True, default=0.0)
    description = fields.Text(string='Descrição')
    company_id = fields.Many2one('res.company', string='Hotel/Empresa', default=lambda self: self.env.company, required=True)


class HotelRoom(models.Model):
    _name = 'hotel.room'
    _description = 'Quarto de Hotel'
    _inherit = ['mail.thread', 'mail.activity.mixin'] # Para termos histórico de mudanças
    _order = 'name'

    name = fields.Char(string='Número/Nome do Quarto', required=True, tracking=True)
    floor_id = fields.Many2one('hotel.floor', string='Andar', required=True, tracking=True)
    room_type_id = fields.Many2one('hotel.room.type', string='Tipo de Quarto', required=True, tracking=True)
    
    # Baseado nas cores da sua imagem: Vacant (Verde), Reserved (Laranja), Occupied (Vermelho)
    status = fields.Selection([
        ('vacant', 'Livre'),
        ('reserved', 'Reservado'),
        ('occupied', 'Ocupado')
    ], string='Status', default='vacant', required=True, tracking=True)

    capacity = fields.Integer(string='Capacidade Máxima', default=2)
    is_active = fields.Boolean(string='Ativo', default=True)
    company_id = fields.Many2one('res.company', string='Hotel/Empresa', default=lambda self: self.env.company, required=True)

    # Comodidades (Facilities)
    has_wifi = fields.Boolean(string='Wi-Fi')
    has_minibar = fields.Boolean(string='Minibar')
    has_jacuzzi = fields.Boolean(string='Jacuzzi')
    has_balcony = fields.Boolean(string='Varanda')

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        """ Isso garante que as 3 colunas de status sempre apareçam no Kanban, mesmo vazias """
        return ['vacant', 'reserved', 'occupied']

    @api.model
    def action_update_room_statuses(self):
        """ Atualiza o status de todos os quartos com base nas reservas de hoje """
        today = fields.Date.today()
        rooms = self.search([])
        for room in rooms:
            # 1. Verificar se há reserva em check_in ativa hoje neste quarto
            active_booking = self.env['hotel.booking.room.line'].search([
                ('room_id', '=', room.id),
                ('booking_id.status', '=', 'checked_in'),
                ('booking_id.check_in', '<=', today),
                ('booking_id.check_out', '>=', today),
            ], limit=1)
            
            if active_booking:
                room.status = 'occupied'
                continue
                
            # 2. Verificar se há reserva confirmada futura/iniciando hoje
            reserved_booking = self.env['hotel.booking.room.line'].search([
                ('room_id', '=', room.id),
                ('booking_id.status', '=', 'confirmed'),
                ('booking_id.check_in', '<=', today),
                ('booking_id.check_out', '>=', today),
            ], limit=1)
            
            if reserved_booking:
                room.status = 'reserved'
                continue
                
            # 3. Caso contrário, quarto está livre
            room.status = 'vacant'