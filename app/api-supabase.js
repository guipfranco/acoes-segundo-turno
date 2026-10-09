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
    };
  }
  const deOrg = o => ({ id: o.id, nome: o.nome, tipo: o.tipo, verificada: !!o.verificada,
    foto: o.foto_url ? { url: o.foto_url, credito: o.foto_credito || '', pagina: o.foto_pagina || null } : null });
  const deTurno = r => ({ id: r.id, acao: r.acao, inicio: semSeg(r.inicio), fim: semSeg(r.fim), lotacao: r.lotacao == null ? null : r.lotacao, vao: r.vao || 0 });
  const dePessoa = p => ({ id: p.id, nome: p.nome, email: p.email || null, telefone: p.telefone || null, papel: p.papel, bloqueada: !!p.bloqueada, organizacao: p.organizacao == null ? null : p.organizacao });
  // ação de quem organiza (ou da fila): turnos com a lista de quem vai
  const comInscritos = m => ({ acao: Object.assign(deAcao(m.acao), { detalhe: m.acao.detalhe || null, contatoLink: m.acao.contato_link || null,
      organizacaoLink: m.acao.organizacao_link || null, organizacaoDados: m.acao.organizacao_dados || null }),
    turnos: (m.turnos || []).map(t => Object.assign(deTurno(t), { inscritos: t.inscritos || [], desistiram: t.desistiram || [] })) });
  // publico.json: lista pública gerada pelo workflow do Pages (scripts/snapshot_publico.py) de hora em hora, para
  // quem só olha o site não gastar a saída do Supabase. Vale por 3 h; na prévia por branch não existe (404).
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
  function montarPublico(cfgLinhas, orgs, acoes, turnos) {
    const hoje = hojeBrasilia();
    const config = { hoje, frase: '', vaquinha: '#' };
    for (const c of cfgLinhas) config[c.chave] = c.valor;
    return { config, organizacoes: orgs.map(deOrg), acoes: acoes.map(deAcao),
      turnos: turnos.filter(t => String(t.inicio).slice(0, 16) >= hoje + 'T00:00').map(deTurno) };
  }
  function erroDe(e) { const x = new Error(e.message || 'erro'); x.codigo = (e.message || '').trim(); x.original = e; return x; }

  function criar(cfg) {
    const sb = window.supabase.createClient(cfg.url, cfg.anonKey, { auth: { flowType: 'pkce', detectSessionInUrl: true, persistSession: true } });
    async function uid() { const { data } = await sb.auth.getSession(); return data.session ? data.session.user.id : null; }
    async function rpc(nome, args) { const { data, error } = await sb.rpc(nome, args || {}); if (error) throw erroDe(error); return data; }
    const api = {
      modo: 'supabase',
      origemPublico: null, // 'snapshot' | 'supabase', para depuração
      async sessao() {
        const id = await uid(); if (!id) return null;
        const { data, error } = await sb.from('pessoa').select('id,nome,email,telefone,papel,bloqueada,organizacao').eq('id', id).maybeSingle();
        if (error) throw erroDe(error); return data ? dePessoa(data) : null;
      },
      async entrar() {
        const volta = location.origin + location.pathname + location.hash;
        const { error } = await sb.auth.signInWithOAuth({ provider: 'google', options: { redirectTo: volta } });
        if (error) throw erroDe(error);
      },
      async sair() { await sb.auth.signOut(); },
      async publico() {
        const snap = await lerSnapshot();
        if (snap) { api.origemPublico = 'snapshot'; return montarPublico(snap.configuracao, snap.organizacoes, snap.acoes, snap.turnos); }
        const [cfgR, orgR, acR, tR] = await Promise.all([
          sb.from('configuracao_publica').select('chave,valor'),
          sb.from('organizacao_publica').select('id,nome,tipo,verificada,foto_url,foto_credito,foto_pagina'),
          sb.from('acao_publica').select('*'),
          sb.from('turno_publico').select('*').gte('inicio', hojeBrasilia() + 'T00:00:00'),
        ]);
        for (const r of [cfgR, orgR, acR, tR]) if (r.error) throw erroDe(r.error);
        api.origemPublico = 'supabase';
        return montarPublico(cfgR.data, orgR.data, acR.data, tR.data);
      },
      async acao(id) {
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
      async inscrever(turnoId) { return rpc('inscrever', { turno_id: turnoId }); },
      async desistir(turnoId) { await rpc('desistir', { turno_id: turnoId }); },
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
      async criarAcao(dados) { return rpc('criar_acao', { dados }); },
      async minhasAcoes() { return (await rpc('minhas_acoes')).map(comInscritos); },
      async encerrarAcao(id) { await rpc('encerrar_acao', { acao_id: id }); },
      async fila(situacao) { return (await rpc('fila_moderacao', { situacao: situacao || 'em análise' })).map(m => Object.assign(comInscritos(m), { organizador: m.organizador })); },
      async aprovar(id) { await rpc('aprovar_acao', { acao_id: id }); },
      async recusar(id, motivo) { await rpc('recusar_acao', { acao_id: id, motivo }); },
      async suspender(id, motivo) { await rpc('suspender_acao', { acao_id: id, motivo: motivo || null }); },
      async reativar(id) { await rpc('reativar_acao', { acao_id: id }); },
      async excluir(id) { await rpc('excluir_acao', { acao_id: id }); },
      // bloquear tira do ar as publicadas da pessoa; desbloquear só desmarca (o moderador reativa uma a uma)
      async bloquear(pessoaId, motivo) { await rpc('bloquear_pessoa', { pessoa_id: pessoaId, motivo: motivo || null }); },
      async desbloquear(pessoaId) { await rpc('desbloquear_pessoa', { pessoa_id: pessoaId }); },
      async minhasInscricoes() { return (await rpc('minhas_inscricoes')).map(m => ({ acao: deAcao(m.acao), turno: deTurno(m.turno), desistiu: !!m.desistiu })); },
    };
    return api;
  }
  return { criar, deAcao, deTurno, dePessoa, deOrg, hojeBrasilia };
});
