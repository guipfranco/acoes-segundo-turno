window.DADOS = {
 "config": {
  "vaquinha": "https://exemplo.vaquinha.oficial/lula",
  "frase": "O que você pode fazer hoje para eleger o Lula",
  "hoje": "2026-10-09",
  "eu": 2
 },
 "organizacoes": [
  {
   "id": 1,
   "nome": "Mandato Barba",
   "tipo": "mandato",
   "verificada": true
  },
  {
   "id": 2,
   "nome": "Mandato Alfredinho",
   "tipo": "mandato",
   "verificada": true
  },
  {
   "id": 3,
   "nome": "PT Diadema",
   "tipo": "partido",
   "verificada": true
  },
  {
   "id": 4,
   "nome": "Coletivo Periferia Viva",
   "tipo": "coletivo",
   "verificada": false
  },
  {
   "id": 5,
   "nome": "MTST Grajaú",
   "tipo": "movimento",
   "verificada": true
  }
 ],
 "pessoas": [
  {
   "id": 1,
   "nome": "Ana Souza",
   "papel": "moderador",
   "organizacao": null,
   "telefone": "(11) 9xxxx-xxxx",
   "bloqueada": false
  },
  {
   "id": 2,
   "nome": "Carlos Lima",
   "papel": "organizador",
   "organizacao": null,
   "telefone": "(11) 9xxxx-xxxx",
   "bloqueada": false
  },
  {
   "id": 3,
   "nome": "Beatriz Ramos",
   "papel": "organizador",
   "organizacao": 1,
   "telefone": "(11) 9xxxx-xxxx",
   "bloqueada": false
  },
  {
   "id": 4,
   "nome": "Diego Alves",
   "papel": "organizador",
   "organizacao": 4,
   "telefone": "(11) 9xxxx-xxxx",
   "bloqueada": false
  },
  {
   "id": 5,
   "nome": "Fernanda Costa",
   "papel": "participante",
   "organizacao": null,
   "telefone": "(11) 9xxxx-xxxx",
   "bloqueada": false
  },
  {
   "id": 6,
   "nome": "Gustavo Pereira",
   "papel": "participante",
   "organizacao": null,
   "telefone": "(11) 9xxxx-xxxx",
   "bloqueada": false
  },
  {
   "id": 7,
   "nome": "Helena Martins",
   "papel": "participante",
   "organizacao": null,
   "telefone": "(11) 9xxxx-xxxx",
   "bloqueada": false
  },
  {
   "id": 8,
   "nome": "Igor Santos",
   "papel": "participante",
   "organizacao": null,
   "telefone": "(11) 9xxxx-xxxx",
   "bloqueada": false
  }
 ],
 "acoes": [
  {
   "id": 1,
   "titulo": "Panfletagem na estação Grajaú",
   "tipo": "panfletagem",
   "descricao": "Vamos distribuir material do Lula na saída da estação. Traga disposição; o material a gente leva.",
   "organizador": 2,
   "organizacao": null,
   "lugar": {
    "nome": "Estação Grajaú",
    "bairro": "Grajaú",
    "cidade": "São Paulo",
    "lat": -23.7746,
    "lon": -46.6978
   },
   "detalhe": "Saída principal, perto do ponto de ônibus. Procure a camisa vermelha.",
   "grupo": "https://chat.whatsapp.com/exemplo0001",
   "status": "publicada",
   "motivoRecusa": null,
   "prioritaria": true,
   "criadaEm": "2026-10-02"
  },
  {
   "id": 2,
   "titulo": "Roda de conversa em Parelheiros",
   "tipo": "roda de conversa",
   "descricao": "Conversa aberta sobre por que votar no Lula e como responder às dúvidas de vizinhos e família.",
   "organizador": 2,
   "organizacao": null,
   "lugar": {
    "nome": "Terminal Parelheiros",
    "bairro": "Parelheiros",
    "cidade": "São Paulo",
    "lat": -23.8273,
    "lon": -46.7271
   },
   "detalhe": "Saída principal, perto do ponto de ônibus. Procure a camisa vermelha.",
   "grupo": "https://chat.whatsapp.com/exemplo0002",
   "status": "publicada",
   "motivoRecusa": null,
   "prioritaria": true,
   "criadaEm": "2026-10-03"
  },
  {
   "id": 3,
   "titulo": "Adesivaço na Sé",
   "tipo": "adesivaço",
   "descricao": "Adesivos do Lula para carros, motos e quem passar. Material garantido.",
   "organizador": 3,
   "organizacao": 1,
   "lugar": {
    "nome": "Praça da Sé",
    "bairro": "Sé",
    "cidade": "São Paulo",
    "lat": -23.5505,
    "lon": -46.6333
   },
   "detalhe": "Saída principal, perto do ponto de ônibus. Procure a camisa vermelha.",
   "grupo": "https://chat.whatsapp.com/exemplo0003",
   "status": "publicada",
   "motivoRecusa": null,
   "prioritaria": false,
   "criadaEm": "2026-10-04"
  },
  {
   "id": 4,
   "titulo": "Porta a porta no Jardim Ângela",
   "tipo": "porta a porta",
   "descricao": "Em duplas, conversa na porta com quem mora na região. Roteiro e material no ponto de encontro.",
   "organizador": 3,
   "organizacao": 1,
   "lugar": {
    "nome": "Estação Jardim Ângela",
    "bairro": "Jardim Ângela",
    "cidade": "São Paulo",
    "lat": -23.7138,
    "lon": -46.7609
   },
   "detalhe": "Saída principal, perto do ponto de ônibus. Procure a camisa vermelha.",
   "grupo": "https://chat.whatsapp.com/exemplo0004",
   "status": "publicada",
   "motivoRecusa": null,
   "prioritaria": true,
   "criadaEm": "2026-10-05"
  },
  {
   "id": 5,
   "titulo": "Bandeiraço no Largo 13",
   "tipo": "bandeiraço",
   "descricao": "Bandeiras e faixas do Lula na hora do rush. Traga bandeira se tiver.",
   "organizador": 3,
   "organizacao": 1,
   "lugar": {
    "nome": "Largo 13 de Maio",
    "bairro": "Santo Amaro",
    "cidade": "São Paulo",
    "lat": -23.651,
    "lon": -46.7087
   },
   "detalhe": "Saída principal, perto do ponto de ônibus. Procure a camisa vermelha.",
   "grupo": "https://chat.whatsapp.com/exemplo0005",
   "status": "publicada",
   "motivoRecusa": null,
   "prioritaria": false,
   "criadaEm": "2026-10-06"
  },
  {
   "id": 6,
   "titulo": "Ligatona para indecisos de Diadema",
   "tipo": "ligatona",
   "descricao": "Cada pessoa liga para os próprios contatos com um roteiro simples. Pode ser de casa.",
   "organizador": 3,
   "organizacao": 3,
   "lugar": {
    "nome": "Terminal Diadema",
    "bairro": "Diadema",
    "cidade": "Diadema",
    "lat": -23.6861,
    "lon": -46.6228
   },
   "detalhe": "Saída principal, perto do ponto de ônibus. Procure a camisa vermelha.",
   "grupo": "https://chat.whatsapp.com/exemplo0006",
   "status": "publicada",
   "motivoRecusa": null,
   "prioritaria": true,
   "criadaEm": "2026-10-07"
  },
  {
   "id": 7,
   "titulo": "Panfletagem na Praça da Matriz",
   "tipo": "panfletagem",
   "descricao": "Vamos distribuir material do Lula na saída da estação. Traga disposição; o material a gente leva.",
   "organizador": 3,
   "organizacao": 3,
   "lugar": {
    "nome": "Praça da Matriz",
    "bairro": "São Bernardo do Campo",
    "cidade": "São Bernardo do Campo",
    "lat": -23.6944,
    "lon": -46.5654
   },
   "detalhe": "Saída principal, perto do ponto de ônibus. Procure a camisa vermelha.",
   "grupo": "https://chat.whatsapp.com/exemplo0007",
   "status": "publicada",
   "motivoRecusa": null,
   "prioritaria": true,
   "criadaEm": "2026-10-08"
  },
  {
   "id": 8,
   "titulo": "Roda de conversa na Brasilândia",
   "tipo": "roda de conversa",
   "descricao": "Conversa aberta sobre por que votar no Lula e como responder às dúvidas de vizinhos e família.",
   "organizador": 4,
   "organizacao": 4,
   "lugar": {
    "nome": "Estação Brasilândia",
    "bairro": "Brasilândia",
    "cidade": "São Paulo",
    "lat": -23.4616,
    "lon": -46.6895
   },
   "detalhe": "Saída principal, perto do ponto de ônibus. Procure a camisa vermelha.",
   "grupo": "https://chat.whatsapp.com/exemplo0008",
   "status": "publicada",
   "motivoRecusa": null,
   "prioritaria": true,
   "criadaEm": "2026-10-01"
  },
  {
   "id": 9,
   "titulo": "Adesivaço em Guaianases",
   "tipo": "adesivaço",
   "descricao": "Adesivos do Lula para carros, motos e quem passar. Material garantido.",
   "organizador": 3,
   "organizacao": 2,
   "lugar": {
    "nome": "Estação Guaianases",
    "bairro": "Guaianases",
    "cidade": "São Paulo",
    "lat": -23.541,
    "lon": -46.4103
   },
   "detalhe": "Saída principal, perto do ponto de ônibus. Procure a camisa vermelha.",
   "grupo": "https://chat.whatsapp.com/exemplo0009",
   "status": "publicada",
   "motivoRecusa": null,
   "prioritaria": true,
   "criadaEm": "2026-10-02"
  },
  {
   "id": 10,
   "titulo": "Panfletagem na feira de Cidade Tiradentes",
   "tipo": "panfletagem",
   "descricao": "Vamos distribuir material do Lula na saída da estação. Traga disposição; o material a gente leva.",
   "organizador": 3,
   "organizacao": 2,
   "lugar": {
    "nome": "Feira de Cidade Tiradentes",
    "bairro": "Cidade Tiradentes",
    "cidade": "São Paulo",
    "lat": -23.5853,
    "lon": -46.4035
   },
   "detalhe": "Saída principal, perto do ponto de ônibus. Procure a camisa vermelha.",
   "grupo": "https://chat.whatsapp.com/exemplo0010",
   "status": "publicada",
   "motivoRecusa": null,
   "prioritaria": true,
   "criadaEm": "2026-10-03"
  },
  {
   "id": 11,
   "titulo": "Bandeiraço no Largo da Batata",
   "tipo": "bandeiraço",
   "descricao": "Bandeiras e faixas do Lula na hora do rush. Traga bandeira se tiver.",
   "organizador": 3,
   "organizacao": 1,
   "lugar": {
    "nome": "Largo da Batata",
    "bairro": "Pinheiros",
    "cidade": "São Paulo",
    "lat": -23.5668,
    "lon": -46.6931
   },
   "detalhe": "Saída principal, perto do ponto de ônibus. Procure a camisa vermelha.",
   "grupo": "https://chat.whatsapp.com/exemplo0011",
   "status": "encerrada",
   "motivoRecusa": null,
   "prioritaria": false,
   "criadaEm": "2026-10-04"
  },
  {
   "id": 12,
   "titulo": "Porta a porta na Pedreira",
   "tipo": "porta a porta",
   "descricao": "Em duplas, conversa na porta com quem mora na região. Roteiro e material no ponto de encontro.",
   "organizador": 2,
   "organizacao": null,
   "lugar": {
    "nome": "Terminal Pedreira",
    "bairro": "Pedreira",
    "cidade": "São Paulo",
    "lat": -23.6999,
    "lon": -46.669
   },
   "detalhe": "Saída principal, perto do ponto de ônibus. Procure a camisa vermelha.",
   "grupo": "https://chat.whatsapp.com/exemplo0012",
   "status": "em análise",
   "motivoRecusa": null,
   "prioritaria": true,
   "criadaEm": "2026-10-05"
  },
  {
   "id": 13,
   "titulo": "Panfletagem em Itaquera",
   "tipo": "panfletagem",
   "descricao": "Vamos distribuir material do Lula na saída da estação. Traga disposição; o material a gente leva.",
   "organizador": 4,
   "organizacao": 4,
   "lugar": {
    "nome": "Estação Itaquera",
    "bairro": "Itaquera",
    "cidade": "São Paulo",
    "lat": -23.5403,
    "lon": -46.4625
   },
   "detalhe": "Saída principal, perto do ponto de ônibus. Procure a camisa vermelha.",
   "grupo": "https://chat.whatsapp.com/exemplo0013",
   "status": "em análise",
   "motivoRecusa": null,
   "prioritaria": false,
   "criadaEm": "2026-10-06"
  },
  {
   "id": 14,
   "titulo": "Roda de conversa no Capão Redondo",
   "tipo": "roda de conversa",
   "descricao": "Conversa aberta sobre por que votar no Lula e como responder às dúvidas de vizinhos e família.",
   "organizador": 4,
   "organizacao": 4,
   "lugar": {
    "nome": "Terminal Capão Redondo",
    "bairro": "Capão Redondo",
    "cidade": "São Paulo",
    "lat": -23.6666,
    "lon": -46.768
   },
   "detalhe": "Saída principal, perto do ponto de ônibus. Procure a camisa vermelha.",
   "grupo": "https://chat.whatsapp.com/exemplo0014",
   "status": "recusada",
   "motivoRecusa": "pede dinheiro para o material",
   "prioritaria": true,
   "criadaEm": "2026-10-07"
  }
 ],
 "turnos": [
  {
   "id": 1,
   "acao": 1,
   "inicio": "2026-10-10T08:00",
   "fim": "2026-10-10T10:00",
   "lotacao": null
  },
  {
   "id": 2,
   "acao": 1,
   "inicio": "2026-10-10T17:00",
   "fim": "2026-10-10T19:00",
   "lotacao": null
  },
  {
   "id": 3,
   "acao": 2,
   "inicio": "2026-10-07T18:30",
   "fim": "2026-10-07T20:00",
   "lotacao": null
  },
  {
   "id": 4,
   "acao": 2,
   "inicio": "2026-10-14T18:30",
   "fim": "2026-10-14T20:00",
   "lotacao": null
  },
  {
   "id": 5,
   "acao": 3,
   "inicio": "2026-10-09T12:00",
   "fim": "2026-10-09T14:00",
   "lotacao": 2
  },
  {
   "id": 6,
   "acao": 3,
   "inicio": "2026-10-11T10:00",
   "fim": "2026-10-11T13:00",
   "lotacao": null
  },
  {
   "id": 7,
   "acao": 4,
   "inicio": "2026-10-11T09:00",
   "fim": "2026-10-11T12:00",
   "lotacao": null
  },
  {
   "id": 8,
   "acao": 5,
   "inicio": "2026-10-10T17:30",
   "fim": "2026-10-10T19:00",
   "lotacao": null
  },
  {
   "id": 9,
   "acao": 6,
   "inicio": "2026-10-12T14:00",
   "fim": "2026-10-12T17:00",
   "lotacao": 20
  },
  {
   "id": 10,
   "acao": 7,
   "inicio": "2026-10-11T09:00",
   "fim": "2026-10-11T12:00",
   "lotacao": null
  },
  {
   "id": 11,
   "acao": 8,
   "inicio": "2026-10-13T19:00",
   "fim": "2026-10-13T20:30",
   "lotacao": null
  },
  {
   "id": 12,
   "acao": 9,
   "inicio": "2026-10-17T09:00",
   "fim": "2026-10-17T12:00",
   "lotacao": null
  },
  {
   "id": 13,
   "acao": 10,
   "inicio": "2026-10-07T07:00",
   "fim": "2026-10-07T10:00",
   "lotacao": null
  },
  {
   "id": 14,
   "acao": 11,
   "inicio": "2026-10-05T17:30",
   "fim": "2026-10-05T19:00",
   "lotacao": null
  },
  {
   "id": 15,
   "acao": 12,
   "inicio": "2026-10-18T09:00",
   "fim": "2026-10-18T12:00",
   "lotacao": null
  },
  {
   "id": 16,
   "acao": 13,
   "inicio": "2026-10-16T17:00",
   "fim": "2026-10-16T19:00",
   "lotacao": null
  },
  {
   "id": 17,
   "acao": 14,
   "inicio": "2026-10-15T19:00",
   "fim": "2026-10-15T20:30",
   "lotacao": null
  }
 ],
 "inscricoes": [
  {
   "id": 1,
   "pessoa": 5,
   "turno": 5,
   "criadaEm": "2026-10-08",
   "canceladaEm": null,
   "presenca": null
  },
  {
   "id": 2,
   "pessoa": 6,
   "turno": 5,
   "criadaEm": "2026-10-08",
   "canceladaEm": null,
   "presenca": null
  },
  {
   "id": 3,
   "pessoa": 2,
   "turno": 7,
   "criadaEm": "2026-10-08",
   "canceladaEm": null,
   "presenca": null
  },
  {
   "id": 4,
   "pessoa": 7,
   "turno": 7,
   "criadaEm": "2026-10-08",
   "canceladaEm": null,
   "presenca": null
  },
  {
   "id": 5,
   "pessoa": 5,
   "turno": 1,
   "criadaEm": "2026-10-08",
   "canceladaEm": null,
   "presenca": null
  },
  {
   "id": 6,
   "pessoa": 6,
   "turno": 1,
   "criadaEm": "2026-10-08",
   "canceladaEm": null,
   "presenca": null
  },
  {
   "id": 7,
   "pessoa": 8,
   "turno": 2,
   "criadaEm": "2026-10-08",
   "canceladaEm": null,
   "presenca": null
  },
  {
   "id": 8,
   "pessoa": 7,
   "turno": 4,
   "criadaEm": "2026-10-08",
   "canceladaEm": null,
   "presenca": null
  },
  {
   "id": 9,
   "pessoa": 8,
   "turno": 6,
   "criadaEm": "2026-10-08",
   "canceladaEm": null,
   "presenca": null
  },
  {
   "id": 10,
   "pessoa": 5,
   "turno": 8,
   "criadaEm": "2026-10-08",
   "canceladaEm": null,
   "presenca": null
  },
  {
   "id": 11,
   "pessoa": 7,
   "turno": 3,
   "criadaEm": "2026-10-08",
   "canceladaEm": null,
   "presenca": null
  },
  {
   "id": 12,
   "pessoa": 6,
   "turno": 3,
   "criadaEm": "2026-10-08",
   "canceladaEm": null,
   "presenca": null
  },
  {
   "id": 13,
   "pessoa": 5,
   "turno": 14,
   "criadaEm": "2026-10-03",
   "canceladaEm": null,
   "presenca": true
  },
  {
   "id": 14,
   "pessoa": 6,
   "turno": 14,
   "criadaEm": "2026-10-03",
   "canceladaEm": null,
   "presenca": true
  },
  {
   "id": 15,
   "pessoa": 8,
   "turno": 14,
   "criadaEm": "2026-10-03",
   "canceladaEm": null,
   "presenca": false
  }
 ],
 "areasPrioritarias": [
  "Grajaú",
  "Jardim Ângela",
  "Parelheiros",
  "Cidade Dutra",
  "Pedreira",
  "Diadema",
  "São Bernardo do Campo",
  "Guaianases",
  "Cidade Tiradentes",
  "Brasilândia",
  "Capão Redondo"
 ]
};
