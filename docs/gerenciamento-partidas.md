# Gerenciamento de partidas

## Fluxo implementado

1. Acessar **Partidas → Minhas partidas** (`/games`).
2. Selecionar explicitamente um evento permitido ao usuário. Sem seleção,
   nenhuma partida aparece, mesmo que exista um evento salvo na sessão.
3. Combinar os filtros de modalidade, categoria, equipe e pesquisa textual
   (nome de equipe, local ou ID exato). **Limpar** mantém somente o evento.
4. Escolher **Novo → Partida**, modalidade e categoria; selecionar duas equipes
   inscritas nessa modalidade e categoria do evento.
5. Informar opcionalmente grupo, local e data/hora. Confirmar o cadastro.
6. Retornar à listagem do evento. Dados inválidos abrem um formulário de correção
   preservando os valores enviados e sem gravações parciais.

## Regras adotadas nesta implementação

- A seleção lista somente eventos acessíveis: administrador geral/superusuário
  acessa todos; demais usuários acessam seu evento vinculado. Permissões de
  visualização e cadastro continuam obrigatórias.
- Evento, modalidade, equipes e grupo precisam ser coerentes entre si.
- A categoria precisa estar habilitada na modalidade. O grupo, quando informado,
  precisa corresponder à mesma modalidade e categoria.
- Equipes A e B precisam ser distintas. Inscrição na modalidade/categoria é
  obrigatória; o campo de prontidão `Team_sport.status` não foi transformado em
  uma nova exigência para agendamento.
- Data/hora continuam opcionais. Quando informadas, devem respeitar as datas
  inicial/final do evento, se configuradas, considerando o fuso da aplicação.
- Partidas começam em “Em breve”. Os atletas inscritos são copiados para a partida
  no momento do cadastro. Reenviar um cadastro não reescreve sua escalação.
- Mesmo evento, esporte, categoria, grupo, horário e par de equipes identificam
  um cadastro repetido, inclusive com A/B invertidos. Outro confronto no mesmo
  horário é permitido. Para uma revanche, informar outro horário ou grupo.
- Partida, vínculos de equipes, atletas e registro de vôlei são gravados numa
  transação. Uma falha reverte todo o cadastro.
- Voleibol e voleibol sentado criam um único registro de controle de sets por
  confronto novo. Reenvios não deixam registros de vôlei órfãos.
- `/manage/match`, a listagem antiga, encaminha consultas para `/games`.

## Revisão complementar

- Fases e grupos também exigem seleção explícita do evento e permissão de cadastro.
- Fase exige modalidade do evento, tipo de fase válido e categoria habilitada.
- Grupo exige fase do evento e nome não vazio, limitado a 50 caracteres.
- Reenvios sequenciais da mesma fase ou do mesmo nome de grupo na fase reutilizam o cadastro.
- Erros preservam o formulário e sua ação para correção, sem criar registros inválidos.
- Seletores descartam respostas antigas após troca de modalidade/categoria e apresentam
  mensagem quando a busca falha. Isso evita exibir equipes ou grupos de uma seleção anterior.

## Decisões de negócio ainda em aberto

Estas regras formalizam o cadastro manual existente; não constituem aprovação
de um regulamento esportivo específico. Ainda precisam ser definidos:

- Se equipes sem o mínimo de atletas podem ser agendadas ou iniciar a partida.
- Duração dos confrontos, intervalos e conflitos de quadra/equipe. Sem duração
  definida, não há validação de sobreposição de horários.
- Sorteio, avanço automático de fases, critérios de desempate e chaveamento.
- Modelo de provas individuais e atletismo: o fluxo atual representa confrontos
  entre duas equipes, não baterias com vários competidores.
- Concorrência no ambiente de produção: o cadastro usa bloqueio por evento nos
  bancos que suportam `select_for_update`. SQLite mantém atomicidade, mas não
  oferece esse bloqueio de linha; a corrida entre cadastros simultâneos não foi
  validada nesta entrega.

## Validação

```bash
.venv/bin/python manage.py check
.venv/bin/python manage.py test app.tests.MatchManagementTests --noinput
```

Testes usam banco separado, cobrindo seleção explícita, filtros, isolamento entre
eventos, permissões, validações, reenvio, confrontos simultâneos distintos e
rollback. A interação visual no navegador deve ser conferida no ambiente local.
Não há mudança de esquema ou migração de banco nesta entrega.
