STORE é uma aplicação de e-commerce desenvolvida com Python 3.13 e Django 5.2, estruturada segundo o padrão arquitetural MTV (Model-Template-View). O projeto implementa o fluxo completo de compra, incluindo navegação por produtos, carrinho, checkout com seleção de endereço, criação de pedidos e simulação de pagamento.

O backend utiliza o Django ORM com SQLite em ambiente de desenvolvimento, modelando entidades como Product, Cart, Order, OrderItem, Payment e Address. A lógica de negócio foi organizada de forma modular, separando regras de cálculo (como resumo do carrinho) da camada de controle, promovendo melhor manutenção e escalabilidade.

A aplicação conta com sistema de autenticação nativo do Django (registro, login e logout), controle de acesso por usuário e gerenciamento individual de carrinho, pedidos e endereços. O fluxo simula um ambiente real de e-commerce, incluindo atualização de status de pedidos e processamento de pagamento (simulado).

O frontend foi desenvolvido com HTML5 e CSS3, utilizando o sistema de templates do Django com herança estrutural (base.html) e organização adequada de arquivos estáticos.

O projeto demonstra domínio de:

Modelagem relacional com Django ORM

Organização modular de aplicações

Manipulação de formulários

Class-Based e Function-Based Views

Sistema de autenticação e autorização

Gerenciamento de arquivos estáticos

Boas práticas de arquitetura em aplicações web

A estrutura está preparada para evoluir para banco de dados como PostgreSQL, integração com gateways de pagamento reais ou APIs REST com Django REST Framework.
