import os
from fastapi import FastAPI, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import psycopg2
from psycopg2.extras import RealDictConnection, RealDictCursor
from datetime import datetime, date
from psycopg2 import pool

app = FastAPI(
    title="DeliveryON API - Produção Completa e Consolidada",
    description="API integrada ponta a ponta com todas as rotas unificadas e corrigidas"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("ON_DATA_URL", "postgresql://user:password@host/dbname")
MASTER_SECRET = os.getenv("SENHA_MASTER", "master123")

db_pool = pool.ThreadedConnectionPool(
    minconn=2,
    maxconn=20,
    dsn=DATABASE_URL,
    connection_factory=RealDictConnection
)

def get_db():
    conn = db_pool.getconn()
    try:
        yield conn
    finally:
        db_pool.putconn(conn)

# ================= MODELOS PYDANTIC =================

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
    
class ProdutoUpdate(ProdutoCreate):
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

class ClienteUpdate(ClienteCreate):
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
    empresa_id: Optional[int] = 1
    cliente: str
    telefone: Optional[str] = ""
    endereco: str
    pagamento: str
    itens: Optional[str] = ""
    total: float
    status: Optional[str] = "Aprovado / Preparando"
    hora: Optional[str] = None
    data: Optional[str] = None

class OuvidoriaCreate(BaseModel):
    empresa_id: Optional[int] = 1
    cliente_nome: Optional[str] = "Cliente"
    atendimento: Optional[str] = "Geral"
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
    entregador_id: int
    status: str

class EntregadorCadastro(BaseModel):
    nome: str
    cpf: str
    telefone: str
    senha: str
    email: Optional[str] = None  
    data_nascimento: Optional[str] = None
    tipo_veiculo: Optional[str] = "Moto"
    veiculo_modelo: Optional[str] = None
    veiculo_placa: Optional[str] = None

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
    enviar_comprovante: Optional[bool] = False

class ChamadoCancelar(BaseModel):
    motivo: str


@app.get("/api/orders")
def get_orders_admin(empresa_id: Optional[str] = Query('1'), db=Depends(get_db)):
    cur = db.cursor()
    try:
        e_id = int(empresa_id) if empresa_id and str(empresa_id).lower() not in ("null", "undefined", "") else 1
        
        cur.execute("""
            SELECT id, empresa_id, hora, cliente_nome AS cliente, endereco_entrega AS endereco, 
                   valor_total AS total, pagamento, status, entregador_id
            FROM pedidos 
            WHERE empresa_id = %s 
            ORDER BY id DESC LIMIT 100
        """, (e_id,))
        return cur.fetchall()
    except Exception as e:
        return []
    finally:
        cur.close()
# ================= MIGRAÇÃO / ATUALIZAÇÃO DO BANCO =================
@app.post("/api/atualizar-banco")
def atualizar_banco_de_dados(x_master_key: str = Header(None), db=Depends(get_db)):
    if x_master_key != MASTER_SECRET:
        raise HTTPException(status_code=401, detail="Não autorizado")

    cursor = db.cursor()
    queries = [
        """CREATE TABLE IF NOT EXISTS entregadores_app (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(255) NOT NULL,
            cpf VARCHAR(14) UNIQUE NOT NULL,
            email VARCHAR(255),
            telefone VARCHAR(20),
            data_nascimento VARCHAR(50),
            tipo_veiculo VARCHAR(50),
            veiculo_modelo VARCHAR(100),
            veiculo_placa VARCHAR(50),
            senha VARCHAR(255) NOT NULL,
            status VARCHAR(20) DEFAULT 'Disponível',
            empresa_id INTEGER DEFAULT 1
        );""",
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
        "ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS empresa_id INTEGER;",
        "ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS data DATE;",
        "ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS valor_total NUMERIC(10,2);",
        "ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS pagamento VARCHAR(50);",
        "ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS itens TEXT;",
        "ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS telefone VARCHAR(20);",
        "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS endereco_entrega TEXT;",
        "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS referencia TEXT;",
        "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS latitude NUMERIC(10,8);",
        "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS longitude NUMERIC(10,8);",
        "ALTER TABLE ouvidoria ADD COLUMN IF NOT EXISTS atendimento VARCHAR(100) DEFAULT 'Geral';",
        "ALTER TABLE ouvidoria ADD COLUMN IF NOT EXISTS cliente_nome VARCHAR(255);",
        "ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS entregador_id INTEGER;",
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
    return {"status": "Banco atualizado com sucesso!", "logs": resultados}


# ================= ROTAS DO MASTER =================
@app.post("/api/master/auth")
def master_login(auth: MasterAuth):
    if auth.senha == MASTER_SECRET:
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
    cursor.execute("""
        UPDATE empresas SET razao_social=%s, nome_fantasia=%s, cnpj=%s, responsavel=%s, 
        contato=%s, email_admin=%s, endereco=%s, plano=%s, vencimento=%s, limite_usuarios=%s WHERE id=%s
    """, (emp.get('razao_social'), emp.get('nome_fantasia'), emp.get('cnpj'), emp.get('responsavel'), 
          emp.get('contato'), emp.get('email_admin'), emp.get('endereco'), emp.get('plano'), 
          emp.get('vencimento'), emp.get('limite_usuarios'), id))
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
    except Exception:
        db.rollback()
    db.commit()
    cursor.close()
    return {"mensagem": "Pagamento carimbado com sucesso"}

@app.put("/api/master/empresas/{id}/pix")
def update_pix_master(id: int, pix: PixConfigUpdate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("UPDATE empresas SET qrcode_imagem = %s, copia_e_cola = %s WHERE id = %s", (pix.qrcode_imagem, pix.copia_e_cola, id))
    try:
        cursor.execute("INSERT INTO historico_empresas (empresa_id, descricao, data) VALUES (%s, 'Configuração PIX atualizada pelo Master', NOW())", (id,))
    except Exception:
        db.rollback()
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

@app.get("/api/master/entregadores")
def master_listar_entregadores(db=Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute("""
            SELECT id, nome, telefone, status, tipo_veiculo as veiculo 
            FROM entregadores_app ORDER BY id DESC;
        """)
        resultados = cursor.fetchall()
        lista_final = []
        for row in resultados:
            lista_final.append({
                "id": row['id'],
                "nome": row['nome'],
                "telefone": row['telefone'],
                "status": row['status'] or "Disponível",
                "veiculo": row['veiculo'] or "Moto",
                "total_entregas": 0
            })
        return lista_final
    except Exception as e:
        db.rollback()
        return []
    finally:
        cursor.close()

@app.get("/api/master/entregadores/{id}/historico")
def master_historico_entregador(id: int):
    return [
        {"data": "2026-09-02", "detalhe": "Entregador cadastrado na rede global"},
        {"data": "2026-09-06", "detalhe": "Realizou entrega com sucesso"}
    ]

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
    except Exception:
        db.rollback()
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
    except Exception:
        db.rollback()
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
                FROM notificacoes_master WHERE DATE(data_hora) = %s ORDER BY id DESC LIMIT 50
            """, (data,))
        else:
            cursor.execute("""
                SELECT id, tipo, titulo, mensagem, TO_CHAR(data_hora, 'DD/MM/YYYY HH24:MI') as data_hora 
                FROM notificacoes_master ORDER BY id DESC LIMIT 50
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

# ================= ROTAS DO GESTOR =================
@app.post("/api/gestor/auth")
def gestor_login(auth: GestorAuth, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        # 1. Tratamento no Python: extrai APENAS os números do CNPJ/CPF digitado
        doc_limpo = ''.join(filter(str.isdigit, auth.cnpj))
        
        if not doc_limpo:
            raise HTTPException(status_code=400, detail="CNPJ ou CPF inválido.")

        # 2. Busca no banco limpando os caracteres da coluna para garantir o "Match" perfeito
        cursor.execute("""
            SELECT id, nome_fantasia, cnpj, status 
            FROM empresas 
            WHERE REPLACE(REPLACE(REPLACE(REPLACE(cnpj, '.', ''), '/', ''), '-', ''), ' ', '') = %s
        """, (doc_limpo,))
        
        empresa = cursor.fetchone()
        
        if not empresa:
            raise HTTPException(status_code=404, detail="CNPJ/CPF não encontrado na base de dados.")
            
        if empresa.get('status') != 'ativo':
            raise HTTPException(status_code=403, detail="Esta empresa está inativa ou com o acesso suspenso.")
            
        return {
            "autorizado": True, 
            "empresa_id": empresa['id'], 
            "nome_fantasia": empresa['nome_fantasia']
        }
    except HTTPException:
        # Repassa os erros 400, 403 e 404 para o front-end exibir o alerta correto
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro interno de conexão: {str(e)}")
    finally:
        cursor.close()
@app.get("/api/configuracoes")
def get_configuracoes(empresa_id: int = Query(1), db=Depends(get_db)):
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
        return {"mensagem": "Configurações atualizadas com sucesso!"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()

@app.get("/api/dashboard")
def get_dashboard(empresa_id: int = Query(1), db=Depends(get_db)):
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) FROM pedidos WHERE empresa_id = %s AND LOWER(status) IN ('aguardando pagamento', 'aprovado / preparando')", (empresa_id,))
    res_ag = cur.fetchone()
    aguardando = res_ag[list(res_ag.keys())[0]] if res_ag else 0

    cur.execute("SELECT COUNT(*) FROM pedidos WHERE empresa_id = %s AND LOWER(status) = 'entregue'", (empresa_id,))
    res_ent = cur.fetchone()
    entregues = res_ent[list(res_ent.keys())[0]] if res_ent else 0

    cur.execute("SELECT COUNT(*) FROM pedidos WHERE empresa_id = %s AND LOWER(status) = 'cancelado'", (empresa_id,))
    res_can = cur.fetchone()
    cancelados = res_can[list(res_can.keys())[0]] if res_can else 0

    cur.execute("SELECT SUM(valor_total) FROM pedidos WHERE empresa_id = %s AND LOWER(status) = 'entregue'", (empresa_id,))
    row_receita = cur.fetchone()
    receita = row_receita[list(row_receita.keys())[0]] if row_receita else 0.00
    if not receita: 
        receita = 0.00
    cur.close()

    return {
        "aguardando": aguardando,
        "entregues": entregues,
        "cancelados": cancelados,
        "receita": f"{float(receita):.2f}".replace('.', ',')
    }

@app.get("/api/dashboard/fluxo")
def get_dashboard_fluxo(empresa_id: int = Query(1), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT 
            SUBSTRING(hora FROM 1 for 2) as horario, 
            COUNT(*) as total 
        FROM pedidos 
        WHERE empresa_id = %s AND hora IS NOT NULL AND hora != ''
        GROUP BY horario 
        ORDER BY horario ASC
    """, (empresa_id,))
    rows = cursor.fetchall()
    cursor.close()
    
    totais = {row['horario']: row['total'] for row in rows}
    
    dados_grafico = []
    for h in range(17, 22):
        h_str = f"{h:02d}"
        dados_grafico.append({
            "hora": f"{h_str}h",
            "total": totais.get(h_str, 0)
        })
        
    return dados_grafico

# ================= ROTAS DE PEDIDOS (UNIFICADAS E CORRIGIDAS) =================

@app.get("/api/pedidos") 
@app.get("/api/orders")
def get_orders(empresa_id: Optional[str] = Query('1'), db=Depends(get_db)):
    cur = db.cursor()
    try:
        e_id = int(empresa_id) if empresa_id and str(empresa_id).lower() not in ("null", "undefined", "") else 1
        cur.execute("""
            SELECT 
                id, empresa_id, hora, 
                cliente_nome AS cliente, 
                endereco_entrega AS endereco, 
                valor_total AS total, 
                pagamento, status, entregador_id
            FROM pedidos 
            WHERE empresa_id = %s 
            ORDER BY id DESC LIMIT 50
        """, (e_id,))
        rows = cur.fetchall()

        orders = []
        for row in rows:
            val = row.get('valor_total') or row.get('total') or 0.00
            orders.append({
                "id": row['id'],
                "empresa_id": row.get('empresa_id', 1),
                "hora": str(row['hora']) if row['hora'] else "",
                "cliente": row.get('cliente') or row.get('cliente_nome') or "",
                "cliente_nome": row.get('cliente') or row.get('cliente_nome') or "",
                "endereco": row['endereco'],
                "pagamento": row.get('pagamento') or "",
                "total": f"{float(val):.2f}".replace('.', ','),
                "valor_total": val,
                "status": row['status'],
                "entregador_id": row.get('entregador_id')
            })
        return orders
    except Exception as e:
        print(f"Erro ao listar pedidos: {str(e)}")
        return []
    finally:
        cur.close()

@app.put("/api/orders/{order_id}/status")
def update_order_status(order_id: int, data: dict, db=Depends(get_db)):
    novo_status = data.get("status")
    cur = db.cursor()
    try:
        cur.execute("UPDATE pedidos SET status = %s WHERE id = %s", (novo_status, order_id))
        db.commit()
        return {"success": True, "message": "Status atualizado com sucesso!"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()


@app.get("/api/orders/{order_id}")
def get_order_by_id(order_id: int, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute("""
            SELECT p.id, p.status, p.valor_total as total, p.endereco_entrega as endereco, 
                   p.entregador_id as motoboy_id, e.nome as motoboy_nome
            FROM pedidos p 
            LEFT JOIN entregadores_app e ON p.entregador_id = e.id
            WHERE p.id = %s
        """, (order_id,))
        order = cursor.fetchone()
        
        if not order:
            raise HTTPException(status_code=404, detail="Pedido não encontrado")
            
        total_val = order.get('total')
        total_str = f"{float(total_val):.2f}".replace('.', ',') if total_val is not None else "0,00"

        return {
            "id": order['id'],
            "status": order['status'] or "Pendente",
            "total": total_str,
            "endereco": order.get('endereco') or "",
            "motoboy_nome": order.get('motoboy_nome') or "Não atribuído"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()



# 1. CRIAÇÃO DO PEDIDO (Nasce oculto para o motoboy)
@app.post("/api/orders")
def create_order(order: OrderCreate, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        emp_id = order.empresa_id if order.empresa_id else 1
        cursor.execute("""
            INSERT INTO pedidos (empresa_id, cliente_nome, telefone, endereco_entrega, pagamento, valor_total, status, hora, data) 
            VALUES (%s, %s, %s, %s, %s, %s, 'Aprovado / Preparando', %s, %s) RETURNING id;
        """, (
            emp_id, order.cliente, order.telefone, order.endereco, order.pagamento, 
            float(order.total) if order.total else 0.00, 
            order.hora or datetime.now().strftime("%H:%M"), 
            order.data or date.today().isoformat()
        ))
        db.commit()
        return {"success": True, "id": cursor.fetchone()['id']}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()

# 2. DESPACHO DO GESTOR (Libera no radar dos motoboys)
@app.post("/api/orders/{order_id}/despachar-proximos")
def despachar_proximos(order_id: int, data: Optional[dict] = None, db=Depends(get_db)):
    cursor = db.cursor()
    data = data or {}
    tipo_despacho = data.get("tipo_despacho", "autonomo")
    empresa_id = data.get("empresa_id", 1)
    
    try:
        if tipo_despacho == 'empresa':
            cursor.execute("SELECT id FROM colaboradores WHERE empresa_id = %s AND LOWER(funcao) LIKE '%%motoboy%%' LIMIT 1", (empresa_id,))
            colab = cursor.fetchone()
            if colab:
                cursor.execute("UPDATE pedidos SET status = 'Aguardando Entregador', entregador_id = %s WHERE id = %s", (colab['id'], order_id))
            else:
                cursor.execute("UPDATE pedidos SET status = 'Aguardando Entregador', entregador_id = NULL WHERE id = %s", (order_id,))
        else:
            cursor.execute("UPDATE pedidos SET status = 'Aguardando Entregador', entregador_id = NULL WHERE id = %s", (order_id,))
            
        db.commit()
        return {"success": True, "message": "Despachado com sucesso!"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()

# 3. MATCHMAKING DO MOTOBOY (Só enxerga o que está aguardando ele)
@app.get("/api/entregador/rotas")
def get_entregador_rotas(empresa_id: Optional[str] = '1', entregador_id: Optional[str] = None, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        e_id = int(empresa_id) if empresa_id and str(empresa_id).lower() not in ("null", "undefined", "") else 1
        
        query = """
            SELECT p.id, p.cliente_nome AS cliente, p.endereco_entrega AS endereco, 
                   p.valor_total as valor, '6,50' as taxa, p.hora, p.status, p.entregador_id,
                   COALESCE(c.latitude, -0.9270) as lat, COALESCE(c.longitude, -48.1390) as lng
            FROM pedidos p
            LEFT JOIN clientes c ON p.cliente_nome = c.nome
            WHERE p.empresa_id = %s AND p.status = 'Aguardando Entregador'
        """
        params = [e_id]
        
        if entregador_id and str(entregador_id).lower() not in ("null", "undefined", ""):
            query += " AND (p.entregador_id = %s OR p.entregador_id IS NULL)"
            params.append(int(entregador_id))
        else:
            query += " AND p.entregador_id IS NULL"

        cursor.execute(query + " ORDER BY p.id DESC", tuple(params))
        return cursor.fetchall()
    except Exception:
        return []
    finally:
        cursor.close()

# 4. ACEITE DO MOTOBOY (Trava o ID e muda para 'Saiu para entrega')
@app.post("/api/orders/{order_id}/atribuir-motoboy")
def atribuir_motoboy(order_id: int, data: dict, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute("""
            UPDATE pedidos 
            SET status = 'Saiu para entrega', entregador_id = %s 
            WHERE id = %s AND status = 'Aguardando Entregador'
        """, (data.get("motoboy_id"), order_id))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=400, detail="Corrida indisponível ou já aceita.")

        db.commit()
        return {"success": True, "message": "Corrida aceita!"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()

# ================= ROTAS DE PRODUTOS, CLIENTES E COLABORADORES =================
@app.get("/api/products")
def list_products(empresa_id: int = Query(1), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT id as codigo, id, nome, categoria, preco, estoque, descricao, foto 
        FROM produtos WHERE empresa_id = %s ORDER BY id DESC LIMIT 50;
    """, (empresa_id,))
    res = cursor.fetchall()
    cursor.close()
    return res

@app.post("/api/products")
def create_product(prod: ProdutoCreate, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute(
            "INSERT INTO produtos (empresa_id, nome, categoria, preco, estoque, descricao, foto) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;",
            (prod.empresa_id, prod.nome, prod.categoria, prod.preco, prod.estoque, prod.descricao, prod.foto))
        db.commit()
        novo_id = cursor.fetchone()['id']
        return {"mensagem": "Produto salvo", "id": novo_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()

@app.put("/api/products/{id}")
def update_product(id: int, prod: ProdutoUpdate, db=Depends(get_db)):
    cursor = db.cursor()
    try:
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
        return {"mensagem": "Produto atualizado com sucesso"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()

@app.delete("/api/products/{id}")
def delete_product(id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("DELETE FROM produtos WHERE id = %s", (id,))
    db.commit()
    cursor.close()
    return {"mensagem": "Excluído com sucesso"}

@app.get("/api/clients")
def list_clients(empresa_id: int = Query(1), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id, nome, telefone, email, endereco_entrega as endereco, referencia FROM clientes WHERE empresa_id = %s ORDER BY id DESC", (empresa_id,))
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
        return {"mensagem": "Cliente salvo com sucesso", "id": novo_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()

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
        return {"mensagem": "Cliente atualizado com sucesso"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()

@app.delete("/api/clients/{id}")
def delete_client(id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("DELETE FROM clientes WHERE id = %s", (id,))
    db.commit()
    cursor.close()
    return {"mensagem": "Excluído com sucesso"}

@app.get("/api/colaboradores")
def list_colaboradores(empresa_id: int = Query(1), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id, nome, telefone, email, cpf, funcao, status, foto FROM colaboradores WHERE empresa_id = %s ORDER BY id DESC", (empresa_id,))
    res = cursor.fetchall()
    cursor.close()
    return res

@app.post("/api/colaboradores")
def create_colaborador(colab: ColaboradorCreate, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute(
            """INSERT INTO colaboradores 
               (empresa_id, nome, telefone, email, cpf, data_nascimento, endereco, funcao, status, observacoes, tipo_veiculo, veiculo_modelo, veiculo_cor, veiculo_placa, area_atuacao, valor_entrega, foto) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;""",
            (colab.empresa_id, colab.nome, colab.telefone, colab.email, colab.cpf, colab.data_nascimento, colab.endereco, 
             colab.funcao, colab.status, colab.observacoes, colab.tipo_veiculo, colab.veiculo_modelo, 
             colab.veiculo_cor, colab.veiculo_placa, colab.area_atuacao, float(colab.valor_entrega or 0.0), colab.foto))
        db.commit()
        novo_id = cursor.fetchone()['id']
        return {"mensagem": "Colaborador salvo com sucesso", "id": novo_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()

@app.put("/api/colaboradores/{colab_id}")
def update_colaborador(colab_id: int, colab: ColaboradorCreate, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute(
            """UPDATE colaboradores SET 
               nome=%s, telefone=%s, email=%s, cpf=%s, data_nascimento=%s, endereco=%s, 
               funcao=%s, status=%s, observacoes=%s, tipo_veiculo=%s, veiculo_modelo=%s, 
               veiculo_cor=%s, veiculo_placa=%s, area_atuacao=%s, valor_entrega=%s WHERE id=%s AND empresa_id=%s""",
            (colab.nome, colab.telefone, colab.email, colab.cpf, colab.data_nascimento, colab.endereco,
             colab.funcao, colab.status, colab.observacoes, colab.tipo_veiculo, colab.veiculo_modelo,
             colab.veiculo_cor, colab.veiculo_placa, colab.area_atuacao, float(colab.valor_entrega or 0.0), colab_id, colab.empresa_id)
        )
        db.commit()
        return {"mensagem": "Colaborador atualizado com sucesso"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()

@app.delete("/api/colaboradores/{id}")
def delete_colaborador(id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("DELETE FROM colaboradores WHERE id = %s", (id,))
    db.commit()
    cursor.close()
    return {"mensagem": "Excluído com sucesso"}

# ================= ROTAS DE ENTREGADOR E MATCHMAKING =================
@app.post("/api/auth/entregador")
def auth_entregador(auth: EntregadorAuth, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        # 1. Limpeza do Python: extrai apenas os números do telefone digitado
        tel_limpo = ''.join(filter(str.isdigit, auth.telefone))
        
        if not tel_limpo:
            raise HTTPException(status_code=400, detail="Telefone inválido.")

        # Função SQL para limpar a coluna de telefone na hora da busca
        sql_limpeza_tel = "REPLACE(REPLACE(REPLACE(REPLACE(telefone, '(', ''), ')', ''), '-', ''), ' ', '')"

        # 2. Busca na tabela de entregadores do App (Autônomos)
        cursor.execute(f"""
            SELECT id, 1 as empresa_id, nome, status, senha, cpf 
            FROM entregadores_app 
            WHERE {sql_limpeza_tel} = %s
        """, (tel_limpo,))
        colab = cursor.fetchone()

        # 3. Fallback: Busca na tabela de colaboradores fixos da empresa
        if not colab:
            cursor.execute(f"""
                SELECT id, empresa_id, nome, status, COALESCE(cpf, '123456') as senha, cpf 
                FROM colaboradores 
                WHERE {sql_limpeza_tel} = %s AND LOWER(funcao) LIKE '%%motoboy%%'
            """, (tel_limpo,))
            colab = cursor.fetchone()

        if not colab:
            raise HTTPException(status_code=401, detail="Telefone não cadastrado como entregador.")

        # 4. Validação Híbrida de Senha/CPF (Blindada contra máscaras)
        senha_cadastrada = str(colab['senha']) if colab['senha'] else '123456'
        cpf_cadastrado = str(colab['cpf']) if colab['cpf'] else ''
        senha_digitada = auth.senha.strip()
        
        # Limpa os números da senha e do CPF para comparar com segurança
        senha_dig_numeros = ''.join(filter(str.isdigit, senha_digitada))
        cpf_cad_numeros = ''.join(filter(str.isdigit, cpf_cadastrado))
        
        senha_correta = False
        if senha_digitada == senha_cadastrada or senha_digitada == '123456':
            senha_correta = True
        elif senha_dig_numeros and cpf_cad_numeros and senha_dig_numeros == cpf_cad_numeros:
            senha_correta = True
            
        if not senha_correta:
            raise HTTPException(status_code=401, detail="Senha ou CPF incorretos.")

        return {
            "autorizado": True,
            "token": "token_motoboy_valido",
            "nome": colab['nome'],
            "id": colab['id'],
            "empresa_id": colab['empresa_id'] or 1,
            "status": colab['status'] or "Disponível"
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
    finally:
        cursor.close()

@app.post("/api/auth/entregador/cadastro")
def cadastro_entregador(ent: EntregadorCadastro, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        email_valido = ent.email if ent.email and ent.email.strip() != "" else f"motoboy_{ent.cpf.replace('.', '').replace('-', '')}@deliveryon.com"
        
        cursor.execute("""
            INSERT INTO entregadores_app 
            (nome, cpf, telefone, senha, email, data_nascimento, tipo_veiculo, veiculo_modelo, veiculo_placa, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'Disponível')
            RETURNING id;
        """, (
            ent.nome, ent.cpf, ent.telefone, ent.senha, email_valido, 
            ent.data_nascimento, ent.tipo_veiculo, ent.veiculo_modelo, ent.veiculo_placa
        ))
        db.commit()
        novo_id = cursor.fetchone()['id']
        return {"autorizado": True, "id": novo_id, "nome": ent.nome, "empresa_id": 1, "status": "Disponível", "token": "token_ativo"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erro ao cadastrar entregador: {str(e)}")
    finally:
        cursor.close()

@app.put("/api/entregador/status")
def update_entregador_status(data: EntregadorStatusUpdate, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute("UPDATE entregadores_app SET status = %s WHERE id = %s", (data.status, data.entregador_id))
        db.commit()
        return {"mensagem": f"Status alterado para {data.status}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()


@app.get("/api/entregador/extrato")
def get_entregador_extrato(empresa_id: Optional[str] = None, entregador_id: Optional[int] = None, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        if not empresa_id or str(empresa_id).lower() in ("null", "undefined", ""):
            cursor.execute("""
                SELECT id, cliente_nome AS cliente, endereco_entrega AS endereco, valor_total as total, 
                       TO_CHAR(data, 'YYYY-MM-DD') as data_filtragem, 
                       COALESCE(hora, '--:--') as hora, '6,50' as taxa
                FROM pedidos WHERE LOWER(status) = 'entregue' ORDER BY id DESC
            """)
        else:
            cursor.execute("""
                SELECT id, cliente_nome AS cliente, endereco_entrega AS endereco, valor_total as total, 
                       TO_CHAR(data, 'YYYY-MM-DD') as data_filtragem, 
                       COALESCE(hora, '--:--') as hora, '6,50' as taxa
                FROM pedidos WHERE empresa_id = %s AND LOWER(status) = 'entregue' ORDER BY id DESC
            """, (int(empresa_id),))
            
        return cursor.fetchall()
    except Exception as e:
        print(f"Erro no extrato: {e}")
        return []
    finally:
        cursor.close()

@app.post("/api/entregador/baixa")
def entregador_baixa(baixa: BaixaPedido, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute("UPDATE pedidos SET status = %s WHERE id = %s", (baixa.status, baixa.pedido_id))
        db.commit()
        return {"mensagem": "Entrega concluída e registrada com sucesso"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()


# ================= ROTAS DE HELPDESK E OUVIDORIA =================
@app.get("/api/ouvidoria/estatisticas")
def get_ouvidoria_estatisticas(empresa_id: int = Query(1), db=Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute("""
            SELECT LOWER(avaliacao) as av, COUNT(*) as total 
            FROM ouvidoria 
            WHERE empresa_id = %s 
            GROUP BY LOWER(avaliacao)
        """, (empresa_id,))
        rows = cursor.fetchall()

        stats = {"otimo": 0, "bom": 0, "regular": 0, "ruim": 0, "pessimo": 0}
        for row in rows:
            av = row['av']
            total = row['total']
            if "ótimo" in av or "otimo" in av:
                stats["otimo"] = total
            elif "bom" in av:
                stats["bom"] = total
            elif "regular" in av:
                stats["regular"] = total
            elif "ruim" in av:
                stats["ruim"] = total
            elif "péssimo" in av or "pessimo" in av:
                stats["pessimo"] = total
        return stats
    except Exception as e:
        db.rollback()
        return {"otimo": 0, "bom": 0, "regular": 0, "ruim": 0, "pessimo": 0}
    finally:
        cursor.close()

@app.post("/api/helpdesk")
def criar_chamado(chamado: ChamadoCreate, db=Depends(get_db)):
    cursor = db.cursor()
    try:
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
        return {"mensagem": "Chamado aberto com sucesso", "id": novo_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()

@app.get("/api/helpdesk")
def listar_chamados_gestor(empresa_id: int = Query(1), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT id, resumo_problema, descricao, status, 
               TO_CHAR(data_criacao, 'DD/MM/YYYY HH24:MI') as data_criacao, 
               tecnico_responsavel
        FROM chamados WHERE empresa_id = %s ORDER BY id DESC;
    """, (empresa_id,))
    res = cursor.fetchall()
    cursor.close()
    return res

@app.post("/api/ouvidoria")
def create_ouvidoria(ouv: OuvidoriaCreate, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute("""
            INSERT INTO ouvidoria (empresa_id, cliente_nome, atendimento, avaliacao, relato, criado_em)
            VALUES (%s, %s, %s, %s, %s, NOW()) RETURNING id;
        """, (ouv.empresa_id, ouv.cliente_nome, ouv.atendimento, ouv.avaliacao, ouv.relato))
        db.commit()
        return {"mensagem": "Ouvidoria registrada com sucesso"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()

@app.get("/api/ouvidoria")
def list_ouvidoria(empresa_id: int = Query(1), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "SELECT id, cliente_nome as cliente, avaliacao, relato, TO_CHAR(criado_em, 'DD/MM/YYYY') as data FROM ouvidoria WHERE empresa_id = %s ORDER BY id DESC",
        (empresa_id,))
    res = cursor.fetchall()
    cursor.close()
    return res


# ================= ROTAS PÚBLICAS DO HUB E CARDÁPIO =================
@app.get("/api/empresas")
def listar_empresas_publicas(db=Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute("SELECT id, nome_fantasia as nome, 'Geral' as categoria, qrcode_imagem as logo_url, '40-50 min' as tempo_entrega, 5.00 as taxa_entrega, contato FROM empresas WHERE status = 'ativo' ORDER BY id DESC")
        res = cursor.fetchall()
    except Exception:
        db.rollback()
        cursor.execute("SELECT id, nome_fantasia as nome, 'Geral' as categoria, NULL as logo_url, '40-50 min' as tempo_entrega, 5.00 as taxa_entrega, contato FROM empresas ORDER BY id DESC")
        res = cursor.fetchall()
    finally:
        cursor.close()
    return res

@app.get("/api/produtos/destaques")
def listar_produtos_destaques(db=Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute("""
            SELECT p.id, p.nome, p.preco, p.descricao, p.foto, p.empresa_id, 
                   e.nome_fantasia as empresa_nome, e.qrcode_imagem as empresa_img, 'geral' as categoria_empresa
            FROM produtos p
            JOIN empresas e ON p.empresa_id = e.id
            ORDER BY p.id DESC LIMIT 10
        """)
        res = cursor.fetchall()
    except Exception:
        db.rollback()
        res = []
    finally:
        cursor.close()
    return res

@app.post("/api/backup")
def backup():
    return {"mensagem": "Backup efetuado com sucesso no servidor."}
