# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ReportBiOcupacao(models.AbstractModel):
    _name = 'report.dl_hotel_management.report_bi_ocupacao_template'
    _description = 'Parser do Relatório de Ocupação'

    @api.model
    def _get_report_values(self, docids, data=None):
        domain = [('id', 'in', docids)]
        # Agrupamento por quarto_id
        groups = self.env['hotel.booking'].read_group(
            domain,
            ['quarto_id', 'subtotal_hospedagem', 'numero_noites'],
            ['quarto_id']
        )
        # Buscar os dados de cada quarto agrupado
        report_data = []
        for g in groups:
            quarto = self.env['hotel.room'].browse(g['quarto_id'][0]) if g.get('quarto_id') else False
            report_data.append({
                'quarto': quarto.name if quarto else 'Não Definido',
                'noites': g.get('numero_noites', 0),
                'faturado': g.get('subtotal_hospedagem', 0.0),
            })
        return {
            'doc_ids': docids,
            'doc_model': 'hotel.booking',
            'data': data,
            'report_data': report_data,
            'area': 'Ocupação & Alojamento',
            'date_emission': fields.Date.today(),
            'user': self.env.user,
        }

class ReportBiLavanderia(models.AbstractModel):
    _name = 'report.dl_hotel_management.report_bi_lavanderia_template'
    _description = 'Parser do Relatório de Lavandaria'

    @api.model
    def _get_report_values(self, docids, data=None):
        domain = [('id', 'in', docids)]
        # Agrupamento por servico_id
        groups = self.env['hotel.laundry.line'].read_group(
            domain,
            ['servico_id', 'qty', 'price_total'],
            ['servico_id']
        )
        report_data = []
        for g in groups:
            servico = self.env['hotel.lavanderia.servico'].browse(g['servico_id'][0]) if g.get('servico_id') else False
            report_data.append({
                'servico': servico.name if servico else 'Não Definido',
                'quantidade': g.get('qty', 0),
                'faturado': g.get('price_total', 0.0),
            })
        return {
            'doc_ids': docids,
            'doc_model': 'hotel.laundry.line',
            'data': data,
            'report_data': report_data,
            'area': 'Serviços de Lavandaria',
            'date_emission': fields.Date.today(),
            'user': self.env.user,
        }

class ReportBiRestaurante(models.AbstractModel):
    _name = 'report.dl_hotel_management.report_bi_restaurante_template'
    _description = 'Parser do Relatório de Restaurante'

    @api.model
    def _get_report_values(self, docids, data=None):
        domain = [('id', 'in', docids)]
        # Agrupamento por servico_id
        groups = self.env['hotel.restaurant.line'].read_group(
            domain,
            ['servico_id', 'qty', 'price_total'],
            ['servico_id']
        )
        report_data = []
        for g in groups:
            servico = self.env['hotel.restaurante.servico'].browse(g['servico_id'][0]) if g.get('servico_id') else False
            report_data.append({
                'servico': servico.name if servico else 'Não Definido',
                'quantidade': g.get('qty', 0),
                'faturado': g.get('price_total', 0.0),
            })
        return {
            'doc_ids': docids,
            'doc_model': 'hotel.restaurant.line',
            'data': data,
            'report_data': report_data,
            'area': 'Consumos do Restaurante',
            'date_emission': fields.Date.today(),
            'user': self.env.user,
        }

class ReportBiTransporte(models.AbstractModel):
    _name = 'report.dl_hotel_management.report_bi_transporte_template'
    _description = 'Parser do Relatório de Transporte'

    @api.model
    def _get_report_values(self, docids, data=None):
        domain = [('id', 'in', docids)]
        # Agrupamento por servico_id
        groups = self.env['hotel.transport.request'].read_group(
            domain,
            ['servico_id', 'num_passageiros', 'total_geral'],
            ['servico_id']
        )
        report_data = []
        for g in groups:
            servico = self.env['hotel.transporte.servico'].browse(g['servico_id'][0]) if g.get('servico_id') else False
            report_data.append({
                'servico': servico.name if servico else 'Não Definido',
                'quantidade': g.get('num_passageiros', 0),
                'faturado': g.get('total_geral', 0.0),
            })
        return {
            'doc_ids': docids,
            'doc_model': 'hotel.transport.request',
            'data': data,
            'report_data': report_data,
            'area': 'Serviços de Transporte',
            'date_emission': fields.Date.today(),
            'user': self.env.user,
        }
