# 🧿 Glyph

Glyph é um terminal híbrido desktop que unifica **CMD, PowerShell e Bash** em uma única interface moderna baseada em HTML. No seu núcleo opera um **daemon local persistente**, responsável por orquestrar processos, sessões e automações com controle total do sistema.

> **Projeto de uso pessoal/local.** Glyph não foi concebido para exposição em rede, ambientes multiusuário ou execução remota.

## ✨ Visão Geral

Glyph não é apenas um emulador de terminal. Ele é um **orquestrador de shells** com estado persistente, capaz de alternar ambientes, capturar entradas/saídas em tempo real e integrar automações avançadas sem perder contexto.

* Interface rica (HTML/CSS/JS)
* Execução real de shells do sistema
* Daemon contínuo para gerenciamento de estado
* Arquitetura extensível

---

## 🧠 Arquitetura

```
UI (HTML / Electron)
          │
          ▼
Comunicação (WebSocket / IPC)
          │
          ▼
Python Core (orquestração)
          │
  ┌───────┼─────────┐
  ▼       ▼         ▼
 CMD  PowerShell  Bash
```

O **daemon** é iniciado localmente e mantém:

* sessões ativas
* histórico
* controle de processos
* hooks e automações

A interface conecta-se ao daemon para enviar comandos e receber saídas em streaming.

---

## 🧩 Shells Suportados

Glyph integra shells como **processos independentes**:

* **CMD** (Windows)
* **PowerShell** (`powershell.exe` ou `pwsh`)
* **Bash** (Git Bash, WSL ou micro-shell virtual)

Cada shell possui:

* contexto próprio
* histórico isolado
* variáveis independentes

---

## 🧿 O Daemon

O daemon é o coração do Glyph. Ele permanece ativo enquanto o app estiver em execução e é responsável por:

* spawn e controle de processos
* multiplexação de entrada/saída
* gerenciamento de sessões
* automações e eventos
* comunicação com a UI

> O daemon **não expõe portas externas** e **não aceita conexões remotas**.

---

## ⚠️ AVISOS IMPORTANTES

### 🔥 Uso Local Apenas

Glyph foi projetado **exclusivamente para uso local**.
**O criador não se reposbilizará por nenhum problema que venha a acontecer durante o uso!**

❌ Não utilize em servidores públicos
❌ Não exponha portas para a rede
❌ Não rode como serviço de sistema

---

### 🔐 Permissões

Glyph executa comandos reais do sistema:

* respeita permissões do usuário
* não contorna UAC
* não eleva privilégios automaticamente

---

### 🧨 Riscos

* Comandos malformados podem causar perda de dados
* Processos longos podem consumir recursos
* Automação mal configurada pode gerar efeitos colaterais

Use com consciência.

---

## 🛠️ Status do Projeto

Glyph é um projeto **experimental e em evolução contínua**.

* Arquitetura pode evoluir
* Recursos podem ser reescritos

---

## 🧭 Filosofia

Glyph nasce da ideia de que o terminal moderno precisa ser:

* visual
* persistente
* extensível
* consciente de contexto

O objetivo não é substituir shells tradicionais, mas **orquestrá-los sob um único símbolo**.
