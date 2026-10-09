from pathlib import Path
import re

RAIZ = Path(__file__).resolve().parents[1]
HTML = (RAIZ / "app" / "index.html").read_text(encoding="utf-8")


def test_tem_as_seis_telas():
    for nome in ["telaInicio", "telaMapa", "telaAcao", "telaCriar", "telaMinhas", "telaFila"]:
        assert f"function {nome}" in HTML, nome


def test_nav_e_doar():
    assert 'id="app"' in HTML
    assert "<nav" in HTML
    assert "Doar" in HTML
import json

DADOS_JS = (RAIZ / "app" / "dados.js").read_text(encoding="utf-8") if (RAIZ / "app" / "dados.js").exists() else ""


def carregar_dados():
    # dados.js é "window.DADOS = {...};" com JSON puro dentro
    corpo = DADOS_JS.split("=", 1)[1].strip().rstrip(";")
    return json.loads(corpo)


def test_dados_tem_pelo_menos_12_acoes_e_todas_com_turno():
    d = carregar_dados()
    assert len(d["acoes"]) >= 12
    acoes_com_turno = {t["acao"] for t in d["turnos"]}
    for a in d["acoes"]:
        assert a["id"] in acoes_com_turno, a["titulo"]


def test_dados_cobrem_os_tipos_e_os_status():
    d = carregar_dados()
    tipos = {a["tipo"] for a in d["acoes"]}
    assert tipos >= {"panfletagem", "adesivaço", "roda de conversa", "ligatona", "porta a porta", "bandeiraço"}
    status = {a["status"] for a in d["acoes"]}
    assert status >= {"publicada", "em análise", "recusada", "encerrada"}


def test_dados_sem_telefone_real():
    for p in carregar_dados()["pessoas"]:
        assert re.fullmatch(r"\(11\) 9x{4}-x{4}", p["telefone"]), p


def test_dados_tem_verificada_e_nao_verificada_e_eu_sou_organizador():
    d = carregar_dados()
    assert {o["verificada"] for o in d["organizacoes"]} == {True, False}
    eu = next(p for p in d["pessoas"] if p["id"] == d["config"]["eu"])
    assert eu["papel"] == "organizador"


def test_inicio_tem_filtros_abas_e_helpers():
    for s in ["function fmtData", "function turnosFuturos", "function vaoNa", "function distanciaKm",
              "data-${campo}=\"${k}\"", "'fds'", "id=\"gaveta\"",
              "Ainda não tem ação", "Área prioritária", "leaflet"]:
        assert s in HTML, s


def test_acao_com_turno_passado_fica_fora_da_lista():
    d = carregar_dados()
    hoje = d["config"]["hoje"]
    futuros = {t["acao"] for t in d["turnos"] if t["inicio"][:10] >= hoje}
    a10 = next(a for a in d["acoes"] if a["id"] == 10)
    assert a10["status"] == "publicada" and 10 not in futuros
    assert "turnosNoFiltro(a.id)[0]" in HTML  # a lista só entra com turno futuro que caiba no filtro de data


def test_tela_acao_regras_de_inscricao():
    for s in ["function telaAcao", "function inscrever", "function desistir", "lotado", "horário encerrado",
              "Esta ação já aconteceu", "Inscrito", "Seu nome e telefone vão para quem organiza esta ação",
              "Confirmar", "Entrar no grupo do WhatsApp", "minimapa"]:
        assert s in HTML, s


def test_detalhe_e_grupo_so_para_inscritos():
    # o bloco "Combinado" só é montado quando a API devolve o combinado, e a API só devolve a quem se inscreveu
    i = HTML.index("Combinado")
    assert "ab.combinado?" in HTML[i-400:i]
    assert "combinado: podeVer(a) ?" in (RAIZ / "app" / "api-exemplo.js").read_text(encoding="utf-8")


def test_turno_lotado_e_inscricao_duplicada_nos_dados_e_no_codigo():
    d = carregar_dados()
    t5 = next(t for t in d["turnos"] if t["id"] == 5)
    n5 = len([i for i in d["inscricoes"] if i["turno"] == 5 and not i["canceladaEm"]])
    assert t5["lotacao"] == n5 == 2
    assert any(i["turno"] == 7 and i["pessoa"] == d["config"]["eu"] for i in d["inscricoes"])
    assert "if (!(ja && !ja.canceladaEm))" in (RAIZ / "app" / "api-exemplo.js").read_text(encoding="utf-8")  # não duplica
    assert "n>=t.lotacao" in HTML


def test_criar_tem_tres_passos_modelos_e_validacao():
    for s in ["function telaCriar", "function publicarAcao", "const MODELOS", "function buscarLugares",
              "Continuar", "Publicar", "sua ação está em análise", "publica na hora", "passa pela fila",
              "Detalhe do encontro, só para inscritos", "Link do grupo de WhatsApp"]:
        assert s in HTML, s


def test_status_nasce_publicada_so_com_organizacao_verificada():
    assert "o&&o.verificada?'publicada':'em análise'" in HTML


def test_validacao_dos_campos_obrigatorios():
    for s in ["Dê um título.", "Diga o nome do ponto de encontro.", "Marque o lugar no mapa.", "Informe pelo menos um turno.",
              "Telefone no formato", "t.fim<=t.inicio"]:
        assert s in HTML, s


def test_minhas_e_fila():
    for s in ["function telaMinhas", "function telaFila", "Copiar números", "Mandar aviso", "Marcar presença",
              "Encerrar", "Editar", "Aprovar", "Recusar", "Dar selo à organização", "Despublicar",
              "Bloquear organizador", "Recuse se:", "já criou"]:
        assert s in HTML, s


def test_recusa_exige_motivo_e_bloqueio_despublica_tudo():
    assert "Escreva o motivo" in HTML
    assert "bloqueada=true" in HTML.replace(" ", "")


def test_fluxo_de_status_nos_dados_e_no_codigo():
    d = carregar_dados()
    a12 = next(a for a in d["acoes"] if a["id"] == 12)
    assert a12["status"] == "em análise" and a12["organizacao"] in (None, 4)
    assert ".status='publicada'" in HTML  # aprovar
    assert "a.status='recusada'" in HTML  # recusar


def test_turno_passado_do_organizador_tem_inscritos_para_marcar_presenca():
    d = carregar_dados()
    hoje = d["config"]["hoje"]
    meus_passados = {t["id"] for t in d["turnos"] if t["inicio"][:10] < hoje
                     and next(a for a in d["acoes"] if a["id"] == t["acao"])["organizador"] == d["config"]["eu"]}
    assert any(i["turno"] in meus_passados for i in d["inscricoes"])


def test_textos_singular_e_bairro_igual_a_cidade():
    assert "function quantosVao" in HTML and "1 vai" in HTML
    assert "function lugarCurto" in HTML


def test_inscritos_no_singular():
    assert "function quantosInscritos" in HTML and "1 inscrito'" in HTML


# Achados da revisão final
def test_editar_preserva_turnos_e_inscritos():
    assert "function atualizarTurnos" in HTML
    assert "DADOS.turnos=DADOS.turnos.filter(t=>t.acao!==a.id)" not in HTML


def test_acao_fora_de_publicada_nao_aceita_inscricao():
    assert "não está aberta a inscrições" in HTML
    assert "a.status!=='publicada'" in HTML


def test_voltar_na_edicao_nao_perde_texto_e_nav_reseta_criacao():
    assert 'onclick="novaCriacao()"' in HTML
    assert "if(!c.editando){c.titulo=MODELOS[t].titulo" in HTML


def test_turno_no_passado_e_recusado_ao_criar():
    assert "Turno no passado." in HTML


def test_turno_encerrado_vence_inscrito():
    i = HTML.index("function botaoTurno")
    corpo = HTML[i:i + 800]
    assert corpo.index("horário encerrado") < corpo.index("Inscrito")


def test_marcadores_sem_imagem_externa():
    assert "L.divIcon" in HTML


# Redesenho (Airbnb/Meetup): busca por lugar, lista acompanha o mapa, fundo da RMSP no artifact
LUGARES_JS = (RAIZ / "app" / "lugares.js").read_text(encoding="utf-8")


def test_lugares_tem_municipios_do_brasil_e_distritos_da_capital():
    corpo = LUGARES_JS.split("LUGARES_BR =", 1)[1].strip().rstrip(";")
    lugares = json.loads(corpo)
    assert len(lugares) >= 5570 + 96
    ufs = {l[1] for l in lugares}
    assert {"SP", "RS", "AM", "BA", "DF"} <= ufs
    assert any(l[0] == "Grajaú" and l[4] == "d" for l in lugares)
    assert any(l[0] == "Porto Alegre" and l[4] == "c" for l in lugares)


def test_busca_por_lugar_e_lista_pela_area_do_mapa():
    for s in ["function buscarLugares", "function irParaLugar", "getBounds()", "function acoesNaArea",
              "nesta área", "moveend", 'id="busca-lugar"', "lugares.js"]:
        assert s in HTML, s


def test_fundo_da_rmsp_com_fallback_para_tiles():
    for s in ["function fundoBase", "/_blob/", "pmtiles", "protomaps-leaflet", "tile.openstreetmap.org"]:
        assert s in HTML, s


def test_pino_mostra_dia_e_hora():
    assert "function etiquetaPino" in HTML


def test_criar_marca_o_lugar_no_mapa():
    for s in ["draggable:!!arrastavel", "Nome do ponto de encontro", "Cidade ou bairro"]:
        assert s in HTML, s


# Inicial sem mapa (Airbnb/Meetup): busca por cidade, vitrine por cidade com foto, filtro de data claro, ações online
WORKFLOW = (RAIZ / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")


def test_inicial_sem_mapa_com_busca_e_vitrine():
    i = HTML.index("function telaInicio"); corpo = HTML[i:HTML.index("function irParaCidade")]
    assert 'id="mapa"' not in corpo
    for s in ["Em que cidade você está?", "Perto de você", "Chutamos a cidade", "Online, de qualquer lugar", "Ver no mapa",
              "blocoVitrine", "Criar a primeira ação"]:
        assert s in corpo, s
    assert "function chutarCidade" in HTML and "getCurrentPosition" in HTML


def test_vitrine_tem_cidades_exemplo_pelo_brasil_e_foto_por_acao():
    for c in ["Recife", "Belo Horizonte", "Porto Alegre", "Salvador", "São Paulo"]:
        assert c in HTML[HTML.index("const VITRINE"):HTML.index("const PADRAO")], c
    assert "function fotoEvento" in HTML and 'class="foto f-${' in HTML


def test_dados_tem_acoes_em_pelo_menos_quatro_cidades_e_online():
    d = carregar_dados()
    pub = [a for a in d["acoes"] if a["status"] == "publicada"]
    cidades = {a["lugar"]["cidade"] for a in pub if not a["lugar"].get("online")}
    assert {"Recife", "Belo Horizonte", "Porto Alegre", "Salvador", "São Paulo"} <= cidades
    online = [a for a in pub if a["lugar"].get("online")]
    assert len(online) >= 2
    for a in online:
        assert a["lugar"]["lat"] is None and a["lugar"]["lon"] is None and not a["prioritaria"]


def test_organizacoes_de_exemplo_sao_ficticias():
    nomes = {o["nome"] for o in carregar_dados()["organizacoes"]}
    for real in ["Mandato Barba", "Mandato Alfredinho", "PT Diadema", "MTST Grajaú"]:
        assert real not in nomes, real


def test_filtro_de_data_claro_com_proximos_primeiro_e_intervalo():
    for k in ["'breve'", "'hoje'", "'amanha'", "'semana'", "'fds'", "'proxima'", "'datas'"]:
        assert k in HTML[HTML.index("const QUANDO"):HTML.index("const FORMATOS")], k
    for s in ["Escolher datas", 'type="date"', "function intervaloQuando", "function turnosNoFiltro",
              "p.t.inicio.localeCompare(q.t.inicio)"]:
        assert s in HTML, s


def test_formato_presencial_ou_online_em_toda_a_cadeia():
    for s in ["const FORMATOS", "'presencial'", "'online'", "const ehOnline", "acoesOnline", "LUGAR_ONLINE",
              "Ação online (ligatona", "O link da chamada vai para quem se inscreve", "if(!c.online){"]:
        assert s in HTML, s
    assert "!ehOnline(ab.acao)" in HTML  # ação online não monta minimapa
    assert "if(l.online)return 'Online'" in HTML


def test_mapa_virou_rota_propria():
    assert 'href="#/mapa"' in HTML and "rota==='mapa'?telaMapa()" in HTML and "function montarMapa" in HTML
    assert "location.hash='#/mapa'" in HTML  # escolher cidade na inicial leva ao mapa


def test_workflow_do_pages_publica_so_a_pasta_mockup():
    assert "actions/upload-pages-artifact" in WORKFLOW and "actions/deploy-pages" in WORKFLOW
    assert "path: app" in WORKFLOW


# Fotos de verdade nos cards (Wikimedia Commons, licença livre), com o ícone de reserva
def test_acoes_de_exemplo_tem_foto_livre_com_credito():
    d = carregar_dados()
    com_foto = [a for a in d["acoes"] if a.get("foto")]
    assert len(com_foto) >= 18
    for a in com_foto:
        assert a["foto"]["url"].startswith("https://commons.wikimedia.org/wiki/Special:Redirect/file/"), a["titulo"]
        assert "via Wikimedia Commons" in a["foto"]["credito"]


def test_foto_tem_reserva_e_credito_e_campo_no_criar():
    for s in ["const imgFoto", 'onerror="this.remove()"', "function creditoFoto", "const cuboAcao",
              "Foto da ação (link, opcional)", "foto:c.foto.trim()", 'class="foto capa']:
        assert s in HTML, s


def test_mapa_ignora_acao_presencial_sem_coordenada():
    # ação importada sem cidade reconhecida tem lat/lon null e não pode quebrar o mapa
    assert "const temPino=" in HTML
    assert "function acoesNaArea(){const todas=acoesVisiveis().filter(x=>temPino(x.a))" in HTML


def test_telas_de_participante_leem_pela_api():
    for s in ['src="api.js"', 'src="api-exemplo.js"', 'src="config.js"', "async function render", "await API.acao(",
              "API.publico()", "const vaoNo=", "estado.acaoAberta", "data-so-exemplo"]:
        assert s in HTML, s
    inicio = HTML[HTML.index("function acoesVisiveis"):HTML.index("function telaCriar")]
    assert "DADOS.acoes" not in inicio and "DADOS.inscricoes" not in inicio and "DADOS.config" not in inicio


def test_publicar_recarrega_antes_de_ir_para_minhas_sem_render_duplo():
    # um render a mais apagaria o aviso de Minhas (telaMinhas zera estado.aviso)
    corpo = HTML[HTML.index("function publicarAcao"):HTML.index("// ---------- minhas")]
    assert "sincronizar();location.hash" not in corpo
    assert corpo.count("recarregar().then(()=>{location.hash='#/minhas'})") == 2


def test_vou_pede_telefone_uma_vez_e_mostra_a_forma_de_contato():
    acao = HTML[HTML.index("function telaAcao"):HTML.index("function montarMiniMapa")]
    assert "Receber código" not in HTML and "Código que chegou" not in HTML
    for s in ["Seu nome e telefone vão para quem organiza esta ação", "vai entrar em contato", "Chamar no WhatsApp",
              "Entrar no grupo do WhatsApp", "wa.me/55", "organizador_chama", "'whatsapp'", "link_grupo"]:
        assert s in acao, s
    assert "function continuarVouPendente" in HTML and "vouPendente" in HTML
    assert ">Inscreva-se<" in HTML and "Inscrito ✓" in HTML and ">Vou<" not in HTML
