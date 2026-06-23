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
    tax_id = fields.Many2one('account.tax', string='Imposto', required=True, domain=[('type_tax_use', '=', 'sale')])
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

    housekeeping_status = fields.Selection([
        ('dirty', 'Sujo'),
        ('cleaning', 'Em Limpeza'),
        ('clean', 'Limpo'),
        ('inspected', 'Inspecionado')
    ], string='Estado de Limpeza', default='clean', tracking=True)

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
        """ Atualiza o status de todos os quartos com base nas reservas de hoje de forma eficiente """
        from datetime import datetime, time
        today = fields.Date.today()
        today_start = datetime.combine(today, time.min)
        today_end = datetime.combine(today, time.max)
        
        rooms = self.search([])
        
        # 1. Procurar todas as reservas que se sobrepõem com hoje em uma única consulta
        overlapping_lines = self.env['hotel.booking.room.line'].search([
            ('booking_id.status', 'in', ['confirmed', 'checked_in']),
            ('booking_id.check_in', '<=', today_end),
            ('booking_id.check_out', '>=', today_start),
        ])
        
        # 2. Agrupar em memória os estados por quarto
        status_by_room = {}
        for line in overlapping_lines:
            r_id = line.room_id.id
            b_status = line.booking_id.status
            if b_status == 'checked_in':
                status_by_room[r_id] = 'occupied'
            elif b_status == 'confirmed' and status_by_room.get(r_id) != 'occupied':
                status_by_room[r_id] = 'reserved'
                
        # 3. Atualizar status dos quartos
        for room in rooms:
            new_status = status_by_room.get(room.id, 'vacant')
            if room.status != new_status:
                room.status = new_status