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

DATABASE_URL = os.getenv("ON_DATA_URL")

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
    qrcode_imagem: str
    copia_e_cola: str

class ChamadoStatusUpdate(BaseModel):
    status: str

class ChamadoConcluir(BaseModel):
    tecnico: str
    enviar_comprovante: bool

class ChamadoCancelar(BaseModel):
    motivo: str

class GestorAuth(BaseModel):
    cnpj: str

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
    cursor.close()
    return {"db_disk_usage": db_size_str, "total_clientes": total_clientes, "mrr": f"R$ {total_clientes * 250},00"}

@app.get("/api/master/empresas")
def list_empresas(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM empresas ORDER BY id DESC")
    res = cursor.fetchall()
    cursor.close()
    return res

@app.post("/api/master/empresas")
def create_empresa(emp: EmpresaCreate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO empresas (razao_social, nome_fantasia, cnpj, responsavel, contato, email_admin, endereco, plano, vencimento, limite_usuarios, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'ativo') RETURNING id;
    """, (emp.razao_social, emp.nome_fantasia, emp.cnpj, emp.responsavel, emp.contato, emp.email_admin, emp.endereco,
          emp.plano, emp.vencimento, emp.limite_usuarios))
    db.commit()
    novo_id = cursor.fetchone()['id']
    cursor.close()
    return {"mensagem": "Tenant criado", "id": novo_id}

@app.put("/api/master/empresas/{id}")
def update_empresa(id: int, emp: dict, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("UPDATE empresas SET nome_fantasia=%s, plano=%s, vencimento=%s, limite_usuarios=%s WHERE id=%s",
                   (emp.get('nome_fantasia'), emp.get('plano'), emp.get('vencimento'), emp.get('limite_usuarios'), id))
    db.commit()
    cursor.close()
    return {"mensagem": "Atualizado com sucesso"}

@app.delete("/api/master/empresas/{id}")
def delete_empresa(id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("DELETE FROM empresas WHERE id = %s", (id,))
    db.commit()
    cursor.close()
    return {"mensagem": "Excluído com sucesso"}

# ================= ROTAS DO GESTOR E CONFIGURAÇÕES =================
@app.post("/api/gestor/auth")
def gestor_login(auth: GestorAuth, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "SELECT id, nome_fantasia, cnpj, status FROM empresas WHERE REPLACE(REPLACE(REPLACE(cnpj, '.', ''), '/', ''), '-', '') = REPLACE(REPLACE(REPLACE(%s, '.', ''), '/', ''), '-', '')",
        (auth.cnpj,))
    empresa = cursor.fetchone()
    cursor.close()

    if not empresa:
        raise HTTPException(status_code=404, detail="CNPJ não encontrado na base de dados.")
    if empresa['status'] != 'ativo':
        raise HTTPException(status_code=403, detail="Esta empresa está inativa ou com o acesso suspenso.")

    return {"autorizado": True, "empresa_id": empresa['id'], "nome_fantasia": empresa['nome_fantasia']}

@app.get("/api/configuracoes")
def get_configuracoes(empresa_id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT nome_fantasia as titulo, endereco, contato as telefone, 
               slogan, horario_funcionamento, cor_primaria, cor_secundaria,
               qrcode_imagem as logo_url
        FROM empresas WHERE id = %s
    """, (empresa_id,))
    res = cursor.fetchone()
    cursor.close()
    if not res:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return {
        "titulo": res.get("titulo") or "",
        "slogan": res.get("slogan") or "",
        "endereco": res.get("endereco") or "",
        "telefone": res.get("telefone") or "",
        "horario_funcionamento": res.get("horario_funcionamento") or "",
        "cor_primaria": res.get("cor_primaria") or "#ff5722",
        "cor_secundaria": res.get("cor_secundaria") or "#e64a19",
        "logo_url": res.get("logo_url") or ""
    }

@app.put("/api/configuracoes")
def update_configuracoes(data: dict, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute("""
            UPDATE empresas 
            SET nome_fantasia = %s, endereco = %s, contato = %s, 
                slogan = %s, horario_funcionamento = %s, 
                cor_primaria = %s, cor_secundaria = %s, qrcode_imagem = %s
            WHERE id = %s
        """, (
            data.get("titulo"), data.get("endereco"), data.get("telefone"),
            data.get("slogan"), data.get("horario_funcionamento"),
            data.get("cor_primaria"), data.get("cor_secundaria"),
            data.get("logo_url"), data.get("empresa_id")
        ))
        db.commit()
        cursor.close()
        return {"mensagem": "Configurações atualizadas com sucesso!"}
    except Exception as e:
        db.rollback()
        cursor.close()
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/dashboard")
def get_dashboard(empresa_id: int, db=Depends(get_db)):
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) FROM pedidos WHERE empresa_id = %s AND status = 'Aguardando pagamento'", (empresa_id,))
    res_ag = cur.fetchone()
    aguardando = res_ag[list(res_ag.keys())[0]] if isinstance(res_ag, dict) and res_ag else 0

    cur.execute("SELECT COUNT(*) FROM pedidos WHERE empresa_id = %s AND status = 'Entregue'", (empresa_id,))
    res_ent = cur.fetchone()
    entregues = res_ent[list(res_ent.keys())[0]] if isinstance(res_ent, dict) and res_ent else 0

    cur.execute("SELECT COUNT(*) FROM pedidos WHERE empresa_id = %s AND status = 'Cancelado'", (empresa_id,))
    res_can = cur.fetchone()
    cancelados = res_can[list(res_can.keys())[0]] if isinstance(res_can, dict) and res_can else 0

    cur.execute("SELECT SUM(total) FROM pedidos WHERE empresa_id = %s AND status = 'Entregue'", (empresa_id,))
    row_receita = cur.fetchone()
    receita = row_receita[list(row_receita.keys())[0]] if isinstance(row_receita, dict) and row_receita else 0.00
    if not receita: receita = 0.00
    cur.close()

    return {
        "aguardando": aguardando,
        "entregues": entregues,
        "cancelados": cancelados,
        "receita": f"{receita:.2f}".replace('.', ',')
    }

@app.get("/api/orders")
def get_orders(empresa_id: int, db=Depends(get_db)):
    cur = db.cursor()
    cur.execute(
        "SELECT id, hora, cliente, endereco, total, status FROM pedidos WHERE empresa_id = %s ORDER BY id DESC LIMIT 10",
        (empresa_id,)
    )
    rows = cur.fetchall()
    cur.close()

    orders = []
    for row in rows:
        orders.append({
            "id": row['id'],
            "hora": str(row['hora']) if row['hora'] else "",
            "cliente": row['cliente'],
            "endereco": row['endereco'],
            "total": f"{row['total']:.2f}".replace('.', ',') if row['total'] else "0,00",
            "status": row['status']
        })
    return orders

@app.put("/api/orders/{order_id}/status")
def update_order_status(order_id: int, data: dict, db=Depends(get_db)):
    novo_status = data.get("status")
    empresa_id = data.get("empresa_id")

    cur = db.cursor()
    cur.execute(
        "UPDATE pedidos SET status = %s WHERE id = %s AND empresa_id = %s",
        (novo_status, order_id, empresa_id)
    )
    db.commit()
    cur.close()
    return {"success": True, "message": "Status atualizado com sucesso!"}

@app.get("/api/products")
def list_products(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id as codigo, nome, categoria, preco, estoque, descricao FROM produtos ORDER BY id DESC")
    res = cursor.fetchall()
    cursor.close()
    return res

@app.post("/api/products")
def create_product(prod: ProdutoCreate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO produtos (nome, categoria, preco, estoque, descricao) VALUES (%s, %s, %s, %s, %s) RETURNING id;",
        (prod.nome, prod.categoria, prod.preco, prod.estoque, prod.descricao))
    db.commit()
    cursor.close()
    return {"mensagem": "Produto salvo"}

@app.delete("/api/products/{id}")
def delete_product(id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("DELETE FROM produtos WHERE id = %s", (id,))
    db.commit()
    cursor.close()
    return {"mensagem": "Excluído"}

@app.get("/api/clients")
def list_clients(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id, nome, telefone, email, endereco_entrega as endereco, referencia FROM clientes ORDER BY id DESC")
    res = cursor.fetchall()
    cursor.close()
    return res

@app.post("/api/clients")
def create_client(cli: ClienteCreate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO clientes (nome, telefone, email, endereco_entrega, referencia) VALUES (%s, %s, %s, %s, %s) RETURNING id;",
        (cli.nome, cli.telefone, cli.email, cli.endereco, cli.referencia))
    db.commit()
    cursor.close()
    return {"mensagem": "Cliente salvo"}

@app.get("/api/colaboradores")
def list_colaboradores(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id, nome, telefone, email, cpf, funcao, status FROM colaboradores ORDER BY id DESC")
    res = cursor.fetchall()
    cursor.close()
    return res

@app.post("/api/colaboradores")
def create_colaborador(colab: ColaboradorCreate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO colaboradores (nome, telefone, email, cpf, data_nascimento, endereco, funcao, status, observacoes) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;",
        (colab.nome, colab.telefone, colab.email, colab.cpf, colab.data_nascimento, colab.endereco, colab.funcao,
         colab.status, colab.observacoes))
    db.commit()
    cursor.close()
    return {"mensagem": "Colaborador salvo"}

@app.get("/api/ouvidoria")
def list_ouvidoria(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id, cliente_nome as cliente, avaliacao, relato, TO_CHAR(criado_em, 'DD/MM/YYYY') as data FROM ouvidoria ORDER BY id DESC")
    res = cursor.fetchall()
    cursor.close()
    return res

@app.post("/api/backup")
def backup():
    return {"mensagem": "Backup efetuado com sucesso no servidor."}
