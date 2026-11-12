# Apoio e patrocínio (promo.json)

O app lê `https://cortefacil.melhor.dev/promo.json` no máximo 1 vez por dia (módulo `cortefacil/promo.py`).
Editar esse arquivo no site liga, troca ou desliga apoios e patrocínios **sem lançar versão nova**.

## Onde aparece
| Espaço | Quando |
|---|---|
| `home` | tela inicial, abaixo dos recursos |
| `export` | logo abaixo do “Baixar MP4”, quando o vídeo fica pronto |
| `support` | engrenagem ⚙︎ › “Apoie o CorteFácil” (e o link “Apoie o projeto” na tela inicial) |

Aparece no máximo uma campanha por espaço: a primeira ativa da lista.

## Formato
```json
{
  "version": 1,
  "support": {
    "title": "Apoie o CorteFácil",
    "text": "Texto curto (até 240 caracteres)",
    "links": [{"label": "GitHub Sponsors", "url": "https://github.com/sponsors/..."}],
    "pix": "sua-chave-pix"
  },
  "campaigns": [
    {
      "id": "marca-2027-01",
      "slot": "home",
      "kind": "sponsor",
      "title": "Até 70 caracteres",
      "text": "Até 180 caracteres",
      "cta": "Ver oferta",
      "url": "https://marca.com/?utm_source=cortefacil&utm_campaign=2027-01",
      "image": "https://cortefacil.melhor.dev/promo/marca.png",
      "start": "2027-01-01",
      "end": "2027-01-31"
    }
  ]
}
```
- `kind`: `sponsor` (rótulo “Patrocinado”), `affiliate` (“Indicação (link de parceiro)”) ou `house` (avisos do próprio CorteFácil).
- `id`: minúsculas, números e `-_.`. Um `id` novo volta a aparecer para quem fechou o anterior.
- `image`: opcional, quadrada, **hospedada em cortefacil.melhor.dev** (pasta `site/promo/`). Imagens de outros domínios são ignoradas.
- Links só `https`. Campos inválidos são descartados em silêncio.

## Regras (privacidade e confiança)
- O app **não conta visualizações nem cliques** e não envia nenhum dado. Para medir resultado, use UTM ou cupom exclusivo no link do patrocinador.
- Patrocínio e afiliado são sempre rotulados. Quem fecha (×) não vê mais aquela campanha.
- Sem internet ou com o arquivo quebrado, nada aparece e nada trava.
