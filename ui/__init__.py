"""Interface gráfica do INS Dashboard Studio (PyQt6, visual Frutiger Aero).

Módulos:

* :mod:`ui.theme` -- paleta de cores e folha de estilo QSS;
* :mod:`ui.widgets` -- componentes reutilizáveis (céu, vidro, botões, log…);
* :mod:`ui.worker` -- execução do backend em ``QThread``;
* :mod:`ui.main_window` -- janela principal.
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
