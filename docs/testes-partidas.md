# Revisão e testes do gerenciamento de partidas

## Antes e depois

| Comportamento | Antes | Agora |
|---|---|---|
| Entrada em `/games` | Podia listar todas as partidas ou assumir o evento do usuário/sessão | Exige seleção explícita; sem evento, lista vazia |
| Seleção de evento | Controle dependia também de permissões de criação | Disponível para quem pode visualizar, restrito aos eventos acessíveis |
| Aplicar filtros | Controles sem formulário e sem aplicação dos critérios na consulta | Formulário GET; esporte, categoria, equipe e texto combináveis |
| Pesquisa | Sem pesquisa textual integrada à consulta | Nome da equipe, local ou ID exato |
| Limpar | Link vazio, sem limpeza definida | Remove filtros e mantém o evento |
| Cadastro | Lógica dentro da view, com verificações parciais | Formulário valida evento, inscrições, categoria, grupo, data e campos |
| Reenvio | Identificação não incluía equipes; vôlei criava outro controle | Mesmo confronto retorna o existente, sem reescrever escalação |
| Falha durante cadastro | Podia deixar gravações parciais | Transação reverte partida, equipes, atletas e controle de vôlei |
| Erros de entrada | Podiam perder contexto ou gerar exceção | Formulário de correção preserva os valores |
| Listagem antiga | Consulta global independente | Redireciona a `/games`, mantendo parâmetros |
| Exclusão | Permissão incompleta; limpeza do controle de vôlei existia | Permissão/evento verificados; limpeza do último vínculo preservada |
| Logs | Alguns formulários, senhas e hashes eram impressos | Essas impressões foram removidas; autenticação continua usando Django |

A primeira alteração da exclusão tinha perdido a limpeza do controle de vôlei.
Um teste de regressão reproduziu a falha e a correção recuperou esse comportamento.

## Como executar no PyCharm

A configuração local **JIFS Testes** executa a suíte pelo mesmo interpretador do
projeto. Selecione-a na lista de execução e clique em Run. Ela usa `manage.py test`
e mostra cada nome seguido de `ok`, `FAIL` ou `ERROR` no console.

No terminal do PyCharm, na raiz do projeto:

```bash
# Toda a suíte disponível (44 testes nesta revisão)
.venv/bin/python manage.py test app --noinput --verbosity 2

# Apenas os testes unitários do middleware, sem banco
.venv/bin/python manage.py test app.test_match_regressions.EventSelectionUnitTests --verbosity 2

# Validações e gravação do formulário, com banco de teste
.venv/bin/python manage.py test app.test_match_regressions.MatchFormTests --verbosity 2

# Um cenário específico
.venv/bin/python manage.py test app.test_match_regressions.MatchRegressionTests.test_delete_last_volleyball_match_removes_set_control --verbosity 2
```

`Ran 44 tests` seguido de `OK` indica aprovação. `FAIL` significa resultado diferente
do esperado; `ERROR` significa erro durante a execução. O traceback mostra arquivo,
linha e asserção. Não use o servidor de desenvolvimento para executar estes testes.
Ele pode continuar rodando em paralelo.

Os testes usam dados fictícios e banco temporário em memória no ambiente SQLite
local. Não usam a conta pessoal, a senha pessoal nem os eventos de `db.sqlite3`.

## Mapa de cobertura

| Alteração/regra | Classe e testes principais |
|---|---|
| Seleção explícita e isolamento de evento | `MatchManagementTests.test_explicit_event_selection_and_isolation`, `test_invalid_event`, `test_permission_and_event_scope` |
| Persistência antiga continua nas outras páginas | `EventSelectionUnitTests`: os três testes da classe |
| Filtros combinados, inclusive valor zero | `MatchManagementTests.test_combined_filters_including_zero_values` |
| Pesquisa por local/ID e controles HTML | `MatchRegressionTests.test_search_location_and_id`, `test_filter_controls_preserve_selection_and_clear_event` |
| Equipes iguais, ausentes ou de outro evento | `MatchManagementTests.test_invalid_registration_does_not_write` |
| Categorias, grupo, limites de campos e datas | `MatchFormTests`: testes `test_disabled_category_*`, `test_foreign_sport_*`, `test_group_must_*`, `test_location_length_*`, `test_event_date_*`, `test_event_without_dates_*` |
| Campos opcionais e grupo válido | `MatchFormTests.test_valid_group_and_optional_fields`, `MatchManagementTests.test_optional_schedule` |
| Reenvio e confrontos distintos no mesmo horário | `MatchManagementTests.test_create_and_resubmission_preserve_two_teams`, `test_different_confrontations_at_same_time` |
| Atletas copiados e escalação preservada | `MatchFormTests.test_roster_copied_and_resubmission_does_not_replace_it` |
| Vôlei, vôlei sentado e rollback | `MatchManagementTests.test_volleyball_duplicate_and_atomic_rollback`, `MatchFormTests.test_sitting_volleyball_gets_set_control` |
| Erros preservados na tela de correção | `MatchRegressionTests.test_error_form_preserves_values_and_allows_correction` |
| Opções dinâmicas e entradas inválidas | `MatchRegressionTests.test_lookup_options_are_event_and_category_scoped`, `test_malformed_lookup_inputs` |
| Permissões e ações entre eventos | `MatchRegressionTests.test_no_view_permission_and_no_change_permission`, `test_actions_cannot_cross_event_boundary`, `test_delete_requires_permission` |
| Caminhos antigos | `MatchRegressionTests.test_legacy_list_redirect_preserves_filters`, `test_existing_phase_and_group_creation`, `test_scores_still_count_points_per_team`, `test_start_match_and_block_second_live_match` |
| Exclusão normal e de vôlei | `MatchRegressionTests.test_existing_delete_removes_match_and_team_links`, `test_delete_last_volleyball_match_removes_set_control`, `test_delete_one_set_preserves_other_matches` |
| Login e troca de senha sem impressão de segredos | `CredentialRegressionTests.test_login_and_password_update_do_not_print_secrets` |

Os testes HTTP também renderizam os templates, mas não executam JavaScript.
A publicação via WebSocket é isolada no teste de início de partida; esse teste
valida a transição no banco, não a entrega em tempo real ao navegador.

## Roteiro manual: perceber o novo e conferir o antigo

Use eventos e equipes de demonstração. Exclusões e alterações manuais afetam o
banco local real; os testes automatizados acima não.

| Passo | Ação | Resultado esperado |
|---|---|---|
| 1 | Entrar e abrir `/games` sem `?e=` | Solicitação de seleção; nenhuma partida |
| 2 | Selecionar evento A, depois B | Somente partidas/opções do evento escolhido |
| 3 | Voltar à opção vazia do seletor | Lista vazia novamente |
| 4 | Combinar esporte, categoria, equipe e pesquisa | Somente partidas que atendem a todos os critérios |
| 5 | Clicar Limpar | Mesmo evento, sem os demais filtros |
| 6 | Novo → Partida; escolher esporte e categoria | Equipes e grupos compatíveis; grupos atualizam ao trocar categoria |
| 7 | Cadastrar confronto válido | Mensagem de sucesso, duas equipes e estado “Em breve” |
| 8 | Informar data fora do evento | Tela de correção; local e demais valores preservados |
| 9 | Corrigir e reenviar | Cadastro válido, retorno ao evento |
| 10 | Repetir confronto e inverter A/B | Aviso de existente; sem duplicação |
| 11 | Cadastrar outras equipes no mesmo horário | Outro confronto criado |
| 12 | Criar fase/grupo e usá-los no cadastro | Fluxo antigo continua disponível |
| 13 | Iniciar partida e tentar iniciar outra no evento | Primeira inicia; segunda é bloqueada |
| 14 | Conferir pontos e placar no navegador | Pontos por equipe; validar atualização em tempo real manualmente |
| 15 | Testar conta sem permissão de cadastro | Botão ausente; tentativa direta não grava |
| 16 | Abrir listagem antiga com evento na URL | Redirecionamento para `/games` com o mesmo evento |
| 17 | Entrar, sair e trocar senha de conta fictícia | Acesso correto; sem senha/hash no console |

## Limites da validação

44 testes aprovados não significam que todo o JIFS foi validado. Edição antiga de
partidas, geração completa de PDFs/súmulas, placar em tempo real, uploads,
inscrições, certificados, relatórios, demais módulos e todos os perfis ainda
precisam de uma campanha própria de regressão. Não foram declarados aprovados
por esta entrega. Testar todos os módulos é um escopo maior que as alterações
no gerenciamento de partidas.

Também permanecem em aberto as regras de duração/conflito de quadra, mínimo de
atletas para agendar, provas individuais e concorrência real em produção.

## Separação entre código compartilhável e ambiente local

O código da funcionalidade não contém nome de usuário pessoal ou caminho absoluto
para o computador do desenvolvedor. Os testes usam usuários fictícios.

Somente locais/ignorados pelo Git: `.env`, `db.sqlite3`, `.venv/`, o backup do
ambiente, `.idea/` (configurações JIFS Local e JIFS Testes) e `LOCAL_SETUP.md`.
O guia local contém o caminho do computador; as configurações de execução usam
`$PROJECT_DIR$`. A conta administrativa e as sessões pertencem ao banco local.
Não há migration/fixture/seed que recrie a conta pessoal em outro ambiente.


## Revisão complementar de fases, grupos e seletores

`PhaseGroupValidationTests` acrescenta cinco testes: evento obrigatório, dados de
fase inválidos, nome/vínculo de grupo, reenvio e preservação da ação na tela de erro.
Os testes anteriores de criação de fase/grupo agora informam o evento na URL.

```bash
node tests/match_selectors.cjs
```

Essa verificação executa o carregador JavaScript com respostas controladas,
validando respostas fora de ordem, invalidação ao trocar modalidade e erro HTTP.
Não substitui a conferência visual no navegador.
