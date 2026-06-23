# Relatório de Análise e Sugestões de Melhorias

Este relatório apresenta uma análise detalhada dos dois módulos identificados em desenvolvimento:
1. **`dl_hotel_management`** (Módulo no espaço de trabalho ativo)
2. **`l10n_ao_fe`** (Módulo com o arquivo [fe_service.py](file:///c:/Users/bvieira/Documents/Projectos_BV/Novo%20Intellectus/l10n_ao_fe/models/fe_service.py) aberto no editor)

---

## 1. Módulo: `dl_hotel_management` (Gestão Hoteleira)

Este módulo apresenta alguns erros impeditivos de inicialização e algumas oportunidades de melhorias funcionais importantes para o fluxo de negócio do Odoo 17.

### 🔴 Erros Críticos (Impedem a instalação/carregamento)

#### A. Erro de Sintaxe no Manifesto
* **Arquivo**: [__manifest__.py](file:///c:/Users/bvieira/Documents/Projectos_BV/dl_hotel_management/__manifest__.py#L25-L27)
* **Problema**: Presença de um caractere de fecho de lista `],` órfão na linha 27.
* **Impacto**: O Odoo falha ao compilar o manifesto com um `SyntaxError`, impedindo que o módulo seja listado ou instalado.
* **Correção**:
  ```diff
      'images': ['static/description/banner.png'],
  -
  -   ],
      'installable': True,
  ```

#### B. Ordem de Carregamento dos XML (External ID Not Found)
* **Arquivos**: [__manifest__.py](file:///c:/Users/bvieira/Documents/Projectos_BV/dl_hotel_management/__manifest__.py#L17-L23), [hotel_room_views.xml](file:///c:/Users/bvieira/Documents/Projectos_BV/dl_hotel_management/views/hotel_room_views.xml), [hotel_booking_views.xml](file:///c:/Users/bvieira/Documents/Projectos_BV/dl_hotel_management/views/hotel_booking_views.xml) e [hotel_services_views.xml](file:///c:/Users/bvieira/Documents/Projectos_BV/dl_hotel_management/views/hotel_services_views.xml)
* **Problema**: O arquivo de menus (`hotel_menus.xml`) é carregado por último no manifesto. No entanto, os arquivos de visualização carregados antes dele tentam usar menus pais definidos nele (como `parent="menu_hotel_root"` ou `parent="menu_hotel_bookings"`).
* **Impacto**: Erro de inicialização do Odoo: `ValueError: External ID not found in the system`.
* **Solução recomendada**:
  1. Mover a estrutura de menus principais (sem as ações associadas) para o início do carregamento.
  2. Declarar os submenus com as ações nos respectivos arquivos de visualização (ex: colocar o menu de quartos em `hotel_room_views.xml`).
  
  **Nova ordem de carregamento no manifesto**:
  ```python
      'data': [
          'security/ir.model.access.csv',
          'views/hotel_menus.xml',  # Estrutura base de menus carregada primeiro
          'views/hotel_room_views.xml',
          'views/hotel_services_views.xml',
          'views/hotel_booking_views.xml',
      ],
  ```

---

### 🟡 Melhorias de Código e Padrões Odoo

#### C. Falta do decorador `@api.depends` no Folio
* **Arquivo**: [models/hotel_folio.py](file:///c:/Users/bvieira/Documents/Projectos_BV/dl_hotel_management/models/hotel_folio.py#L15-L19)
* **Problema**: O campo computado `grand_total` não possui o decorador `@api.depends`.
* **Impacto**: No Odoo 17, campos computados devem ter dependências declaradas para acionar o recalculo. Sem isso, o valor pode ficar desatualizado ou gerar avisos de sistema.
* **Correção**:
  ```python
      @api.depends('room_charge_total')
      def _compute_grand_total(self):
          for folio in self:
              folio.grand_total = folio.room_charge_total
  ```

#### D. Subtotais de Linhas Não Armazenados (Performance)
* **Arquivo**: [models/hotel_services.py](file:///c:/Users/bvieira/Documents/Projectos_BV/dl_hotel_management/models/hotel_services.py#L31) e [models/hotel_services.py](file:///c:/Users/bvieira/Documents/Projectos_BV/dl_hotel_management/models/hotel_services.py#L66)
* **Problema**: Os campos `subtotal` das linhas de lavanderia e restaurante são computados mas não guardados na base de dados (`store=True` ausente).
* **Impacto**: O Odoo precisa calcular os subtotais dinamicamente toda vez que a lista/formulário é aberto, o que prejudica a performance com muitos registros e impede relatórios de pivot/gráfico nativos baseados nesse campo.
* **Correção**: Adicionar `store=True` e `@api.depends('qty', 'price')` nos campos de subtotal.

---

### 🟢 Oportunidades de Melhoria Funcional (Negócio)

#### E. Automatizar o Status dos Quartos
* **Problema**: O modelo `hotel.room` tem um campo `status` (`vacant`, `reserved`, `occupied`), mas atualmente nenhuma lógica altera este status ao criar ou alterar reservas.
* **Sugestão**: Adicionar métodos na reserva (`hotel.booking`) que alterem o status dos quartos vinculados automaticamente quando a reserva for confirmada (`reserved`), feito o check-in (`occupied`) ou check-out/cancelamento (`vacant`).

#### F. Adicionar Botões de Ação no Formulário de Reserva
* **Problema**: O campo `status` no formulário de reserva usa o widget `statusbar` mas não há botões no header para avançar ou recuar o estado da reserva. O utilizador teria de editar o campo manualmente.
* **Sugestão**: Adicionar botões como "Confirmar", "Fazer Check-In", "Fazer Check-Out" e "Cancelar" no header do formulário e implementar os respectivos métodos Python.

#### G. Validação de Datas de Check-In e Check-Out
* **Sugestão**: Adicionar uma restrição `@api.constrains` para garantir que a data de Check-Out é sempre posterior à data de Check-In.
  ```python
  from odoo.exceptions import ValidationError

  @api.constrains('check_in', 'check_out')
  def _check_booking_dates(self):
      for rec in self:
          if rec.check_in and rec.check_out and rec.check_out <= rec.check_in:
              raise ValidationError("A data de Check-Out deve ser posterior à data de Check-In!")
  ```

---

## 2. Módulo: `l10n_ao_fe` (Facturação Electrónica Angola)

O código em [fe_service.py](file:///c:/Users/bvieira/Documents/Projectos_BV/Novo%20Intellectus/l10n_ao_fe/models/fe_service.py) é robusto e lida bem com os requisitos complexos de arredondamento da AGT, mas existem pontos de atenção sintática e otimização.

### 🟡 Melhorias de Código e Padrões Odoo

#### A. Sintaxe Incorreta nos Métodos de Tradução `_()`
* **Linhas**: 32, 42, 82, 910, 911
* **Problema**: O código passa múltiplos argumentos diretamente na função de tradução: `_("Erro ao ler chave privada: %s", e)`.
* **Impacto**: O mecanismo de tradução do Odoo (`xgettext` e arquivos PO) não consegue extrair as strings corretamente se os parâmetros forem passados como argumentos de função em vez de operadores de string Python.
* **Correção**: Alterar a sintaxe para utilizar o operador `%` fora do método de tradução.
  ```python
  # Incorreto:
  raise UserError(_("Erro de conexão: %s", e))
  
  # Correto:
  raise UserError(_("Erro de conexão: %s") % e)
  ```

#### B. Importação Redundante de Biblioteca
* **Linha**: 301 (dentro de `registar_factura`)
* **Problema**: O módulo realiza `import json` dentro do método, embora a biblioteca já tenha sido importada globalmente na linha 2.
* **Correção**: Remover a linha `import json` redundante de dentro da função para limpar o código.

#### C. Acúmulo de Arredondamento em Loops (Retenções do Recibo)
* **Linhas**: 558-560
* **Problema**: Na consolidação das retenções no recibo, o arredondamento `self._round_tax()` é aplicado a cada iteração do loop ao somar a nova parcela.
* **Impacto**: Pode causar pequenas variações de cêntimos devido ao arredondamento progressivo por excesso.
* **Sugestão**: Somar todos os valores em float puro no loop e, apenas no final (fora do loop), aplicar a função `_round_tax` ao valor total consolidado por grupo.
