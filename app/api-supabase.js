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
      foto: r.foto_url ? { url: r.foto_url, credito: r.foto_credito || '', pagina: r.foto_pagina || null } : null,
      prioritaria: !!r.prioritaria, status: r.status, contatoTipo: r.contato_tipo || 'organizador_chama',
      criadaEm: r.criada_em ? String(r.criada_em).slice(0, 10) : null,
      fonte: r.fonte || null, linkDivulgacao: r.link_divulgacao || null,
    };
  }
  const deTurno = r => ({ id: r.id, acao: r.acao, inicio: semSeg(r.inicio), fim: semSeg(r.fim), lotacao: r.lotacao == null ? null : r.lotacao, vao: r.vao || 0 });
  const dePessoa = p => ({ id: p.id, nome: p.nome, email: p.email || null, telefone: p.telefone || null, papel: p.papel, bloqueada: !!p.bloqueada });
  function erroDe(e) { const x = new Error(e.message || 'erro'); x.codigo = (e.message || '').trim(); x.original = e; return x; }

  function criar(cfg) {
    const sb = window.supabase.createClient(cfg.url, cfg.anonKey, { auth: { flowType: 'pkce', detectSessionInUrl: true, persistSession: true } });
    async function uid() { const { data } = await sb.auth.getSession(); return data.session ? data.session.user.id : null; }
    async function rpc(nome, args) { const { data, error } = await sb.rpc(nome, args || {}); if (error) throw erroDe(error); return data; }
    return {
      modo: 'supabase',
      async sessao() {
        const id = await uid(); if (!id) return null;
        const { data, error } = await sb.from('pessoa').select('id,nome,email,telefone,papel,bloqueada').eq('id', id).maybeSingle();
        if (error) throw erroDe(error); return data ? dePessoa(data) : null;
      },
      async entrar() {
        const volta = location.origin + location.pathname + location.hash;
        const { error } = await sb.auth.signInWithOAuth({ provider: 'google', options: { redirectTo: volta } });
        if (error) throw erroDe(error);
      },
      async sair() { await sb.auth.signOut(); },
      async publico() {
        const [cfgR, orgR, acR, tR] = await Promise.all([
          sb.from('configuracao_publica').select('chave,valor'),
          sb.from('organizacao_publica').select('id,nome,tipo,verificada'),
          sb.from('acao_publica').select('*'),
          sb.from('turno_publico').select('*').gte('inicio', hojeBrasilia() + 'T00:00:00'),
        ]);
        for (const r of [cfgR, orgR, acR, tR]) if (r.error) throw erroDe(r.error);
        const config = { hoje: hojeBrasilia(), frase: '', vaquinha: '#' };
        for (const c of cfgR.data) config[c.chave] = c.valor;
        return { config, organizacoes: orgR.data, acoes: acR.data.map(deAcao), turnos: tR.data.map(deTurno) };
      },
      async acao(id) {
        const [aR, tR, mim] = await Promise.all([
          sb.from('acao_publica').select('*').eq('id', id).maybeSingle(),
          sb.from('turno_publico').select('*').eq('acao', id).order('inicio'),
          rpc('acao_para_mim', { acao_id: id }),
        ]);
        if (aR.error) throw erroDe(aR.error); if (tR.error) throw erroDe(tR.error);
        if (!aR.data) return null;
        return { acao: deAcao(aR.data), turnos: tR.data.map(deTurno), inscrita: (mim && mim.inscrita) || [], combinado: (mim && mim.combinado) || null };
      },
      async salvarTelefone(telefone) { return dePessoa(await rpc('salvar_telefone', { telefone })); },
      async inscrever(turnoId) { return rpc('inscrever', { turno_id: turnoId }); },
      async desistir(turnoId) { await rpc('desistir', { turno_id: turnoId }); },
      async minhasInscricoes() { return (await rpc('minhas_inscricoes')).map(m => ({ acao: deAcao(m.acao), turno: deTurno(m.turno) })); },
    };
  }
  return { criar, deAcao, deTurno, dePessoa, hojeBrasilia };
});
