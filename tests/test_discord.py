"""Aviso no Discord: só com webhook válido, uma vez por recompensa, nunca derruba o motor."""
import json
from types import SimpleNamespace

from wheres_the_duck.config import Config
from wheres_the_duck.notificacoes import NotificadorDiscord, montar_mensagem, url_valida
from wheres_the_duck.registro import Registro

URL = "https://discord.com/api/webhooks/123456/abc_DEF-ghi"


def notificador(tmp_path, **discord):
    cfg = Config()
    for k, v in discord.items():
        setattr(cfg.discord, k, v)
    enviados = []

    def enviar(url, corpo, tipo):
        enviados.append((url, corpo, tipo))
        return 204

    n = NotificadorDiscord(lambda: cfg, tmp_path, Registro(), enviar, em_segundo_plano=False)
    return n, enviados


def item(tipo="gizmo", ident="1", antes="p.png"):
    return {"id": ident, "tipo": tipo, "data": "12/11/2026", "hora": "10:00:00", "partida": 3, "antes": antes}


def test_url_valida():
    assert url_valida(URL) and url_valida("https://discordapp.com/api/webhooks/1/x")
    assert not url_valida("https://exemplo.com/api/webhooks/1/x")
    assert not url_valida("http://discord.com/api/webhooks/1/x")
    assert not url_valida("")


def test_desligado_por_padrao_nao_envia(tmp_path):
    n, enviados = notificador(tmp_path, webhook_url=URL)
    n.recompensa(item())
    assert enviados == []


def test_envia_uma_vez_por_recompensa_com_print(tmp_path):
    (tmp_path / "p.png").write_bytes(b"\x89PNGdados")
    n, enviados = notificador(tmp_path, ativo=True, webhook_url=URL)
    n.recompensa(item())
    n.recompensa(dict(item(), depois="d.png"))  # o mesmo item, com o print de depois
    assert len(enviados) == 1
    url, corpo, tipo = enviados[0]
    assert url == URL and tipo.startswith("multipart/form-data") and b"\x89PNGdados" in corpo
    assert "Gizmo" in corpo.decode("utf-8", "ignore")


def test_filtros(tmp_path):
    n, enviados = notificador(tmp_path, ativo=True, webhook_url=URL, filtro="so_pirata")
    n.recompensa(item("gizmo", "1"))
    n.recompensa(item("acesso_pirata", "2"))
    assert len(enviados) == 1
    n, enviados = notificador(tmp_path, ativo=True, webhook_url=URL, filtro="sem_gizmo")
    n.recompensa(item("gizmo", "1"))
    n.recompensa(item("faixa", "2"))
    assert len(enviados) == 1


def test_mencao_so_no_token():
    pirata = montar_mensagem(item("acesso_pirata"), "@everyone")
    assert pirata["content"].startswith("@everyone") and "15/12/2026" in pirata["content"]
    assert pirata["allowed_mentions"]["parse"]
    comum = montar_mensagem(item("faixa"), "@everyone")
    assert "@everyone" not in comum["content"] and comum["allowed_mentions"]["parse"] == []


def test_erro_de_rede_nao_derruba(tmp_path):
    cfg = Config()
    cfg.discord.ativo, cfg.discord.webhook_url = True, URL

    def falha(*_):
        raise OSError("sem rede")

    reg = Registro()
    n = NotificadorDiscord(lambda: cfg, tmp_path, reg, falha, em_segundo_plano=False)
    n.recompensa(item())
    assert any("Discord" in l["msg"] for l in reg.linhas())
    ok, _ = n.testar()
    assert not ok


def test_teste_rejeita_url_invalida(tmp_path):
    n, enviados = notificador(tmp_path)
    ok, msg = n.testar("https://outro-site.com/x")
    assert not ok and enviados == []
    ok, _ = n.testar(URL)
    assert ok and json.loads(enviados[0][1].split(b"\r\n\r\n", 1)[1].split(b"\r\n")[0])["content"]
