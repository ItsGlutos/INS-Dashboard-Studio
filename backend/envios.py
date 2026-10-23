"""Lógica de envio dos relatórios INS por transportadora.

O módulo é independente da interface gráfica e do Outlook na importação:
a automação do Outlook só acontece quando um envio real é executado.

Fluxo principal:

1. :func:`ler_contatos` lê a planilha-dicionário (``Transportadora`` + ``E-mail``);
2. :func:`localizar_arquivos` encontra os ``INS do Motorista/Transportador - *.xlsx``;
3. :func:`montar_plano` cruza os dois lados e monta um :class:`PlanoEnvios`;
4. :func:`enviar_plano` envia apenas os grupos selecionados, um e-mail por
   transportadora, com o arquivo correspondente anexado.

O envio real usa o Outlook Desktop via ``pywin32`` (o mesmo caminho dos
notebooks originais). Para testes, :func:`enviar_plano` aceita um
``sender_factory`` que devolve qualquer objeto com ``enviar(grupo)`` e
``fechar()``.
"""

from __future__ import annotations

import re
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Sequence

import pandas as pd

__all__ = [
    "DEFAULT_ASSUNTOS",
    "DEFAULT_CORPOS",
    "PREFIXOS",
    "Contato",
    "EnvioError",
    "EnvioResultado",
    "GrupoEnvio",
    "OutlookSender",
    "PlanoEnvios",
    "dividir_emails",
    "enviar_plano",
    "ler_contatos",
    "localizar_arquivos",
    "montar_plano",
    "normalizar_chave",
    "renderizar_template",
    "validar_email",
]


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
PREFIXOS: dict[str, str] = {
    "motorista": "INS do Motorista - ",
    "transportador": "INS do Transportador - ",
}

DEFAULT_ASSUNTOS: dict[str, str] = {
    "motorista": "{transportadora} - INS do Motorista 2026",
    "transportador": "{transportadora} - INS do Transportador 2026",
}

DEFAULT_CORPOS: dict[str, str] = {
    "motorista": """
<p>Olá, time <strong>{transportadora}</strong>! Tudo bem?</p>

<p>
Compartilhamos o relatório mensal do <strong>Indicador de Nível de Serviço (INS) do Motorista</strong>,
parte da rotina de acompanhamento dos indicadores de performance da operação de transporte.
</p>

<p>
O relatório contempla informações referentes ao mês imediatamente anterior ao atual,
conforme calendário de fechamento e consolidação dos indicadores da equipe de Transportes.
</p>

<p><strong>O INS do Motorista é composto pelas seguintes métricas:</strong></p>

<ul>
    <li><strong>Transit Time:</strong> percentual de rotas concluídas dentro do horário meta estabelecido pelo sistema TNS.</li>
    <li><strong>Logins TNS:</strong> realização do login no aplicativo TNS no momento do início da rota.</li>
    <li><strong>Ocorrências:</strong> registro adequado das ocorrências no aplicativo TNS, seguindo os padrões definidos para apontamentos.</li>
    <li><strong>Volumes Conferidos:</strong> percentual de volumes expedidos que foram devidamente bipados e conferidos durante a operação.</li>
</ul>

<p><strong>Meta do INS Motorista: 95%</strong></p>

<p>
O acompanhamento contínuo deste resultado é fundamental para garantir a excelência operacional
e promover ações de melhoria contínua na execução das rotas.
</p>

<p>Em caso de dúvidas ou necessidade de esclarecimentos adicionais, nossa equipe permanece à disposição.</p>

<p>Atenciosamente,<br></p>

<p><strong>Qualidade | Transporte &amp; Segurança</strong></p>
""".strip(),
    "transportador": """
<p>Olá, time <strong>{transportadora}</strong>.</p>

<p>Espero que estejam bem.</p>

<p>
Compartilhamos o relatório mensal do <strong>Indicador de Nível de Serviço (INS) do Transportador</strong>,
parte da rotina de acompanhamento dos indicadores de performance da operação de transporte.
</p>

<p>
O relatório contempla informações com uma defasagem de dois meses em relação ao período atual,
em função dos calendários de fechamento e consolidação das informações pelas equipes responsáveis pelo processo.
</p>

<p><strong>O INS do Transportador é composto pelas seguintes métricas:</strong></p>

<ul>
    <li><strong>Transit Time:</strong> percentual de rotas concluídas dentro do horário meta estabelecido pelo sistema TNS.</li>
    <li><strong>Logins TNS:</strong> realização do login no aplicativo TNS no momento do início da rota.</li>
    <li><strong>Ocorrências:</strong> registro adequado das ocorrências no aplicativo TNS, seguindo os padrões definidos para apontamentos.</li>
    <li><strong>Volumes Conferidos:</strong> percentual de volumes expedidos que foram devidamente bipados e conferidos durante a operação.</li>
    <li><strong>CFD:</strong> aplicação da Confissão de Dívida.</li>
    <li><strong>Protocolos:</strong> percentual de protocolos de devolução pendentes de regularização.</li>
    <li><strong>Classificação Sanitária/Regulatória:</strong> avaliação sanitária dos pontos de transbordo realizada pela equipe de Regulatório.</li>
    <li><strong>Manifestos:</strong> percentual de manifestos de entrega pendentes de regularização.</li>
    <li><strong>Entregas:</strong> percentual de entregas realizadas até às 15h, conforme meta operacional estabelecida.</li>
    <li><strong>Quebras de Veículos:</strong> monitoramento de ocorrências de falhas mecânicas na frota durante as operações de entrega.</li>
</ul>

<p><strong>Meta do INS Transportador: 90%</strong></p>

<p>
O acompanhamento contínuo deste resultado é fundamental para fortalecer a qualidade operacional,
garantir a conformidade dos processos e direcionar oportunidades de melhoria junto aos parceiros transportadores.
</p>

<p>Em caso de dúvidas ou necessidade de esclarecimentos adicionais, nossa equipe permanece à disposição.</p>

<p>Atenciosamente,<br></p>

<p><strong>Qualidade | Transporte &amp; Segurança</strong></p>
""".strip(),
}

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_SEPARADORES_RE = re.compile(r"[;,\s]+")
_ESPACOS_RE = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# Exceções
# ---------------------------------------------------------------------------
class EnvioError(Exception):
    """Erro esperado, com mensagem pronta para ser mostrada ao usuário."""


# ---------------------------------------------------------------------------
# Normalização e validação
# ---------------------------------------------------------------------------
def normalizar_chave(texto: object) -> str:
    """Padroniza nomes para o cruzamento entre arquivos e contatos.

    Remove acentos, ignora caixa e colapsa espaços — assim
    ``" Ála  Uber "`` e ``"ALA UBER"`` viram a mesma chave.
    """
    decomposto = unicodedata.normalize("NFKD", str(texto))
    sem_acento = "".join(
        caractere
        for caractere in decomposto
        if not unicodedata.combining(caractere)
    )
    return _ESPACOS_RE.sub(" ", sem_acento).strip().lower()


def validar_email(email: object) -> bool:
    """Diz se um endereço tem o formato mínimo aceito pelo Outlook.

    Além do formato básico, rejeita pontos no início/fim da parte local ou do
    domínio e pontos consecutivos, que são erros comuns de digitação.
    """
    texto = str(email).strip().strip(";, ")
    if not texto or ".." in texto:
        return False
    if not _EMAIL_RE.match(texto):
        return False
    local, separador, dominio = texto.partition("@")
    if not separador or not local or not dominio:
        return False
    if local.startswith(".") or local.endswith("."):
        return False
    if (
        dominio.startswith(".")
        or dominio.endswith(".")
        or "." not in dominio
    ):
        return False
    return True


def dividir_emails(texto: object) -> list[str]:
    """Divide uma célula/lista em e-mails únicos, preservando a ordem."""
    if texto is None or (isinstance(texto, float) and pd.isna(texto)):
        return []
    partes = _SEPARADORES_RE.split(str(texto).strip())
    vistos: set[str] = set()
    resultado: list[str] = []
    for parte in partes:
        email = parte.strip().strip(",;")
        if not email:
            continue
        chave = email.lower()
        if chave in vistos:
            continue
        vistos.add(chave)
        resultado.append(email)
    return resultado


def renderizar_template(texto: str, nome_transportadora: str) -> str:
    """Troca ``{transportadora}`` pelo nome do grupo no assunto/corpo."""
    return str(texto).replace("{transportadora}", nome_transportadora)


# ---------------------------------------------------------------------------
# Leitura das fontes
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Contato:
    """Contato consolidado de uma transportadora."""

    nome: str
    emails: tuple[str, ...]
    emails_invalidos: tuple[str, ...] = ()


@dataclass(frozen=True)
class ArquivoINS:
    """Arquivo ``INS do ... - <transportadora>.xlsx`` encontrado na pasta."""

    caminho: Path
    nome_transportador: str
    chave: str


def ler_contatos(caminho: str | Path) -> dict[str, Contato]:
    """Lê a planilha-dicionário de contatos e consolida por transportadora.

    Aceita variações de caixa nas colunas (``Transportadora``/``E-mail``).
    E-mails repetidos são removidos e os inválidos ficam separados para que
    a interface possa avisar sem bloquear os endereços bons.
    """
    caminho = Path(caminho)
    if not caminho.is_file():
        raise EnvioError(
            f"Planilha de contatos não encontrada:\n{caminho}\n\n"
            "Escolha o arquivo .xlsx com as colunas 'Transportadora' e 'E-mail'."
        )

    try:
        dataframe = pd.read_excel(caminho, index_col=False)
    except Exception as erro:  # noqa: BLE001 - mensagem amigável
        raise EnvioError(
            f"Não foi possível ler a planilha de contatos:\n{caminho}\n\n"
            f"Detalhe técnico: {erro}"
        ) from erro

    colunas = {
        str(coluna).strip().lower(): coluna for coluna in dataframe.columns
    }
    coluna_transportadora = colunas.get("transportadora")
    coluna_email = next(
        (
            colunas[chave]
            for chave in ("e-mail", "email", "e mail", "e-mails", "emails")
            if chave in colunas
        ),
        None,
    )
    if coluna_transportadora is None or coluna_email is None:
        encontradas = ", ".join(str(coluna) for coluna in dataframe.columns)
        raise EnvioError(
            "A planilha de contatos precisa das colunas 'Transportadora' e "
            "'E-mail'.\n\n"
            f"Colunas encontradas: {encontradas or '(nenhuma)'}"
        )

    contatos: dict[str, Contato] = {}
    for _, linha in dataframe.iterrows():
        nome_bruto = linha[coluna_transportadora]
        if nome_bruto is None or (isinstance(nome_bruto, float) and pd.isna(nome_bruto)):
            continue
        nome = str(nome_bruto).strip()
        if not nome:
            continue
        chave = normalizar_chave(nome)
        if not chave:
            continue

        texto_email = linha[coluna_email]
        emails = dividir_emails(texto_email)
        validos = tuple(email for email in emails if validar_email(email))
        invalidos = tuple(email for email in emails if not validar_email(email))

        existente = contatos.get(chave)
        if existente is None:
            contatos[chave] = Contato(
                nome=nome, emails=validos, emails_invalidos=invalidos
            )
            continue

        contatos[chave] = Contato(
            nome=existente.nome,
            emails=_unir_unicos(existente.emails, validos),
            emails_invalidos=_unir_unicos(
                existente.emails_invalidos, invalidos
            ),
        )
    return contatos


def localizar_arquivos(
    pasta: str | Path, report_key: str
) -> list[ArquivoINS]:
    """Lista os arquivos do tipo informado, ignorando temporários do Excel."""
    pasta = Path(pasta)
    if not pasta.is_dir():
        raise EnvioError(
            f"Pasta de arquivos INS não encontrada:\n{pasta}\n\n"
            "Escolha a pasta que contém os arquivos gerados."
        )
    prefixo = PREFIXOS.get(report_key)
    if prefixo is None:
        raise EnvioError(f"Tipo de relatório desconhecido: {report_key!r}.")

    arquivos: list[ArquivoINS] = []
    for caminho in pasta.iterdir():
        if not caminho.is_file():
            continue
        nome = caminho.name
        if nome.startswith("~$"):
            continue
        if not nome.lower().endswith(".xlsx"):
            continue
        if not nome.lower().startswith(prefixo.lower()):
            continue
        resto = nome[len(prefixo):]
        nome_transportador = resto[: -len(".xlsx")].strip()
        if not nome_transportador:
            continue
        arquivos.append(
            ArquivoINS(
                caminho=caminho,
                nome_transportador=nome_transportador,
                chave=normalizar_chave(nome_transportador),
            )
        )
    arquivos.sort(key=lambda arquivo: arquivo.chave)
    return arquivos


# ---------------------------------------------------------------------------
# Plano de envios
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class GrupoEnvio:
    """Um e-mail que será montado para uma transportadora."""

    chave: str
    nome: str
    arquivo: Path
    para: tuple[str, ...]
    copia: tuple[str, ...]
    assunto: str
    corpo: str
    status: str
    detalhe: str = ""
    emails_invalidos: tuple[str, ...] = ()

    @property
    def pronto(self) -> bool:
        """Indica se o grupo tem arquivo e pelo menos um destinatário válido."""
        return self.status == "pronto" and bool(self.para)

    @property
    def rotulo_status(self) -> str:
        """Texto amigável da situação do grupo."""
        return {
            "pronto": "Pronto para envio",
            "sem_contato": "Sem contato na planilha",
            "sem_email": "Contato sem e-mail",
            "email_invalido": "E-mail inválido",
        }.get(self.status, self.status)


@dataclass
class PlanoEnvios:
    """Resultado do cruzamento entre contatos, arquivos e modelos."""

    report_key: str
    grupos: list[GrupoEnvio] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    @property
    def prontos(self) -> list[GrupoEnvio]:
        """Grupos que podem ser enviados agora."""
        return [grupo for grupo in self.grupos if grupo.pronto]

    @property
    def sem_contato(self) -> list[GrupoEnvio]:
        """Arquivos cuja transportadora não existe na planilha."""
        return [grupo for grupo in self.grupos if grupo.status == "sem_contato"]

    @property
    def sem_email(self) -> list[GrupoEnvio]:
        """Transportadoras cadastradas, mas sem nenhum e-mail."""
        return [grupo for grupo in self.grupos if grupo.status == "sem_email"]

    @property
    def email_invalido(self) -> list[GrupoEnvio]:
        """Transportadoras cujo cadastro não tem nenhum e-mail válido."""
        return [grupo for grupo in self.grupos if grupo.status == "email_invalido"]

    @property
    def nao_encontrados(self) -> list[GrupoEnvio]:
        """Grupos que não podem ser enviados, por qualquer motivo."""
        return [grupo for grupo in self.grupos if not grupo.pronto]

    def resumo(self) -> str:
        """Resumo curto para a interface e para o log."""
        return (
            f"{len(self.grupos)} grupo(s) · "
            f"{len(self.prontos)} pronto(s) · "
            f"{len(self.sem_contato)} sem contato · "
            f"{len(self.sem_email)} sem e-mail · "
            f"{len(self.email_invalido)} com e-mail inválido"
        )


def montar_plano(
    report_key: str,
    contatos_path: str | Path,
    pasta_arquivos: str | Path,
    copia_manual: Iterable[str] | None = None,
    assunto: str | None = None,
    corpo: str | None = None,
) -> PlanoEnvios:
    """Cruza contatos e arquivos e devolve todos os grupos de envio.

    Quando existem dois arquivos para a mesma transportadora, o mais recente
    é usado e o outro é registrado em ``avisos``. Isso evita disparar o mesmo
    e-mail duas vezes por causa de uma versão antiga esquecida na pasta.
    """
    if report_key not in PREFIXOS:
        raise EnvioError(f"Tipo de relatório desconhecido: {report_key!r}.")

    assunto_template = (
        DEFAULT_ASSUNTOS[report_key] if assunto is None else assunto
    )
    corpo_template = DEFAULT_CORPOS[report_key] if corpo is None else corpo

    contatos = ler_contatos(contatos_path)
    arquivos = localizar_arquivos(pasta_arquivos, report_key)

    copia_validos, copia_invalidos = _processar_copia(copia_manual)
    avisos: list[str] = []
    for invalido in copia_invalidos:
        avisos.append(
            f"E-mail de cópia inválido ignorado: {invalido}"
        )

    por_chave: dict[str, list[ArquivoINS]] = {}
    for arquivo in arquivos:
        por_chave.setdefault(arquivo.chave, []).append(arquivo)

    grupos: list[GrupoEnvio] = []
    for chave in sorted(por_chave):
        candidatos = sorted(
            por_chave[chave],
            key=lambda arquivo: (
                arquivo.caminho.stat().st_mtime,
                arquivo.caminho.name.lower(),
            ),
            reverse=True,
        )
        escolhido = candidatos[0]
        for ignorado in candidatos[1:]:
            avisos.append(
                "Arquivo duplicado ignorado para "
                f"'{escolhido.nome_transportador}': {ignorado.caminho} "
                f"(mantido: {escolhido.caminho.name})"
            )

        contato = contatos.get(chave)
        if contato is None:
            status = "sem_contato"
            para: tuple[str, ...] = ()
            invalidos: tuple[str, ...] = ()
            detalhe = (
                "Transportadora não encontrada na planilha de contatos."
            )
        elif contato.emails:
            status = "pronto"
            para = contato.emails
            invalidos = contato.emails_invalidos
            detalhe = ""
            if invalidos:
                detalhe = (
                    "E-mails inválidos ignorados: " + ", ".join(invalidos)
                )
        elif contato.emails_invalidos:
            status = "email_invalido"
            para = ()
            invalidos = contato.emails_invalidos
            detalhe = (
                "Nenhum e-mail válido no cadastro: " + ", ".join(invalidos)
            )
        else:
            status = "sem_email"
            para = ()
            invalidos = ()
            detalhe = "A transportadora está cadastrada, mas sem e-mail."

        nome = escolhido.nome_transportador
        grupos.append(
            GrupoEnvio(
                chave=chave,
                nome=nome,
                arquivo=escolhido.caminho,
                para=para,
                copia=copia_validos,
                assunto=renderizar_template(assunto_template, nome),
                corpo=renderizar_template(corpo_template, nome),
                status=status,
                detalhe=detalhe,
                emails_invalidos=invalidos,
            )
        )

    plano = PlanoEnvios(report_key=report_key, grupos=grupos, avisos=avisos)
    if not grupos:
        plano.avisos.append(
            f"Nenhum arquivo '{PREFIXOS[report_key]}*.xlsx' foi encontrado "
            "na pasta selecionada."
        )
    return plano


# ---------------------------------------------------------------------------
# Envio
# ---------------------------------------------------------------------------
@dataclass
class EnvioResultado:
    """Resultado de uma rodada de envios."""

    enviados: list[GrupoEnvio] = field(default_factory=list)
    falhos: list[GrupoEnvio] = field(default_factory=list)
    nao_encontrados: list[GrupoEnvio] = field(default_factory=list)
    ignorados: list[GrupoEnvio] = field(default_factory=list)
    cancelado: bool = False
    duracao_segundos: float = 0.0

    @property
    def total(self) -> int:
        """Quantidade de grupos considerados na rodada."""
        return (
            len(self.enviados)
            + len(self.falhos)
            + len(self.nao_encontrados)
            + len(self.ignorados)
        )


SenderFactory = Callable[[], object]


def enviar_plano(
    plano: PlanoEnvios,
    chaves: Sequence[str] | Iterable[str],
    sender_factory: SenderFactory | None = None,
    on_progress: Callable[[int, int, str], None] | None = None,
    on_log: Callable[[str, str], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> EnvioResultado:
    """Envia os grupos selecionados, um e-mail por transportadora.

    Falhas individuais não interrompem os demais envios. Grupos sem e-mail
    válido entram em ``nao_encontrados`` e nunca acionam o Outlook.
    """
    iniciado = time.monotonic()
    resultado = EnvioResultado()
    selecionadas = {normalizar_chave(chave) for chave in chaves}
    selecionados = [
        grupo for grupo in plano.grupos if grupo.chave in selecionadas
    ]
    prontos = [grupo for grupo in selecionados if grupo.pronto]
    total = len(prontos)

    for grupo in selecionados:
        if not grupo.pronto:
            resultado.nao_encontrados.append(grupo)
            _log(
                on_log,
                f"NÃO ENCONTRADO: {grupo.nome} — {grupo.rotulo_status}"
                + (f" ({grupo.detalhe})" if grupo.detalhe else ""),
                "warning",
            )

    if not prontos:
        resultado.duracao_segundos = time.monotonic() - iniciado
        _log(
            on_log,
            "Nenhum grupo pronto para envio. Nada foi disparado.",
            "warning",
        )
        return resultado

    fabrica = sender_factory or OutlookSender
    try:
        sender = fabrica()
    except Exception as erro:  # noqa: BLE001 - falha ao abrir o Outlook
        mensagem = _mensagem_sender(erro)
        for grupo in prontos:
            resultado.falhos.append(grupo)
            _log(on_log, f"FALHA: {grupo.nome} — {mensagem}", "error")
        resultado.duracao_segundos = time.monotonic() - iniciado
        return resultado

    try:
        for indice, grupo in enumerate(prontos, start=1):
            if should_cancel is not None and should_cancel():
                resultado.cancelado = True
                resultado.ignorados.extend(prontos[indice - 1 :])
                _log(
                    on_log,
                    "Envio cancelado pelo usuário. Os e-mails restantes "
                    "não foram disparados.",
                    "warning",
                )
                break

            try:
                sender.enviar(grupo)
            except Exception as erro:  # noqa: BLE001 - continua os demais
                resultado.falhos.append(grupo)
                _log(
                    on_log,
                    f"FALHA: {grupo.nome} — {_mensagem_sender(erro)}",
                    "error",
                )
            else:
                resultado.enviados.append(grupo)
                _log(
                    on_log,
                    f"ENVIADO: {grupo.nome} — {', '.join(grupo.para)}",
                    "success",
                )

            if on_progress is not None:
                on_progress(indice, total, grupo.nome)
    finally:
        try:
            sender.fechar()
        except Exception:  # noqa: BLE001 - encerramento best-effort
            pass

    resultado.duracao_segundos = time.monotonic() - iniciado
    return resultado


class OutlookSender:
    """Remetente real: cria e dispara cada e-mail pelo Outlook Desktop."""

    def __init__(self) -> None:
        try:
            import pythoncom  # type: ignore[import-not-found]
            import win32com.client  # type: ignore[import-not-found]
        except Exception as erro:  # noqa: BLE001 - dependência opcional
            raise EnvioError(
                "O Outlook Desktop não está disponível neste computador.\n\n"
                "Instale o Microsoft Outlook e o pacote pywin32 para enviar "
                f"os e-mails.\n\nDetalhe técnico: {erro}"
            ) from erro

        self._pythoncom = pythoncom
        self._win32 = win32com.client
        self._inicializado = False
        try:
            pythoncom.CoInitialize()
            self._inicializado = True
            self._outlook = win32com.client.Dispatch("outlook.application")
        except Exception as erro:  # noqa: BLE001
            if self._inicializado:
                try:
                    pythoncom.CoUninitialize()
                except Exception:  # noqa: BLE001
                    pass
            raise EnvioError(
                "Não foi possível abrir o Outlook Desktop.\n\n"
                "Verifique se o Outlook está instalado, aberto e com o perfil "
                f"de e-mail configurado.\n\nDetalhe técnico: {erro}"
            ) from erro

    def enviar(self, grupo: GrupoEnvio) -> None:
        """Cria o e-mail do grupo, anexa o arquivo e o envia imediatamente."""
        if not grupo.arquivo.is_file():
            raise EnvioError(
                f"O arquivo anexo não existe mais:\n{grupo.arquivo}"
            )
        item = self._outlook.CreateItem(0)
        item.To = "; ".join(grupo.para)
        if grupo.copia:
            item.CC = "; ".join(grupo.copia)
        item.Subject = grupo.assunto
        item.HTMLBody = grupo.corpo
        item.Attachments.Add(str(grupo.arquivo))
        item.Send()

    def fechar(self) -> None:
        """Encerra o COM do thread atual."""
        if not self._inicializado:
            return
        try:
            self._pythoncom.CoUninitialize()
        finally:
            self._inicializado = False


# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------
def _unir_unicos(
    existentes: Iterable[str], novos: Iterable[str]
) -> tuple[str, ...]:
    vistos = {item.lower() for item in existentes}
    resultado = list(existentes)
    for item in novos:
        if item.lower() in vistos:
            continue
        vistos.add(item.lower())
        resultado.append(item)
    return tuple(resultado)


def _processar_copia(
    copia_manual: Iterable[str] | None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if not copia_manual:
        return (), ()
    textos = list(copia_manual)
    emails = dividir_emails(";".join(textos))
    validos: list[str] = []
    invalidos: list[str] = []
    vistos: set[str] = set()
    for email in emails:
        chave = email.lower()
        if chave in vistos:
            continue
        vistos.add(chave)
        if validar_email(email):
            validos.append(email)
        else:
            invalidos.append(email)
    return tuple(validos), tuple(invalidos)


def _log(
    callback: Callable[[str, str], None] | None, mensagem: str, nivel: str
) -> None:
    if callback is not None:
        callback(mensagem, nivel)


def _mensagem_sender(erro: BaseException) -> str:
    if isinstance(erro, EnvioError):
        return str(erro)
    return f"Erro inesperado: {erro}"
