import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

# Inicialização do App FastAPI
app = FastAPI(title="DeliveryON API", description="API Serverless para Vercel + Neon DB")

# Configuração de CORS (Permitir requisições do Front-end)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conexão com o Neon PostgreSQL (Variável de Ambiente configurada no Vercel)
DATABASE_URL = os.getenv("DATABASE_URL", "Sua_String_De_Conexao_Neon_Aqui")

def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()

# ==========================================
# SCHEMAS (Modelos de Validação de Dados JSON)
# ==========================================

class AuthLogin(BaseModel):
    email: str
    senha: str

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
    foto: str

class ColaboradorCreate(BaseModel):
    nome: str
    telefone: str
    email: str
    cpf: str
    nascimento: str
    endereco: str
    funcao: str
    status: str
    veiculo_tipo: Optional[str] = None
    veiculo_modelo: Optional[str] = None
    veiculo_placa: Optional[str] = None
    taxa_entrega: Optional[float] = None

class StatusUpdate(BaseModel):
    status: str

# ==========================================
# ENDPOINTS: MASTER (Gestão SaaS)
# ==========================================

@app.post("/api/master/auth")
def master_login(login: AuthLogin):
    # Lógica simples de autenticação (Deve ser aprimorada com hash/JWT)
    if login.email == "admin@master.com" and login.senha == "master123":
        return {"token": "token_jwt_master_valido", "role": "master"}
    raise HTTPException(status_code=401, detail="Credenciais Master Inválidas")

@app.get("/api/master/metrics")
def get_master_metrics(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM empresas")
    total_clientes = cursor.fetchone()['total']
    return {
        "db_disk_usage": "45%",
        "total_clientes": total_clientes,
        "mrr": f"R$ {total_clientes * 250},00" # Simulação de MRR
    }

@app.post("/api/master/empresas")
def create_empresa(empresa: EmpresaCreate, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        query = """
            INSERT INTO empresas (razao_social, nome_fantasia, cnpj, responsavel, contato, email_admin, endereco, plano, vencimento, limite_usuarios)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
        """
        cursor.execute(query, (empresa.razao_social, empresa.nome_fantasia, empresa.cnpj, empresa.responsavel, empresa.contato, empresa.email_admin, empresa.endereco, empresa.plano, empresa.vencimento, empresa.limite_usuarios))
        novo_id = cursor.fetchone()['id']
        db.commit()
        return {"mensagem": "Tenant criado com sucesso", "id": novo_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

# ==========================================
# ENDPOINTS: ADMIN (Gestão do Restaurante)
# ==========================================

@app.post("/api/admin/auth")
def admin_login(login: AuthLogin, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id, nome_fantasia FROM empresas WHERE email_admin = %s", (login.email,))
    empresa = cursor.fetchone()
    if empresa:
        # Pula validação real de senha neste exemplo base
        return {"token": "token_admin_valido", "empresa_id": empresa['id'], "nome": empresa['nome_fantasia']}
    raise HTTPException(status_code=401, detail="Acesso não autorizado")

@app.post("/api/admin/produtos")
def create_produto(produto: ProdutoCreate, db=Depends(get_db)):
    cursor = db.cursor()
    query = "INSERT INTO produtos (nome, categoria, preco, estoque, descricao, foto) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id"
    cursor.execute(query, (produto.nome, produto.categoria, produto.preco, produto.estoque, produto.descricao, produto.foto))
    db.commit()
    return {"id": cursor.fetchone()['id'], "status": "criado"}

@app.post("/api/admin/colaboradores")
def create_colaborador(colab: ColaboradorCreate, db=Depends(get_db)):
    cursor = db.cursor()
    query = """
        INSERT INTO colaboradores (nome, telefone, email, cpf, funcao, status, veiculo_placa, taxa_entrega)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
    """
    cursor.execute(query, (colab.nome, colab.telefone, colab.email, colab.cpf, colab.funcao, colab.status, colab.veiculo_placa, colab.taxa_entrega))
    db.commit()
    return {"id": cursor.fetchone()['id']}

# ==========================================
# ENDPOINTS: ENTREGADOR (App Motoboy)
# ==========================================

@app.get("/api/entregador/rotas")
def get_rotas_ativas(db=Depends(get_db)):
    # Simula busca de rotas ativas (Status: 'saiu_para_entrega')
    cursor = db.cursor()
    cursor.execute("SELECT * FROM pedidos WHERE status = 'saiu' ORDER BY id DESC")
    rotas = cursor.fetchall()
    return rotas

@app.put("/api/entregador/pedidos/{pedido_id}/status")
def update_pedido_status(pedido_id: int, payload: StatusUpdate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("UPDATE pedidos SET status = %s WHERE id = %s", (payload.status, pedido_id))
    db.commit()
    return {"mensagem": f"Pedido {pedido_id} marcado como {payload.status}"}

# ==========================================
# ENDPOINTS: CLIENTE (Cardápio App)
# ==========================================

@app.get("/api/produtos")
def list_produtos(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM produtos WHERE estoque > 0 ORDER BY categoria, nome")
    return cursor.fetchall()
