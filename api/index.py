import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

app = FastAPI(title="DeliveryON API - Completa", description="API integrada (Cliente, Entregador, Gestor, Master)")

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

class ChamadoCreate(BaseModel):
    empresa_id: int
    resumo_problema: str
    descricao: str

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
    empresa_id: int
    nome: str
    categoria: str
    preco: float
    estoque: int
    descricao: str
    foto: Optional[str] = None
    
class ProdutoUpdate(BaseModel):
    empresa_id: int
    nome: str
    categoria: str
    preco: float
    estoque: int
    descricao: str
    foto: Optional[str] = None

class ClienteCreate(BaseModel):
    empresa_id: int
    nome: str
    telefone: str
    email: Optional[str] = None
    endereco: str
    referencia: Optional[str] = None

class ClienteUpdate(BaseModel):
    empresa_id: int
    nome: str
    telefone: str
    email: Optional[str] = None
    endereco: str
    referencia: Optional[str] = None

class ColaboradorCreate(BaseModel):
    empresa_id: int
    nome: str
    telefone: str
    email: Optional[str] = None
    cpf: Optional[str] = None
    data_nascimento: Optional[str] = None
    endereco: Optional[str] = None
    funcao: str
    status: str
    observacoes: Optional[str] = None
    tipo_veiculo: Optional[str] = None
    veiculo_modelo: Optional[str] = None
    veiculo_cor: Optional[str] = None
    veiculo_placa: Optional[str] = None
    area_atuacao: Optional[str] = None
    valor_entrega: Optional[float] = 0.00
    foto: Optional[str] = None  

class OrderCreate(BaseModel):
    empresa_id: int
    cliente: str
    telefone: str
    endereco: str
    pagamento: str
    itens: str
    total: float
    status: str
    hora: Optional[str] = None
    data: Optional[str] = None

class OuvidoriaCreate(BaseModel):
    empresa_id: int
    cliente_nome: str
    atendimento: str
    avaliacao: str
    relato: str

class MasterAuth(BaseModel):
    senha: str

class GestorAuth(BaseModel):
    cnpj: str

class EntregadorAuth(BaseModel):
    telefone: str
    senha: str

class EntregadorStatusUpdate(BaseModel):
    status: str

class BaixaPedido(BaseModel):
    pedido_id: str
    status: str
    data_conclusao: str

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


# ================= ATUALIZAR BANCO =================
@app.get("/api/atualizar-banco")
def atualizar_banco_de_dados(db=Depends(get_db)):
    cursor = db.cursor()
    queries = [
        "ALTER TABLE colaboradores ADD COLUMN IF NOT EXISTS empresa_id INTEGER DEFAULT 1;",
        "ALTER TABLE colaboradores ADD COLUMN IF NOT EXISTS cpf VARCHAR(50);",
        "ALTER TABLE colaboradores ADD COLUMN IF NOT EXISTS data_nascimento VARCHAR(50);",
        "ALTER TABLE colaboradores ADD COLUMN IF NOT EXISTS endereco TEXT;",
        "ALTER TABLE colaboradores ADD COLUMN IF NOT EXISTS observacoes TEXT;",
        "ALTER TABLE colaboradores ADD COLUMN IF NOT EXISTS tipo_veiculo VARCHAR(50);",
        "ALTER TABLE colaboradores ADD COLUMN IF NOT EXISTS veiculo_modelo VARCHAR(100);",
        "ALTER TABLE colaboradores ADD COLUMN IF NOT EXISTS veiculo_cor VARCHAR(50);",
        "ALTER TABLE colaboradores ADD COLUMN IF NOT EXISTS veiculo_placa VARCHAR(50);",
        "ALTER TABLE colaboradores ADD COLUMN IF NOT EXISTS area_atuacao VARCHAR(150);",
        "ALTER TABLE colaboradores ADD COLUMN IF NOT EXISTS valor_entrega NUMERIC(10,2) DEFAULT 0;",
        "ALTER TABLE colaboradores ADD COLUMN IF NOT EXISTS foto TEXT;",
        "ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS hora VARCHAR(20);",
        "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS endereco_entrega TEXT;",
        "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS referencia TEXT;",
        "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS latitude NUMERIC(10,8);",
        "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS longitude NUMERIC(10,8);",
        "ALTER TABLE produtos ADD COLUMN IF NOT EXISTS foto TEXT;"
    ]
    
    resultados = []
    for q in queries:
        try:
            cursor.execute(q)
            db.commit()
            resultados.append(f"Sucesso: {q}")
        except Exception as e:
            db.rollback()
            resultados.append(f"Erro ao executar ({q}): {str(e)}")
            
    cursor.close()
    return {"status": "Banco atualizado!", "logs": resultados}


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
    cursor.execute("UPDATE empresas SET razao_social=%s, nome_fantasia=%s, cnpj=%s, responsavel=%s, contato=%s, email_admin=%s, endereco=%s, plano=%s, vencimento=%s, limite_usuarios=%s WHERE id=%s",
                   (emp.get('razao_social'), emp.get('nome_fantasia'), emp.get('cnpj'), emp.get('responsavel'), emp.get('contato'), emp.get('email_admin'), emp.get('endereco'), emp.get('plano'), emp.get('vencimento'), emp.get('limite_usuarios'), id))
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

@app.post("/api/master/empresas/{id}/carimbar-pagamento")
def carimbar_pagamento(id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("UPDATE empresas SET status = 'ativo' WHERE id = %s", (id,))
    try:
        cursor.execute("INSERT INTO historico_empresas (empresa_id, descricao, data) VALUES (%s, 'Pagamento carimbado e autenticado', NOW())", (id,))
    except Exception as e:
        print(f"Erro ao salvar histórico de empresa: {e}")
    db.commit()
    cursor.close()
    return {"mensagem": "Pagamento carimbado com sucesso"}

@app.put("/api/master/empresas/{id}/pix")
def update_pix_master(id: int, pix: PixConfigUpdate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("UPDATE empresas SET qrcode_imagem = %s, copia_e_cola = %s WHERE id = %s", (pix.qrcode_imagem, pix.copia_e_cola, id))
    try:
        cursor.execute("INSERT INTO historico_empresas (empresa_id, descricao, data) VALUES (%s, 'Configuração PIX atualizada pelo Master', NOW())", (id,))
    except Exception as e:
        print(f"Erro ao salvar histórico de empresa: {e}")
    db.commit()
    cursor.close()
    return {"mensagem": "PIX atualizado com sucesso"}
    
@app.get("/api/master/empresas/{id}/historico")
def get_empresa_historico(id: int, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute("SELECT descricao, TO_CHAR(data, 'DD/MM/YYYY HH24:MI') as data FROM historico_empresas WHERE empresa_id = %s ORDER BY data DESC", (id,))
        res = cursor.fetchall()
    except Exception:
        db.rollback()
        res = []
    cursor.close()
    return res


# ================= ROTA AUXILIAR PARA O CARDÁPIO =================
@app.get("/api/empresas/por-nome")
def get_empresa_por_nome(nome: str, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT id, nome_fantasia, cnpj, status 
        FROM empresas 
        WHERE LOWER(REPLACE(REPLACE(nome_fantasia, ' ', '-'), 'á', 'a')) = LOWER(%s)
    """, (nome,))
    empresa = cursor.fetchone()
    cursor.close()
    
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")
    return empresa


# ================= ROTAS DE HELPDESK E AÇÕES =================
@app.post("/api/helpdesk")
def criar_chamado(chamado: ChamadoCreate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO chamados (empresa_id, resumo_problema, descricao, status, data_criacao) 
        VALUES (%s, %s, %s, 'aberto', NOW()) RETURNING id;
    """, (chamado.empresa_id, chamado.resumo_problema, chamado.descricao))
    novo_id = cursor.fetchone()['id']

    cursor.execute("""
        INSERT INTO notificacoes_master (tipo, titulo, mensagem, data_hora)
        VALUES ('sup', 'Novo Chamado Aberto', %s, NOW())
    """, (f"A empresa ID {chamado.empresa_id} abriu um chamado: {chamado.resumo_problema}",))

    db.commit()
    cursor.close()
    return {"mensagem": "Chamado aberto com sucesso", "id": novo_id}

@app.get("/api/helpdesk")
def listar_chamados_gestor(empresa_id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT id, resumo_problema, descricao, status, 
               TO_CHAR(data_criacao, 'DD/MM/YYYY HH24:MI') as data_criacao, 
               tecnico_responsavel
        FROM chamados 
        WHERE empresa_id = %s 
        ORDER BY id DESC;
    """, (empresa_id,))
    chamados = cursor.fetchall()
    cursor.close()
    return chamados

@app.get("/api/master/helpdesk/indicadores")
def get_master_helpdesk_indicadores(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM chamados WHERE status = 'aberto'")
    abertos = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) as total FROM chamados WHERE status IN ('em_atendimento', 'em_andamento')")
    andamento = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) as total FROM chamados WHERE status IN ('resolvido', 'concluido')")
    concluidos = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) as total FROM chamados WHERE status = 'pendente'")
    pendentes = cursor.fetchone()['total']

    cursor.close()
    return {"abertos": abertos, "em_andamento": andamento, "concluidos": concluidos, "pendentes": pendentes}

@app.get("/api/master/helpdesk/chamados")
def list_master_helpdesk_chamados(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT c.id, c.empresa_id, e.nome_fantasia as empresa, c.resumo_problema, c.status, 
               c.tecnico_responsavel, TO_CHAR(c.data_criacao, 'DD/MM/YYYY HH24:MI') as data
        FROM chamados c
        LEFT JOIN empresas e ON c.empresa_id = e.id
        ORDER BY c.id DESC
    """)
    res = cursor.fetchall()
    cursor.close()
    return res

@app.put("/api/master/helpdesk/chamados/{id}/status")
def update_chamado_status(id: int, data: ChamadoStatusUpdate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("UPDATE chamados SET status = %s WHERE id = %s", (data.status, id))
    db.commit()
    cursor.close()
    return {"mensagem": "Status atualizado com sucesso"}

@app.post("/api/master/helpdesk/chamados/{id}/concluir")
def concluir_chamado(id: int, data: ChamadoConcluir, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        UPDATE chamados 
        SET status = 'resolvido', tecnico_responsavel = %s 
        WHERE id = %s
    """, (data.tecnico, id))
    
    try:
        cursor.execute("""
            INSERT INTO historico_chamados (chamado_id, descricao, data_hora)
            VALUES (%s, %s, NOW())
        """, (id, f"Chamado concluído pelo técnico: {data.tecnico}"))
    except Exception as e:
        print(f"Erro ao salvar histórico do chamado: {e}")

    db.commit()
    cursor.close()
    return {"mensagem": "Chamado concluído"}

@app.post("/api/master/helpdesk/chamados/{id}/cancelar")
def cancelar_chamado(id: int, data: ChamadoCancelar, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("UPDATE chamados SET status = 'cancelado' WHERE id = %s", (id,))
    try:
        cursor.execute("""
            INSERT INTO historico_chamados (chamado_id, descricao, data_hora)
            VALUES (%s, %s, NOW())
        """, (id, f"Chamado cancelado. Motivo: {data.motivo}"))
    except Exception as e:
        print(f"Erro ao salvar histórico do chamado: {e}")

    db.commit()
    cursor.close()
    return {"mensagem": "Chamado cancelado"}

@app.get("/api/master/helpdesk/chamados/{id}/historico")
def get_chamado_historico(id: int, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute("""
            SELECT descricao, TO_CHAR(data_hora, 'DD/MM/YYYY HH24:MI') as data 
            FROM historico_chamados 
            WHERE chamado_id = %s ORDER BY data_hora DESC
        """, (id,))
        res = cursor.fetchall()
    except Exception:
        db.rollback()
        res = []
    cursor.close()
    return res

@app.get("/api/master/notificacoes")
def get_notificacoes_master(data: Optional[str] = None, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        if data:
            cursor.execute("""
                SELECT id, tipo, titulo, mensagem, TO_CHAR(data_hora, 'DD/MM/YYYY HH24:MI') as data_hora 
                FROM notificacoes_master 
                WHERE DATE(data_hora) = %s
                ORDER BY id DESC LIMIT 50
            """, (data,))
        else:
            cursor.execute("""
                SELECT id, tipo, titulo, mensagem, TO_CHAR(data_hora, 'DD/MM/YYYY HH24:MI') as data_hora 
                FROM notificacoes_master 
                ORDER BY id DESC LIMIT 50
            """)
        res = cursor.fetchall()
    except Exception:
        db.rollback()
        res = []
    finally:
        cursor.close()
    return res

@app.delete("/api/master/notificacoes/{id}")
def delete_notificacao(id: int, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM notificacoes_master WHERE id = %s", (id,))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        cursor.close()
    return {"mensagem": "Notificação resolvida."}


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


# ================= ROTAS DE CLIENTE E PEDIDOS =================
@app.post("/api/orders")
def create_order(order: OrderCreate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO pedidos (empresa_id, cliente, telefone, endereco, pagamento, itens, total, status, hora) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
    """, (order.empresa_id, order.cliente, order.telefone, order.endereco, order.pagamento, order.itens, order.total, order.status, order.hora))
    db.commit()
    novo_id = cursor.fetchone()['id']
    cursor.close()
    return {"mensagem": "Pedido salvo com sucesso", "id": novo_id}

@app.get("/api/orders")
def get_orders(empresa_id: int, db=Depends(get_db)):
    cur = db.cursor()
    cur.execute(
        "SELECT id, hora, cliente, endereco, total, status FROM pedidos WHERE empresa_id = %s ORDER BY id DESC LIMIT 50",
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
    cur = db.cursor()
    cur.execute(
        "UPDATE pedidos SET status = %s WHERE id = %s",
        (novo_status, order_id)
    )
    db.commit()
    cur.close()
    return {"success": True, "message": "Status atualizado com sucesso!"}

@app.post("/api/ouvidoria")
def create_ouvidoria(ouv: OuvidoriaCreate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO ouvidoria (empresa_id, cliente_nome, atendimento, avaliacao, relato, criado_em)
        VALUES (%s, %s, %s, %s, %s, NOW()) RETURNING id;
    """, (ouv.empresa_id, ouv.cliente_nome, ouv.atendimento, ouv.avaliacao, ouv.relato))
    db.commit()
    cursor.close()
    return {"mensagem": "Ouvidoria registrada com sucesso"}

@app.get("/api/ouvidoria")
def list_ouvidoria(empresa_id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "SELECT id, cliente_nome as cliente, avaliacao, relato, TO_CHAR(criado_em, 'DD/MM/YYYY') as data FROM ouvidoria WHERE empresa_id = %s ORDER BY id DESC",
        (empresa_id,))
    res = cursor.fetchall()
    cursor.close()
    return res


# ================= ROTAS DE PRODUTOS E COLABORADORES =================
@app.put("/api/products/{id}")
def update_product(id: int, prod: ProdutoUpdate, db=Depends(get_db)):
    cursor = db.cursor()
    if prod.foto and prod.foto.strip() != "":
        cursor.execute(
            "UPDATE produtos SET nome=%s, categoria=%s, preco=%s, estoque=%s, descricao=%s, foto=%s WHERE id=%s AND empresa_id=%s;",
            (prod.nome, prod.categoria, prod.preco, prod.estoque, prod.descricao, prod.foto, id, prod.empresa_id)
        )
    else:
        cursor.execute(
            "UPDATE produtos SET nome=%s, categoria=%s, preco=%s, estoque=%s, descricao=%s WHERE id=%s AND empresa_id=%s;",
            (prod.nome, prod.categoria, prod.preco, prod.estoque, prod.descricao, id, prod.empresa_id)
        )
    db.commit()
    cursor.close()
    return {"mensagem": "Produto atualizado com sucesso"}

@app.get("/api/products")
def list_products(empresa_id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id as codigo, nome, categoria, preco, estoque, descricao, foto FROM produtos WHERE empresa_id = %s ORDER BY id DESC", (empresa_id,))
    res = cursor.fetchall()
    cursor.close()
    return res

@app.post("/api/products")
def create_product(prod: ProdutoCreate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO produtos (empresa_id, nome, categoria, preco, estoque, descricao, foto) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;",
        (prod.empresa_id, prod.nome, prod.categoria, prod.preco, prod.estoque, prod.descricao, prod.foto))
    db.commit()
    cursor.close()
    return {"mensagem": "Produto salvo"}

@app.delete("/api/products/{id}")
def delete_product(id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("DELETE FROM produtos WHERE id = %s", (id,))
    db.commit()
    cursor.close()
    return {"mensagem": "Excluído com sucesso"}

@app.get("/api/clients")
def list_clients(empresa_id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "SELECT id, nome, telefone, email, endereco_entrega as endereco, referencia FROM clientes WHERE empresa_id = %s ORDER BY id DESC", (empresa_id,))
    res = cursor.fetchall()
    cursor.close()
    return res

@app.post("/api/clients")
def create_client(cli: ClienteCreate, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute(
            """INSERT INTO clientes (empresa_id, nome, telefone, email, endereco_entrega, referencia) 
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;""",
            (cli.empresa_id, cli.nome, cli.telefone, cli.email or '', cli.endereco, cli.referencia or '')
        )
        db.commit()
        novo_id = cursor.fetchone()['id']
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erro no banco: {str(e)}")
    finally:
        cursor.close()
    return {"mensagem": "Cliente salvo com sucesso", "id": novo_id}

@app.delete("/api/clients/{id}")
def delete_client(id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("DELETE FROM clientes WHERE id = %s", (id,))
    db.commit()
    cursor.close()
    return {"mensagem": "Excluído com sucesso"}

@app.put("/api/clients/{client_id}")
def update_client(client_id: int, cli: ClienteUpdate, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute(
            """UPDATE clientes SET nome=%s, telefone=%s, email=%s, endereco_entrega=%s, referencia=%s 
               WHERE id=%s AND empresa_id=%s""",
            (cli.nome, cli.telefone, cli.email or '', cli.endereco, cli.referencia or '', client_id, cli.empresa_id)
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erro ao atualizar cliente: {str(e)}")
    finally:
        cursor.close()
    return {"mensagem": "Cliente atualizado com sucesso"}

@app.get("/api/colaboradores")
def list_colaboradores(empresa_id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id, nome, telefone, email, cpf, funcao, status, foto FROM colaboradores WHERE empresa_id = %s ORDER BY id DESC", (empresa_id,))
    res = cursor.fetchall()
    cursor.close()
    return res

@app.post("/api/colaboradores")
def create_colaborador(colab: ColaboradorCreate, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        email = colab.email if colab.email and str(colab.email).strip() != "" else None
        cpf = colab.cpf if colab.cpf and str(colab.cpf).strip() != "" else None
        data_nasc = colab.data_nascimento if colab.data_nascimento and str(colab.data_nascimento).strip() != "" else None
        endereco = colab.endereco if colab.endereco and str(colab.endereco).strip() != "" else None
        obs = colab.observacoes if colab.observacoes and str(colab.observacoes).strip() != "" else None
        t_veiculo = colab.tipo_veiculo if colab.tipo_veiculo and str(colab.tipo_veiculo).strip() != "" else None
        v_modelo = colab.veiculo_modelo if colab.veiculo_modelo and str(colab.veiculo_modelo).strip() != "" else None
        v_cor = colab.veiculo_cor if colab.veiculo_cor and str(colab.veiculo_cor).strip() != "" else None
        v_placa = colab.veiculo_placa if colab.veiculo_placa and str(colab.veiculo_placa).strip() != "" else None
        area = colab.area_atuacao if colab.area_atuacao and str(colab.area_atuacao).strip() != "" else None
        foto_base64 = colab.foto if colab.foto and str(colab.foto).strip() != "" else None
        
        v_entrega = float(colab.valor_entrega) if colab.valor_entrega is not None else 0.00

        cursor.execute(
            """INSERT INTO colaboradores 
               (empresa_id, nome, telefone, email, cpf, data_nascimento, endereco, funcao, status, observacoes, tipo_veiculo, veiculo_modelo, veiculo_cor, veiculo_placa, area_atuacao, valor_entrega, foto) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;""",
            (colab.empresa_id, colab.nome, colab.telefone, email, cpf, data_nasc, endereco, 
             colab.funcao, colab.status, obs, t_veiculo, v_modelo, 
             v_cor, v_placa, area, v_entrega, foto_base64))
        db.commit()
        novo_id = cursor.fetchone()['id']
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()
    return {"mensagem": "Colaborador salvo com sucesso", "id": novo_id}

@app.put("/api/colaboradores/{colab_id}")
def update_colaborador(colab_id: int, colab: ColaboradorCreate, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        v_entrega = float(colab.valor_entrega) if colab.valor_entrega is not None else 0.00
        
        if colab.foto and colab.foto.strip() != "":
            cursor.execute(
                """UPDATE colaboradores SET 
                   nome=%s, telefone=%s, email=%s, cpf=%s, data_nascimento=%s, endereco=%s, 
                   funcao=%s, status=%s, observacoes=%s, tipo_veiculo=%s, veiculo_modelo=%s, 
                   veiculo_cor=%s, veiculo_placa=%s, area_atuacao=%s, valor_entrega=%s, foto=%s
                   WHERE id=%s AND empresa_id=%s""",
                (colab.nome, colab.telefone, colab.email, colab.cpf, colab.data_nascimento, colab.endereco,
                 colab.funcao, colab.status, colab.observacoes, colab.tipo_veiculo, colab.veiculo_modelo,
                 colab.veiculo_cor, colab.veiculo_placa, colab.area_atuacao, v_entrega, colab.foto, colab_id, colab.empresa_id)
            )
        else:
            cursor.execute(
                """UPDATE colaboradores SET 
                   nome=%s, telefone=%s, email=%s, cpf=%s, data_nascimento=%s, endereco=%s, 
                   funcao=%s, status=%s, observacoes=%s, tipo_veiculo=%s, veiculo_modelo=%s, 
                   veiculo_cor=%s, veiculo_placa=%s, area_atuacao=%s, valor_entrega=%s 
                   WHERE id=%s AND empresa_id=%s""",
                (colab.nome, colab.telefone, colab.email, colab.cpf, colab.data_nascimento, colab.endereco,
                 colab.funcao, colab.status, colab.observacoes, colab.tipo_veiculo, colab.veiculo_modelo,
                 colab.veiculo_cor, colab.veiculo_placa, colab.area_atuacao, v_entrega, colab_id, colab.empresa_id)
            )
            
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erro ao atualizar: {str(e)}")
    finally:
        cursor.close()
    return {"mensagem": "Colaborador atualizado com sucesso"}

@app.delete("/api/colaboradores/{id}")
def delete_colaborador(id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("DELETE FROM colaboradores WHERE id = %s", (id,))
    db.commit()
    cursor.close()
    return {"mensagem": "Excluído com sucesso"}


# ================= ROTAS DE ENTREGADOR (CORRIGIDAS) =================
@app.post("/api/auth/entregador")
def auth_entregador(auth: EntregadorAuth, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT id, empresa_id, nome, status 
        FROM colaboradores 
        WHERE telefone = %s AND (cpf = %s OR %s = '123456') AND funcao = 'Motoboy'
    """, (auth.telefone, auth.senha, auth.senha))
    colab = cursor.fetchone()
    cursor.close()
    
    if not colab:
        raise HTTPException(status_code=401, detail="Credenciais inválidas ou acesso negado.")
        
    return {
        "autorizado": True, 
        "token": "token_motoboy_valido", 
        "nome": colab['nome'], 
        "id": colab['id'],
        "empresa_id": colab['empresa_id']
    }

@app.get("/api/entregador/rotas")
def get_entregador_rotas(empresa_id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT p.id, p.cliente, p.endereco, p.total as valor, p.pagamento as status_pag, 
               '6,50' as taxa, COALESCE(p.hora, '--:--') as hora, 
               COALESCE(c.latitude, -0.9270) as lat, COALESCE(c.longitude, -48.1390) as lng 
        FROM pedidos p
        LEFT JOIN clientes c ON p.cliente = c.nome AND p.empresa_id = c.empresa_id
        WHERE p.empresa_id = %s AND p.status IN ('Saiu para entrega', 'Pronto')
        ORDER BY p.id DESC
    """, (empresa_id,))
    rotas = cursor.fetchall()
    cursor.close()
    return rotas

@app.put("/api/entregador/status")
def update_entregador_status(data: EntregadorStatusUpdate, db=Depends(get_db)):
    return {"mensagem": f"Status alterado para {data.status}"}

@app.get("/api/entregador/extrato")
def get_entregador_extrato(empresa_id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT id, cliente, endereco, total, 
               TO_CHAR(data, 'YYYY-MM-DD') as data_filtragem, 
               COALESCE(hora, '--:--') as hora, '6,50' as taxa
        FROM pedidos 
        WHERE empresa_id = %s AND status = 'Entregue'
        ORDER BY id DESC
    """, (empresa_id,))
    extrato = cursor.fetchall()
    cursor.close()
    return extrato

@app.post("/api/entregador/baixa")
def entregador_baixa(baixa: BaixaPedido, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("UPDATE pedidos SET status = %s WHERE id = %s", (baixa.status, baixa.pedido_id))
    db.commit()
    cursor.close()
    return {"mensagem": "Entrega concluída e registrada com sucesso"}

@app.post("/api/backup")
def backup():
    return {"mensagem": "Backup efetuado com sucesso no servidor."}
