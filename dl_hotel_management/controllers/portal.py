# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager

class HotelCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super(HotelCustomerPortal, self)._prepare_home_portal_values(counters)
        if 'booking_count' in counters:
            partner = request.env.user.partner_id
            booking_count = request.env['hotel.booking'].sudo().search_count([
                ('partner_id', '=', partner.id),
                ('status', 'not in', ['cancelled'])
            ])
            values['booking_count'] = booking_count
        return values

    @http.route(['/my/bookings', '/my/bookings/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_bookings(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        Booking = request.env['hotel.booking'].sudo()

        domain = [('partner_id', '=', partner.id), ('status', 'not in', ['cancelled'])]

        # Paginação
        booking_count = Booking.search_count(domain)
        pager = portal_pager(
            url="/my/bookings",
            total=booking_count,
            page=page,
            step=10
        )
        
        bookings = Booking.search(domain, limit=10, offset=pager['offset'], order="check_in desc")

        values.update({
            'bookings': bookings,
            'page_name': 'bookings',
            'pager': pager,
            'default_url': '/my/bookings',
        })
        return request.render("dl_hotel_management.portal_my_bookings", values)

    @http.route(['/my/booking/<int:booking_id>'], type='http', auth="user", website=True)
    def portal_my_booking_detail(self, booking_id, **kw):
        booking = request.env['hotel.booking'].sudo().browse(booking_id)
        if not booking.exists() or booking.partner_id.id != request.env.user.partner_id.id:
            return request.redirect('/my')

        # Buscar fólio e fatura associada em segundo plano
        folio = request.env['hotel.folio'].sudo().search([('booking_id', '=', booking.id)], limit=1)
        invoice = folio.invoice_id if folio else False

        values = {
            'booking': booking,
            'folio': folio,
            'invoice': invoice,
            'page_name': 'booking_detail',
        }
        return request.render("dl_hotel_management.portal_my_booking_detail", values)

    @http.route(['/my/booking/<int:booking_id>/pdf'], type='http', auth="user", website=True)
    def portal_my_booking_pdf(self, booking_id, **kw):
        booking = request.env['hotel.booking'].sudo().browse(booking_id)
        if not booking.exists() or booking.partner_id.id != request.env.user.partner_id.id:
            return request.redirect('/my')

        # Usar sudo para renderizar o PDF e ignorar verificações de segurança do ir.actions.report
        pdf_content, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf('dl_hotel_management.action_report_hotel_booking', [booking.id])

        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf_content)),
            ('Content-Disposition', f'attachment; filename="Confirmacao_Reserva_{booking.name}.pdf"')
        ]
        return request.make_response(pdf_content, headers=pdfhttpheaders)

    @http.route(['/my/vacancies'], type='http', auth="user", website=True)
    def portal_my_vacancies(self, check_in=None, check_out=None, **kw):
        import datetime

        values = self._prepare_portal_layout_values()
        now = datetime.datetime.now()
        
        # Datas padrão (amanhã e depois)
        default_check_in = (now + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        default_check_out = (now + datetime.timedelta(days=2)).strftime('%Y-%m-%d')

        if not check_in:
            check_in = default_check_in
        if not check_out:
            check_out = default_check_out

        check_in_dt = None
        check_out_dt = None
        error_msg = None
        vacancies = []

        try:
            # Tentar analisar as datas
            check_in_date = datetime.datetime.strptime(check_in, '%Y-%m-%d')
            check_out_date = datetime.datetime.strptime(check_out, '%Y-%m-%d')
            
            if check_out_date <= check_in_date:
                error_msg = "A data de Check-Out deve ser posterior à data de Check-In."
            else:
                # Odoo armazena Datetime. Converter para formato datetime com hora padrão (check-in 14:00, check-out 12:00)
                check_in_dt = check_in_date.replace(hour=14, minute=0, second=0)
                check_out_dt = check_out_date.replace(hour=12, minute=0, second=0)
        except ValueError:
            error_msg = "Formato de data inválido. Por favor, use AAAA-MM-DD."

        if not error_msg and check_in_dt and check_out_dt:
            # 1. Procurar todos os quartos ativos
            rooms = request.env['hotel.room'].sudo().search([('is_active', '=', True)])
            
            # 2. Encontrar ocupações sobrepostas
            overlapping_room_lines = request.env['hotel.booking.room.line'].sudo().search([
                ('booking_id.status', 'in', ['confirmed', 'checked_in']),
                ('booking_id.check_in', '<', check_out_dt),
                ('booking_id.check_out', '>', check_in_dt),
            ])
            booked_room_ids = overlapping_room_lines.mapped('room_id.id')
            
            # 3. Filtrar quartos livres
            available_rooms = rooms.filtered(lambda r: r.id not in booked_room_ids)
            
            # 4. Agrupar por tipo de quarto
            room_types = request.env['hotel.room.type'].sudo().search([])
            for rt in room_types:
                rt_rooms = available_rooms.filtered(lambda r: r.room_type_id.id == rt.id)
                if rt_rooms:
                    vacancies.append({
                        'room_type': rt,
                        'available_count': len(rt_rooms),
                        'rooms_list': ", ".join(rt_rooms.mapped('name')),
                        'price': rt.base_price,
                        'capacity': max(rt_rooms.mapped('capacity')) if rt_rooms else 2,
                        'has_wifi': any(rt_rooms.mapped('has_wifi')),
                        'has_minibar': any(rt_rooms.mapped('has_minibar')),
                        'has_jacuzzi': any(rt_rooms.mapped('has_jacuzzi')),
                        'has_balcony': any(rt_rooms.mapped('has_balcony')),
                    })

        values.update({
            'page_name': 'vacancies',
            'check_in': check_in,
            'check_out': check_out,
            'error_msg': error_msg,
            'vacancies': vacancies,
        })
        return request.render("dl_hotel_management.portal_my_vacancies", values)
