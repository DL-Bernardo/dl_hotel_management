from odoo import models, fields, api, _, Command
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
    pos_order_ids = fields.One2many(related='booking_id.pos_order_ids', string='Pedidos do POS', readonly=True)
    
    # Ligação com a fatura nativa do Odoo
    invoice_id = fields.Many2one('account.move', string='Fatura Odoo', ondelete='restrict', readonly=True, copy=False)
    company_id = fields.Many2one('res.company', related='booking_id.company_id', string='Hotel/Empresa', store=True, readonly=True)
    
    # Em um cenário real, estas linhas seriam auto-calculadas. Para o protótipo, criamos ligações textuais simples.
    room_charge_total = fields.Float(related='booking_id.total_amount', string='Total do Quarto')
    
    grand_total = fields.Float(string='Total Geral', compute='_compute_grand_total', store=True)

    @api.depends('room_charge_total', 'booking_id.laundry_order_ids.total_amount', 'booking_id.restaurant_order_ids.total_amount', 'booking_id.transport_request_ids.charge', 'pos_order_ids.amount_total')
    def _compute_grand_total(self):
        for folio in self:
            laundry_total = sum(order.total_amount for order in folio.laundry_order_ids)
            restaurant_total = sum(order.total_amount for order in folio.restaurant_order_ids)
            transport_total = sum(request.charge for request in folio.transport_request_ids)
            pos_total = sum(order.amount_total for order in folio.pos_order_ids)
            folio.grand_total = folio.room_charge_total + laundry_total + restaurant_total + transport_total + pos_total

    def _get_or_create_hotel_product(self, xml_id, code, name):
        try:
            product = self.env.ref(xml_id)
            if product:
                return product
        except ValueError:
            pass
        product = self.env['product.product'].search([('default_code', '=', code), ('company_id', 'in', [self.company_id.id, False])], limit=1)
        if not product:
            account = self.env['account.account'].search([
                ('account_type', '=', 'income'),
                ('company_id', '=', self.company_id.id)
            ], limit=1)
            product = self.env['product.product'].create({
                'name': name,
                'default_code': code,
                'type': 'service',
                'property_account_income_id': account.id if account else False,
                'company_id': self.company_id.id,
                'sale_line_warn': 'no-message',
            })
        return product

    def action_create_invoice(self):
        self.ensure_one()
        if self.invoice_id:
            raise UserError(_("Já existe uma fatura criada para este Folio."))
        if not self.partner_id:
            raise UserError(_("A reserva não possui um Hóspede associado."))

        # --- Validações de Conformidade Fiscal AGT (Angola) ---
        partner = self.partner_id
        errors = []
        if not partner.vat:
            errors.append(_("- NIF (Nº de Contribuinte) ausente. Adicione o NIF do cliente (ou '999999999' para Consumidor Final)."))
        if not partner.street:
            errors.append(_("- Morada (Rua/Bairro) ausente. A morada é obrigatória para a faturação certificada."))
        if not partner.country_id:
            errors.append(_("- País de residência ausente. É obrigatório selecionar o país do hóspede."))
            
        if errors:
            error_msg = _(
                "Erro de Conformidade Fiscal (AGT):\n"
                "Para emitir uma fatura válida para o hóspede %s, corrija os seguintes campos na ficha do contacto:\n%s"
            ) % (partner.name, "\n".join(errors))
            raise UserError(error_msg)
        # ------------------------------------------------------
        
        invoice_lines = []
        
        # 1. Hospedagem (uma linha por quarto da reserva com o respetivo imposto)
        for line in self.booking_id.room_line_ids:
            if line.subtotal > 0:
                product = self._get_or_create_hotel_product('dl_hotel_management.prod_hospedagem', 'HOTEL_HOSP', 'Serviço de Hospedagem')
                invoice_lines.append(Command.create({
                    'product_id': product.id,
                    'name': f"Hospedagem - Reserva {self.booking_id.name} (Quarto {line.room_id.name}, {line.nights} noites)",
                    'quantity': 1.0,
                    'price_unit': line.subtotal,
                    'tax_ids': [Command.set([line.tax_id.id])] if line.tax_id else [],
                }))
        
        # 2. Lavanderia
        for order in self.laundry_order_ids:
            for line in order.line_ids:
                if line.subtotal > 0:
                    product = self._get_or_create_hotel_product('dl_hotel_management.prod_lavandaria', 'HOTEL_LND', 'Serviço de Lavandaria')
                    invoice_lines.append(Command.create({
                        'product_id': product.id,
                        'name': f"Serviço de Lavandaria - {line.name} (Reserva {self.booking_id.name}, Pedido {order.name})",
                        'quantity': float(line.qty),
                        'price_unit': line.price,
                        'tax_ids': [Command.set([line.tax_id.id])] if line.tax_id else [],
                    }))
                
        # 3. Restaurante
        for order in self.restaurant_order_ids:
            for line in order.line_ids:
                if line.subtotal > 0:
                    product = self._get_or_create_hotel_product('dl_hotel_management.prod_restaurante', 'HOTEL_RST', 'Serviço de Restaurante')
                    invoice_lines.append(Command.create({
                        'product_id': product.id,
                        'name': f"Serviço de Restaurante - {line.name} (Reserva {self.booking_id.name}, Pedido {order.name})",
                        'quantity': float(line.qty),
                        'price_unit': line.price,
                        'tax_ids': [Command.set([line.tax_id.id])] if line.tax_id else [],
                    }))
                
        # 4. Transporte
        for request in self.transport_request_ids:
            if request.charge > 0:
                product = self._get_or_create_hotel_product('dl_hotel_management.prod_transporte', 'HOTEL_TRN', 'Serviço de Transporte')
                invoice_lines.append(Command.create({
                    'product_id': product.id,
                    'name': f"Serviço de Transporte - {request.name} (Reserva {self.booking_id.name}, {request.tipo_trajeto})",
                    'quantity': 1.0,
                    'price_unit': request.charge,
                    'tax_ids': [Command.set([request.tax_id.id])] if request.tax_id else [],
                }))
                
        # 5. Ponto de Venda (POS)
        for order in self.pos_order_ids:
            for line in order.lines:
                if line.price_subtotal_incl > 0:
                    product = self._get_or_create_hotel_product('dl_hotel_management.prod_pos', 'HOTEL_POS', 'Consumos do Ponto de Venda')
                    taxes = line.tax_ids_after_fiscal_position or line.tax_ids
                    invoice_lines.append(Command.create({
                        'product_id': product.id,
                        'name': f"Consumo POS - {line.product_id.name} (Reserva {self.booking_id.name}, Pedido {order.name})",
                        'quantity': line.qty,
                        'price_unit': line.price_unit,
                        'discount': line.discount,
                        'tax_ids': [Command.set(taxes.ids)] if taxes else [],
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