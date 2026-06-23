# Plano de Implementação - dl_hotel_management

Este plano descreve as correções de bugs impeditivos e a implementação de melhorias no módulo de Gestão Hoteleira.

## Proposed Changes

### [Configuração do Módulo]

#### [MODIFY] [__manifest__.py](file:///c:/Users/bvieira/Documents/Projectos_BV/dl_hotel_management/__manifest__.py)
* Remover o caractere `],` órfão que causa erro de sintaxe.
* Reorganizar a lista de `'data'` para carregar os menus antes das visualizações que os utilizam como pais.

---

### [Visualizações e Interface de Usuário]

#### [MODIFY] [hotel_menus.xml](file:///c:/Users/bvieira/Documents/Projectos_BV/dl_hotel_management/views/hotel_menus.xml)
* Definir apenas a estrutura básica e os menus principais (sem apontar para ações que ainda não foram carregadas).
* Mover os submenus de andares, tipos de quarto e quartos gerais para `hotel_room_views.xml` (carregado após os menus).

#### [MODIFY] [hotel_room_views.xml](file:///c:/Users/bvieira/Documents/Projectos_BV/dl_hotel_management/views/hotel_room_views.xml)
* Mover as definições dos submenus de configuração e do menu de quartos principal para este ficheiro, garantindo que as ações existem no momento do registo do menu.

#### [MODIFY] [hotel_booking_views.xml](file:///c:/Users/bvieira/Documents/Projectos_BV/dl_hotel_management/views/hotel_booking_views.xml)
* Adicionar botões no cabeçalho do formulário de reserva (`Confirmar`, `Check-in`, `Check-out`, `Cancelar`) para permitir a mudança do estado da reserva.

---

### [Lógica de Negócio e Modelos]

#### [MODIFY] [hotel_booking.py](file:///c:/Users/bvieira/Documents/Projectos_BV/dl_hotel_management/models/hotel_booking.py)
* Adicionar constrangimento `@api.constrains('check_in', 'check_out')` para evitar datas inválidas (check-out anterior ao check-in).
* Converter o `_onchange_room_id` em um campo computado com `readonly=False` e `store=True` no `price_unit` da linha para melhor persistência e compatibilidade com APIs/importações.
* Implementar métodos para transições de estado (`action_confirm`, `action_check_in`, `action_check_out`, `action_cancel`) que atualizam o status correspondente do quarto (`reserved`, `occupied`, `vacant`).

#### [MODIFY] [hotel_folio.py](file:///c:/Users/bvieira/Documents/Projectos_BV/dl_hotel_management/models/hotel_folio.py)
* Adicionar o decorador `@api.depends('room_charge_total')` no método `_compute_grand_total`.

#### [MODIFY] [hotel_services.py](file:///c:/Users/bvieira/Documents/Projectos_BV/dl_hotel_management/models/hotel_services.py)
* Definir os campos `subtotal` nas linhas de lavanderia e restaurante com `store=True` e adicionar `@api.depends('qty', 'price')` nos respetivos métodos de cálculo.

---

## Verification Plan

### Automated Tests
* Não existem testes automatizados definidos. Verificaremos a sintaxe e o carregamento do módulo no Odoo.

### Manual Verification
1. Instalar/Atualizar o módulo no Odoo 17 para verificar se carrega sem erros.
2. Criar uma reserva e tentar colocar a data de Check-Out anterior ao Check-In para testar o constrangimento.
3. Avançar o fluxo da reserva usando os novos botões do formulário e confirmar se o status do quarto no Kanban muda de `Livre` (Vacant) para `Reservado` (Reserved) e depois `Ocupado` (Occupied).
