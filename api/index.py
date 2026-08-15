import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI(title="DeliveryON API", description="API Serverless para Vercel + Neon DB")

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

class MasterAuth(BaseModel):
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

@app.post("/api/master/auth")
def master_login(auth: MasterAuth):
    SENHA_CORRETA = os.getenv("SENHA_MASTER", "master123")
    if auth.senha == SENHA_CORRETA:
        return {"autorizado": True, "token": "token_jwt_backinformatica_valido"}
    raise HTTPException(status_code=401, detail="Senha Master incorreta")

@app.get("/api/master/metrics")
def get_master_metrics(db=Depends(get_db)):
    cursor = db.cursor()
    
    # Conta total de clientes
    cursor.execute("SELECT COUNT(*) as total FROM empresas")
    total_clientes = cursor.fetchone()['total']
    
    # Consulta o tamanho real do banco de dados atual em bytes
    cursor.execute("SELECT pg_database_size(current_database()) as db_size;")
    db_bytes = cursor.fetchone()['db_size']
    
    # Converte os bytes para formato amigável (Ex: MB ou KB)
    if db_bytes < 1024 * 1024:
        db_size_str = f"{round(db_bytes / 1024, 2)} KB"
    elif db_bytes < 1024 * 1024 * 1024:
        db_size_str = f"{round(db_bytes / (1024 * 1024), 2)} MB"
    else:
        db_size_str = f"{round(db_bytes / (1024 * 1024 * 1024), 2)} GB"

    return {
        "db_disk_usage": db_size_str,  # Retorna o tamanho real medido no Neon DB
        "total_clientes": total_clientes,
        "mrr": f"R$ {total_clientes * 250},00"
    }

@app.get("/api/master/empresas")
def list_empresas(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id, nome_fantasia, cnpj, plano, status FROM empresas ORDER BY id DESC")
    return cursor.fetchall()

@app.post("/api/master/empresas")
def create_empresa(empresa: EmpresaCreate, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        query = """
            INSERT INTO empresas (razao_social, nome_fantasia, cnpj, responsavel, contato, email_admin, endereco, plano, vencimento, limite_usuarios, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'ativo') RETURNING id;
        """
        cursor.execute(query, (
            empresa.razao_social, empresa.nome_fantasia, empresa.cnpj, empresa.responsavel, 
            empresa.contato, empresa.email_admin, empresa.endereco, empresa.plano, 
            empresa.vencimento, empresa.limite_usuarios
        ))
        novo_id = cursor.fetchone()['id']
        db.commit()
        return {"mensagem": "Tenant criado com sucesso", "id": novo_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
