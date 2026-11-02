# Contrato entre backend e interface (INS Dashboard Studio)

Este documento é obrigatório para o subagente `frontend`. O backend **já está
pronto e testado**; a interface apenas o consome.

## Estrutura

```text
ins_dashboard_app/
├── main.py              # entrada do app
├── backend/             # pandas + xlwings + Outlook (não alterar pela UI)
│   ├── __init__.py
│   ├── reports.py
│   ├── models.py
│   ├── processor.py
│   └── envios.py
├── ui/                  # interface PyQt6
│   ├── theme.py
│   ├── widgets.py
│   ├── worker.py
│   ├── envios_worker.py
│   ├── envios_dialog.py
│   ├── envios_tab.py
│   └── main_window.py
├── testes/              # testes do backend e smoke tests da UI
└── requirements.txt
```

## API do backend (importar de `backend`)

```python
from backend import (
    REPORT_TYPES,        # dict[str, ReportType]: "motorista" | "transportador"
    get_report_type,
    JobConfig,           # dataclass: report_type, source_file, template_file, output_dir
    DashboardProcessor,  # motor de geração
    JobError,            # erro esperado, com mensagem pronta para o usuário
    JobCancelled,        # cancelamento solicitado pelo usuário
    GroupInfo,           # name, rows, output_name
    GroupResult,         # group, rows, output_path
    JobResult,           # report_label, outputs, total_rows, duration_seconds, warnings
)
```

### `ReportType`

Campos úteis para a UI: `key`, `label` ("INS do Motorista"), `short_label`
("Motorista"), `description`, `group_column`.

### `JobConfig`

```python
config = JobConfig(
    report_type=get_report_type("motorista"),
    source_file=Path(...),     # planilha INS de origem (.xlsx)
    template_file=Path(...),   # template do dashboard (.xlsx)
    output_dir=Path(...),      # pasta de saída
)
config.validate()              # levanta JobError com mensagem amigável
```

### `DashboardProcessor`

```python
processor = DashboardProcessor(
    on_progress=callback,   # (atual: int, total: int, grupo: str) -> None
    on_log=callback,        # (mensagem: str, nivel: str) -> None
    should_cancel=callback, # () -> bool
)
grupos = processor.discover_groups(config)  # list[GroupInfo], não abre o Excel
resultado = processor.run(config)           # JobResult (bloqueante!)
```

Níveis de log: `"info"`, `"success"`, `"warning"`, `"error"`.

**`run()` é bloqueante e usa COM/Excel: execute SEMPRE em uma thread
trabalhadora** (QThread), nunca na thread da GUI.

### Envios (`from backend.envios import ...`)

```python
ler_contatos(caminho)          # dict[str, Contato] (Transportadora + E-mail)
localizar_arquivos(pasta, key) # list[ArquivoINS] pelos prefixos INS do ...
montar_plano(report_key, contatos_path, pasta_arquivos,
             copia_manual=None, assunto=None, corpo=None)  # PlanoEnvios
enviar_plano(plano, chaves, sender_factory=None,
             on_progress=None, on_log=None,
             should_cancel=None)  # EnvioResultado
```

- `PlanoEnvios.grupos` traz `status` (`pronto`, `sem_contato`, `sem_email`,
  `email_invalido`), `para`, `copia`, `assunto`, `corpo` e `arquivo`.
- `OutlookSender` abre o Outlook via `pywin32`; `enviar_plano` aceita um
  `sender_factory` falso nos testes.
- `montar_plano` e `enviar_plano` são bloqueantes: executar em `PlanWorker` e
  `SendWorker` (`ui/envios_worker.py`), nunca na thread da GUI.
- Nada é enviado antes da confirmação em `EnviosConfirmDialog`; em modo debug
  o diálogo apenas valida.

## Requisitos funcionais da UI

1. Seletor do tipo de relatório: **Motorista** vs **Transportador**, com
   destaque claro do tipo ativo. Ao trocar, atualizar textos auxiliares
   (coluna de agrupamento e descrição).
2. Seletor do **arquivo do relatório** (planilha de origem) via `QFileDialog`.
3. Seletor do **template do dashboard** via `QFileDialog`.
4. Seletor da **pasta de saída** via `QFileDialog.getExistingDirectory`.
5. Mostrar o caminho escolhido (elidido no meio, tooltip com caminho completo)
   e permitir trocar/limpar.
6. Botão **Gerar dashboards**: valida com `config.validate()`, desabilita
   entradas, mostra progresso (`atual/total`, barra, nome do grupo) e logs.
7. Botão **Cancelar** durante a execução (seta flag consultada por
   `should_cancel`), e restauração do estado ao final.
8. Ao concluir, resumo (nº de dashboards, linhas, duração) e opção de abrir a
   pasta de saída no Explorador (`os.startfile` no Windows).
9. Erros de `JobError` em `QMessageBox` com a mensagem do backend; nunca
   traceback cru para o usuário.
10. Persistir última pasta/arquivos e tipo de relatório com `QSettings`
    (opcional, mas recomendado).

### Aba Envios de INS

1. Abas internas **Envios**, **Corpo do e-mail**, **Em cópia (CC)** e **Log**.
2. Seletores da **planilha de contatos** e da **pasta com os arquivos INS**.
3. **Preparar envios** monta o plano sem disparar nada e abre a confirmação.
4. Confirmação com tabela por transportadora (arquivo, para, cópia, situação),
   prévia de assunto/corpo e seleção individual; **só os grupos marcados e
   prontos** são enviados.
5. **Modo debug** valida tudo e registra no log sem acionar o Outlook.
6. Assunto e corpo editáveis por tipo, com `{transportadora}`, formatação
   básica e restauração do texto padrão.
7. Lista de cópia (CC) aplicada a todos os envios, com validação de e-mail.
8. Log por transportadora, contadores e exportação para CSV.
9. **Cancelar** interrompe após o e-mail atual; fechar a janela durante um
   envio é bloqueado.

## Acessibilidade e responsividade

- Nome acessível (`setAccessibleName`) em botões, campos, tabelas, listas,
  abas e indicadores; descrições nos controles não óbvios.
- Ordem de foco explícita no diálogo (`select_all` → tabela → prévia →
  Cancelar → Confirmar) e indicador de foco visível com contraste reforçado.
- Alvos de clique com pelo menos 24×24 px (checkbox, limpar seleção, botões).
- `Espaço`/`Enter` alternam a transportadora selecionada na tabela.
- Janela mínima de 860×480, dimensionada pela área útil da tela; conteúdo das
  abas e prévia do diálogo em `QScrollArea` para não cortar em telas baixas.
- Cores de texto e status com contraste legível nos temas claro e escuro.

## Requisitos técnicos

- PyQt6, Python 3.11+, Windows.
- `main.py` cria `QApplication`, define estilo `Fusion` + QSS, fonte
  "Chivo" (com fallback "Segoe UI"), abre `MainWindow` centralizada e roda o
  loop. As fontes Chivo são embarcadas em `ui/assets/fonts` (licença OFL).
- Separação em módulos: `ui/theme.py` (QSS/cores), `ui/widgets.py`
  (componentes reutilizáveis), `ui/worker.py` e `ui/envios_worker.py`
  (QThread), `ui/envios_tab.py`, `ui/envios_dialog.py` e
  `ui/main_window.py`.
- Nada de caminhos fixos de arquivos: **toda** seleção de arquivo/pasta passa
  por `QFileDialog`.
- Sem imagens externas: fundo e ícones são desenhados com `QPainter`/QSS.
  Apenas os arquivos de fonte Chivo (OFL) acompanham o projeto.
- Não alterar os `.ipynb`.

## Direção visual: manual institucional GrupoSC

Referência: `ins.fig` (frames claro e escuro), implementado com `QPainter` e
QSS — sem imagens.

- **Base clara**: fundo `#F8FAFC` com malha técnica discreta, cartões brancos
  de aresta 8 px (`#E2E8F0`), texto `#1C2445`.
- **Base escura**: fundo `#101B33`, cartões `#16224A`, bordas `#23335A`,
  texto `#FFFFFF`/`#C9D6E8`, console `#08132B`.
- **Institucional**: barra superior e rodapé em azul-marinho `#1C2445`
  (escuro: `#08132B`), filetes de acento laranja `#FF9F00` e azul `#0090D0`
  (escuro: `#33A6DE`), classificação em âmbar.
- **Tipografia Chivo** (Regular/SemiBold/Bold/ExtraBold/Black) com fallback
  Segoe UI; títulos 25 px, corpo 13 px, rótulos técnicos 10 px com
  `letter-spacing`.
- **Componentes**: cartões com filete 40×4 px no topo esquerdo, seletor
  segmentado (laranja/azul), selos de estado (`PENDENTE`, `SELECIONADO`,
  `PRONTO`), console escuro com cabeçalho de terminal e log com hora/nível.
- **Tema claro/escuro**: alternado pelo botão sol/lua no cabeçalho
  (`ThemeToggle`), persistido em `QSettings` (`ui/theme`). `build_stylesheet()`
  recebe o tema e `ui/widgets` lê a paleta em tempo de pintura.
- **Ícones**: vetoriais em `ui/icons.py` (grade 24×24), coloridos por papel
  semântico (`accent`, `muted`, `navy`, etc.).
- **Acessibilidade**: foco visível, alvos ≥ 24 px, contraste AA nos dois temas;
  o console mantém texto claro sobre fundo escuro em ambos.

O visual "Frutiger Aero" (céu, bolhas, vidro glossy) foi substituído por esta
linguagem institucional; nenhuma lógica de backend ou fluxo operacional mudou.

## Critérios de aceite

- `python -m py_compile main.py ui/*.py` sem erros.
- Smoke test offscreen sem exceções:

  ```powershell
  $env:QT_QPA_PLATFORM='offscreen'; python -c "from PyQt6.QtWidgets import QApplication; from ui.main_window import MainWindow; from ui.theme import build_stylesheet, set_theme; app=QApplication([]); app.setStyleSheet(build_stylesheet()); w=MainWindow(); w._apply_theme('dark'); w._apply_theme('light'); print(w.windowTitle()); w.close()"
  ```

- Nenhuma chamada ao backend na thread da GUI.
- Os quatro controles exigidos existem e abrem `QFileDialog`.
- Aba Envios e diálogo de confirmação validados sem Outlook:

  ```powershell
  python -m testes.envios_ui_smoke
  ```
