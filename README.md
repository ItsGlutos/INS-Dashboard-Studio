# INS Dashboard Studio

Aplicativo desktop (Windows) para a rotina mensal de **INS**:

1. **Geração de dashboards** — cria, em lote, os dashboards **INS do Motorista**
   e **INS do Transportador** a partir das planilhas de origem e dos templates
   do Excel.
2. **Envios de INS** — envia por e-mail, via Outlook Desktop, o dashboard de
   cada transportadora, com assunto e corpo editáveis, cópia (CC) e
   confirmação antes de qualquer disparo.

A interface foi construída em **PyQt6** com estética *Frutiger Aero* (vidro,
céu em degradê e botões glossy). O processamento dos dashboards usa
**pandas + xlwings** para preencher o template no Microsoft Excel e salvar um
arquivo por motorista/transportadora. Os envios usam **pywin32** para falar com
o Outlook.

> Os notebooks originais (`EnviosINS_Motorista.ipynb` e
> `EnviosINS_Transportador.ipynb`) **não são modificados**. Este projeto é uma
> pasta separada que reproduz a mesma lógica em uma aplicação.

## Requisitos

- Windows 10/11
- Microsoft Excel instalado (a geração usa o Excel via COM)
- Microsoft Outlook Desktop instalado e com um perfil de e-mail configurado
  (necessário apenas para a aba **Envios**)
- Python 3.11+ (testado com 3.14)

Instale as dependências:

```powershell
cd ins_dashboard_app
pip install -r requirements.txt
```

O `pywin32` é instalado apenas no Windows e é obrigatório para o envio real.
Sem ele, a aba **Envios** abre e planeja normalmente, mas o disparo falha com
uma mensagem explicando o que instalar.

## Como executar

```powershell
cd ins_dashboard_app
python main.py
```

ou dê duplo clique em `iniciar.bat`.

A janela principal tem duas abas: **Geração de dashboards** e
**Envios de INS**. As preferências de cada aba são lembradas entre execuções
via `QSettings`.

## Aba Geração de dashboards

1. Escolha o tipo de relatório: **Motorista** ou **Transportador**.
2. Selecione o **arquivo do relatório** (planilha `.xlsx` com a aba `INS`).
3. Selecione o **template do dashboard** (`.xlsx`).
4. Selecione a **pasta de saída** onde os dashboards serão salvos.
5. Clique em **Gerar dashboards** e acompanhe o progresso/log.

Todos os caminhos são escolhidos no explorador de arquivos — nada é fixo no
código. Os últimos caminhos usados são lembrados entre execuções.

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
**Data Wrangling**: linhas sem valor são ignoradas, espaços/quebras de linha
são colapsados e as pontas são removidas com `strip()`. No **Motorista** o
`Apelido` também é convertido para MAIÚSCULAS — assim `" joão "`, `"João"` e
`"JOÃO"` geram **um único** dashboard `INS do Motorista - JOÃO.xlsx`, e a
tabela do dashboard já sai com o nome padronizado.

Durante a geração o Excel é aberto **invisível**. No **Transportador** o
template é aberto uma única vez e reaproveitado entre os grupos (cada grupo é
salvo como cópia, preservando pivôs e formas do `Resumo`); no **Motorista** o
template é aberto por grupo. Evite abrir/editar os arquivos de origem,
template ou saída enquanto o processo roda.

- **Gerar dashboards** executa em uma thread separada (a janela continua
  responsiva), com barra de progresso, grupo atual e log colorido.
- **Cancelar** interrompe entre um grupo e outro; os dashboards já salvos são
  mantidos.
- **Abrir pasta de saída** abre o resultado no Explorador de Arquivos.

## Aba Envios de INS

A aba reúne quatro etapas, em abas internas:

### 1. Envios

1. Escolha **Motorista** ou **Transportador**.
2. Selecione a **planilha de contatos** (`.xlsx`/`.xlsm`) com as colunas
   `Transportadora` e `E-mail`. Vários endereços na mesma célula podem ser
   separados por `;`, `,` ou espaço.
3. Selecione a **pasta com os arquivos INS** gerados pelo aplicativo (ou pelos
   notebooks).
4. Clique em **Preparar envios**.

Nada é enviado nesse momento. O aplicativo cruza contatos e arquivos, monta um
plano e abre uma **tela de confirmação** com uma linha por transportadora
mostrando arquivo, destinatários, cópia e situação. Só as linhas marcadas e
prontas são enviadas; a prévia do assunto e do corpo pode ser conferida antes
do disparo.

- **Modo debug (validar sem enviar)** faz todo o caminho — leitura, plano,
  conferência e log — sem acionar o Outlook. O botão passa a se chamar
  **Validar envios (debug)**.
- **Cancelar** interrompe após o e-mail atual; os já enviados permanecem.
- **Abrir pasta** abre no Explorador a pasta de arquivos selecionada.

### 2. Corpo do e-mail

Assunto e corpo são editáveis **por tipo de relatório**. O texto usa o marcador
`{transportadora}`, substituído pelo nome do grupo em cada e-mail. O corpo tem
editor com negrito, itálico e sublinhado (atalhos `Ctrl+B`, `Ctrl+I`, `Ctrl+U`),
além de **Inserir {transportadora}** e **Restaurar padrão**.

Os modelos padrão já vêm preenchidos com o texto institucional do INS do
Motorista e do INS do Transportador, incluindo as métricas e as metas de cada
relatório.

### 3. Em cópia (CC)

Lista manual de endereços que entram em **cópia em todos os envios**,
independentemente da transportadora. É possível colar vários de uma vez,
separados por `;`, `,` ou quebra de linha. Endereços inválidos são recusados
na inclusão e, se escaparem, aparecem como aviso no plano.

### 4. Log

Cada transportadora aparece com o resultado do último envio (enviado, falho ou
não encontrado), com contadores de **enviados**, **falhos** e
**não encontrados**. Falhas individuais não interrompem os demais envios. O log
pode ser **exportado para CSV** ou limpo.

### Como os arquivos e contatos são emparelhados

- O nome do arquivo define a transportadora: o trecho entre o prefixo
  (`INS do Motorista - ` ou `INS do Transportador - `) e o `.xlsx` é comparado
  com a coluna `Transportadora`.
- A comparação ignora acentos, caixa e espaços extras — `"Ála Uber"`,
  `"ALA  UBER"` e `"ala uber"` são o mesmo grupo.
- Quando existem dois arquivos para a mesma transportadora, o **mais recente**
  é usado e o outro é registrado como aviso.
- Arquivos temporários do Excel (`~$...`) e planilhas sem o prefixo correto são
  ignorados.
- Cada transportadora recebe **um e-mail**, com o arquivo correspondente
  anexado e o assunto/corpo já personalizados.

## Acessibilidade e telas pequenas

- A janela abre ajustada à área útil da tela (mínimo 860×480) e o conteúdo das
  abas rola quando falta espaço; nada fica cortado em notebooks menores.
- O diálogo de confirmação também se adapta à tela, mantém os botões sempre
  visíveis e rola a prévia do e-mail.
- Navegação por teclado: `Tab` percorre os controles na ordem lógica e
  `Espaço`/`Enter` marcam ou desmarcam a transportadora selecionada na tabela.
- Controles têm nome acessível e os campos exibem anel de foco com contraste
  reforçado, incluindo botões, abas, tabelas e listas.
- Cores de status, botões e textos foram ajustadas para manter contraste
  legível sobre os painéis de vidro.

## Estrutura

```text
ins_dashboard_app/
├── main.py                  # entrada do aplicativo
├── iniciar.bat              # atalho para Windows
├── requirements.txt
├── CONTRATO_UI.md           # contrato entre backend e interface
├── backend/
│   ├── __init__.py
│   ├── reports.py           # regras de cada tipo de relatório
│   ├── models.py            # JobConfig, JobResult, erros
│   ├── processor.py         # leitura, agrupamento e automação do Excel
│   └── envios.py            # contatos, plano de envios e Outlook
├── ui/
│   ├── theme.py             # paleta e QSS Frutiger Aero
│   ├── widgets.py           # fundo, vidro, botões, checkbox, seletores, log
│   ├── worker.py            # QThread da geração de dashboards
│   ├── envios_worker.py     # QThread do planejamento e do envio
│   ├── envios_dialog.py     # confirmação visual antes do disparo
│   ├── envios_tab.py        # aba Envios de INS
│   └── main_window.py       # janela principal (abas)
└── testes/
    ├── smoke_test.py        # valida o backend sem abrir o Excel
    ├── processor_perf_test.py  # reuso do template e leitura com calamine
    ├── estrutura_test.py    # verificador estrutural (pivôs/formas/gráfico)
    ├── estrutura_dashboard.py  # CLI: compara saída real com o template
    ├── e2e_excel.py         # geração real (requer Excel)
    ├── ui_e2e.py            # interface + thread + Excel, ponta a ponta
    ├── envios_test.py       # lógica de envio (sem Outlook)
    └── envios_ui_smoke.py   # aba Envios offscreen (salva captura)
```

## Testes

```powershell
cd ins_dashboard_app
python -m unittest testes.envios_test -v   # envios, sem abrir o Outlook
python -m unittest testes.normalizacao_test -v   # Data Wrangling do Apelido
python -m unittest testes.processor_perf_test testes.estrutura_test -v
python -m testes.smoke_test                # geração, sem abrir o Excel
python -m testes.envios_ui_smoke           # aba Envios offscreen
python -m testes.e2e_excel                 # geração real, abre o Excel
python -m testes.ui_e2e                    # clica em "Gerar" na interface
```

Depois de gerar dashboards reais, o verificador estrutural confere se cada
arquivo manteve as tabelas dinâmicas, o Data Model, o gráfico e as formas do
`Resumo` — é o teste que pega perda de elementos visuais:

```powershell
python -m testes.estrutura_dashboard --template "C:\INS\Template - Transportador.xlsx" --pasta "C:\...\saida"
```

O `envios_ui_smoke` usa planilhas e arquivos sintéticos, não envia e-mail e
valida também proporções, rolagem, foco e nomes acessíveis do diálogo de
confirmação. Ele salva capturas em `_saida_teste/envios.png` e
`_saida_teste/envios_dialogo_baixo.png`.

Os testes de envio usam um remetente falso: nenhum e-mail é disparado.

## Solução de problemas

### Geração de dashboards

- **"Não foi possível abrir o Microsoft Excel"**: confirme que o Excel está
  instalado e feche caixas de diálogo abertas no Excel.
- **"A aba 'INS' não foi encontrada"**: o arquivo escolhido não é o relatório
  correto (Motorista/Transportador) ou a aba foi renomeada.
- **"A tabela '...' não existe"**: o template escolhido não corresponde ao
  tipo de relatório.
- **Aviso de cabeçalho diferente**: o template pode ser de outro relatório; o
  app avisa, mas continua (útil quando o template tem colunas extras).
- **Sem permissão ao salvar**: feche o dashboard no Excel e tente novamente.
- **Geração lenta**: no **Transportador** o template é aberto uma vez e
  reaproveitado entre os grupos; no **Motorista** cada grupo abre e fecha o
  template. Feche outras janelas do Excel e evite manter o template aberto
  durante a geração.

### Envios

- **"O Outlook Desktop não está disponível"**: instale o Microsoft Outlook e o
  `pywin32` (`pip install pywin32`).
- **"Não foi possível abrir o Outlook Desktop"**: abra o Outlook uma vez,
  confirme que o perfil de e-mail está configurado e tente novamente.
- **Planilha de contatos inválida**: o arquivo precisa ter as colunas
  `Transportadora` e `E-mail` (variações como `Email` também são aceitas).
- **Transportadora "Sem contato na planilha"**: o nome do arquivo não bate com
  nenhuma linha da planilha. Ajuste o nome do arquivo ou o cadastro.
- **"Sem e-mail" ou "E-mail inválido"**: o grupo aparece na confirmação, mas
  nunca é disparado; corrija o cadastro e prepare novamente.
- **Nenhum arquivo encontrado**: confira se a pasta é a certa e se os nomes
  começam com `INS do Motorista - ` ou `INS do Transportador - `.
- **Arquivo duplicado ignorado**: o aplicativo usa o mais recente da pasta e
  informa qual foi mantido.
- **Envio lento**: cada e-mail abre o Outlook via COM; em máquinas mais lentas
  alguns segundos por transportadora são normais.

## Privacidade e segurança

A leitura e a geração dos dashboards acontecem localmente, via pandas e Excel.
Os envios saem apenas pelo Outlook já configurado na máquina, para os
destinatários da planilha de contatos e para a lista de cópia — nenhum serviço
externo é usado e nada é enviado sem a confirmação na tela de revisão.

Planilhas, templates e dashboards não são versionados no repositório
(`.gitignore` bloqueia `*.xlsx`), assim como pastas de teste e caches.
