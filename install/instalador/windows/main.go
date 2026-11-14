// Instalador do CorteFácil para Windows (clique duplo).
// Baixa o mesmo install/install.ps1 do comando do site e roda no PowerShell, nesta janela.
// Teste: CORTEFACIL_INSTALL_URL troca o endereço do script.
package main

import (
	"bufio"
	"bytes"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"syscall"
	"time"
)

const defaultURL = "https://raw.githubusercontent.com/danilocaffaro/cortefacil/main/install/install.ps1"

func main() {
	// acentos certos no console
	syscall.NewLazyDLL("kernel32.dll").NewProc("SetConsoleOutputCP").Call(65001)
	fmt.Print("\n  Instalador do CorteFácil\n\n")

	url := os.Getenv("CORTEFACIL_INSTALL_URL")
	if url == "" {
		url = defaultURL
	}
	dir, err := os.MkdirTemp("", "cortefacil-instalador-")
	if err != nil {
		fail("Não consegui criar uma pasta temporária: " + err.Error())
	}
	defer os.RemoveAll(dir)
	script := filepath.Join(dir, "install.ps1")
	if err := download(url, script); err != nil {
		fail("Não consegui baixar o instalador. Verifique sua internet e tente de novo.\n  (" + err.Error() + ")")
	}

	ps := filepath.Join(os.Getenv("SystemRoot"), "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
	if _, err := os.Stat(ps); err != nil {
		ps = "powershell.exe"
	}
	cmd := exec.Command(ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script)
	cmd.Stdin, cmd.Stdout, cmd.Stderr = os.Stdin, os.Stdout, os.Stderr
	cmd.Env = append(os.Environ(), "CORTEFACIL_NO_PAUSE=1")
	if err := cmd.Run(); err != nil {
		os.RemoveAll(dir)
		fail("A instalação não terminou. Rode o instalador de novo; se continuar, abra uma issue em github.com/danilocaffaro/cortefacil.")
	}
	fmt.Print("\n  Esta janela fecha sozinha em 10 segundos.\n")
	time.Sleep(10 * time.Second)
}

func download(url, dest string) error {
	c := &http.Client{Timeout: 60 * time.Second}
	r, err := c.Get(url)
	if err != nil {
		return err
	}
	defer r.Body.Close()
	if r.StatusCode != http.StatusOK {
		return fmt.Errorf("resposta %d", r.StatusCode)
	}
	b, err := io.ReadAll(io.LimitReader(r.Body, 1<<20))
	if err != nil {
		return err
	}
	if !bytes.Contains(b, []byte("CorteFácil")) {
		return fmt.Errorf("o arquivo baixado não é o instalador do CorteFácil")
	}
	return os.WriteFile(dest, b, 0o600)
}

func fail(msg string) {
	fmt.Print("\n  ✗ " + msg + "\n\n  Pressione Enter para fechar.")
	bufio.NewReader(os.Stdin).ReadString('\n')
	os.Exit(1)
}
