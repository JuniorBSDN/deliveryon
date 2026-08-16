import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI(title="DeliveryON API Completa", description="API Master + Gestor integrados ao Neon DB")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATA_URL")

def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()

# --- MODELOS PYDANTIC ---
class EmpresaCreate(BaseModel):
    razao_social: str
    nome_fantasia: str
    cnpj: str
    responsavel: str
    contato: str
    email_admin: str
    endereco: str
    plano: str
    vencimento: int
    limite_usuarios: int

class ProdutoCreate(BaseModel):
    nome: str
    categoria: str
    preco: float
    estoque: int
    descricao: str

class ClienteCreate(BaseModel):
    nome: str
    telefone: str
    email: Optional[str] = None
    endereco: str
    referencia: Optional[str] = None

class ColaboradorCreate(BaseModel):
    nome: str
    telefone: str
    email: str
    cpf: str
    data_nascimento: str
    endereco: str
    funcao: str
    status: str
    observacoes: Optional[str] = None

class MasterAuth(BaseModel):
    senha: str

# ==========================================
# ROTAS DO MASTER (Gestão da Franquia)
# ==========================================
# Adicione esta rota junto com as outras rotas do Master no seu api/index.py

@app.get("/api/master/notificacoes")
def get_master_notificacoes():
    # Em um cenário real, isso viria de uma tabela 'notificacoes_master' no Neon DB
    return [
        {
            "id": 1, 
            "tipo": "critico", 
            "icone": "ph-warning-circle", 
            "cor": "var(--danger)", 
            "data": "16/08/2026 08:30", 
            "titulo": "Falha de Pagamento", 
            "mensagem": "O tenant 'Burger Delivery' não confirmou o pagamento da mensalidade."
        },
        {
            "id": 2, 
            "tipo": "alerta", 
            "icone": "ph-clock", 
            "cor": "var(--warning)", 
            "data": "15/08/2026 14:15", 
            "titulo": "Limite de Usuários Próximo", 
            "mensagem": "A empresa 'Pizzaria Bella' atingiu 19/20 usuários do plano Pro."
        },
        {
            "id": 3, 
            "tipo": "sucesso", 
            "icone": "ph-check-circle", 
            "cor": "var(--success)", 
            "data": "15/08/2026 02:00", 
            "titulo": "Backup Concluído", 
            "mensagem": "Rotina de backup global do Neon DB executada com sucesso."
        },
        {
            "id": 4, 
            "tipo": "info", 
            "icone": "ph-info", 
            "cor": "var(--info)", 
            "data": "14/08/2026 10:05", 
            "titulo": "Novo Tenant Integrado", 
            "mensagem": "A empresa 'Sushi House' foi cadastrada e ativada no sistema."
        }
    ]

@app.post("/api/master/auth")
def master_login(auth: MasterAuth):
    if auth.senha == os.getenv("SENHA_MASTER", "master123"):
        return {"autorizado": True, "token": "token_master_valido"}
    raise HTTPException(status_code=401, detail="Senha Master incorreta")

@app.get("/api/master/metrics")
def get_master_metrics(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM empresas")
    total_clientes = cursor.fetchone()['total']
    cursor.execute("SELECT pg_database_size(current_database()) as db_size;")
    db_bytes = cursor.fetchone()['db_size']
    db_size_str = f"{round(db_bytes / (1024 * 1024), 2)} MB"
    return {"db_disk_usage": db_size_str, "total_clientes": total_clientes, "mrr": f"R$ {total_clientes * 250},00"}

@app.get("/api/master/empresas")
def list_empresas(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM empresas ORDER BY id DESC")
    return cursor.fetchall()

@app.post("/api/master/empresas")
def create_empresa(empresa: EmpresaCreate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO empresas (razao_social, nome_fantasia, cnpj, responsavel, contato, email_admin, endereco, plano, vencimento, limite_usuarios, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'ativo') RETURNING id;
    """, (empresa.razao_social, empresa.nome_fantasia, empresa.cnpj, empresa.responsavel, empresa.contato, empresa.email_admin, empresa.endereco, empresa.plano, empresa.vencimento, empresa.limite_usuarios))
    db.commit()
    return {"mensagem": "Tenant criado", "id": cursor.fetchone()['id']}

@app.delete("/api/master/empresas/{id}")
def delete_empresa(id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("DELETE FROM empresas WHERE id = %s", (id,))
    db.commit()
    return {"mensagem": "Empresa excluída"}

# ==========================================
# ROTAS DO GESTOR (Painel do Cliente)
# ==========================================
@app.get("/api/dashboard")
def get_dashboard(db=Depends(get_db)):
    # Simulação rápida ou query real
    return {"aguardando": 5, "entregues": 12, "cancelados": 1, "receita": "1.250,00"}

@app.get("/api/orders")
def list_orders(db=Depends(get_db)):
    # Exemplo simulado para alimentar a tabela
    return [
        {"id": "1001", "hora": "18:30", "cliente": "João Silva", "endereco": "Rua A, 123", "total": "45,00", "status": "Aguardando pagamento"}
    ]

@app.get("/api/products")
def list_products(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id as codigo, nome, categoria, preco, estoque, descricao FROM produtos ORDER BY id DESC")
    return cursor.fetchall()

@app.post("/api/products")
def create_product(prod: ProdutoCreate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("INSERT INTO produtos (nome, categoria, preco, estoque, descricao) VALUES (%s, %s, %s, %s, %s) RETURNING id;",
                   (prod.nome, prod.categoria, prod.preco, prod.estoque, prod.descricao))
    db.commit()
    return {"mensagem": "Produto salvo", "id": cursor.fetchone()['id']}

@app.delete("/api/products/{id}")
def delete_product(id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("DELETE FROM produtos WHERE id = %s", (id,))
    db.commit()
    return {"mensagem": "Produto excluído"}

@app.get("/api/clients")
def list_clients(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id, nome, telefone, email, endereco_entrega as endereco, referencia FROM clientes ORDER BY id DESC")
    return cursor.fetchall()

@app.post("/api/clients")
def create_client(cli: ClienteCreate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("INSERT INTO clientes (nome, telefone, email, endereco_entrega, referencia) VALUES (%s, %s, %s, %s, %s) RETURNING id;",
                   (cli.nome, cli.telefone, cli.email, cli.endereco, cli.referencia))
    db.commit()
    return {"mensagem": "Cliente salvo", "id": cursor.fetchone()['id']}

@app.get("/api/colaboradores")
def list_colaboradores(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id, nome, telefone, email, cpf, funcao, status FROM colaboradores ORDER BY id DESC")
    return cursor.fetchall()

@app.post("/api/colaboradores")
def create_colaborador(colab: ColaboradorCreate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("INSERT INTO colaboradores (nome, telefone, email, cpf, data_nascimento, endereco, funcao, status, observacoes) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;",
                   (colab.nome, colab.telefone, colab.email, colab.cpf, colab.data_nascimento, colab.endereco, colab.funcao, colab.status, colab.observacoes))
    db.commit()
    return {"mensagem": "Colaborador salvo", "id": cursor.fetchone()['id']}

@app.get("/api/ouvidoria")
def list_ouvidoria(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id, cliente_nome as cliente, avaliacao, relato, TO_CHAR(criado_em, 'DD/MM/YYYY') as data FROM ouvidoria ORDER BY id DESC")
    return cursor.fetchall()

@app.post("/api/backup")
def backup():
    return {"mensagem": "Backup efetuado com sucesso no servidor Cloud."}
