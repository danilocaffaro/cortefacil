# Deploy da home page (cortefacil.melhor.dev)

Página estática em `site/`, servida pelo Caddy da VM Oracle (`caffaroos-oracle`) através do túnel Cloudflare `multi-agent-ui`.

| Item | Valor |
|---|---|
| URL | https://cortefacil.melhor.dev |
| Releases | `/opt/cortefacil-site/releases/<commit>` (o atual fica em `current`, um symlink) |
| Caddy | `/etc/caddy/cortefacil.caddy`, importado no bloco `:80` logo após `resumeai.caddy` |
| Backup do Caddyfile | `/etc/caddy/Caddyfile.before-cortefacil-20261112T002859Z` |
| DNS | CNAME proxied `cortefacil` → `3fb6bfa3-1c2b-47b5-99fb-1e203cd7e766.cfargotunnel.com` |

## Publicar uma nova versão

```bash
REL=$(git rev-parse --short HEAD)
ssh oracle "mkdir -p /opt/cortefacil-site/releases/$REL"
rsync -a --delete site/ oracle:/opt/cortefacil-site/releases/$REL/
ssh oracle "ln -sfn /opt/cortefacil-site/releases/$REL /opt/cortefacil-site/current"
```

As imagens em `/img/*` ficam 1 dia no cache. Ao trocar uma imagem, mude a URL (por exemplo `?v=3`).

## Voltar para a versão anterior

```bash
ssh oracle "ln -sfn /opt/cortefacil-site/releases/<commit-anterior> /opt/cortefacil-site/current"
```

Para remover a rota, apague a linha `import /etc/caddy/cortefacil.caddy` e o próprio fragmento, rode `sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile` e depois `sudo systemctl reload caddy`.
