// Configuração pública do app. Sem `supabase`, o app roda no modo exemplo (dados fictícios em memória).
// A chave anon do Supabase é pública por desenho: o que protege os dados é o RLS no banco.
window.CONFIG = { supabase: null };
