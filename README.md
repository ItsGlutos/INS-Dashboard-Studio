# INS Dashboard Studio

**Gere, em lote, os dashboards de INS do Motorista e do Transportador — e envie cada um por e-mail sem sair do aplicativo.**

![Plataforma](https://img.shields.io/badge/plataforma-Windows%2010%2F11-0078D6?logo=windows&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Interface](https://img.shields.io/badge/interface-PyQt6-41CD52?logo=qt&logoColor=white)
![Versão](https://img.shields.io/badge/vers%C3%A3o-1.0.0-0B3C6E)

---

## ⬇️ Download

O aplicativo é distribuído como um instalador para Windows — **não é preciso ter Python instalado**.

[![Baixar o instalador](https://img.shields.io/badge/%E2%AC%87%20Baixar%20INS__Instalador.exe-41%20MB-0B3C6E?style=for-the-badge)](../../raw/main/INS_Instalador.exe)

1. Clique no botão acima (ou baixe [`INS_Instalador.exe`](INS_Instalador.exe)) e salve o arquivo.
2. Execute o instalador e siga as instruções na tela.
3. Abra o **INS Dashboard Studio** pelo atalho criado no Menu Iniciar.

> **Aviso do Windows SmartScreen:** o instalador não tem assinatura digital paga, então o
> Windows pode exibir *"O Windows protegeu o seu PC"*. Clique em **Mais informações →
> Executar assim mesmo**. Se preferir, valide o arquivo com o time de TI antes de instalar.

Para rodar a partir do código-fonte, veja [Executando pelo código](#-executando-pelo-código).

---

## 📑 Sumário

- [O que o aplicativo faz](#-o-que-o-aplicativo-faz)
- [Requisitos](#-requisitos)
- [Executando pelo código](#-executando-pelo-código)
- [Aba Geração de dashboards](#-aba-geração-de-dashboards)
- [Aba Envios de INS](#-aba-envios-de-ins)
- [Acessibilidade e telas pequenas](#-acessibilidade-e-telas-pequenas)
- [Estrutura do projeto](#-estrutura-do-projeto)
- [Gerando o executável](#-gerando-o-executável)
- [Testes](#-testes)
- [Solução de problemas](#-solução-de-problemas)
- [Privacidade e segurança](#-privacidade-e-segurança)

---

## ✨ O que o aplicativo faz

| | Recurso | Descrição |
|---|---|---|
| 📊 | **Geração de dashboards** | Cria, em lote, os dashboards **INS do Motorista** e **INS do Transportador** a partir das planilhas de origem e dos templates do Excel. |
| ✉️ | **Envios de INS** | Envia por e-mail, via Outlook Desktop, o dashboard de cada transportadora, com assunto e corpo editáveis, cópia (CC) e confirmação antes de qualquer disparo. |

A interface foi construída em **PyQt6** com a identidade visual institucional GrupoSC
(azul-marinho, laranja de destaque, tipografia Chivo e temas claro e escuro).
O processamento dos dashboards usa **pandas + xlwings** para preencher o template no
Microsoft Excel e salvar um arquivo por motorista/transportadora. Os envios usam
**pywin32** para falar com o Outlook.

> Os notebooks originais (`EnviosINS_Motorista.ipynb` e `EnviosINS_Transportador.ipynb`)
> **não são modificados**. Este projeto é uma pasta separada que reproduz a mesma lógica
> em uma aplicação desktop.

---

## ✅ Requisitos

| Requisito | Necessário para |
|---|---|
| Windows 10/11 | Executar o aplicativo |
| Microsoft Excel instalado | Geração dos dashboards (o app usa o Excel via COM) |
| Microsoft Outlook Desktop com perfil configurado | Aba **Envios** |
| Python 3.11+ (testado com 3.14) | Apenas para executar pelo código-fonte |

O `pywin32` é instalado apenas no Windows e é obrigatório para o envio real. Sem ele, a
aba **Envios** abre e planeja normalmente, mas o disparo falha com uma mensagem explicando
o que instalar.

---

## 🧑‍💻 Executando pelo código

```powershell
cd ins_dashboard_app
pip install -r requirements.txt
python main.py
```

Ou dê duplo clique em `iniciar.bat`.

A janela principal tem duas abas: **Geração de dashboards** e **Envios de INS**.
As preferências de cada aba são lembradas entre execuções via `QSettings`.

O botão sol/lua no canto direito do cabeçalho alterna entre o **tema claro** e o
**tema escuro**; a escolha também é lembrada entre execuções. Nada no fluxo de geração ou
envio muda com a troca de tema: é apenas aparência.

---

## 📊 Aba Geração de dashboards

1. Escolha o tipo de relatório: **Motorista** ou **Transportador**.
2. Selecione o **arquivo do relatório** (planilha `.xlsx` com a aba `INS`).
3. Selecione o **template do dashboard** (`.xlsx`).
4. Selecione a **pasta de saída** onde os dashboards serão salvos.
5. Clique em **Gerar dashboards** e acompanhe o progresso/log.

Todos os caminhos são escolhidos no explorador de arquivos — nada é fixo no código.
Os últimos caminhos usados são lembrados entre execuções.

### O que cada tipo espera

| | Motorista | Transportador |
|---|---|---|
| Aba de origem | `INS` | `INS` |
| Agrupamento | `Apelido` | `TRANSPORTADOR` |
| Colunas | mantém 14 colunas do relatório | remove 12 colunas auxiliares |
| Aba do template | `INS` | `Dados` |
| Tabela do template | `INS` | `Tabela3` |
| Nome do arquivo | `INS do Motorista - <GRUPO>.xlsx` | `INS do Transportador - <GRUPO>.xlsx` |

Antes de separar os grupos, a coluna de agrupamento passa por uma etapa de
**Data Wrangling**: linhas sem valor são ignoradas, espaços/quebras de linha são
colapsados e as pontas são removidas com `strip()`. No **Motorista** o `Apelido` também é
convertido para MAIÚSCULAS — assim `" joão "`, `"João"` e `"JOÃO"` geram **um único**
dashboard `INS do Motorista - JOÃO.xlsx`, e a tabela do dashboard já sai com o nome
padronizado.

Durante a geração o Excel é aberto **invisível**. No **Transportador** o template é aberto
uma única vez e reaproveitado entre os grupos (cada grupo é salvo como cópia, preservando
pivôs e formas do `Resumo`); no **Motorista** o template é aberto por grupo. Evite
abrir/editar os arquivos de origem, template ou saída enquanto o processo roda.

- **Gerar dashboards** executa em uma thread separada (a janela continua responsiva), com
  barra de progresso, grupo atual e log colorido.
- **Cancelar** interrompe entre um grupo e outro; os dashboards já salvos são mantidos.
- **Abrir pasta de saída** abre o resultado no Explorador de Arquivos.

---

## ✉️ Aba Envios de INS

A aba reúne quatro etapas, em abas internas:

### 1. Envios

1. Escolha **Motorista** ou **Transportador**.
2. Selecione a **planilha de contatos** (`.xlsx`/`.xlsm`) com as colunas
   `Transportadora` e `E-mail`. Vários endereços na mesma célula podem ser separados por
   `;`, `,` ou espaço.
3. Selecione a **pasta com os arquivos INS** gerados pelo aplicativo (ou pelos notebooks).
4. Clique em **Preparar envios**.

Nada é enviado nesse momento. O aplicativo cruza contatos e arquivos, monta um plano e
abre uma **tela de confirmação** com uma linha por transportadora mostrando arquivo,
destinatários, cópia e situação. Só as linhas marcadas e prontas são enviadas; a prévia do
assunto e do corpo pode ser conferida antes do disparo.

- **Modo debug (validar sem enviar)** faz todo o caminho — leitura, plano, conferência e
  log — sem acionar o Outlook. O botão passa a se chamar
  **Validar envios (debug)**.
- **Cancelar** interrompe após o e-mail atual; os já enviados permanecem.
- **Abrir pasta** abre no Explorador a pasta de arquivos selecionada.

### 2. Corpo do e-mail

Assunto e corpo são editáveis **por tipo de relatório**. O texto usa o marcador
`{transportadora}`, substituído pelo nome do grupo em cada e-mail. O corpo tem editor com
negrito, itálico e sublinhado (atalhos `Ctrl+B`, `Ctrl+I`, `Ctrl+U`), além de
**Inserir {transportadora}** e **Restaurar padrão**.

Os modelos padrão já vêm preenchidos com o texto institucional do INS do Motorista e do
INS do Transportador, incluindo as métricas e as metas de cada relatório.

### 3. Em cópia (CC)

Lista manual de endereços que entram em **cópia em todos os envios**, independentemente da
transportadora. É possível colar vários de uma vez, separados por `;`, `,` ou quebra de
linha. Endereços inválidos são recusados na inclusão e, se escaparem, aparecem como aviso
no plano.

### 4. Log

Cada transportadora aparece com o resultado do último envio (enviado, falho ou não
encontrado), com contadores de **enviados**, **falhos** e **não encontrados**. Falhas
individuais não interrompem os demais envios. O log pode ser **exportado para CSV** ou
limpo.

### Como os arquivos e contatos são emparelhados

- O nome do arquivo define a transportadora: o trecho entre o prefixo
  (`INS do Motorista - ` ou `INS do Transportador - `) e o `.xlsx` é comparado com a coluna
  `Transportadora`.
- A comparação ignora acentos, caixa e espaços extras — `"Ála Uber"`, `"ALA  UBER"` e
  `"ala uber"` são o mesmo grupo.
- Quando existem dois arquivos para a mesma transportadora, o **mais recente** é usado e o
  outro é registrado como aviso.
- Arquivos temporários do Excel (`~$...`) e planilhas sem o prefixo correto são ignorados.
- Cada transportadora recebe **um e-mail**, com o arquivo correspondente anexado e o
  assunto/corpo já personalizados.

---

## ♿ Acessibilidade e telas pequenas

- A janela abre ajustada à área útil da tela (mínimo 860×480) e o conteúdo das abas rola
  quando falta espaço; nada fica cortado em notebooks menores.
- O diálogo de confirmação também se adapta à tela, mantém os botões sempre visíveis e rola
  a prévia do e-mail.
- Navegação por teclado: `Tab` percorre os controles na ordem lógica e `Espaço`/`Enter`
  marcam ou desmarcam a transportadora selecionada na tabela.
- Controles têm nome acessível e os campos exibem anel de foco com contraste reforçado,
  incluindo botões, abas, tabelas e listas.
- Cores de status, botões e textos foram ajustadas para manter contraste legível nos temas
  claro e escuro.

---

## 🗂️ Estrutura do projeto

```text
ins_dashboard_app/
├── main.py                     # entrada do aplicativo
├── iniciar.bat                 # atalho para Windows
├── INS_Instalador.exe          # instalador pronto para distribuição
├── build_exe.ps1               # script de build do executável
├── ins_dashboard.spec          # configuração do PyInstaller
├── version_info.txt            # metadados de versão do .exe
├── requirements.txt            # dependências de execução
├── requirements-build.txt      # dependências de build
├── CONTRATO_UI.md              # contrato entre backend e interface
├── backend/
│   ├── __init__.py
│   ├── reports.py              # regras de cada tipo de relatório
│   ├── models.py               # JobConfig, JobResult, erros
│   ├── processor.py            # leitura, agrupamento e automação do Excel
│   └── envios.py               # contatos, plano de envios e Outlook
├── ui/
│   ├── theme.py                # paletas clara/escura e QSS institucional
│   ├── icons.py                # ícones vetoriais desenhados em QPainter
│   ├── widgets.py              # fundo, cartões, botões, checkbox, seletores, console
│   ├── assets/fonts/           # Chivo (OFL) embarcada para uso offline
│   ├── worker.py               # QThread da geração de dashboards
│   ├── envios_worker.py        # QThread do planejamento e do envio
│   ├── envios_dialog.py        # confirmação visual antes do disparo
│   ├── envios_tab.py           # aba Envios de INS
│   └── main_window.py          # janela principal (abas)
└── testes/
    ├── smoke_test.py           # valida o backend sem abrir o Excel
    ├── processor_perf_test.py  # reuso do template e leitura com calamine
    ├── estrutura_test.py       # verificador estrutural (pivôs/formas/gráfico)
    ├── estrutura_dashboard.py  # CLI: compara saída real com o template
    ├── e2e_excel.py            # geração real (requer Excel)
    ├── ui_e2e.py               # interface + thread + Excel, ponta a ponta
    ├── envios_test.py          # lógica de envio (sem Outlook)
    └── envios_ui_smoke.py      # aba Envios offscreen (salva captura)
```

---

## 📦 Gerando o executável

O build usa **PyInstaller** em modo *onedir* (pasta com o `.exe` + dependências), que
inicia bem mais rápido que o modo *onefile* — este último descompacta PyQt6 e pandas em uma
pasta temporária a cada execução.

```powershell
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

O script cria um ambiente virtual em `%LOCALAPPDATA%\insbuild` (fora do OneDrive, para não
esbarrar no limite de caminho do Windows), instala as dependências de
`requirements-build.txt` e gera o resultado em `dist\INS Dashboard Studio\`. O executável
final é `dist\INS Dashboard Studio\INS Dashboard Studio.exe`.

Depois de gerar a distribuição, empacote-a com o seu instalador de preferência e publique
o novo `INS_Instalador.exe` no repositório para que o link de download continue válido.

---

## 🧪 Testes

```powershell
cd ins_dashboard_app
python -m unittest testes.envios_test -v             # envios, sem abrir o Outlook
python -m unittest testes.normalizacao_test -v       # Data Wrangling do Apelido
python -m unittest testes.processor_perf_test testes.estrutura_test -v
python -m testes.smoke_test                          # geração, sem abrir o Excel
python -m testes.envios_ui_smoke                     # aba Envios offscreen
python -m testes.e2e_excel                           # geração real, abre o Excel
python -m testes.ui_e2e                              # clica em "Gerar" na interface
```

Depois de gerar dashboards reais, o verificador estrutural confere se cada arquivo manteve
as tabelas dinâmicas, o Data Model, o gráfico e as formas do `Resumo` — é o teste que pega
perda de elementos visuais:

```powershell
python -m testes.estrutura_dashboard --template "C:\INS\Template - Transportador.xlsx" --pasta "C:\...\saida"
```

O `envios_ui_smoke` usa planilhas e arquivos sintéticos, não envia e-mail e valida também
proporções, rolagem, foco e nomes acessíveis do diálogo de confirmação. Ele salva capturas
em `_saida_teste/envios.png` e `_saida_teste/envios_dialogo_baixo.png`.

Os testes de envio usam um remetente falso: nenhum e-mail é disparado.

---

## 🛠️ Solução de problemas

<details>
<summary><strong>Geração de dashboards</strong></summary>

- **"Não foi possível abrir o Microsoft Excel"**: confirme que o Excel está instalado e
  feche caixas de diálogo abertas no Excel.
- **"A aba 'INS' não foi encontrada"**: o arquivo escolhido não é o relatório correto
  (Motorista/Transportador) ou a aba foi renomeada.
- **"A tabela '...' não existe"**: o template escolhido não corresponde ao tipo de
  relatório.
- **Aviso de cabeçalho diferente**: o template pode ser de outro relatório; o app avisa,
  mas continua (útil quando o template tem colunas extras).
- **Sem permissão ao salvar**: feche o dashboard no Excel e tente novamente.
- **Geração lenta**: no **Transportador** o template é aberto uma vez e reaproveitado entre
  os grupos; no **Motorista** cada grupo abre e fecha o template. Feche outras janelas do
  Excel e evite manter o template aberto durante a geração.

</details>

<details>
<summary><strong>Envios</strong></summary>

- **"O Outlook Desktop não está disponível"**: instale o Microsoft Outlook e o `pywin32`
  (`pip install pywin32`).
- **"Não foi possível abrir o Outlook Desktop"**: abra o Outlook uma vez, confirme que o
  perfil de e-mail está configurado e tente novamente.
- **Planilha de contatos inválida**: o arquivo precisa ter as colunas `Transportadora` e
  `E-mail` (variações como `Email` também são aceitas).
- **Transportadora "Sem contato na planilha"**: o nome do arquivo não bate com nenhuma linha
  da planilha. Ajuste o nome do arquivo ou o cadastro.
- **"Sem e-mail" ou "E-mail inválido"**: o grupo aparece na confirmação, mas nunca é
  disparado; corrija o cadastro e prepare novamente.
- **Nenhum arquivo encontrado**: confira se a pasta é a certa e se os nomes começam com
  `INS do Motorista - ` ou `INS do Transportador - `.
- **Arquivo duplicado ignorado**: o aplicativo usa o mais recente da pasta e informa qual
  foi mantido.
- **Envio lento**: cada e-mail abre o Outlook via COM; em máquinas mais lentas alguns
  segundos por transportadora são normais.

</details>

<details>
<summary><strong>Instalador e executável</strong></summary>

- **O Windows bloqueou o instalador (SmartScreen)**: clique em **Mais informações →
  Executar assim mesmo**. O binário não possui assinatura digital.
- **O antivírus colocou o instalador em quarentena**: restaure o arquivo e adicione uma
  exceção para a pasta de instalação; executáveis gerados por PyInstaller às vezes são
  sinalizados por heurística.
- **O aplicativo abre e fecha sozinho**: confirme que o Microsoft Excel está instalado e
  que o Visual C++ Redistributable está atualizado.
- **Preferir sem instalar**: gere a distribuição com `build_exe.ps1` e execute
  `dist\INS Dashboard Studio\INS Dashboard Studio.exe` diretamente.

</details>

---

## 🔒 Privacidade e segurança

A leitura e a geração dos dashboards acontecem localmente, via pandas e Excel. Os envios
saem apenas pelo Outlook já configurado na máquina, para os destinatários da planilha de
contatos e para a lista de cópia — nenhum serviço externo é usado e nada é enviado sem a
confirmação na tela de revisão.

Planilhas, templates e dashboards **não são versionados** no repositório (`.gitignore`
bloqueia `*.xlsx`, `*.xlsm` e `*.xls`), assim como pastas de teste e caches.
