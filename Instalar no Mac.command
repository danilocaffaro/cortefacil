#!/bin/bash
# Duplo clique para instalar (se o Mac bloquear: Ajustes do Sistema › Privacidade e Segurança › Abrir Mesmo Assim)
cd "$(dirname "$0")" && bash install/install.sh
echo; read -n 1 -s -r -p "Pressione qualquer tecla para fechar esta janela…"
