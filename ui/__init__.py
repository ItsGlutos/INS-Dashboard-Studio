"""Interface gráfica do INS Dashboard Studio (PyQt6, identidade GrupoSC).

Módulos:

* :mod:`ui.theme` -- paletas clara/escura e folha de estilo QSS;
* :mod:`ui.icons` -- ícones vetoriais desenhados com ``QPainter``;
* :mod:`ui.widgets` -- componentes reutilizáveis (cartões, botões, console…);
* :mod:`ui.worker` -- execução do backend em ``QThread``;
* :mod:`ui.main_window` -- janela principal.

.. note::
   Ao ler este pacote, separe mentalmente duas camadas:

   * **estética** -- QSS, cores, ``QPainter``, ícones, espaçamentos e temas.
   * **funcional** -- ligação de sinais, threads, validações, persistência
     (``QSettings``), acessibilidade e regras de negócio.

   Os componentes de :mod:`ui.widgets` expõem uma API pública estável; o
   desenho interno pode mudar, mas os nomes/métodos usados pelas telas não.
   A alternância claro/escuro é a única interação acrescentada ao aplicativo.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Garante que o pacote ``backend`` (que fica ao lado de ``ui``) possa ser
# importado mesmo quando a aplicação é iniciada de fora do diretório do app.
_APP_DIR = Path(__file__).resolve().parent.parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

__all__ = ["icons", "main_window", "theme", "widgets", "worker"]
