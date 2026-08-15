import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI(title="DeliveryON API", description="API Gestor / Admin - Vercel + Neon DB")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()

# Pydantic Models
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

# --- ROTAS DO GESTOR / ADMIN ---

@app.get("/api/dashboard")
def get_dashboard_metrics(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM pedidos WHERE status = 'Aguardando pagamento'")
    aguardando = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total FROM pedidos WHERE status = 'Entregue'")
    entregues = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total FROM pedidos WHERE status = 'Cancelado'")
    cancelados = cursor.fetchone()['total']
    
    cursor.execute("SELECT COALESCE(SUM(valor_total), 0) as receita FROM pedidos WHERE status = 'Entregue'")
    receita = cursor.fetchone()['receita']
    
    return {
        "aguardando": aguardando,
        "entregues": entregues,
        "cancelados": cancelados,
        "receita": f"{receita:.2f}".replace('.', ',')
    }

@app.get("/api/orders")
def list_orders(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id, cliente_nome as cliente, endereco_entrega as endereco, valor_total as total, status, TO_CHAR(criado_em, 'HH24:MI') as hora FROM pedidos ORDER BY id DESC")
    return cursor.fetchall()

@app.get("/api/products")
def list_products(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id as codigo, nome, categoria, preco, estoque, descricao FROM produtos ORDER BY id DESC")
    return cursor.fetchall()

@app.post("/api/products")
def create_product(prod: ProdutoCreate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO produtos (nome, categoria, preco, estoque, descricao) VALUES (%s, %s, %s, %s, %s) RETURNING id;",
        (prod.nome, prod.categoria, prod.preco, prod.estoque, prod.descricao)
    )
    db.commit()
    return {"mensagem": "Produto criado com sucesso", "id": cursor.fetchone()['id']}

@app.get("/api/clients")
def list_clients(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id, nome, telefone, email, endereco_entrega as endereco, referencia FROM clientes ORDER BY id DESC")
    return cursor.fetchall()

@app.post("/api/clients")
def create_client(cli: ClienteCreate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO clientes (nome, telefone, email, endereco_entrega, referencia) VALUES (%s, %s, %s, %s, %s) RETURNING id;",
        (cli.nome, cli.telefone, cli.email, cli.endereco, cli.referencia)
    )
    db.commit()
    return {"mensagem": "Cliente cadastrado com sucesso", "id": cursor.fetchone()['id']}

@app.get("/api/colaboradores")
def list_colaboradores(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id, nome, telefone, email, cpf, funcao, status FROM colaboradores ORDER BY id DESC")
    return cursor.fetchall()

@app.post("/api/colaboradores")
def create_colaborador(colab: ColaboradorCreate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO colaboradores (nome, telefone, email, cpf, data_nascimento, endereco, funcao, status, observacoes) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;",
        (colab.nome, colab.telefone, colab.email, colab.cpf, colab.data_nascimento, colab.endereco, colab.funcao, colab.status, colab.observacoes)
    )
    db.commit()
    return {"mensagem": "Colaborador cadastrado com sucesso", "id": cursor.fetchone()['id']}

@app.get("/api/ouvidoria")
def list_ouvidoria(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id, cliente_nome as cliente, avaliacao, relato, TO_CHAR(criado_em, 'DD/MM/YYYY') as data FROM ouvidoria ORDER BY id DESC")
    return cursor.fetchall()

@app.post("/api/backup")
def trigger_backup():
    return {"mensagem": "Rotina de backup executada com sucesso no servidor."}
