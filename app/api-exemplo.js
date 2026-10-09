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
      lugar: Object.assign({}, a.lugar, a.lugar.online ? {} : { aproximado: a.lugar.precisao === 'cidade' }), foto: a.foto ? Object.assign({}, a.foto) : null,
      prioritaria: !!a.prioritaria, status: a.status, contatoTipo: a.contatoTipo || 'organizador_chama', criadaEm: a.criadaEm,
      fonte: a.fonte || null, linkDivulgacao: a.contatoTipo === 'divulgacao' ? a.contatoLink || null : null,
    });
    const turno = t => ({ id: t.id, acao: t.acao, inicio: t.inicio, fim: t.fim, lotacao: t.lotacao || null, vao: ativas(t.id).length });
    const turnosDa = aid => dados.turnos.filter(t => t.acao === aid).sort((a, b) => a.inicio.localeCompare(b.inicio)).map(turno);
    const combinadoDe = a => ({ detalhe: a.detalhe || null, contato: { tipo: a.contatoTipo || 'organizador_chama', whatsapp: a.contatoWhatsapp || null, link: a.contatoLink || null } });
    const inscritaEm = aid => dados.turnos.filter(t => t.acao === aid && sessao != null && ativas(t.id).some(i => i.pessoa === sessao)).map(t => t.id);
    const podeVer = a => sessao != null && (a.organizador === sessao || (pessoa(sessao) || {}).papel === 'moderador' || (a.status === 'publicada' && inscritaEm(a.id).length > 0));
    const ehModerador = () => sessao != null && (pessoa(sessao) || {}).papel === 'moderador' && !(pessoa(sessao) || {}).bloqueada;
    const completa = a => Object.assign(publica(a), { motivoRecusa: a.motivoRecusa || null, detalhe: a.detalhe || null, contatoLink: a.contatoLink || null });
    const comInscritos = aid => turnosDa(aid).map(t => Object.assign(t, { inscritos: ativas(t.id).map(i => { const q = pessoa(i.pessoa) || {}; return { nome: q.nome, telefone: q.telefone || null }; }) }));
    const sessaoObj = () => { if (sessao == null) return null; const p = pessoa(sessao); return { id: p.id, nome: p.nome, email: p.email || null, telefone: p.telefone || null, papel: p.papel, bloqueada: !!p.bloqueada, organizacao: p.organizacao || null }; };
    return {
      modo: 'exemplo',
      async sessao() { return sessaoObj(); },
      async entrar() { sessao = dados.config.eu; },
      async sair() { sessao = null; },
      async publico() {
        return {
          config: { vaquinha: dados.config.vaquinha, frase: dados.config.frase, hoje: dados.config.hoje },
          organizacoes: dados.organizacoes.map(o => ({ id: o.id, nome: o.nome, tipo: o.tipo, verificada: !!o.verificada, foto: o.foto && o.foto.url ? Object.assign({}, o.foto) : null })),
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
        const t = dados.turnos.find(x => x.id === tid); const a = t && dados.acoes.find(x => x.id === t.acao);
        if (!a || a.status !== 'publicada') throw erro('nao_publicada');
        // ação de divulgação: "Eu vou!" só marca presença, sem telefone
        if (a.contatoTipo !== 'divulgacao' && !p.telefone) throw erro('sem_telefone');
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
      async enviarFoto(blob) { if (sessao == null) throw erro('precisa_entrar'); return URL.createObjectURL(blob); },
      async fotoDoInstagram() { throw erro('so_no_site'); },
      // criar ação: nasce em análise, a não ser que quem cria seja verificado (papel ou organização verificada)
      async criarAcao(d) {
        if (sessao == null) throw erro('precisa_entrar');
        const p = pessoa(sessao), hoje = dados.config.hoje;
        if (p.bloqueada) throw erro('bloqueada');
        if (!p.telefone) throw erro('sem_telefone');
        const minhas = dados.acoes.filter(a => a.organizador === sessao);
        if (minhas.filter(a => a.criadaEm === hoje).length >= 10) throw erro('limite_diario');
        if (minhas.filter(a => a.status === 'em análise').length >= 10) throw erro('limite_em_analise');
        if (!String(d.titulo || '').trim()) throw erro('sem_titulo');
        const foto = String(d.foto || '').trim();
        if (!/^(https:|blob:)/.test(foto)) throw erro('sem_foto');
        if (!d.online && (!String(d.lugar_nome || '').trim() || d.lat == null || d.lon == null)) throw erro('sem_lugar');
        const ts = d.turnos || [];
        if (!ts.length || ts.some(t => !t.inicio || !t.fim || t.fim <= t.inicio || t.inicio.slice(0, 10) < hoje)) throw erro('turno_invalido');
        const grupo = String(d.grupo || '').trim();
        if (grupo && !/^https:\/\/chat\.whatsapp\.com\//.test(grupo)) throw erro('grupo_invalido');
        const verificada = p.papel === 'organizador' || p.papel === 'moderador' || !!(p.organizacao && (org(p.organizacao) || {}).verificada);
        const status = verificada ? 'publicada' : 'em análise';
        const id = Math.max(0, ...dados.acoes.map(a => a.id)) + 1;
        const lugar = d.online ? { nome: 'Online', bairro: 'Online', cidade: 'Online', lat: null, lon: null, online: true }
          : { nome: d.lugar_nome, bairro: d.bairro || '', cidade: d.cidade || '', lat: d.lat, lon: d.lon };
        dados.acoes.push({ id, titulo: d.titulo.trim(), tipo: d.tipo, descricao: d.descricao || '', organizador: sessao, organizacao: d.organizacao || null,
          lugar, detalhe: d.detalhe || '', contatoTipo: grupo ? 'link_grupo' : 'organizador_chama', contatoLink: grupo || null,
          foto: { url: foto, credito: '' },
          status, motivoRecusa: null, prioritaria: false, criadaEm: hoje });
        ts.forEach((t, i) => dados.turnos.push({ id: Date.now() + i, acao: id, inicio: t.inicio, fim: t.fim, lotacao: t.lotacao ? Number(t.lotacao) : null }));
        return { id, status };
      },
      async minhasAcoes() {
        if (sessao == null) return [];
        return dados.acoes.filter(a => a.organizador === sessao).sort((p, q) => String(q.criadaEm).localeCompare(String(p.criadaEm)) || q.id - p.id)
          .map(a => ({ acao: completa(a), turnos: comInscritos(a.id) }));
      },
      async encerrarAcao(id) {
        const a = dados.acoes.find(x => x.id === id);
        if (!a || sessao == null || !(a.organizador === sessao || ehModerador()) || !['em análise', 'publicada'].includes(a.status)) throw erro('nao_pode');
        a.status = 'encerrada';
      },
      async fila(situacao = 'em análise') {
        if (!ehModerador()) throw erro('so_moderador');
        // suspensas inclui as importadas: suspender é o jeito de tirar uma importada do ar
        return dados.acoes.filter(a => a.status === situacao && (!a.fonte || situacao === 'rascunho')).sort((p, q) => String(q.criadaEm).localeCompare(String(p.criadaEm)))
          .map(a => {
            const p = pessoa(a.organizador) || {}; const delas = dados.acoes.filter(x => x.organizador === p.id);
            return { acao: completa(a), turnos: comInscritos(a.id), organizador: { id: p.id, nome: p.nome, email: p.email || null, telefone: p.telefone || null, bloqueada: !!p.bloqueada,
              criadas: delas.length, aprovadas: delas.filter(x => x.status === 'publicada' || x.status === 'encerrada').length, recusadas: delas.filter(x => x.status === 'recusada').length } };
          });
      },
      async aprovar(id) {
        if (!ehModerador()) throw erro('so_moderador');
        const a = dados.acoes.find(x => x.id === id); if (!a || a.status !== 'em análise') throw erro('nao_pode');
        a.status = 'publicada'; a.motivoRecusa = null;
      },
      async recusar(id, motivo) {
        if (!ehModerador()) throw erro('so_moderador');
        if (!String(motivo || '').trim()) throw erro('sem_motivo');
        const a = dados.acoes.find(x => x.id === id); if (!a || !['em análise', 'publicada'].includes(a.status)) throw erro('nao_pode');
        a.status = 'recusada'; a.motivoRecusa = String(motivo).trim();
      },
      async suspender(id, motivo) {
        if (!ehModerador()) throw erro('so_moderador');
        const a = dados.acoes.find(x => x.id === id); if (!a || a.status !== 'publicada') throw erro('nao_pode');
        a.status = 'rascunho'; a.motivoRecusa = String(motivo || '').trim() || null;
      },
      async reativar(id) {
        if (!ehModerador()) throw erro('so_moderador');
        const a = dados.acoes.find(x => x.id === id); if (!a || a.status !== 'rascunho') throw erro('nao_pode');
        if ((pessoa(a.organizador) || {}).bloqueada) throw erro('organizador_bloqueado');
        a.status = 'publicada'; a.motivoRecusa = null;
      },
      // apaga a ação com turnos e inscrições; importada não (a próxima importação traria de volta): suspende
      async excluir(id) {
        if (!ehModerador()) throw erro('so_moderador');
        const a = dados.acoes.find(x => x.id === id); if (!a) throw erro('nao_pode');
        if (a.fonte) throw erro('importada');
        const tids = dados.turnos.filter(t => t.acao === id).map(t => t.id);
        const tirar = (lista, fora) => { for (let k = lista.length - 1; k >= 0; k--) if (fora(lista[k])) lista.splice(k, 1); };
        tirar(dados.inscricoes, i => tids.includes(i.turno)); tirar(dados.turnos, t => t.acao === id); tirar(dados.acoes, x => x.id === id);
      },
    };
  }
  return { criar, formatarTelefone };
});
