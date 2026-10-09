// Miolo de exemplo da camada de dados: opera sobre window.DADOS em memória.
// Mesmo contrato de api-supabase.js. Serve para desenvolver e para o protótipo seguir navegável.
(function (raiz, fabrica) {
  if (typeof module !== 'undefined' && module.exports) module.exports = fabrica();
  else raiz.ApiExemplo = fabrica();
})(typeof window !== 'undefined' ? window : this, function () {
  function erro(codigo) { const e = new Error(codigo); e.codigo = codigo; return e; }
  function formatarTelefone(t) {
    const d = String(t || '').replace(/[^\dx]/gi, '');
    if (!/^\d{2}9[\dx]{8}$/i.test(d)) throw erro('telefone_invalido');
    return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
  }
  function criar(dados) {
    let sessao = dados.config.eu;
    const pessoa = id => dados.pessoas.find(p => p.id === id);
    const org = id => dados.organizacoes.find(o => o.id === id);
    const ativas = tid => dados.inscricoes.filter(i => i.turno === tid && !i.canceladaEm);
    const publica = a => ({
      id: a.id, titulo: a.titulo, tipo: a.tipo, descricao: a.descricao, organizador: a.organizador,
      organizadorNome: (pessoa(a.organizador) || { nome: '' }).nome, organizacao: a.organizacao,
      lugar: Object.assign({}, a.lugar), foto: a.foto ? Object.assign({}, a.foto) : null,
      prioritaria: !!a.prioritaria, status: a.status, contatoTipo: a.contatoTipo || 'organizador_chama', criadaEm: a.criadaEm,
    });
    const turno = t => ({ id: t.id, acao: t.acao, inicio: t.inicio, fim: t.fim, lotacao: t.lotacao || null, vao: ativas(t.id).length });
    const turnosDa = aid => dados.turnos.filter(t => t.acao === aid).sort((a, b) => a.inicio.localeCompare(b.inicio)).map(turno);
    const combinadoDe = a => ({ detalhe: a.detalhe || null, contato: { tipo: a.contatoTipo || 'organizador_chama', whatsapp: a.contatoWhatsapp || null, link: a.contatoLink || null } });
    const inscritaEm = aid => dados.turnos.filter(t => t.acao === aid && sessao != null && ativas(t.id).some(i => i.pessoa === sessao)).map(t => t.id);
    const podeVer = a => sessao != null && (a.organizador === sessao || (pessoa(sessao) || {}).papel === 'moderador' || (a.status === 'publicada' && inscritaEm(a.id).length > 0));
    const sessaoObj = () => { if (sessao == null) return null; const p = pessoa(sessao); return { id: p.id, nome: p.nome, email: p.email || null, telefone: p.telefone || null, papel: p.papel, bloqueada: !!p.bloqueada }; };
    return {
      modo: 'exemplo',
      async sessao() { return sessaoObj(); },
      async entrar() { sessao = dados.config.eu; },
      async sair() { sessao = null; },
      async publico() {
        return {
          config: { vaquinha: dados.config.vaquinha, frase: dados.config.frase, hoje: dados.config.hoje },
          organizacoes: dados.organizacoes.map(o => ({ id: o.id, nome: o.nome, tipo: o.tipo, verificada: !!o.verificada })),
          acoes: dados.acoes.filter(a => a.status === 'publicada').map(publica),
          turnos: dados.turnos.filter(t => (dados.acoes.find(a => a.id === t.acao) || {}).status === 'publicada').map(turno),
        };
      },
      async acao(id) {
        const a = dados.acoes.find(x => x.id === id);
        if (!a || (a.status !== 'publicada' && !(sessao != null && (a.organizador === sessao || (pessoa(sessao) || {}).papel === 'moderador')))) return null;
        return { acao: publica(a), turnos: turnosDa(a.id), inscrita: inscritaEm(a.id), combinado: podeVer(a) ? combinadoDe(a) : null };
      },
      async salvarTelefone(telefone) {
        if (sessao == null) throw erro('precisa_entrar');
        pessoa(sessao).telefone = formatarTelefone(telefone);
        return sessaoObj();
      },
      async inscrever(tid) {
        if (sessao == null) throw erro('precisa_entrar');
        const p = pessoa(sessao);
        if (p.bloqueada) throw erro('bloqueada');
        if (!p.telefone) throw erro('sem_telefone');
        const t = dados.turnos.find(x => x.id === tid); const a = t && dados.acoes.find(x => x.id === t.acao);
        if (!a || a.status !== 'publicada') throw erro('nao_publicada');
        if (t.inicio.slice(0, 10) < dados.config.hoje) throw erro('turno_passado');
        const ja = dados.inscricoes.find(i => i.turno === tid && i.pessoa === sessao);
        if (!(ja && !ja.canceladaEm)) {
          if (t.lotacao && ativas(tid).length >= t.lotacao) throw erro('lotado');
          if (ja) { ja.canceladaEm = null; ja.criadaEm = dados.config.hoje; }
          else dados.inscricoes.push({ id: Date.now() + Math.floor(Math.random() * 1000), pessoa: sessao, turno: tid, criadaEm: dados.config.hoje, canceladaEm: null, presenca: null });
        }
        return { combinado: combinadoDe(a) };
      },
      async desistir(tid) {
        if (sessao == null) throw erro('precisa_entrar');
        const i = dados.inscricoes.find(i => i.turno === tid && i.pessoa === sessao && !i.canceladaEm);
        if (i) i.canceladaEm = dados.config.hoje;
      },
      async minhasInscricoes() {
        if (sessao == null) return [];
        return dados.inscricoes.filter(i => i.pessoa === sessao && !i.canceladaEm).map(i => {
          const t = dados.turnos.find(x => x.id === i.turno); const a = t && dados.acoes.find(x => x.id === t.acao);
          return a ? { acao: publica(a), turno: turno(t) } : null;
        }).filter(Boolean).sort((p, q) => p.turno.inicio.localeCompare(q.turno.inicio));
      },
    };
  }
  return { criar, formatarTelefone };
});
