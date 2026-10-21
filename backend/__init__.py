"""Backend de geração dos dashboards INS.

A interface gráfica consome apenas este pacote e não conhece xlwings/pandas:

.. code-block:: python

    from backend import (
        REPORT_TYPES,
        DashboardProcessor,
        GroupInfo,
        GroupResult,
        JobCancelled,
        JobConfig,
        JobError,
        JobResult,
        get_report_type,
    )

    config = JobConfig(
        report_type=get_report_type("motorista"),
        source_file=Path("INS do Motorista - 2026.xlsx"),
        template_file=Path("Dashboard - Template.xlsx"),
        output_dir=Path("Pasta resultados"),
    )

    processor = DashboardProcessor(
        on_progress=lambda atual, total, grupo: ...,
        on_log=lambda mensagem, nivel: ...,   # nivel: info|success|warning|error
        should_cancel=lambda: parar.is_set(),
    )

    grupos = processor.discover_groups(config)  # opcional, sem abrir o Excel
    resultado = processor.run(config)
"""

from .models import (
    GroupInfo,
    GroupResult,
    JobCancelled,
    JobConfig,
    JobError,
    JobResult,
)
from .processor import DashboardProcessor
from .reports import (
    MOTORISTA,
    REPORT_TYPES,
    TRANSPORTADOR,
    ReportType,
    get_report_type,
    sanitize_filename,
)

__all__ = [
    "DashboardProcessor",
    "GroupInfo",
    "GroupResult",
    "JobCancelled",
    "JobConfig",
    "JobError",
    "JobResult",
    "MOTORISTA",
    "TRANSPORTADOR",
    "REPORT_TYPES",
    "ReportType",
    "get_report_type",
    "sanitize_filename",
]
