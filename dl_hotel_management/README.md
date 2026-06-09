# Gestão Hoteleira Completa - Odoo 17 (Community)

Módulo completo e integrado para gestão de hotéis, pousadas e alojamentos locais, construído de forma nativa para o Odoo 17. 
Faça a gestão de quartos, reservas, serviços de hóspedes, faturação e operações diárias a partir de uma única plataforma.

## 🌟 Principais Funcionalidades

- **🏨 Gestão de Quartos:** Vista Kanban em tempo real agrupada por andares com crachás de estado por cores (Verde: Livre, Laranja: Reservado, Vermelho: Ocupado).
- **📅 Gestão de Reservas:** Ciclo de vida completo da reserva (Rascunho → Confirmado → Check-in → Check-out).
- **🧾 Folios & Faturação:** Criação automática de contas de hóspedes (Folios). Todos os gastos extras sincronizam instantaneamente.
- **👕 Lavanderia:** Fluxo de trabalho independente para a equipa de lavanderia faturar diretamente na conta do quarto.
- **🍽️ Restaurante e Serviço de Quartos:** Pedidos de comida e bebida com sincronização de faturação na reserva.
- **🚗 Transporte e Motoristas:** Agendamento de transfers (Pickup/Drop) baseados em distância (KM).

## 🛠️ Instalação

1. Clone ou faça o download deste repositório.
2. Coloque a pasta `hotel_management_pt` dentro do diretório `addons` do seu Odoo 17.
3. Reinicie o serviço do Odoo (`sudo service odoo restart`).
4. Ative o "Modo de Desenvolvedor" no Odoo.
5. Vá a **Aplicações** > **Atualizar Lista de Aplicações**.
6. Procure por `Gestão Hoteleira Completa` e clique em **Instalar**.

## 👨‍💻 Dependências
- `base`
- `mail` (Para o chatter e histórico)
- `account` (Para a faturação futura)

## 📄 Licença
Distribuído sob a licença LGPL-3.