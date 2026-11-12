# Deploy da home page (cortefacil.melhor.dev)

A página é estática (pasta `site/`, sem build). Qualquer servidor de arquivos serve: basta publicar o conteúdo de `site/` na raiz do domínio.

- **Versões imutáveis:** cada publicação vai para uma pasta própria (`releases/<commit>`), e um link `current` aponta para a versão no ar. Para voltar, aponte `current` para a pasta anterior.
- **Cache:** as imagens em `/img/*` ficam 1 dia em cache. Ao trocar uma imagem, mude a URL (por exemplo `?v=4`).
- **Cabeçalhos de segurança recomendados:** `Strict-Transport-Security`, `Content-Security-Policy` (sem scripts inline: o site usa `theme.js` e `site.js`), `X-Frame-Options: DENY`, `Permissions-Policy` e `X-Content-Type-Options: nosniff`.

Os detalhes da infraestrutura do mantenedor (servidor, túnel e DNS) ficam fora do repositório público.
