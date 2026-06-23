/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class OccupancyMatrix extends Component {
    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        
        const today = new Date();
        this.state = useState({
            currentYear: today.getFullYear(),
            currentMonth: today.getMonth(),
            rooms: [],
            bookings: [],
            daysInMonth: [],
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        const year = this.state.currentYear;
        const month = this.state.currentMonth;
        
        // 1. Calcular dias do mês selecionado
        const date = new Date(year, month, 1);
        const days = [];
        while (date.getMonth() === month) {
            days.push(new Date(date));
            date.setDate(date.getDate() + 1);
        }
        this.state.daysInMonth = days;

        // 2. Procurar quartos
        const rooms = await this.orm.searchRead("hotel.room", [], ["id", "name", "room_type_id", "status"]);
        this.state.rooms = rooms;

        // 3. Procurar reservas que se sobrepõem ao mês selecionado
        const startDate = `${year}-${String(month + 1).padStart(2, '0')}-01 00:00:00`;
        const lastDay = new Date(year, month + 1, 0).getDate();
        const endDate = `${year}-${String(month + 1).padStart(2, '0')}-${String(lastDay).padStart(2, '0')} 23:59:59`;

        const bookings = await this.orm.searchRead(
            "hotel.booking",
            [
                ["check_in", "<=", endDate],
                ["check_out", ">=", startDate],
                ["status", "not in", ["cancelled", "no_show"]]
            ],
            ["id", "name", "partner_id", "check_in", "check_out", "status", "quarto_id"]
        );
        
        this.state.bookings = bookings.map(b => {
            let roomIds = [];
            if (b.quarto_id) {
                roomIds.push(b.quarto_id[0]);
            }
            // Converter datas de UTC String do Odoo para objetos Date
            const checkInUtc = new Date(b.check_in + "Z");
            const checkOutUtc = new Date(b.check_out + "Z");
            return {
                id: b.id,
                name: b.name,
                partner_name: b.partner_id ? b.partner_id[1] : 'Sem Hóspede',
                check_in: checkInUtc,
                check_out: checkOutUtc,
                status: b.status,
                room_ids: roomIds
            };
        });
    }

    async changeMonth(offset) {
        let newMonth = this.state.currentMonth + offset;
        let newYear = this.state.currentYear;
        if (newMonth < 0) {
            newMonth = 11;
            newYear--;
        } else if (newMonth > 11) {
            newMonth = 0;
            newYear++;
        }
        this.state.currentMonth = newMonth;
        this.state.currentYear = newYear;
        await this.loadData();
    }

    getMonthName() {
        const months = [
            "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
        ];
        return `${months[this.state.currentMonth]} de ${this.state.currentYear}`;
    }

    getDayName(date) {
        const days = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];
        return days[date.getDay()];
    }

    getBookingForCell(roomId, date) {
        const cellDate = new Date(date);
        cellDate.setHours(12, 0, 0, 0); // Avaliação ao meio-dia

        return this.state.bookings.find(b => {
            return b.room_ids.includes(roomId) && cellDate >= b.check_in && cellDate <= b.check_out;
        });
    }

    getPrevBooking(roomId, date) {
        const prevDate = new Date(date);
        prevDate.setDate(prevDate.getDate() - 1);
        return this.getBookingForCell(roomId, prevDate);
    }

    getNextBooking(roomId, date) {
        const nextDate = new Date(date);
        nextDate.setDate(nextDate.getDate() + 1);
        return this.getBookingForCell(roomId, nextDate);
    }

    getBookingStyle(booking) {
        switch (booking.status) {
            case 'checked_in': return 'bg-success text-white';
            case 'confirmed': return 'bg-warning text-dark';
            case 'draft': return 'bg-secondary text-white';
            case 'checked_out': return 'bg-info text-white';
            default: return 'bg-primary text-white';
        }
    }

    getBookingClasses(roomId, date, booking) {
        let classes = ['booking-bar', this.getBookingStyle(booking)];
        
        const prev = this.getPrevBooking(roomId, date);
        if (prev && prev.id === booking.id) {
            classes.push('no-left');
        }
        
        const next = this.getNextBooking(roomId, date);
        if (next && next.id === booking.id) {
            classes.push('no-right');
        }
        
        return classes.join(' ');
    }

    isFirstCell(roomId, date, booking) {
        const prev = this.getPrevBooking(roomId, date);
        return !prev || prev.id !== booking.id;
    }

    onCellClick(roomId, date) {
        const booking = this.getBookingForCell(roomId, date);
        if (booking) {
            this.actionService.doAction({
                type: 'ir.actions.act_window',
                res_model: 'hotel.booking',
                res_id: booking.id,
                views: [[false, 'form']],
                target: 'current',
            });
        } else {
            // Formatar datas para strings YYYY-MM-DD
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            const formattedDate = `${year}-${month}-${day}`;
            
            const nextDay = new Date(date);
            nextDay.setDate(nextDay.getDate() + 1);
            const nextYear = nextDay.getFullYear();
            const nextMonth = String(nextDay.getMonth() + 1).padStart(2, '0');
            const nextDayStr = String(nextDay.getDate()).padStart(2, '0');
            const formattedNextDate = `${nextYear}-${nextMonth}-${nextDayStr}`;
            
            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: 'Criar Reserva',
                res_model: 'hotel.booking',
                views: [[false, 'form']],
                target: 'new',
                context: {
                    default_quarto_id: roomId,
                    default_check_in: `${formattedDate} 14:00:00`,
                    default_check_out: `${formattedNextDate} 12:00:00`,
                    default_status: 'draft'
                }
            });
        }
    }
}

OccupancyMatrix.template = "dl_hotel_management.OccupancyMatrix";

registry.category("actions").add("hotel_occupancy_matrix", OccupancyMatrix);
