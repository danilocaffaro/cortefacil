const RAW = 'https://raw.githubusercontent.com/danilocaffaro/cortefacil/main/install';
const DL = 'https://github.com/danilocaffaro/cortefacil/releases/latest/download';
const OS = {
  mac: { label: 'Mac', file: `${DL}/CorteFacil-Instalador-Mac.zip`, steps: [
      ['Baixe o instalador', 'Abra o arquivo baixado e dê dois cliques em <b>Instalar CorteFácil</b>.', '', 'mac'],
      ['Se o Mac avisar que não pode verificar o app', 'Clique em <b>OK</b>, abra <b>Ajustes do Sistema › Privacidade e Segurança</b>, role até o fim e clique em <b>Abrir Mesmo Assim</b>. Isso só acontece na primeira vez: o CorteFácil é gratuito e não tem a assinatura paga da Apple.'],
      ['Pronto', 'Uma janela mostra o progresso (2 a 5 minutos) e o CorteFácil abre sozinho. Depois, é só usar o ícone na Mesa ou em Aplicativos.']],
    term: ['Abra o Terminal (<kbd>⌘</kbd> + <kbd>Espaço</kbd>, digite <b>Terminal</b>) e cole:', `curl -fsSL ${RAW}/install.sh | bash`],
    req: ['macOS 12 ou mais novo', 'Mac com chip Apple ou Intel', '~2 GB livres'] },
  win: { label: 'Windows', file: `${DL}/CorteFacil-Instalador-Windows.exe`, steps: [
      ['Baixe o instalador', 'Dê dois cliques no arquivo baixado.', '', 'win'],
      ['Se aparecer “O Windows protegeu o computador”', 'Clique em <b>Mais informações</b> e depois em <b>Executar assim mesmo</b>. Isso só acontece na primeira vez: o CorteFácil é gratuito e não tem certificado pago.'],
      ['Pronto', 'Uma janela mostra o progresso (2 a 5 minutos) e o CorteFácil abre sozinho. Depois, é só usar o ícone na Área de Trabalho.']],
    term: ['Abra o PowerShell (tecla <kbd>Windows</kbd>, digite <b>PowerShell</b>) e cole:', `irm ${RAW}/install.ps1 | iex`],
    req: ['Windows 10 ou 11 (64 bits)', 'Qualquer PC atual', '~2 GB livres'] },
  linux: { label: 'Linux', steps: [
      ['Abra o terminal', 'Use o atalho do seu sistema, normalmente <kbd>Ctrl</kbd> + <kbd>Alt</kbd> + <kbd>T</kbd>.'],
      ['Cole este comando e aperte Enter', '', `curl -fsSL ${RAW}/install.sh | bash`],
      ['Pronto', 'O CorteFácil abre no navegador e aparece no menu de aplicativos.']],
    req: ['Ubuntu, Fedora e afins', 'Qualquer PC atual', '~2 GB livres'] },
};
function render(os){
  const o = OS[os];
  document.querySelectorAll('.seg button').forEach(b => b.classList.toggle('on', b.dataset.os === os));
  document.getElementById('steps').innerHTML = o.steps.map(([t, d, cmd, dl], i) =>
    `<div class="step"><span class="n">${i+1}</span><div style="flex:1;min-width:0"><p><b>${t}</b></p>${d?`<small>${d}</small>`:''}${cmd?`<div class="cmd"><code id="c${i}">${cmd}</code><button data-copy="c${i}">Copiar</button></div>`:''}${dl?`<a class="btn primary dlbtn" href="${o.file}">Baixar para ${o.label}</a>`:''}</div></div>`).join('') +
    (o.term ? `<details class="term"><summary>Prefere o Terminal? ›</summary><small>${o.term[0]}</small><div class="cmd"><code id="ct">${o.term[1]}</code><button data-copy="ct">Copiar</button></div></details>` : '');
  document.getElementById('req').innerHTML = o.req.map(r => `<span>${r}</span>`).join('');
}
document.addEventListener('click', e => {
  const b = e.target.closest('[data-copy]'); if (!b) return;
  const txt = document.getElementById(b.dataset.copy).textContent;
  navigator.clipboard.writeText(txt).then(() => { b.textContent = 'Copiado ✓'; setTimeout(() => b.textContent = 'Copiar', 1800); });
});
document.querySelectorAll('.seg button').forEach(b => b.onclick = () => render(b.dataset.os));
const ua = navigator.userAgent, mobile = /Android|iPhone|iPad|iPod/i.test(ua);
const myOS = /Windows/i.test(ua) ? 'win' : /Linux/i.test(ua) && !/Android/i.test(ua) ? 'linux' : 'mac';
render(myOS);
// botão do topo: no computador, já baixa o instalador do sistema certo e leva aos passos de liberar
if (!mobile && OS[myOS].file) document.querySelectorAll('a[data-dl]').forEach(a => {
  a.href = OS[myOS].file; a.textContent = `Baixar para ${OS[myOS].label}`;
  a.addEventListener('click', () => setTimeout(() => { location.hash = 'instalar'; }, 300));
});
const tb = document.getElementById('theme');
const sync = () => tb.innerHTML = document.documentElement.dataset.theme === 'dark' ? '<svg class="i" aria-hidden="true"><use href="#i-sun_max_fill"/></svg>' : '<svg class="i" aria-hidden="true"><use href="#i-moon_fill"/></svg>';
tb.onclick = () => { const d = document.documentElement; d.dataset.theme === 'dark' ? delete d.dataset.theme : d.dataset.theme = 'dark';
  try { localStorage.setItem('cf_site_theme', d.dataset.theme || 'light'); } catch(e){} sync(); };
sync();
// menu do celular
const mb = document.getElementById('menuBtn'), mn = document.getElementById('mnav');
const setMenu = open => { mn.classList.toggle('open', open); mb.setAttribute('aria-expanded', open); mb.setAttribute('aria-label', open ? 'Fechar menu' : 'Abrir menu'); };
mb.onclick = () => setMenu(!mn.classList.contains('open'));
mn.addEventListener('click', e => { if (e.target.closest('a')) setMenu(false); });
document.addEventListener('keydown', e => { if (e.key === 'Escape') setMenu(false); });
// no celular: mandar o link para abrir no computador
document.getElementById('shareBtn').onclick = async e => {
  const url = 'https://cortefacil.melhor.dev/#instalar', b = e.currentTarget;
  try { if (navigator.share) { await navigator.share({title: 'CorteFácil', text: 'Instalar o CorteFácil no computador', url}); return; } } catch(err){ return; }
  try { await navigator.clipboard.writeText(url); b.textContent = 'Link copiado ✓'; } catch(err){ b.textContent = url; }
};
