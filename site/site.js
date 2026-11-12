const RAW = 'https://raw.githubusercontent.com/danilocaffaro/cortefacil/main/install';
const OS = {
  mac: { steps: [
      ['Abra o Terminal', 'Aperte <kbd>⌘</kbd> + <kbd>Espaço</kbd>, digite <b>Terminal</b> e aperte <kbd>Enter</kbd>.'],
      ['Cole este comando e aperte Enter', '', `curl -fsSL ${RAW}/install.sh | bash`],
      ['Pronto', 'O CorteFácil abre sozinho. Na primeira vez, escolha transcrever na nuvem (grátis) ou no computador. Depois, é só usar o ícone na Mesa ou em Aplicativos.']],
    req: ['macOS 12 ou mais novo', 'Qualquer Mac com a nuvem', '~2 GB livres'] },
  win: { steps: [
      ['Abra o PowerShell', 'Aperte a tecla <kbd>Windows</kbd>, digite <b>PowerShell</b> e aperte <kbd>Enter</kbd>.'],
      ['Cole este comando e aperte Enter', '', `irm ${RAW}/install.ps1 | iex`],
      ['Pronto', 'O CorteFácil abre sozinho. Na primeira vez, escolha transcrever na nuvem (grátis) ou no computador. Depois, é só usar o ícone na Área de Trabalho.']],
    req: ['Windows 10 ou 11', 'Qualquer PC atual com a nuvem', '~2 GB livres'] },
  linux: { steps: [
      ['Abra o terminal', 'Use o atalho do seu sistema, normalmente <kbd>Ctrl</kbd> + <kbd>Alt</kbd> + <kbd>T</kbd>.'],
      ['Cole este comando e aperte Enter', '', `curl -fsSL ${RAW}/install.sh | bash`],
      ['Pronto', 'O CorteFácil abre no navegador e aparece no menu de aplicativos.']],
    req: ['Ubuntu, Fedora e afins', 'Qualquer PC atual com a nuvem', '~2 GB livres'] },
};
function render(os){
  document.querySelectorAll('.seg button').forEach(b => b.classList.toggle('on', b.dataset.os === os));
  document.getElementById('steps').innerHTML = OS[os].steps.map(([t, d, cmd], i) =>
    `<div class="step"><span class="n">${i+1}</span><div style="flex:1;min-width:0"><p><b>${t}</b></p>${d?`<small>${d}</small>`:''}${cmd?`<div class="cmd"><code id="c${i}">${cmd}</code><button data-copy="c${i}">Copiar</button></div>`:''}</div></div>`).join('');
  document.getElementById('req').innerHTML = OS[os].req.map(r => `<span>${r}</span>`).join('');
}
document.addEventListener('click', e => {
  const b = e.target.closest('[data-copy]'); if (!b) return;
  const txt = document.getElementById(b.dataset.copy).textContent;
  navigator.clipboard.writeText(txt).then(() => { b.textContent = 'Copiado ✓'; setTimeout(() => b.textContent = 'Copiar', 1800); });
});
document.querySelectorAll('.seg button').forEach(b => b.onclick = () => render(b.dataset.os));
const ua = navigator.userAgent; render(/Windows/i.test(ua) ? 'win' : /Linux/i.test(ua) && !/Android/i.test(ua) ? 'linux' : 'mac');
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
