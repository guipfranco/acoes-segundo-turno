// Miolo Supabase da camada de dados. Mesmo contrato de api-exemplo.js.
// Lê as views públicas pela REST e chama as funções SQL para tudo que exige sessão.
(function (raiz, fabrica) {
  if (typeof module !== 'undefined' && module.exports) module.exports = fabrica();
  else raiz.ApiSupabase = fabrica();
})(typeof window !== 'undefined' ? window : this, function () {
  const semSeg = s => (s ? String(s).slice(0, 16) : s);
  function hojeBrasilia() {
    return new Intl.DateTimeFormat('sv-SE', { timeZone: 'America/Sao_Paulo', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());
  }
  // "AAAA-MM-DDTHH:MM" em Brasília: o app esconde o turno que já terminou (compara com turno.fim, no mesmo formato)
  function emBrasilia(d) {
    const s = new Intl.DateTimeFormat('sv-SE', { timeZone: 'America/Sao_Paulo', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(d);
    return s.slice(0, 10) + 'T' + s.slice(11, 16);
  }
  const agoraBrasilia = () => emBrasilia(new Date());
  function deAcao(r) {
    return {
      id: r.id, titulo: r.titulo, tipo: r.tipo, descricao: r.descricao || '', organizador: r.organizador,
      organizadorNome: r.organizador_nome || '', organizacao: r.organizacao == null ? null : r.organizacao,
      lugar: r.online ? { nome: 'Online', bairro: 'Online', cidade: 'Online', lat: null, lon: null, online: true }
        : { nome: r.lugar_nome, bairro: r.bairro, cidade: r.cidade, lat: r.lat, lon: r.lon, online: false, aproximado: !!r.lugar_aproximado },
      foto: r.foto_url ? { url: r.foto_url, mini: r.foto_mini_url || null, credito: r.foto_credito || '', pagina: r.foto_pagina || null } : null,
      prioritaria: !!r.prioritaria, status: r.status, contatoTipo: r.contato_tipo || 'organizador_chama',
      criadaEm: r.criada_em ? String(r.criada_em).slice(0, 10) : null,
      fonte: r.fonte || null, linkDivulgacao: r.link_divulgacao || null, motivoRecusa: r.motivo_recusa || null,
      ultimoInicio: semSeg(r.ultimo_inicio) || null,
      // importada que a moderação ainda não conferiu: o app mostra a etiqueta "Divulgação pública"
      // (sem a coluna, como num snapshot de antes da migração 20261010000010, a importada conta como não conferida)
      divulgacaoPublica: !!r.fonte && !r.verificada,
    };
  }
  const deOrg = o => ({ id: o.id, nome: o.nome, tipo: o.tipo, verificada: !!o.verificada,
    foto: o.foto_url ? { url: o.foto_url, credito: o.foto_credito || '', pagina: o.foto_pagina || null } : null });
  const deTurno = r => ({ id: r.id, acao: r.acao, inicio: semSeg(r.inicio), fim: semSeg(r.fim), lotacao: r.lotacao == null ? null : r.lotacao, vao: r.vao || 0, horaAproximada: !!r.hora_aproximada });
  const deFeedback = f => ({ id: f.id, texto: f.texto, contato: f.contato || null, tela: f.tela || null, acao: f.acao == null ? null : f.acao, acaoTitulo: f.acao_titulo || null,
    navegador: f.navegador || null, criadoEm: f.criado_em ? emBrasilia(new Date(f.criado_em)) : null, tratadoEm: f.tratado_em ? emBrasilia(new Date(f.tratado_em)) : null,
    pessoa: f.pessoa ? { nome: f.pessoa.nome, email: f.pessoa.email || null, telefone: f.pessoa.telefone || null } : null });
  const dePessoa = p => ({ id: p.id, nome: p.nome, email: p.email || null, telefone: p.telefone || null, papel: p.papel, bloqueada: !!p.bloqueada, organizacao: p.organizacao == null ? null : p.organizacao });
  // ação de quem organiza (ou da fila): turnos com a lista de quem vai
  const comInscritos = m => ({ acao: Object.assign(deAcao(m.acao), { detalhe: m.acao.detalhe || null, contatoLink: m.acao.contato_link || null,
      organizacaoLink: m.acao.organizacao_link || null, organizacaoDados: m.acao.organizacao_dados || null }),
    turnos: (m.turnos || []).map(t => Object.assign(deTurno(t), { inscritos: t.inscritos || [], desistiram: t.desistiram || [] })) });
  // publico.json: lista pública gerada pelo workflow do Pages (scripts/snapshot_publico.py) de hora em hora, para
  // quem só olha o site não gastar a saída do Supabase. Vale por 3 h; na prévia por branch não existe (404).
  // Quem está logado, ou já escreveu algo nesta página (cadastrou, marcou "Eu vou", moderou), lê direto do Supabase:
  // precisa ver na hora o que acabou de mudar, e o snapshot pode levar até 1 h para refletir.
  const SNAPSHOT_VALIDADE_MS = 3 * 60 * 60 * 1000;
  async function lerSnapshot() {
    try {
      const r = await fetch('publico.json', { cache: 'no-cache' });
      if (!r.ok) return null;
      const s = await r.json();
      const idade = Date.now() - Date.parse(s && s.geradoEm);
      if (!(idade < SNAPSHOT_VALIDADE_MS)) return null; // NaN (sem geradoEm) também cai aqui
      if (![s.configuracao, s.organizacoes, s.acoes, s.turnos].every(Array.isArray)) return null;
      return s;
    } catch (e) { return null; }
  }
  // A API devolve no máximo max_rows linhas (1000, o padrão do Supabase) por resposta, sem avisar. Pede página a
  // página pelo Range e para na primeira página curta. (Se max_rows baixar de 1000 em produção, PAGINA tem que baixar junto.)
  const PAGINA = 1000;
  async function tudo(consulta) {
    const linhas = [];
    for (let inicio = 0; ; inicio += PAGINA) {
      const { data, error } = await consulta().range(inicio, inicio + PAGINA - 1);
      if (error) throw erroDe(error);
      linhas.push(...(data || []));
      if (!data || data.length < PAGINA) return linhas;
    }
  }
  function montarPublico(cfgLinhas, orgs, acoes, turnos) {
    const hoje = hojeBrasilia();
    const config = { hoje, agora: agoraBrasilia(), frase: '', vaquinha: '#' };
    for (const c of cfgLinhas) config[c.chave] = c.valor;
    return { config, organizacoes: orgs.map(deOrg), acoes: acoes.map(deAcao),
      turnos: turnos.filter(t => String(t.inicio).slice(0, 16) >= hoje + 'T00:00').map(deTurno) };
  }
  async function sha256Hex(texto) {
    const h = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(texto));
    return Array.from(new Uint8Array(h), b => b.toString(16).padStart(2, '0')).join('');
  }
  // Script do "Fazer login com o Google" (Google Identity Services), baixado só quando alguém clica em Entrar.
  // Não leva integrity: o Google atualiza o arquivo no mesmo endereço.
  let googlePromessa = null;
  function carregarGoogle() {
    if (window.google && window.google.accounts && window.google.accounts.id) return Promise.resolve(window.google);
    if (!googlePromessa) {
      googlePromessa = new Promise((resolve, reject) => {
        const s = document.createElement('script');
        s.src = 'https://accounts.google.com/gsi/client'; s.async = true;
        const tempo = setTimeout(() => reject(new Error('demorou')), 8000);
        s.onload = () => { clearTimeout(tempo); window.google && window.google.accounts ? resolve(window.google) : reject(new Error('sem google.accounts')); };
        s.onerror = () => { clearTimeout(tempo); reject(new Error('falhou')); };
        document.head.appendChild(s);
      }).catch(e => { googlePromessa = null; throw e; });
    }
    return googlePromessa;
  }
  function erroDe(e) { const x = new Error(e.message || 'erro'); x.codigo = (e.message || '').trim(); x.original = e; return x; }

  function criar(cfg) {
    const sb = window.supabase.createClient(cfg.url, cfg.anonKey, { auth: { flowType: 'pkce', detectSessionInUrl: true, persistSession: true } });
    async function uid() { const { data } = await sb.auth.getSession(); return data.session ? data.session.user.id : null; }
    async function rpc(nome, args) { const { data, error } = await sb.rpc(nome, args || {}); if (error) throw erroDe(error); return data; }
    let escreveu = false; // esta página já gravou algo: a vitrine passa a vir do Supabase, não do snapshot
    // a mesma página pede o arquivo uma vez por minuto (inicial + ação abertas em seguida), não a cada tela
    const SNAPSHOT_MEMORIA_MS = 60 * 1000;
    let snapshotEmMemoria = null; // { lidoEm, promessa }
    function snapshot() {
      if (!snapshotEmMemoria || Date.now() - snapshotEmMemoria.lidoEm > SNAPSHOT_MEMORIA_MS) {
        snapshotEmMemoria = { lidoEm: Date.now(), promessa: lerSnapshot() };
      }
      return snapshotEmMemoria.promessa;
    }
    // Janela com o botão "Fazer login com o Google". O Google devolve um id_token assinado com o nonce (em sha256) e o
    // Supabase confere o token e o nonce cru. Resolve true ao entrar e false se a pessoa fechar a janela.
    async function entrarPeloBotao(google) {
      const nonce = Array.from(crypto.getRandomValues(new Uint8Array(16)), b => b.toString(16).padStart(2, '0')).join('');
      const nonceSha = await sha256Hex(nonce);
      return new Promise((resolve, reject) => {
        const caixa = document.createElement('dialog');
        caixa.className = 'login-google';
        caixa.innerHTML = '<h2>Entrar</h2><p>Use sua conta Google para dizer "Eu vou!" e cadastrar ações.</p>'
          + '<div class="login-google-botao"></div><p class="login-google-erro" hidden></p>'
          + '<button type="button" class="login-google-fechar">Agora não</button>';
        const erro = caixa.querySelector('.login-google-erro');
        let feito = false;
        const fechar = ok => { if (feito) return; feito = true; caixa.close(); caixa.remove(); resolve(ok); };
        caixa.querySelector('.login-google-fechar').onclick = () => fechar(false);
        caixa.addEventListener('cancel', e => { e.preventDefault(); fechar(false); });
        caixa.addEventListener('click', e => { if (e.target === caixa) fechar(false); });
        google.accounts.id.initialize({
          client_id: cfg.googleClientId, nonce: nonceSha, ux_mode: 'popup', itp_support: true,
          callback: async r => {
            const { error } = await sb.auth.signInWithIdToken({ provider: 'google', token: r.credential, nonce });
            if (error) { console.error(error); erro.textContent = 'Não deu para entrar. Tente de novo.'; erro.hidden = false; return; }
            fechar(true);
          },
        });
        document.body.appendChild(caixa);
        const largura = Math.min(320, Math.max(200, (document.documentElement.clientWidth || 360) - 80));
        google.accounts.id.renderButton(caixa.querySelector('.login-google-botao'),
          { theme: 'filled_black', size: 'large', shape: 'pill', text: 'continue_with', locale: 'pt-BR', width: largura });
        try { caixa.showModal(); } catch (e) { reject(e); }
      });
    }
    const api = {
      modo: 'supabase',
      origemPublico: null, // 'snapshot' | 'supabase', para depuração
      async sessao() {
        const id = await uid(); if (!id) return null;
        const { data, error } = await sb.from('pessoa').select('id,nome,email,telefone,papel,bloqueada,organizacao').eq('id', id).maybeSingle();
        if (error) throw erroDe(error); return data ? dePessoa(data) : null;
      },
      async entrar() {
        // Com googleClientId, entra pelo botão do próprio Google (janela sobre o site): a pessoa vê o nome do app e o
        // endereço do site, não o do Supabase. Se o script do Google não carregar, cai no redirecionamento antigo.
        if (cfg.googleClientId) {
          let google = null;
          try { google = await carregarGoogle(); } catch (e) { console.warn('script do Google não carregou; usando o redirecionamento', e); }
          if (google) return entrarPeloBotao(google);
        }
        const volta = location.origin + location.pathname + location.hash;
        const { error } = await sb.auth.signInWithOAuth({ provider: 'google', options: { redirectTo: volta } });
        if (error) throw erroDe(error);
      },
      async sair() { await sb.auth.signOut(); },
      async publico() {
        const snap = (escreveu || await uid()) ? null : await snapshot();
        if (snap) { api.origemPublico = 'snapshot'; return montarPublico(snap.configuracao, snap.organizacoes, snap.acoes, snap.turnos); }
        const [cfg, orgs, acoes, turnos] = await Promise.all([
          tudo(() => sb.from('configuracao_publica').select('chave,valor').order('chave')),
          tudo(() => sb.from('organizacao_publica').select('id,nome,tipo,verificada,foto_url,foto_credito,foto_pagina').order('id')),
          tudo(() => sb.from('acao_publica').select('*').order('id')),
          tudo(() => sb.from('turno_publico').select('*').gte('inicio', hojeBrasilia() + 'T00:00:00').order('id')),
        ]);
        api.origemPublico = 'supabase';
        return montarPublico(cfg, orgs, acoes, turnos);
      },
      async acao(id) {
        // Quem só olha (sem sessão, sem ter escrito nada) lê a ação do snapshot: é o link que circula no WhatsApp,
        // não precisa bater no banco. Ação fora do arquivo (aprovada há menos de 1 h, cancelada) segue ao vivo.
        const snap = (escreveu || await uid()) ? null : await snapshot();
        if (snap) {
          const linha = snap.acoes.find(a => a.id === id);
          if (linha) {
            const turnos = snap.turnos.filter(t => t.acao === id).sort((x, y) => String(x.inicio).localeCompare(String(y.inicio)));
            return { acao: deAcao(linha), turnos: turnos.map(deTurno), inscrita: [], combinado: null };
          }
        }
        const [aR, tR, mim] = await Promise.all([
          sb.from('acao_publica').select('*').eq('id', id).maybeSingle(),
          sb.from('turno_publico').select('*').eq('acao', id).order('inicio'),
          rpc('acao_para_mim', { acao_id: id }),
        ]);
        if (aR.error) throw erroDe(aR.error); if (tR.error) throw erroDe(tR.error);
        const extra = { inscrita: (mim && mim.inscrita) || [], combinado: (mim && mim.combinado) || null };
        if (aR.data) return Object.assign({ acao: deAcao(aR.data), turnos: tR.data.map(deTurno) }, extra);
        // fora do ar (em análise, suspensa, recusada): só quem criou ou modera vê; cancelada abre para todos
        let r = null;
        try { r = await rpc('acao_restrita', { acao_id: id }); } catch (e) { if (await uid()) throw e; console.warn('acao_restrita sem sessão falhou; a página mostra "não encontrada"', e); }
        if (!r) return null;
        return Object.assign({ acao: Object.assign(deAcao(r.acao), { detalhe: r.acao.detalhe || null, contatoLink: r.acao.contato_link || null }),
          turnos: (r.turnos || []).map(deTurno) }, extra);
      },
      async salvarTelefone(telefone) { return dePessoa(await rpc('salvar_telefone', { telefone })); },
      async inscrever(turnoId) { escreveu = true; return rpc('inscrever', { turno_id: turnoId }); },
      async desistir(turnoId) { escreveu = true; await rpc('desistir', { turno_id: turnoId }); },
      // imagem da ação: cada pessoa envia só para a própria pasta do bucket fotos-acoes
      async enviarFoto(blob) {
        const id = await uid(); if (!id) throw erroDe({ message: 'precisa_entrar' });
        const nome = `${id}/${Date.now()}-${Math.random().toString(36).slice(2, 8)}.jpg`;
        const { error } = await sb.storage.from('fotos-acoes').upload(nome, blob, { contentType: blob.type || 'image/jpeg', cacheControl: '604800' });
        if (error) throw erroDe({ message: 'falha_envio' });
        return sb.storage.from('fotos-acoes').getPublicUrl(nome).data.publicUrl;
      },
      async fotoDoInstagram(link) {
        const { data, error } = await sb.functions.invoke('previa-instagram', { body: { link } });
        if (error) { let c = 'falha_envio'; try { c = (await error.context.json()).erro || c; } catch (e) { /* sem corpo */ } throw erroDe({ message: c }); }
        return data.url;
      },
      // organização de quem usa o app (Perfil) e a moderação delas
      async minhaOrganizacao() {
        const r = await rpc('minha_organizacao'); if (!r) return { organizacao: null, pedido: null };
        const o = r.organizacao;
        return { organizacao: o ? { id: o.id, nome: o.nome, tipo: o.tipo, verificada: !!o.verificada, foto: o.foto_url ? { url: o.foto_url } : null, link: o.link_oficial || null, minha: !!o.minha } : null,
          pedido: r.pedido || null };
      },
      async salvarOrganizacao(nome, tipo, logo, link) { return rpc('salvar_organizacao', { nome, tipo, logo: logo || null, link: link || null }); },
      async sairDaOrganizacao() { await rpc('sair_da_organizacao'); },
      async filaOrganizacoes() {
        const r = await rpc('fila_organizacoes');
        return { pedidos: r.pedidos || [], semSelo: (r.sem_selo || []).map(o => Object.assign({}, o, { foto: o.foto_url ? { url: o.foto_url } : null })) };
      },
      async decidirPedido(id, aprovar, motivo) { await rpc('decidir_pedido_organizacao', { pedido_id: id, aprovar, motivo: motivo || null }); },
      async darSelo(id) { await rpc('dar_selo_organizacao', { organizacao_id: id }); },
      async criarAcao(dados) { escreveu = true; return rpc('criar_acao', { dados }); },
      async minhasAcoes() { return (await rpc('minhas_acoes')).map(comInscritos); },
      async encerrarAcao(id) { escreveu = true; await rpc('encerrar_acao', { acao_id: id }); },
      async fila(situacao) { return (await rpc('fila_moderacao', { situacao: situacao || 'em análise' })).map(m => Object.assign(comInscritos(m), { organizador: m.organizador, duvida: m.duvida || null })); },
      async aprovar(id) { escreveu = true; await rpc('aprovar_acao', { acao_id: id }); },
      async recusar(id, motivo) { escreveu = true; await rpc('recusar_acao', { acao_id: id, motivo }); },
      async verificar(id) { escreveu = true; await rpc('verificar_acao', { acao_id: id }); },
      async desverificar(id) { escreveu = true; await rpc('desverificar_acao', { acao_id: id }); },
      async suspender(id, motivo) { escreveu = true; await rpc('suspender_acao', { acao_id: id, motivo: motivo || null }); },
      async reativar(id) { escreveu = true; await rpc('reativar_acao', { acao_id: id }); },
      async excluir(id) { escreveu = true; await rpc('excluir_acao', { acao_id: id }); },
      // bloquear tira do ar as publicadas da pessoa; desbloquear só desmarca (o moderador reativa uma a uma)
      async bloquear(pessoaId, motivo) { escreveu = true; await rpc('bloquear_pessoa', { pessoa_id: pessoaId, motivo: motivo || null }); },
      async desbloquear(pessoaId) { escreveu = true; await rpc('desbloquear_pessoa', { pessoa_id: pessoaId }); },
      async minhasInscricoes() { return (await rpc('minhas_inscricoes')).map(m => ({ acao: deAcao(m.acao), turno: deTurno(m.turno), desistiu: !!m.desistiu })); },
      // feedback: qualquer pessoa manda (logada ou não); só moderador lê e marca como tratado
      async enviarFeedback(d) { return rpc('enviar_feedback', { texto: d.texto, contato: d.contato || null, tela: d.tela || null, acao_id: d.acaoId == null ? null : d.acaoId, navegador: d.navegador || null }); },
      async feedbacks(pendentes = true) { return (await rpc('feedbacks', { pendentes })).map(deFeedback); },
      async tratarFeedback(id, tratado = true) { await rpc('tratar_feedback', { feedback_id: id, tratado }); },
    };
    return api;
  }
  return { criar, deAcao, deTurno, dePessoa, deOrg, deFeedback, hojeBrasilia, agoraBrasilia };
});
