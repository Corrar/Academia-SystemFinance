"""PIX copia e cola e QR Code no padrão BR Code do Banco Central (EMV QRCPS, PIX estático com valor).

O código é montado com a chave PIX da academia e o valor de cada aluno, então o aluno só
abre o app do banco, cola (ou lê o QR) e confirma. Não precisa de conta em nenhum serviço.
"""
import io
import re
import unicodedata

import segno

import ajustes


def _campo(identificador: str, valor: str) -> str:
    return f"{identificador}{len(valor):02d}{valor}"


def crc16(dados: str) -> str:
    """CRC-16/CCITT-FALSE (polinômio 0x1021, início 0xFFFF), exigido no campo 63 do BR Code."""
    crc = 0xFFFF
    for byte in dados.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return f"{crc:04X}"


def _texto(valor: str, limite: int) -> str:
    """Sem acentos, em maiúsculas e só com caracteres aceitos pelos bancos."""
    sem_acento = unicodedata.normalize("NFD", valor or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9 .\-]", "", sem_acento.upper()).strip()[:limite]


def _cpf_valido(d: str) -> bool:
    if len(d) != 11 or d == d[0] * 11:
        return False
    for n in (9, 10):
        soma = sum(int(d[i]) * (n + 1 - i) for i in range(n))
        if (soma * 10 % 11) % 10 != int(d[n]):
            return False
    return True


def normalizar_chave(chave: str) -> str:
    """Deixa a chave no formato do PIX: e-mail, chave aleatória, CPF/CNPJ só dígitos ou +55 no celular."""
    chave = (chave or "").strip()
    if not chave:
        return ""
    if "@" in chave:
        return chave.lower()
    if re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", chave):
        return chave.lower()
    digitos = re.sub(r"\D", "", chave)
    parece_telefone = chave.startswith("+") or "(" in chave or re.search(r"\d{4,5}-\d{4}$", chave)
    if len(digitos) == 14 and not chave.startswith("+"):
        return digitos  # CNPJ
    if len(digitos) == 11 and not parece_telefone and _cpf_valido(digitos):
        return digitos  # CPF
    if digitos.startswith("55") and len(digitos) in (12, 13):
        return "+" + digitos
    if len(digitos) in (10, 11):
        return "+55" + digitos
    return chave


def cidade() -> str:
    """Cidade do recebedor: a do campo próprio, senão a do foro, senão BRASIL."""
    escolhida = ajustes.obter("pix_cidade") or ajustes.obter("cidade_foro").split("/")[0]
    return _texto(escolhida, 15) or "BRASIL"


def codigo(valor: float | None = None, descricao: str = "", chave: str | None = None) -> str:
    """PIX copia e cola. Vazio se a academia ainda não cadastrou a chave PIX."""
    chave = normalizar_chave(ajustes.obter("chave_pix") if chave is None else chave)
    if not chave:
        return ""
    conta = _campo("00", "br.gov.bcb.pix") + _campo("01", chave)
    descricao = _texto(descricao, max(0, 99 - len(conta) - 4))
    if descricao:
        conta += _campo("02", descricao)
    partes = [
        _campo("00", "01"),
        _campo("26", conta),
        _campo("52", "0000"),
        _campo("53", "986"),
    ]
    if valor and valor > 0:
        partes.append(_campo("54", f"{valor:.2f}"))
    partes += [
        _campo("58", "BR"),
        _campo("59", _texto(ajustes.obter("academia_nome"), 25) or "ACADEMIA"),
        _campo("60", cidade()),
        _campo("62", _campo("05", "***")),
    ]
    sem_crc = "".join(partes) + "6304"
    return sem_crc + crc16(sem_crc)


def qr_svg(payload: str, escala: int = 5) -> str:
    """QR Code em SVG (inline na página, sem depender de nenhum serviço externo)."""
    return segno.make(payload, error="m").svg_inline(scale=escala, border=2, dark="#0a0a0a", light="#ffffff")


def qr_png(payload: str, escala: int = 8) -> bytes:
    saida = io.BytesIO()
    segno.make(payload, error="m").save(saida, kind="png", scale=escala, border=2)
    return saida.getvalue()
