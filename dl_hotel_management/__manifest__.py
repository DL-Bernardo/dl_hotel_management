# -*- coding: utf-8 -*-
{
    'name': 'Complete Hotel & Hospitality Management PMS',
    'version': '17.0.1.0.5',
    'category': 'Industries',
    'summary': 'All-in-One Hotel PMS: Room Bookings, Guest Folios, Housekeeping, Dining & Billing Management',
    'description': """
        Enterprise Hotel Management System (PMS) for Odoo 17.
        Key Features:
        - Interactive Visual Occupancy Matrix & Kanban Room Rack.
        - End-to-end Booking Lifecycle (Check-in, Check-out, No-Show management).
        - Multi-Department Room Folio Billing (Laundry, Restaurant, Minibar).
        - Guest Transportation & Airport Shuttle Fleet Logistics.
        - Comprehensive Hospitality BI: Occupancy Rates, RevPAR & Financial Analytics.
        - Self-Service Guest Booking Portal with WhatsApp & Email confirmations.
    """,
    'author': 'DIGITALUB ANGOLA, LDA',
    'website': 'https://www.digitalub.ao',
    'support': 'suporte@digitalub.ao',
    'license': 'OPL-1',

    # Configuração de Preço Comercial Recomendado
    'price': 490.0,
    'currency': 'EUR',

    # Dependências do módulo
    'depends': [
        'base', 
        'web',
        'mail', 
        'account',
        'sale',
        'point_of_sale'
    ],
    
    # Ficheiros de dados e vistas
    'data': [
        'security/hotel_security.xml',
        'security/ir.model.access.csv',
        'data/hotel_cron.xml',
        'data/hotel_product_data.xml',
        'data/hotel_demo_data.xml',
        'data/laundry_service_data.xml',
        'data/restaurant_service_data.xml',
        'data/transport_service_data.xml',
        'data/hotel_email_templates.xml',
        'views/hotel_menus.xml',
        'views/hotel_room_views.xml',
        'views/hotel_services_views.xml',
        'views/hotel_booking_views.xml',
        'views/pos_order_views.xml',
        'views/hotel_portal_templates.xml',
        'views/hotel_booking_reports.xml',
        'views/hotel_laundry_reports.xml',
        'views/hotel_restaurant_reports.xml',
        'views/hotel_transport_reports.xml',
        'views/hotel_bi_reports.xml',
        'views/hotel_bi_pdf_report.xml',
    ],

    # Padrão de imagem de alta conversão para a loja
    'images': [
        'static/description/banner.png',
        'static/description/imagens_para_index/matriz_ocupacao1.png',
        'static/description/imagens_para_index/portal_hospede_verificar_vaga.png',
        'static/description/imagens_para_index/analise_ocupacao.png',
    ],
    
    'assets': {
        'web.assets_backend': [
            'dl_hotel_management/static/src/js/bi_pivot_view.js',
            'dl_hotel_management/static/src/xml/bi_pivot_view.xml',
            'dl_hotel_management/static/src/js/occupancy_matrix.js',
            'dl_hotel_management/static/src/xml/occupancy_matrix.xml',
            'dl_hotel_management/static/src/css/occupancy_matrix.css',
        ],
        'web.assets_frontend': [
            'dl_hotel_management/static/src/js/hotel_portal.js',
        ],
    },
    
    'installable': True,
    'application': True,
    'auto_install': False,
}
