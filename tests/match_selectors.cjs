// Executar: node tests/match_selectors.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '../app/templates/games.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
new vm.Script(script); // Verifica também a sintaxe do script completo.
const helper = script.slice(script.indexOf('  async function loadOptions'), script.indexOf('  function carregarSexosPhase'));
const pending = [];
const context = vm.createContext({revisions: {teams: 0, groups: 0}, fetch: () => new Promise(resolve => pending.push(resolve))});
vm.runInContext(helper, context);
(async () => {
  const applied = [];
  let failures = 0;
  const first = context.loadOptions('teams', '/old', data => applied.push(data), () => failures++);
  const second = context.loadOptions('teams', '/new', data => applied.push(data), () => failures++);
  pending[1]({ok: true, json: async () => 'new'});
  await second;
  pending[0]({ok: true, json: async () => 'old'});
  await first;
  assert.deepEqual(applied, ['new'], 'Resposta antiga não deve substituir equipes atuais');
  const stale = context.loadOptions('teams', '/invalidated', data => applied.push(data), () => failures++);
  context.revisions.teams++;
  pending[2]({ok: true, json: async () => 'invalidated'});
  await stale;
  assert.deepEqual(applied, ['new'], 'Troca de modalidade invalida a busca anterior');
  const failed = context.loadOptions('groups', '/failure', () => assert.fail('HTTP inválido'), () => failures++);
  pending[3]({ok: false});
  await failed;
  assert.equal(failures, 1);
  console.log('OK: sintaxe, respostas fora de ordem, invalidação e falha HTTP.');
})().catch(error => { console.error(error); process.exitCode = 1; });
