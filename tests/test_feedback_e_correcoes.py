"""Correções do primeiro uso real (WhatsApp, 2026-10-09) e o "Fale com a gente"."""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
HTML = (RAIZ / "app" / "index.html").read_text(encoding="utf-8")
PRIVACIDADE = (RAIZ / "app" / "privacidade.html").read_text(encoding="utf-8")


def dados():
    corpo = (RAIZ / "app" / "dados.js").read_text(encoding="utf-8").split("=", 1)[1].strip().rstrip(";")
    return json.loads(corpo)


def test_turno_que_ja_terminou_sai_das_listas_e_da_pagina():
    # as listas, a página da ação, o "Eu vou!" e a agenda comparam o fim do turno com "agora", não só a data;
    # turno aproximado (sem hora na divulgação) vale até o fim do dia
    assert "const turnoVale=t=>t.horaAproximada?t.fim.slice(0,10)>=agora().slice(0,10):t.fim>agora()" in HTML
    assert "function turnosFuturos(id){return turnosDa(id).filter(turnoVale)}" in HTML
    assert "futuros=ts.filter(turnoVale)" in HTML
    assert "function botaoAgenda(a,t){if(!turnoVale(t))return '';" in HTML
    assert "if(!turnoVale(t))return `<button class=\"btn\" disabled>horário encerrado</button>" in HTML
    assert "t.inicio.slice(0,10)<PUB.config.hoje" not in HTML
    # no site a hora é ao vivo (aba aberta por horas continua certa); no exemplo é a fixa dos dados
    assert "ApiSupabase.agoraBrasilia()" in HTML and "API.modo==='exemplo'?(PUB.config.agora" in HTML
    d = dados()
    assert d["config"]["agora"].startswith(d["config"]["hoje"] + "T")
    # no exemplo tem uma ação de hoje que já terminou, para a prévia mostrar o caso
    assert any(t["inicio"].startswith(d["config"]["hoje"]) and t["fim"] < d["config"]["agora"] for t in d["turnos"])


def test_horario_aproximado_mostra_o_periodo_e_avisa():
    assert "function periodo(t)" in HTML and "'à noite'" in HTML and "'horário a confirmar'" in HTML
    assert "function quandoTurno(t){if(!t.horaAproximada)return fmtData(t.inicio)" in HTML
    assert "quandoTurno(x.t)" in HTML and "quandoCurto(x.t)" in HTML
    assert "A divulgação não informou o horário exato" in HTML
    assert any(t.get("horaAproximada") for t in dados()["turnos"])


def test_online_e_lista_compacta_por_horario_e_nao_trilho_de_cartazes():
    assert "function blocoOnline(lista)" in HTML and "function cardOnline(x)" in HTML
    assert 'class="evento-online"' in HTML and 'class="foto mini' in HTML
    assert "blocoVitrine('Online, de qualquer lugar'" not in HTML
    assert ".lista-online:not(.aberto) .evento-online:nth-child(n+5){display:none}" in HTML


def test_cadastro_nao_recarrega_a_tela_ao_mudar_horario_ou_vagas():
    assert 'onchange="estado.criar.quando.ini=this.value;avisoDiaSeguinte()"' in HTML
    assert 'onchange="estado.criar.quando.fim=this.value;avisoDiaSeguinte()"' in HTML
    assert 'onchange="estado.criar.quando.limitar=this.checked;document.getElementById(\'vagas-box\').hidden=!this.checked"' in HTML
    assert 'id="vagas-box"' in HTML and 'id="dia-seguinte"' in HTML
    assert "quando.ini=this.value;render()" not in HTML and "quando.limitar=this.checked;render()" not in HTML
    # redesenho no lugar (filtros, caixas do cadastro) mantém a rolagem
    assert "function rerender(){manterRolagem=true;return render()}" in HTML
    assert "window.scrollTo(0,manter?y:0)" in HTML
    assert "onchange=\"estado.criar.online=this.checked;rerender()\"" in HTML
    assert "onclick=\"F().${campo}='${k}';rerender()\"" in HTML


def test_fale_com_a_gente_em_toda_parte():
    assert "function telaContato(arg)" in HTML and "async function enviarContato(acaoId)" in HTML
    assert "rota==='contato'?telaContato(arg)" in HTML
    assert 'href="#/contato"' in HTML  # inicial e Perfil
    assert 'href="#/contato/${a.id}"' in HTML  # página da ação, já sobre aquela ação
    assert "API.enviarFeedback({texto" in HTML and "contar('feedback-enviar')" in HTML
    assert "Você não precisa entrar para mandar a mensagem." in HTML
    assert "sem_texto:" in HTML and "muitas_mensagens:" in HTML
    # só o sistema e o navegador, sem identificar o aparelho; Chrome e Firefox no iPhone não viram "Safari"
    assert "function navegador()" in HTML and "navigator.userAgent" in HTML
    assert "/CriOS/.test(u)?'Chrome':/FxiOS/.test(u)?'Firefox'" in HTML and "navigator.maxTouchPoints" in HTML
    # a moderação vê também o telefone de quem mandou logado, e os textos dizem isso
    assert "a mensagem vai com seu nome, e-mail e telefone." in HTML


def test_moderacao_le_as_mensagens_na_fila():
    assert "estado.filaAba='msgs'" in HTML and "function filaMensagensHtml()" in HTML
    assert "API.feedbacks(!estado.msgsTratadas)" in HTML and "API.tratarFeedback(id,tratado)" in HTML
    assert "Marcar como tratada" in HTML and "Reabrir" in HTML
    fs = dados()["feedbacks"]
    assert any(f["pessoa"] is None for f in fs) and any(f["tratadoEm"] for f in fs)


def test_privacidade_fala_das_mensagens():
    assert "Fale com a gente" in PRIVACIDADE and "Só a moderação lê" in PRIVACIDADE
