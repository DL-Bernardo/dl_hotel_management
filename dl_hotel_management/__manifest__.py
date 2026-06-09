# -*- coding: utf-8 -*-
{
    'name': 'Digitalub - Gestão Hoteleira Completa',
    'version': '17.0.1.0.0',
    'category': 'Industries',
    'summary': 'Gestão completa de quartos, reservas, lavandaria, restaurante e transporte integrado.',
    'description': """
        Módulo de Gestão Hoteleira (PMS) avançado e integrado para o Odoo 17.
        Funcionalidades:
        - Gestão de Status de Quartos com Vista Kanban intuitiva.
        - Ciclo completo de Reservas (Check-in, Check-out e No-show).
        - Integração de Serviços de Lavandaria e Restaurante diretamente no quarto.
        - Controlo de Transporte e Transfers de Hóspedes.
        - Faturação unificada de consumos e estadias (Hotel Folios).
    """,
    'author': 'DIGITALUB ANGOLA',
    'website': 'https://apps.digitalub.ao/loja/',
    'license': 'OPL-1',  # Alterado para OPL-1 para proteger um módulo deste valor comercial

    # Configuração de Preço Comercial Recomendado
    'price': 549.00,
    'currency': 'EUR',

    # Dependências do módulo
    'depends': [
        'base', 
        'mail', 
        'account'
    ],
    
    # Ficheiros de dados e vistas
    'data': [
        'security/hotel_security.xml',
        'security/ir.model.access.csv',
        'data/hotel_cron.xml',
        'views/hotel_menus.xml',
        'views/hotel_room_views.xml',
        'views/hotel_services_views.xml',
        'views/hotel_booking_views.xml',
    ],

    # Padrão de imagem de alta conversão para a loja
    'images': [
        'static/description/main_screenshot.png'
    ],
    
    'installable': True,
    'application': True,
    'auto_install': False,
}