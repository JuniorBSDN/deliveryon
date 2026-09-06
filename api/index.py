from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

app = FastAPI(
    title="DeliveryON API",
    description="API unificada para os painéis Master, Gestor, Entregador e Hub (Cliente)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ================= MODELOS PYDANTIC =================
class EmpresaCreate(BaseModel):
    razao_social: str
    nome_fantasia: str
    cnpj: str
    responsavel: str
    contato: str
    email_admin: EmailStr
    endereco: str
    plano: str = "basic"
    vencimento: int = 10
    limite_usuarios: int = 5


class EmpresaUpdate(BaseModel):
    razao_social: Optional[str] = None
    nome_fantasia: Optional[str] = None
    cnpj: Optional[str] = None
    responsavel: Optional[str] = None
    contato: Optional[str] = None
    email_admin: Optional[EmailStr] = None
    endereco: Optional[str] = None
    plano: Optional[str] = None
    vencimento: Optional[int] = None
    limite_usuarios: Optional[int] = None


class PixConfig(BaseModel):
    qrcode_imagem: str
    copia_e_cola: str


class EntregadorAuth(BaseModel):
    telefone: str
    senha: str


class EntregadorCreate(BaseModel):
    nome: str
    email: EmailStr
    cpf: str
    telefone: str
    senha: str
    data_nascimento: str
    tipo_veiculo: str
    veiculo_modelo: str
    veiculo_placa: str


class StatusUpdate(BaseModel):
    status: str


class OrderCreate(BaseModel):
    empresa_id: int
    cliente: str
    cliente_nome: Optional[str] = None
    telefone: str
    endereco: str
    pagamento: str
    itens: str
    total: str
    valor_total: Optional[str] = None
    status: str = "Aguardando pagamento"
    data: Optional[str] = None
    hora: Optional[str] = None


class ProductCreate(BaseModel):
    empresa_id: int
    nome: str
    descricao: Optional[str] = None
    preco: float
    estoque: int = 100
    categoria: str = "geral"
    foto: Optional[str] = None


class ClientCreate(BaseModel):
    empresa_id: int
    nome: str
    telefone: str
    email: Optional[EmailStr] = None
    endereco: str
    referencia: Optional[str] = None


class ColaboradorCreate(BaseModel):
    empresa_id: int
    nome: str
    telefone: str
    email: EmailStr
    cpf: str
    data_nascimento: str
    endereco: str
    funcao: str
    status: str = "Disponível"
    observacoes: Optional[str] = None
    foto: Optional[str] = None


class HelpdeskCreate(BaseModel):
    empresa_id: int
    resumo_problema: str
    descricao: str


class OuvidoriaCreate(BaseModel):
    empresa_id: Optional[int] = 1
    pedido_id: Optional[int] = None
    cliente: Optional[str] = "Cliente Anônimo"
    avaliacao: str
    relato: str


class ConfiguracaoUpdate(BaseModel):
    titulo: Optional[str] = None
    slogan: Optional[str] = None
    endereco: Optional[str] = None
    telefone: Optional[str] = None
    horario_funcionamento: Optional[str] = None
    cor_primaria: Optional[str] = None
    cor_secundaria: Optional[str] = None
    logo_url: Optional[str] = None


# ================= BANCO DE DADOS EM MEMÓRIA =================
DB_EMPRESAS = [
    {
        "id": 1,
        "razao_social": "Burger Delivery Ltda",
        "nome_fantasia": "Burger Express",
        "cnpj": "12.345.678/0001-99",
        "responsavel": "Carlos Silva",
        "contato": "(11) 98888-7777",
        "email_admin": "contato@burgerexpress.com",
        "endereco": "Av. Paulista, 1000 - São Paulo, SP",
        "plano": "pro",
        "vencimento": 10,
        "limite_usuarios": 20,
        "status": "ativo",
        "qrcode_imagem": "",
        "copia_e_cola": "",
    }
]

DB_ENTREGADORES = [
    {
        "id": 1,
        "nome": "João Motoboy",
        "telefone": "(11) 97777-6666",
        "senha": "123456",
        "cpf": "111.222.333-44",
        "veiculo": "Moto",
        "veiculo_modelo": "Honda CG 160",
        "veiculo_placa": "ABC-1234",
        "status": "Disponível",
        "total_entregas": 42,
        "empresa_id": 1,
    }
]

DB_PRODUTOS = [
    {
        "id": 1,
        "codigo": "PRD-01",
        "nome": "X-Burger Especial",
        "descricao": "Pão, carne artesanal 180g, queijo cheddar e bacon.",
        "preco": 29.90,
        "estoque": 100,
        "categoria": "hamburgueres",
        "foto": "",
        "empresa_id": 1,
    }
]

DB_CLIENTES = [
    {
        "id": 1,
        "empresa_id": 1,
        "nome": "Maria Souza",
        "telefone": "(11) 96666-5555",
        "email": "maria@email.com",
        "endereco": "Rua das Flores, 123",
        "referencia": "Próximo à praça",
    }
]

DB_COLABORADORES = [
    {
        "id": 1,
        "empresa_id": 1,
        "nome": "Ana Gerente",
        "telefone": "(11) 95555-4444",
        "email": "ana@burgerexpress.com",
        "cpf": "222.333.444-55",
        "funcao": "Gerente",
        "status": "Disponível",
        "observacoes": "",
        "foto": "",
    }
]

DB_PEDIDOS = [
    {
        "id": 101,
        "empresa_id": 1,
        "cliente": "Maria Souza",
        "telefone": "(11) 96666-5555",
        "endereco": "Rua das Flores, 123",
        "pagamento": "PIX",
        "itens": "1x X-Burger Especial",
        "total": "34.90",
        "status": "Aprovado / Preparando",
        "hora": "19:30",
        "data": "2026-09-06",
        "motoboy_id": None,
        "motoboy_nome": None,
    }
]

DB_NOTIFICACOES = [
    {
        "id": 1,
        "tipo": "infra",
        "titulo": "Uso de Armazenamento Elevado",
        "mensagem": "O banco de dados Neon DB atingiu 78% da capacidade contratada.",
        "data_hora": "06/09/2026 10:15",
    }
]

DB_HELPDESK = [
    {
        "id": 1,
        "empresa_id": 1,
        "empresa": "Burger Express",
        "resumo_problema": "Erro ao emitir nota fiscal eletrônica",
        "descricao": "O sistema retorna erro 500 ao tentar fechar o caixa.",
        "status": "em_atendimento",
        "tecnico_responsavel": "Carlos Nível 2",
        "data": "06/09/2026",
    }
]

DB_OUVIDORIA = [
    {
        "id": 1,
        "empresa_id": 1,
        "pedido_id": 101,
        "cliente": "Maria Souza",
        "avaliacao": "Ótimo",
        "relato": "Entrega super rápida e lanche quente!",
        "data": "06/09/2026",
    }
]

DB_CONFIGURACOES = {
    1: {
        "titulo": "Burger Express",
        "slogan": "O melhor hambúrguer artesanal da região",
        "endereco": "Av. Paulista, 1000",
        "telefone": "(11) 98888-7777",
        "horario_funcionamento": "Seg a Dom: 18h às 23h",
        "cor_primaria": "#ff5722",
        "cor_secundaria": "#e64a19",
        "logo_url": "",
    }
}


# ================= ROTAS MASTER =================
@app.post("/api/master/auth")
def master_auth(data: dict):
    if data.get("senha") == "master123":
        return {"token": "master_token_secure_xyz"}
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Senha incorreta"
    )


@app.get("/api/master/metrics")
def master_metrics():
    return {
        "db_disk_usage": "1.8 GB / 5.0 GB (36%)",
        "total_clientes": len(DB_EMPRESAS),
        "mrr": "R$ 2.490,00",
    }


@app.get("/api/master/notificacoes")
def master_notificacoes(data: Optional[str] = None):
    return DB_NOTIFICACOES


@app.delete("/api/master/notificacoes/{notif_id}")
def master_deletar_notificacao(notif_id: int):
    global DB_NOTIFICACOES
    DB_NOTIFICACOES = [n for n in DB_NOTIFICACOES if n["id"] != notif_id]
    return {"mensagem": "Notificação removida"}


@app.get("/api/master/empresas")
def master_listar_empresas():
    return DB_EMPRESAS


@app.post("/api/master/empresas", status_code=status.HTTP_201_CREATED)
def master_criar_empresa(empresa: EmpresaCreate):
    novo_id = len(DB_EMPRESAS) + 1
    nova = empresa.model_dump()
    nova["id"] = novo_id
    nova["status"] = "ativo"
    nova["qrcode_imagem"] = ""
    nova["copia_e_cola"] = ""
    DB_EMPRESAS.append(nova)

    DB_CONFIGURACOES[novo_id] = {
        "titulo": nova["nome_fantasia"],
        "slogan": "Delivery oficial",
        "endereco": nova["endereco"],
        "telefone": nova["contato"],
        "cor_primaria": "#ff5722",
        "cor_secundaria": "#e64a19",
        "logo_url": "",
    }
    return nova


@app.put("/api/master/empresas/{emp_id}")
def master_atualizar_empresa(emp_id: int, dados: EmpresaUpdate):
    for e in DB_EMPRESAS:
        if e["id"] == emp_id:
            update_data = dados.model_dump(exclude_unset=True)
            e.update(update_data)
            return e
    raise HTTPException(status_code=404, detail="Empresa não encontrada")


@app.delete("/api/master/empresas/{emp_id}")
def master_deletar_empresa(emp_id: int):
    global DB_EMPRESAS
    DB_EMPRESAS = [e for e in DB_EMPRESAS if e["id"] != emp_id]
    return {"mensagem": "Empresa excluída com sucesso"}


@app.put("/api/master/empresas/{emp_id}/pix")
def master_configurar_pix(emp_id: int, pix: PixConfig):
    for e in DB_EMPRESAS:
        if e["id"] == emp_id:
            e["qrcode_imagem"] = pix.qrcode_imagem
            e["copia_e_cola"] = pix.copia_e_cola
            return {"mensagem": "Pix configurado com sucesso"}
    raise HTTPException(status_code=404, detail="Empresa não encontrada")


@app.post("/api/master/empresas/{emp_id}/carimbar-pagamento")
def master_carimbar_pagamento(emp_id: int):
    for e in DB_EMPRESAS:
        if e["id"] == emp_id:
            e["status"] = "ativo"
            return {
                "mensagem": f"Pagamento da empresa {e['nome_fantasia']} carimbado e ativado!"
            }
    raise HTTPException(status_code=404, detail="Empresa não encontrada")


@app.get("/api/master/entregadores")
def master_entregadores():
    return DB_ENTREGADORES


@app.get("/api/master/helpdesk/indicadores")
def master_helpdesk_indicadores():
    return {
        "abertos": len([h for h in DB_HELPDESK if h["status"] == "aberto"]),
        "em_andamento": len(
            [h for h in DB_HELPDESK if h["status"] == "em_atendimento"]
        ),
        "pendentes": len([h for h in DB_HELPDESK if h["status"] == "pendente"]),
        "concluidos": len(
            [h for h in DB_HELPDESK if h["status"] == "concluido"]
        ),
    }


@app.get("/api/master/helpdesk/chamados")
def master_helpdesk_chamados(data: Optional[str] = None):
    return DB_HELPDESK


@app.put("/api/master/helpdesk/chamados/{c_id}/status")
def master_helpdesk_status(c_id: int, dados: dict):
    for h in DB_HELPDESK:
        if h["id"] == c_id:
            h["status"] = dados.get("status")
            return h
    raise HTTPException(status_code=404, detail="Chamado não encontrado")


@app.post("/api/master/helpdesk/chamados/{c_id}/concluir")
def master_helpdesk_concluir(c_id: int, dados: dict):
    for h in DB_HELPDESK:
        if h["id"] == c_id:
            h["status"] = "concluido"
            h["tecnico_responsavel"] = dados.get("tecnico")
            return {"mensagem": "Chamado concluído com sucesso"}
    raise HTTPException(status_code=404, detail="Chamado não encontrado")


@app.post("/api/master/helpdesk/chamados/{c_id}/cancelar")
def master_helpdesk_cancelar(c_id: int, dados: dict):
    for h in DB_HELPDESK:
        if h["id"] == c_id:
            h["status"] = "cancelado"
            return {"mensagem": "Chamado cancelado"}
    raise HTTPException(status_code=404, detail="Chamado não encontrado")


@app.get("/api/master/empresas/{emp_id}/historico")
def master_empresa_historico(emp_id: int):
    return [
        {
            "data": "06/09/2026",
            "descricao": "Sistema acessado e plano verificado no Neon DB",
        }
    ]


@app.get("/api/master/entregadores/{ent_id}/historico")
def master_entregador_historico(ent_id: int):
    return [{"data": "06/09/2026", "detalhe": "Turno iniciado com sucesso"}]


# ================= ROTAS GESTOR =================
@app.post("/api/gestor/auth")
def gestor_auth(dados: dict):
    cnpj = dados.get("cnpj")
    for e in DB_EMPRESAS:
        if e["cnpj"] == cnpj:
            return {"empresa_id": e["id"], "nome_fantasia": e["nome_fantasia"]}
    raise HTTPException(
        status_code=404, detail="CNPJ não encontrado ou empresa inativa"
    )


@app.get("/api/dashboard")
def gestor_dashboard(empresa_id: int = 1):
    pedidos_loja = [p for p in DB_PEDIDOS if p["empresa_id"] == empresa_id]
    receita_total = sum(
        float(p["total"].replace(",", "."))
        for p in pedidos_loja
        if p["status"] == "Entregue"
    )
    return {
        "aguardando": len(
            [p for p in pedidos_loja if p["status"] == "Aguardando pagamento"]
        ),
        "entregues": len([p for p in pedidos_loja if p["status"] == "Entregue"]),
        "cancelados": len(
            [p for p in pedidos_loja if p["status"] == "Cancelado"]
        ),
        "receita": f"{receita_total:.2f}".replace(".", ","),
    }


@app.get("/api/dashboard/fluxo")
def gestor_fluxo(empresa_id: int = 1):
    return [
        {"hora": "17h", "total": 2},
        {"hora": "18h", "total": 5},
        {"hora": "19h", "total": 12},
        {"hora": "20h", "total": 8},
        {"hora": "21h", "total": 4},
    ]


@app.get("/api/orders")
def gestor_orders(empresa_id: int = 1):
    return [p for p in DB_PEDIDOS if p["empresa_id"] == empresa_id]


@app.put("/api/orders/{order_id}/status")
def gestor_order_status(order_id: int, status_data: StatusUpdate):
    for p in DB_PEDIDOS:
        if p["id"] == order_id:
            p["status"] = status_data.status
            return p
    raise HTTPException(status_code=404, detail="Pedido não encontrado")


@app.post("/api/orders/{order_id}/atribuir-motoboy")
def gestor_atribuir_motoboy(order_id: int, dados: dict):
    motoboy_id = dados.get("motoboy_id")
    motoboy_nome = "Entregador"
    for m in DB_ENTREGADORES:
        if m["id"] == motoboy_id:
            motoboy_nome = m["nome"]
    for p in DB_PEDIDOS:
        if p["id"] == order_id:
            p["motoboy_id"] = motoboy_id
            p["motoboy_nome"] = motoboy_nome
            return p
    raise HTTPException(status_code=404, detail="Pedido não encontrado")


@app.post("/api/orders/{order_id}/despachar-proximos")
def gestor_despachar_proximos(order_id: int):
    for p in DB_PEDIDOS:
        if p["id"] == order_id:
            p["status"] = "Saiu para entrega"
            return {"mensagem": "Pedido disparado para a praça (Matchmaking)"}
    raise HTTPException(status_code=404, detail="Pedido não encontrado")


@app.get("/api/products")
def gestor_products(empresa_id: int = 1):
    return [pr for pr in DB_PRODUTOS if pr["empresa_id"] == empresa_id]


@app.post("/api/products", status_code=status.HTTP_201_CREATED)
def gestor_create_product(produto: ProductCreate):
    novo_id = len(DB_PRODUTOS) + 1
    novo = produto.model_dump()
    novo["id"] = novo_id
    novo["codigo"] = f"PRD-{novo_id:02d}"
    DB_PRODUTOS.append(novo)
    return novo


@app.put("/api/products/{code}")
def gestor_update_product(code: str, produto: ProductCreate):
    for p in DB_PRODUTOS:
        if p["codigo"] == code:
            p.update(produto.model_dump())
            return p
    raise HTTPException(status_code=404, detail="Produto não encontrado")


@app.delete("/api/products/{code}")
def gestor_delete_product(code: str):
    global DB_PRODUTOS
    DB_PRODUTOS = [p for p in DB_PRODUTOS if p["codigo"] != code]
    return {"mensagem": "Produto excluído"}


@app.get("/api/produtos/destaques")
def produtos_destaques():
    resultado = []
    for p in DB_PRODUTOS:
        empresa = next(
            (e for e in DB_EMPRESAS if e["id"] == p["empresa_id"]), {}
        )
        resultado.append(
            {
                "id": p["id"],
                "nome": p["nome"],
                "preco": p["preco"],
                "foto": p["foto"],
                "empresa_id": p["empresa_id"],
                "empresa_nome": empresa.get("nome_fantasia", "Loja"),
                "empresa_img": empresa.get("qrcode_imagem", ""),
                "categoria_empresa": empresa.get("plano", "geral"),
            }
        )
    return resultado


@app.get("/api/clients")
def gestor_clients(empresa_id: int = 1):
    return [c for c in DB_CLIENTES if c["empresa_id"] == empresa_id]


@app.post("/api/clients", status_code=status.HTTP_201_CREATED)
def gestor_create_client(cliente: ClientCreate):
    novo_id = len(DB_CLIENTES) + 1
    novo = cliente.model_dump()
    novo["id"] = novo_id
    DB_CLIENTES.append(novo)
    return novo


@app.put("/api/clients/{client_id}")
def gestor_update_client(client_id: int, cliente: ClientCreate):
    for c in DB_CLIENTES:
        if c["id"] == client_id:
            c.update(cliente.model_dump())
            return c
    raise HTTPException(status_code=404, detail="Cliente não encontrado")


@app.delete("/api/clients/{client_id}")
def gestor_delete_client(client_id: int):
    global DB_CLIENTES
    DB_CLIENTES = [c for c in DB_CLIENTES if c["id"] != client_id]
    return {"mensagem": "Cliente excluído"}


@app.get("/api/colaboradores")
def gestor_colaboradores(empresa_id: int = 1):
    return [cb for cb in DB_COLABORADORES if cb["empresa_id"] == empresa_id]


@app.post("/api/colaboradores", status_code=status.HTTP_201_CREATED)
def gestor_create_colab(colab: ColaboradorCreate):
    novo_id = len(DB_COLABORADORES) + 1
    novo = colab.model_dump()
    novo["id"] = novo_id
    DB_COLABORADORES.append(novo)
    return novo


@app.put("/api/colaboradores/{colab_id}")
def gestor_update_colab(colab_id: int, colab: ColaboradorCreate):
    for cb in DB_COLABORADORES:
        if cb["id"] == colab_id:
            cb.update(colab.model_dump())
            return cb
    raise HTTPException(status_code=404, detail="Colaborador não encontrado")


@app.delete("/api/colaboradores/{colab_id}")
def gestor_delete_colab(colab_id: int):
    global DB_COLABORADORES
    DB_COLABORADORES = [cb for cb in DB_COLABORADORES if cb["id"] != colab_id]
    return {"mensagem": "Colaborador excluído"}


@app.get("/api/ouvidoria")
def gestor_ouvidoria(empresa_id: int = 1):
    return [o for o in DB_OUVIDORIA if o["empresa_id"] == empresa_id]


@app.post("/api/ouvidoria", status_code=status.HTTP_201_CREATED)
def gestor_create_ouvidoria(ouvidoria: OuvidoriaCreate):
    novo_id = len(DB_OUVIDORIA) + 1
    novo = ouvidoria.model_dump()
    novo["id"] = novo_id
    novo["data"] = datetime.now().strftime("%d/%m/%Y")
    DB_OUVIDORIA.append(novo)
    return novo


@app.get("/api/ouvidoria/estatisticas")
def ouvidoria_estatisticas(empresa_id: int = 1):
    return {"otimo": 10, "bom": 5, "regular": 2, "ruim": 1, "pessimo": 0}


@app.get("/api/helpdesk")
def gestor_helpdesk(empresa_id: int = 1):
    return [h for h in DB_HELPDESK if h["empresa_id"] == empresa_id]


@app.post("/api/helpdesk", status_code=status.HTTP_201_CREATED)
def gestor_create_helpdesk(helpdesk: HelpdeskCreate):
    novo_id = len(DB_HELPDESK) + 1
    novo = helpdesk.model_dump()
    novo["id"] = novo_id
    novo["status"] = "aberto"
    novo["tecnico_responsavel"] = "Aguardando atribuição"
    novo["data"] = datetime.now().strftime("%d/%m/%Y")
    empresa = next(
        (e for e in DB_EMPRESAS if e["id"] == helpdesk.empresa_id), {}
    )
    novo["empresa"] = empresa.get("nome_fantasia", "Loja")
    DB_HELPDESK.append(novo)
    return novo


@app.get("/api/configuracoes")
def gestor_configuracoes(empresa_id: int = 1):
    return DB_CONFIGURACOES.get(empresa_id, {})


@app.put("/api/configuracoes")
def gestor_update_configuracoes(config: ConfiguracaoUpdate, empresa_id: int = 1):
    dados = config.model_dump(exclude_unset=True)
    if empresa_id not in DB_CONFIGURACOES:
        DB_CONFIGURACOES[empresa_id] = {}
    DB_CONFIGURACOES[empresa_id].update(dados)
    return DB_CONFIGURACOES[empresa_id]


@app.post("/api/backup")
def gestor_backup():
    return {"mensagem": "Backup realizado com sucesso no Neon DB"}


# ================= ROTAS ENTREGADOR E HUB =================
@app.post("/api/auth/entregador/cadastro", status_code=status.HTTP_201_CREATED)
def entregador_cadastro(entregador: EntregadorCreate):
    novo_id = len(DB_ENTREGADORES) + 1
    novo = entregador.model_dump()
    novo["id"] = novo_id
    novo["status"] = "Disponível"
    novo["total_entregas"] = 0
    novo["empresa_id"] = 1
    DB_ENTREGADORES.append(novo)
    return novo


@app.post("/api/auth/entregador")
def entregador_login(auth: EntregadorAuth):
    for ent in DB_ENTREGADORES:
        if ent["telefone"] == auth.telefone:
            return ent
    raise HTTPException(status_code=404, detail="Entregador não encontrado")


@app.put("/api/entregador/status")
def entregador_status(dados: dict):
    ent_id = dados.get("entregador_id")
    novo_status = dados.get("status")
    for ent in DB_ENTREGADORES:
        if ent["id"] == ent_id:
            ent["status"] = novo_status
            return ent
    raise HTTPException(status_code=404, detail="Entregador não encontrado")


@app.get("/api/entregador/disponiveis")
def entregadores_disponiveis(empresa_id: int = 1):
    return [e for e in DB_ENTREGADORES if e["status"] == "Disponível"]


@app.get("/api/entregador/rotas")
def entregador_rotas(empresa_id: int = 1):
    return [
        p
        for p in DB_PEDIDOS
        if p["status"] == "Saiu para entrega"
        or p["status"] == "Aprovado / Preparando"
    ]


@app.post("/api/entregador/baixa")
def entregador_baixa(dados: dict):
    pedido_id = int(dados.get("pedido_id"))
    for p in DB_PEDIDOS:
        if p["id"] == pedido_id:
            p["status"] = "Entregue"
            return {"mensagem": "Baixa realizada com sucesso"}
    raise HTTPException(status_code=404, detail="Pedido não encontrado")


@app.get("/api/entregador/extrato")
def entregador_extrato(empresa_id: int = 1):
    return [
        {
            "id": p["id"],
            "cliente": p["cliente"],
            "endereco": p["endereco"],
            "data": p.get("data", datetime.now().strftime("%Y-%m-%d")),
            "hora": p["hora"],
            "taxa": 6.50,
        }
        for p in DB_PEDIDOS
        if p["status"] == "Entregue"
    ]


@app.get("/api/empresas")
def hub_empresas():
    return DB_EMPRESAS


@app.post("/api/orders", status_code=status.HTTP_201_CREATED)
def hub_criar_pedido(pedido: OrderCreate):
    novo_id = len(DB_PEDIDOS) + 101
    novo = pedido.model_dump()
    novo["id"] = novo_id
    if not novo.get("cliente"):
        novo["cliente"] = novo.get("cliente_nome", "Cliente")
    if not novo.get("total") and novo.get("valor_total"):
        novo["total"] = novo["valor_total"]
    if not novo.get("data"):
        novo["data"] = datetime.now().strftime("%Y-%m-%d")
    if not novo.get("hora"):
        novo["hora"] = datetime.now().strftime("%H:%M")
    novo["motoboy_id"] = None
    novo["motoboy_nome"] = None
    DB_PEDIDOS.append(novo)
    return novo


@app.get("/api/orders/{order_id}")
def hub_pedido_detalhe(order_id: int):
    for p in DB_PEDIDOS:
        if p["id"] == order_id:
            return p
    raise HTTPException(status_code=404, detail="Pedido não encontrado")
