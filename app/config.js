// Configuração pública do app. Sem `supabase`, o app roda no modo exemplo (dados fictícios em memória).
// A chave anon do Supabase é pública por desenho: o que protege os dados é o RLS no banco.
window.CONFIG = { supabase: { url: 'https://ommitzndniqnmsjsjghb.supabase.co', anonKey: 'sb_publishable_s8RK7ex9EwN6b6mz46JY7g_SLsupkXe',
  // ID público do cliente OAuth do Google (o mesmo do provedor no Supabase): liga o botão do Google sobre o site
  googleClientId: '691198373003-m2p6k0kk454kvaom1n8bmor0nmluj47a.apps.googleusercontent.com' } };
