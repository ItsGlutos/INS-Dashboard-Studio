# Contrato entre backend e interface (INS Dashboard Studio)

Este documento é obrigatório para o subagente `frontend`. O backend **já está
pronto e testado**; a interface apenas o consome.

## Estrutura

```text
ins_dashboard_app/
├── main.py              # entrada do app (criada pelo frontend)
├── backend/             # NÃO ALTERAR (pandas + xlwings)
├── ui/                  # interface PyQt6 (criada pelo frontend)
├── testes/              # testes do backend
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

## Requisitos técnicos

- PyQt6, Python 3.14, Windows.
- `main.py` cria `QApplication`, define estilo `Fusion` + QSS, fonte
  "Segoe UI", abre `MainWindow` centralizada (~1000x760) e roda o loop.
- Separação em módulos: `ui/theme.py` (QSS/cores), `ui/widgets.py`
  (componentes reutilizáveis), `ui/worker.py` (QThread), `ui/main_window.py`.
- Nada de caminhos fixos de arquivos: **toda** seleção de arquivo/pasta passa
  por `QFileDialog`.
- Nenhuma dependência além de PyQt6 (e o backend).
- Sem assets externos: desenhe fundo/ícones com `QPainter`/QSS.
- Não alterar `backend/`, `testes/`, `requirements.txt` nem os `.ipynb`.

## Direção visual: Frutiger Aero (anos 2000 / Windows Vista-7)

- Fundo céu em degradê (azul profundo → ciano claro) com brilho de sol,
  bolhas translúcidas e reflexos — desenhado em `paintEvent` do widget
  central, sem imagens.
- Painéis de "vidro" (glassmorphism): fundo semi-transparente claro,
  borda branca suave, cantos arredondados, sombra.
- Botões glossy com degradê vertical, metade superior clara, brilho
  (`qlineargradient`), hover mais claro, pressed mais escuro.
- Paleta: azul #0a4d8c / #1e90ff / #7fd4ff, verde água #63d8c4,
  branco #f5fbff, texto escuro #0b2b46 em painéis claros.
- Tipografia Segoe UI; títulos em negrito; texto legível (contraste AA).
- Detalhes: indicador de status tipo LED, barra de progresso azul brilhante,
  ícone da janela desenhado em código (bolha/onda) via `QPainter`.
- Animações leves são bem-vindas (QPropertyAnimation), sem exageros.
- Evitar aparência "flat genérica"; o alvo é o visual aquoso/brilhante da era
  Frutiger Aero.

## Critérios de aceite

- `python -m py_compile main.py ui/*.py` sem erros.
- Smoke test offscreen sem exceções:

  ```powershell
  $env:QT_QPA_PLATFORM='offscreen'; python -c "from PyQt6.QtWidgets import QApplication; from ui.main_window import MainWindow; app=QApplication([]); w=MainWindow(); print(w.windowTitle()); w.close()"
  ```

- Nenhuma chamada ao backend na thread da GUI.
- Os quatro controles exigidos existem e abrem `QFileDialog`.
