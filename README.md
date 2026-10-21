# INS Dashboard Studio

Aplicativo desktop (Windows) que gera, em lote, os dashboards **INS do
Motorista** e **INS do Transportador** a partir das planilhas de origem e dos
templates do Excel.

A interface foi construída em **PyQt6** com estética *Frutiger Aero* (vidro,
céu em degradê e botões glossy). O processamento usa **pandas + xlwings** para
preencher o template no Microsoft Excel e salvar um arquivo por
motorista/transportadora.

> Os notebooks originais (`Dashboards_Motorista.ipynb` e
> `Dashboards_Transportador.ipynb`) **não são modificados**. Este projeto é uma
> pasta separada que reproduz a mesma lógica.

## Requisitos

- Windows 10/11
- Microsoft Excel instalado (a automação usa o Excel via COM)
- Python 3.11+ (testado com 3.14)

Instale as dependências:

```powershell
cd ins_dashboard_app
pip install -r requirements.txt
```

## Como executar

```powershell
cd ins_dashboard_app
python main.py
```

ou dê duplo clique em `iniciar.bat`.

## Como usar

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

Durante a geração o Excel é aberto **invisível**. Evite abrir/editar os
arquivos de origem, template ou saída enquanto o processo roda.

## Interface

A janela segue o estilo **Frutiger Aero** (céu em degradê com sol e bolhas,
painéis de vidro translúcido, botões glossy), tudo desenhado em QSS/QPainter,
sem imagens externas.

- **Motorista | Transportador**: alterna o tipo de relatório e mostra a coluna
  de agrupamento usada.
- **Arquivo do relatório**, **Template do dashboard** e **Pasta de saída**:
  abrem o explorador de arquivos (`QFileDialog`); o caminho completo aparece
  no tooltip.
- **Gerar dashboards**: executa em uma thread separada (a janela continua
  responsiva), com barra de progresso, grupo atual e log colorido.
- **Cancelar**: interrompe entre um grupo e outro; os dashboards já salvos são
  mantidos.
- **Abrir pasta de saída**: abre o resultado no Explorador de Arquivos.

As preferências (tipo de relatório e últimos caminhos) são lembradas via
`QSettings`. Fechar a janela durante a geração pede confirmação e só encerra
depois que o Excel é liberado.

## Estrutura

```text
ins_dashboard_app/
├── main.py               # entrada do aplicativo
├── iniciar.bat           # atalho para Windows
├── requirements.txt
├── CONTRATO_UI.md        # contrato entre backend e interface
├── backend/
│   ├── reports.py        # regras de cada tipo de relatório
│   ├── models.py         # JobConfig, JobResult, erros
│   └── processor.py      # leitura, agrupamento e automação do Excel
├── ui/
│   ├── theme.py          # paleta e QSS Frutiger Aero
│   ├── widgets.py        # fundo, vidro, botões, seletores, log, LED
│   ├── worker.py         # QThread que executa o backend
│   └── main_window.py    # janela principal
└── testes/
    ├── smoke_test.py     # valida o backend sem abrir o Excel
    ├── e2e_excel.py      # geração real (requer Excel)
    └── ui_e2e.py         # interface + thread + Excel, ponta a ponta
```

O subagente responsável pela interface está em
`.opencode/agents/frontend.md` (OpenCode).

## Testes

```powershell
cd ins_dashboard_app
python -m testes.smoke_test    # rápido, não abre o Excel
python -m testes.e2e_excel     # ponta a ponta, abre o Excel
python -m testes.ui_e2e        # clica em "Gerar" na interface (offscreen)
```

## Solução de problemas

- **"Não foi possível abrir o Microsoft Excel"**: confirme que o Excel está
  instalado e feche caixas de diálogo abertas no Excel.
- **"A aba 'INS' não foi encontrada"**: o arquivo escolhido não é o relatório
  correto (Motorista/Transportador) ou a aba foi renomeada.
- **"A tabela '...' não existe"**: o template escolhido não corresponde ao
  tipo de relatório.
- **Aviso de cabeçalho diferente**: o template pode ser de outro relatório; o
  app avisa, mas continua (útil quando o template tem colunas extras).
- **Sem permissão ao salvar**: feche o dashboard no Excel e tente novamente.
- **Geração lenta**: cada grupo abre e fecha o template no Excel; 20 s por
  grupo é normal em máquinas mais lentas.

## Privacidade e segurança

Nenhum dado sai da máquina: toda a leitura/escrita acontece localmente, via
pandas e Excel.
