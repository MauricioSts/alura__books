import time

import cv2
import pytest
from fastapi.testclient import TestClient

from wheres_the_duck.api import criar_app
from wheres_the_duck.config import ArmazemConfig, Config
from wheres_the_duck.motor import Motor
from wheres_the_duck.registro import Registro
from tests.conftest import Cena, padrao


def esperar(condicao, limite=20.0):
    fim = time.monotonic() + limite
    while time.monotonic() < fim:
        if condicao():
            return True
        time.sleep(0.02)
    return False


def montar_pasta(cena: Cena, pasta, roteiro):
    pasta.mkdir()
    for i, itens in enumerate(roteiro):
        cv2.imwrite(str(pasta / f"{i:03d}.png"), cena.tela(*itens).imagem)


def test_simulacao_roda_a_maquina_sobre_uma_pasta(tmp_path):
    cena = Cena(tmp_path / "templates")
    montar_pasta(cena, tmp_path / "prints", [
        ["jogar"], [], ["pular_onibus"], [], ["resgatar", "gizmo"], [],
        ["fim_partida", "retornar_lobby"], ["jogar"],
    ])
    mensagens = []
    registro = Registro()
    motor = Motor(tmp_path, ArmazemConfig(tmp_path / "config.json"), registro, mensagens.append)
    motor.iniciar("simulacao", str(tmp_path / "prints"), repetir=12)
    assert esperar(lambda: not motor.rodando)
    sessao = motor.historico.listar()[0]
    assert sessao["modo"] == "simulacao" and sessao["motivo"] == "fim da simulação"
    assert sessao["partidas"] == 2 and sessao["tesouros"] == 1 and sessao["por_tipo"] == {"gizmo": 1}
    textos = " ".join(l["msg"] for l in registro.linhas())
    assert "Salto:" in textos and "Clique em Retornar ao lobby" in textos
    assert any(m["tipo"] == "recompensa" for m in mensagens)
    assert motor.estado()["fase"] == "parado"


def test_simulacao_exige_pasta_com_imagens(tmp_path):
    motor = Motor(tmp_path, ArmazemConfig(tmp_path / "config.json"), Registro())
    (tmp_path / "vazia").mkdir()
    with pytest.raises(ValueError):
        motor.iniciar("simulacao", str(tmp_path / "vazia"))
    with pytest.raises(FileNotFoundError):
        motor.iniciar("simulacao", str(tmp_path / "nao_existe"))


def test_config_corrompido_volta_ao_padrao(tmp_path):
    (tmp_path / "config.json").write_text("{ quebrado", encoding="utf-8")
    assert ArmazemConfig(tmp_path / "config.json").atual == Config()


@pytest.fixture
def cliente(tmp_path):
    with TestClient(criar_app(tmp_path)) as c:
        c.base = tmp_path
        yield c


def test_config_ida_e_volta_e_validacao(cliente):
    cfg = cliente.get("/api/config").json()
    assert cfg["automacao"]["apos_acesso_pirata"] == "parar"
    cfg["automacao"]["tempo_max_partida_min"] = 25
    cfg["salto"]["angulo_graus"] = 80
    assert cliente.put("/api/config", json=cfg).status_code == 200
    assert cliente.get("/api/config").json()["salto"]["angulo_graus"] == 80
    cfg["deteccao"]["limiar"] = 5
    assert cliente.put("/api/config", json=cfg).status_code == 422


def test_so_aceita_requisicoes_locais(cliente):
    assert cliente.get("/api/estado", headers={"host": "malicioso.example"}).status_code == 403
    assert cliente.post("/api/parar", headers={"origin": "https://malicioso.example"}).status_code == 403
    assert cliente.post("/api/parar", headers={"origin": "http://127.0.0.1:8765"}).status_code == 200


def test_templates_upload_listagem_e_remocao(cliente):
    lista = cliente.get("/api/templates").json()
    assert len([t for t in lista if t["grupo"] == "principal"]) == 12
    assert not any(t["configurado"] for t in lista)
    png = cv2.imencode(".png", padrao("jogar"))[1].tobytes()
    lista = cliente.put("/api/templates/jogar", content=png).json()
    assert next(t for t in lista if t["nome"] == "jogar")["configurado"]
    assert cliente.get("/api/templates/jogar/imagem").content[:4] == b"\x89PNG"
    assert cliente.put("/api/templates/../../segredo", content=png).status_code in (404, 405)
    assert cliente.put("/api/templates/inventado", content=png).status_code == 404
    assert cliente.put("/api/templates/jogar", content=b"lixo").status_code == 400
    lista = cliente.delete("/api/templates/jogar").json()
    assert not next(t for t in lista if t["nome"] == "jogar")["configurado"]


def test_simulacao_pela_api_com_websocket(cliente):
    cena = Cena(cliente.base / "templates")
    montar_pasta(cena, cliente.base / "prints", [["jogar"], ["resgatar", "acesso_pirata"], [], []])
    with cliente.websocket_connect("/ws") as ws:
        assert ws.receive_json()["estado"]["fase"] == "parado"
        r = cliente.post("/api/iniciar", json={"modo": "simulacao", "pasta": str(cliente.base / "prints"), "repetir": 3})
        assert r.status_code == 200
        tipos = set()
        for _ in range(500):
            msg = ws.receive_json()
            tipos.add(msg["tipo"])
            # Para só no estado final da sessão (com o motivo da parada já gravado).
            if (msg["tipo"] == "estado" and not msg["estado"]["rodando"]
                    and msg["estado"]["ultimo_motivo"] and "recompensa" in tipos):
                break
        assert {"estado", "log", "recompensa"} <= tipos
    assert esperar(lambda: not cliente.app.state.motor.rodando)
    dados = cliente.get("/api/historico").json()
    item = dados["recompensas"][0]
    assert item["tipo"] == "acesso_pirata" and item["depois"]
    assert dados["sessoes"][0]["motivo"].startswith("Acesso à Loja Pirata")
    assert cliente.get(f"/api/capturas/{item['antes']}").status_code == 200
    assert cliente.get("/api/capturas/..%2Fconfig.json").status_code == 404
    assert cliente.get("/api/estado").json()["estado"]["alerta_pirata"]["id"] == item["id"]
    cliente.post("/api/alerta/confirmar")
    assert cliente.get("/api/estado").json()["estado"]["alerta_pirata"] is None


def test_iniciar_com_pedido_invalido_devolve_erro(cliente):
    assert cliente.post("/api/iniciar", json={"modo": "simulacao"}).status_code == 400
    assert cliente.post("/api/iniciar", json={"modo": "inventado"}).status_code == 400
