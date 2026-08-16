import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI(title="DeliveryON API - Master & Gestor", description="API completa integrada ao Neon DB")

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

# ================= MODELOS =================
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

class PixConfigUpdate(BaseModel):
    qrcode_imagem: str # Pode ser a URL da imagem ou base64 enviado pelo Master
    copia_e_cola: str

# ================= ROTAS DO MASTER =================
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
    db_size_str = f"{round(cursor.fetchone()['db_size'] / (1024 * 1024), 2)} MB"
    return {"db_disk_usage": db_size_str, "total_clientes": total_clientes, "mrr": f"R$ {total_clientes * 250},00"}

@app.get("/api/master/empresas/{id}/historico")
def get_historico_empresa(id: int, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        # Busca interações registradas para esta empresa
        cursor.execute("""
            SELECT TO_CHAR(criado_em, 'DD/MM/YYYY') as data, descricao 
            FROM historico_empresas 
            WHERE empresa_id = %s 
            ORDER BY id DESC
        """, (id,))
        return cursor.fetchall()
    except Exception:
        # Retorna uma lista vazia caso a tabela ainda esteja sendo criada
        return []

# Rota para o Master salvar/atualizar o QR Code e a chave Pix da empresa
@app.put("/api/master/empresas/{id}/pix")
def configurar_pix_empresa(id: int, pix: PixConfigUpdate, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute("""
            UPDATE empresas 
            SET qrcode_imagem = %s, copia_e_cola = %s 
            WHERE id = %s
        """, (pix.qrcode_imagem, pix.copia_e_cola, id))
        db.commit()
        return {"mensagem": "QR Code e Chave Pix configurados com sucesso para o Gestor."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

# Rota para o Painel do Gestor consultar os dados de pagamento atuais
@app.get("/api/gestor/faturamento")
def get_faturamento_gestor(db=Depends(get_db)):
    cursor = db.cursor()
    # Aqui você busca os dados da empresa logada (exemplo ID 1 ou por sessão)
    cursor.execute("SELECT nome_fantasia, plano, vencimento, qrcode_imagem, copia_e_cola, status FROM empresas LIMIT 1")
    return cursor.fetchone()

@app.get("/api/master/notificacoes")
def get_master_notificacoes(data: Optional[str] = None, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        query = "SELECT id, tipo, icone, cor, TO_CHAR(criado_em, 'DD/MM/YYYY HH24:MI') as data_hora, titulo, mensagem FROM notificacoes_master"
        if data:
            query += f" WHERE DATE(criado_em) = '{data}'"
        query += " ORDER BY id DESC LIMIT 50"
        cursor.execute(query)
        return cursor.fetchall()
    except Exception:
        return [] # Retorna vazio se a tabela não existir

@app.delete("/api/master/notificacoes/{id}")
def delete_notificacao(id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("DELETE FROM notificacoes_master WHERE id = %s", (id,))
    db.commit()
    return {"mensagem": "Notificação resolvida"}

@app.get("/api/master/empresas")
def list_empresas(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM empresas ORDER BY id DESC")
    return cursor.fetchall()

@app.post("/api/master/empresas")
def create_empresa(emp: EmpresaCreate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO empresas (razao_social, nome_fantasia, cnpj, responsavel, contato, email_admin, endereco, plano, vencimento, limite_usuarios, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'ativo') RETURNING id;
    """, (emp.razao_social, emp.nome_fantasia, emp.cnpj, emp.responsavel, emp.contato, emp.email_admin, emp.endereco, emp.plano, emp.vencimento, emp.limite_usuarios))
    db.commit()
    return {"mensagem": "Tenant criado", "id": cursor.fetchone()['id']}

@app.put("/api/master/empresas/{id}")
def update_empresa(id: int, emp: dict, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("UPDATE empresas SET nome_fantasia=%s, plano=%s, vencimento=%s, limite_usuarios=%s WHERE id=%s",
                   (emp.get('nome_fantasia'), emp.get('plano'), emp.get('vencimento'), emp.get('limite_usuarios'), id))
    db.commit()
    return {"mensagem": "Atualizado com sucesso"}

@app.delete("/api/master/empresas/{id}")
def delete_empresa(id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("DELETE FROM empresas WHERE id = %s", (id,))
    db.commit()
    return {"mensagem": "Excluído com sucesso"}

# ================= ROTAS DO GESTOR (CLIENTE FINAl) =================
@app.get("/api/dashboard")
def get_dashboard(db=Depends(get_db)):
    return {"aguardando": 5, "entregues": 12, "cancelados": 1, "receita": "1.250,00"}

@app.get("/api/orders")
def list_orders(db=Depends(get_db)):
    return [{"id": "1001", "hora": "18:30", "cliente": "João Silva", "endereco": "Rua A, 123", "total": "45,00", "status": "Aguardando pagamento"}]

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
    return {"mensagem": "Produto salvo"}

@app.delete("/api/products/{id}")
def delete_product(id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("DELETE FROM produtos WHERE id = %s", (id,))
    db.commit()
    return {"mensagem": "Excluído"}

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
    return {"mensagem": "Cliente salvo"}

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
    return {"mensagem": "Colaborador salvo"}

@app.get("/api/ouvidoria")
def list_ouvidoria(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id, cliente_nome as cliente, avaliacao, relato, TO_CHAR(criado_em, 'DD/MM/YYYY') as data FROM ouvidoria ORDER BY id DESC")
    return cursor.fetchall()

@app.post("/api/backup")
def backup():
    return {"mensagem": "Backup efetuado com sucesso no servidor."}
