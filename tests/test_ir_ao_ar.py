import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("ir_ao_ar", Path(__file__).resolve().parents[1] / "scripts" / "ir_ao_ar.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_chave_prefere_anon_legada():
    chaves = [{"name": "service_role", "api_key": "eyS"},
              {"name": "default", "type": "publishable", "api_key": "sb_publishable_x"},
              {"name": "anon", "api_key": "eyA"}]
    assert m.chave_publica(chaves) == "eyA"


def test_chave_cai_na_publishable_e_nunca_na_secreta():
    chaves = [{"type": "secret", "api_key": "sb_secret_x"}, {"type": "publishable", "api_key": "sb_publishable_x"}]
    assert m.chave_publica(chaves) == "sb_publishable_x"
    with pytest.raises(m.Falha):
        m.chave_publica([{"name": "service_role", "api_key": "eyS"}, {"type": "secret", "api_key": "sb_secret_x"}])


def test_config_js_tem_url_e_chave():
    t = m.texto_config("https://abc.supabase.co", "eyA")
    assert "window.CONFIG = { supabase: { url: 'https://abc.supabase.co', anonKey: 'eyA' } };" in t


def test_corpo_auth():
    c = m.corpo_auth("", "")
    assert c["external_email_enabled"] is False and "external_google_enabled" not in c
    assert c["site_url"] == "https://guipfranco.github.io/acoes-segundo-turno/"
    assert "http://localhost:8000/**" in c["uri_allow_list"]
    assert m.corpo_auth("id", "seg")["external_google_enabled"] is True


def test_semear_recusa_telefone_estranho():
    assert "(11) 91234-5678" in m.sql_semear("(11) 91234-5678")
    with pytest.raises(m.Falha):
        m.sql_semear("1'; drop table pessoa; --")


def test_sem_token_falha_com_mensagem(monkeypatch, capsys):
    monkeypatch.delenv("SUPABASE_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("SUPABASE_DB_PASSWORD", "x")
    assert m.main(["criar"]) == 1
    assert "SUPABASE_ACCESS_TOKEN" in capsys.readouterr().err


def test_env_le_e_grava_sem_sobrescrever_o_ambiente(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "ARQ_ENV", tmp_path / ".env")
    monkeypatch.delenv("X_TESTE", raising=False)
    monkeypatch.setenv("Y_TESTE", "ambiente")
    (tmp_path / ".env").write_text("# comentário\nX_TESTE='abc'\nY_TESTE=arquivo\n", encoding="utf-8")
    m.ler_env()
    import os
    assert os.environ["X_TESTE"] == "abc" and os.environ["Y_TESTE"] == "ambiente"
    m.gravar_env("X_TESTE", "novo")
    assert os.environ["X_TESTE"] == "novo"
    assert (tmp_path / ".env").read_text(encoding="utf-8") == "# comentário\nY_TESTE=arquivo\nX_TESTE=novo\n"
