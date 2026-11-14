-- Instalador do CorteFácil para Mac (clique duplo).
-- Baixa e roda o mesmo install/install.sh do comando do site e mostra o progresso numa janela.
-- Teste: CORTEFACIL_INSTALL_URL troca o endereço do script (rode o binário em Contents/MacOS/applet).

property defaultURL : "https://raw.githubusercontent.com/danilocaffaro/cortefacil/main/install/install.sh"
property stepNames : {"Baixando o CorteFácil", "Preparando o Python", "Instalando os componentes (pode levar alguns minutos)", "Criando o atalho"}

on run
	set scriptURL to system attribute "CORTEFACIL_INSTALL_URL"
	if scriptURL is "" then set scriptURL to defaultURL
	set tmpDir to do shell script "mktemp -d -t cortefacil-instalador"
	set logFile to tmpDir & "/instalacao.log"
	set scriptFile to tmpDir & "/install.sh"

	set progress total steps to 4
	set progress completed steps to 0
	set progress description to "Instalando o CorteFácil"
	set progress additional description to "Começando…"

	-- roda em segundo plano (login shell, para achar o Homebrew, o Claude Code etc.) e acompanha pelo log
	set inner to "curl -fsSL " & quoted form of scriptURL & " -o " & quoted form of scriptFile & " && /bin/bash " & quoted form of scriptFile & "; echo \"CF_FIM=$?\""
	set cmd to "nohup /bin/bash -c " & quoted form of inner & " > " & quoted form of logFile & " 2>&1 &"
	do shell script "/bin/zsh -lc " & quoted form of cmd

	set fim to ""
	try
		repeat
			delay 1
			set logText to ""
			try
				set logText to do shell script "cat " & quoted form of logFile
			end try
			set etapa to 0
			repeat with i from 1 to 4
				if logText contains ((i as text) & "/4 ") then set etapa to i
			end repeat
			if etapa > 0 then
				set progress completed steps to etapa - 1
				set progress additional description to "Etapa " & etapa & " de 4: " & item etapa of stepNames
			end if
			if logText contains "CF_FIM=" then
				set fim to do shell script "grep -o 'CF_FIM=[0-9]*' " & quoted form of logFile & " | tail -1 | cut -d= -f2"
				exit repeat
			end if
		end repeat
	on error number -128
		-- a pessoa clicou em Parar
		do shell script "pkill -f " & quoted form of scriptFile & " || true"
		return
	end try

	if fim is "0" then
		set progress completed steps to 4
		set progress additional description to "Pronto!"
		display dialog "Pronto! O CorteFácil abriu no navegador." & return & return & "Da próxima vez, abra o ícone CorteFácil na Mesa ou em Aplicativos. Este instalador pode ir para o Lixo." buttons {"OK"} default button 1 with title "CorteFácil" with icon note
	else
		set why to do shell script "tr -d '\\033' < " & quoted form of logFile & " | sed 's/\\[[0-9;]*m//g' | grep '✗' | tail -1 | sed 's/^ *✗ *//' || true"
		if why is "" then set why to "A instalação parou no meio. Verifique a internet e tente de novo."
		set r to display dialog "Não deu para instalar." & return & return & why buttons {"Ver detalhes", "Fechar"} default button 2 with title "CorteFácil" with icon caution
		if button returned of r is "Ver detalhes" then do shell script "open -e " & quoted form of logFile
	end if
end run
