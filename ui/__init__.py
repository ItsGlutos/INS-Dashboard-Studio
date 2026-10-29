"""Interface gráfica do INS Dashboard Studio (PyQt6, visual Frutiger Aero).

Módulos:

* :mod:`ui.theme` -- paleta de cores e folha de estilo QSS;
* :mod:`ui.widgets` -- componentes reutilizáveis (céu, vidro, botões, log…);
* :mod:`ui.worker` -- execução do backend em ``QThread``;
* :mod:`ui.main_window` -- janela principal.

.. note::
   **O visual (Frutiger Aero) será refeito em breve.** Ao ler este pacote,
   separe mentalmente duas camadas:

   * **estética** -- QSS, cores, ``QPainter``, sombras, animações e tamanhos.
     Pode ser substituída no redesign sem afetar o restante do app.
   * **funcional** -- ligação de sinais, threads, validações, persistência
     (``QSettings``), acessibilidade e regras de negócio. **Deve ser
     preservada** no redesign.

   Os componentes de :mod:`ui.widgets` expõem uma API pública estável; o
   desenho interno pode mudar, mas os nomes/métodos usados pelas telas não.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Garante que o pacote ``backend`` (que fica ao lado de ``ui``) possa ser
# importado mesmo quando a aplicação é iniciada de fora do diretório do app.
_APP_DIR = Path(__file__).resolve().parent.parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

__all__ = ["main_window", "theme", "widgets", "worker"]
