import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI(title="DeliveryON API", description="API Master e Admin - Vercel + Neon DB")

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

class EmpresaUpdate(BaseModel):
    nome_fantasia: str
    plano: str
    vencimento: int
    limite_usuarios: int

class AdminAuth(BaseModel):
    cnpj: str

@app.post("/api/master/auth")
def master_login(auth: MasterAuth):
    SENHA_CORRETA = os.getenv("SENHA_MASTER", "master123")
    if auth.senha == SENHA_CORRETA:
        return {"autorizado": True, "token": "token_jwt_backinformatica_valido"}
    raise HTTPException(status_code=401, detail="Senha Master incorreta")

@app.get("/api/master/metrics")
def get_master_metrics(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM empresas")
    total_clientes = cursor.fetchone()['total']
    
    cursor.execute("SELECT pg_database_size(current_database()) as db_size;")
    db_bytes = cursor.fetchone()['db_size']
    if db_bytes < 1024 * 1024:
        db_size_str = f"{round(db_bytes / 1024, 2)} KB"
    elif db_bytes < 1024 * 1024 * 1024:
        db_size_str = f"{round(db_bytes / (1024 * 1024), 2)} MB"
    else:
        db_size_str = f"{round(db_bytes / (1024 * 1024 * 1024), 2)} GB"

    return {
        "db_disk_usage": db_size_str,
        "total_clientes": total_clientes,
        "mrr": f"R$ {total_clientes * 250},00"
    }

@app.get("/api/master/empresas")
def list_empresas(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id, razao_social, nome_fantasia, cnpj, responsavel, contato, email_admin, plano, vencimento, limite_usuarios, status FROM empresas ORDER BY id DESC")
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

@app.put("/api/master/empresas/{empresa_id}")
def update_empresa(empresa_id: int, empresa: EmpresaUpdate, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        query = """
            UPDATE empresas SET nome_fantasia = %s, plano = %s, vencimento = %s, limite_usuarios = %s
            WHERE id = %s;
        """
        cursor.execute(query, (empresa.nome_fantasia, empresa.plano, empresa.vencimento, empresa.limite_usuarios, empresa_id))
        db.commit()
        return {"mensagem": "Empresa atualizada com sucesso"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.patch("/api/master/empresas/{empresa_id}/status")
def toggle_status_empresa(empresa_id: int, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute("SELECT status FROM empresas WHERE id = %s", (empresa_id,))
        emp = cursor.fetchone()
        if not emp:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        
        novo_status = 'bloqueado' if emp['status'] == 'ativo' else 'ativo'
        cursor.execute("UPDATE empresas SET status = %s WHERE id = %s", (novo_status, empresa_id))
        db.commit()
        return {"mensagem": f"Status alterado para {novo_status}", "status": novo_status}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/master/empresas/{empresa_id}/carimbar-pagamento")
def carimbar_pagamento(empresa_id: int, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute("SELECT nome_fantasia FROM empresas WHERE id = %s", (empresa_id,))
        emp = cursor.fetchone()
        if not emp:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        db.commit()
        return {"mensagem": f"Pagamento da empresa {emp['nome_fantasia']} carimbado e validado com sucesso!"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/master/empresas/{empresa_id}")
def delete_empresa(empresa_id: int, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM empresas WHERE id = %s", (empresa_id,))
        db.commit()
        return {"mensagem": "Empresa excluída com sucesso"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/admin/login")
def admin_login(auth: AdminAuth, db=Depends(get_db)):
    cursor = db.cursor()
    cnpj_limpo = ''.join(filter(str.isdigit, auth.cnpj))
    cursor.execute("SELECT id, nome_fantasia, status FROM empresas WHERE REPLACE(REPLACE(REPLACE(cnpj, '.', ''), '/', ''), '-', '') = %s", (cnpj_limpo,))
    empresa = cursor.fetchone()
    
    if not empresa:
        raise HTTPException(status_code=404, detail="CNPJ não encontrado. Verifique com o suporte Master.")
    if empresa['status'] != 'ativo':
        raise HTTPException(status_code=403, detail="Esta empresa está temporariamente bloqueada.")
        
    return {"autorizado": True, "empresa": empresa['nome_fantasia'], "id": empresa['id']}
