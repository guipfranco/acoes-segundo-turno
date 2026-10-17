// Configuração pública do app. Sem `supabase`, o app roda no modo exemplo (dados fictícios em memória).
// A chave anon do Supabase é pública por desenho: o que protege os dados é o RLS no banco.
// Desde 2026-10-17 o app lê e grava no Supabase do boralula.org (o mesmo que boralula.org publica em /config.js), onde
// a Agenda mora depois da fusão. Sem googleClientId: o login vai pelo redirecionamento do Supabase.
window.CONFIG = { supabase: { url: 'https://zpcghehadrztxjlkjnzj.supabase.co', anonKey: 'sb_publishable_9M1Tdg2C5GYkI3Hf87McXA__C2Xxwuq' } };
