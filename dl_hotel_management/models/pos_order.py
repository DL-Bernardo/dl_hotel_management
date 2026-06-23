# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    is_hotel_charge = fields.Boolean(
        string='Cobrar no Quarto',
        default=False,
        help='Ative esta opção para permitir que as compras pagas com este método de pagamento sejam integradas diretamente no Folio da reserva do hóspede.'
    )

class PosOrder(models.Model):
    _inherit = 'pos.order'

    booking_id = fields.Many2one(
        'hotel.booking',
        string='Reserva Hoteleira',
        ondelete='set null',
        help='Reserva associada para faturação do consumo no Folio do hotel.'
    )

    def _process_payment_lines(self, pos_order, order, pos_session, draft):
        res = super(PosOrder, self)._process_payment_lines(pos_order, order, pos_session, draft)
        for payment in order.payment_ids:
            if payment.payment_method_id.is_hotel_charge:
                # Procurar por uma reserva ativa (Checked In) do hóspede/parceiro selecionado no POS
                if order.partner_id:
                    booking = self.env['hotel.booking'].search([
                        ('partner_id', '=', order.partner_id.id),
                        ('status', '=', 'checked_in')
                    ], limit=1)
                    if booking:
                        order.write({'booking_id': booking.id})
                        # Postar mensagem no chatter da reserva para alertar a recepção
                        booking.message_post(body=_(
                            "Consumo de Ponto de Venda (POS) cobrado no quarto: Pedido %s no valor total de %s."
                        ) % (order.name, order.amount_total))
                break
        return res
