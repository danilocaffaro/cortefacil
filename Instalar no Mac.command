#!/bin/bash
# Duplo clique para instalar (se o Mac bloquear: clique com o botão direito › Abrir)
cd "$(dirname "$0")" && bash install/install.sh
echo; read -n 1 -s -r -p "Pressione qualquer tecla para fechar esta janela…"
