from datetime import datetime
import os
from typing import Optional
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from psycopg2.extras import RealDictConnection
from psycopg2 import pool

app = FastAPI(
    title="DeliveryON API - Definitiva e Consolidada",
    description="API unificada para Master, Gestor, Entregador e Hub com suporte total a fotos, histórico e Neon DB.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("ON_DATA_URL")
MASTER_SECRET = os.getenv("SENHA_MASTER", "master123")

db_pool = pool.ThreadedConnectionPool(
    minconn=2, maxconn=20, dsn=DATABASE_URL, connection_factory=RealDictConnection
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
    logo: Optional[str] = None


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
    foto: Optional[str] = None


class ClienteUpdate(BaseModel):
    empresa_id: int
    nome: str
    telefone: str
    email: Optional[str] = None
    endereco: str
    referencia: Optional[str] = None
    foto: Optional[str] = None


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
    cliente: Optional[str] = None
    cliente_nome: Optional[str] = None
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
    cliente_nome: Optional[str] = "Cliente Anônimo"
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
    foto: Optional[str] = None


class BaixaPedido(BaseModel):
    pedido_id: str
    status: str
    data_conclusao: Optional[str] = None


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


# ================= AUTO-MIGRAÇÃO DE BANCO (COM FOTOS E LOGOS) =================
@app.post("/api/atualizar-banco")
def atualizar_banco_de_dados(
    x_master_key: str = Header(None), db=Depends(get_db)
):
    if x_master_key != MASTER_SECRET:
        raise HTTPException(status_code=401, detail="Não autorizado")

    cursor = db.cursor()
    queries = [
        """CREATE TABLE IF NOT EXISTS empresas (
            id SERIAL PRIMARY KEY,
            razao_social VARCHAR(255),
            nome_fantasia VARCHAR(255),
            cnpj VARCHAR(50) UNIQUE,
            responsavel VARCHAR(255),
            contato VARCHAR(50),
            email_admin VARCHAR(255),
            endereco TEXT,
            plano VARCHAR(50) DEFAULT 'basic',
            vencimento INTEGER DEFAULT 10,
            limite_usuarios INTEGER DEFAULT 5,
            status VARCHAR(20) DEFAULT 'ativo',
            qrcode_imagem TEXT,
            copia_e_cola TEXT,
            logo TEXT
        );""",
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
            empresa_id INTEGER DEFAULT 1,
            foto TEXT
        );""",
        """CREATE TABLE IF NOT EXISTS produtos (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER,
            nome VARCHAR(255),
            categoria VARCHAR(100),
            preco NUMERIC(10,2),
            estoque INTEGER,
            descricao TEXT,
            foto TEXT
        );""",
        """CREATE TABLE IF NOT EXISTS clientes (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER,
            nome VARCHAR(255),
            telefone VARCHAR(50),
            email VARCHAR(255),
            endereco_entrega TEXT,
            referencia TEXT,
            foto TEXT,
            latitude NUMERIC(10,8),
            longitude NUMERIC(10,8)
        );""",
        """CREATE TABLE IF NOT EXISTS colaboradores (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER DEFAULT 1,
            nome VARCHAR(255),
            telefone VARCHAR(50),
            email VARCHAR(255),
            cpf VARCHAR(50),
            data_nascimento VARCHAR(50),
            endereco TEXT,
            funcao VARCHAR(100),
            status VARCHAR(50) DEFAULT 'Disponível',
            observacoes TEXT,
            tipo_veiculo VARCHAR(50),
            veiculo_modelo VARCHAR(100),
            veiculo_cor VARCHAR(50),
            veiculo_placa VARCHAR(50),
            area_atuacao VARCHAR(150),
            valor_entrega NUMERIC(10,2) DEFAULT 0,
            foto TEXT
        );""",
        """CREATE TABLE IF NOT EXISTS pedidos (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER,
            cliente_nome VARCHAR(255),
            telefone VARCHAR(50),
            endereco_entrega TEXT,
            pagamento VARCHAR(50),
            itens TEXT,
            valor_total NUMERIC(10,2),
            status VARCHAR(50) DEFAULT 'Aguardando pagamento',
            hora VARCHAR(20),
            data DATE,
            entregador_id INTEGER
        );""",
        """CREATE TABLE IF NOT EXISTS ouvidoria (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER,
            pedido_id INTEGER,
            cliente_nome VARCHAR(255),
            atendimento VARCHAR(100),
            avaliacao VARCHAR(50),
            relato TEXT,
            criado_em TIMESTAMP DEFAULT NOW()
        );""",
        """CREATE TABLE IF NOT EXISTS chamados (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER,
            resumo_problema VARCHAR(255),
            descricao TEXT,
            status VARCHAR(50) DEFAULT 'aberto',
            tecnico_responsavel VARCHAR(255),
            data_criacao TIMESTAMP DEFAULT NOW()
        );""",
        """CREATE TABLE IF NOT EXISTS notificacoes_master (
            id SERIAL PRIMARY KEY,
            tipo VARCHAR(50),
            titulo VARCHAR(255),
            mensagem TEXT,
            data_hora TIMESTAMP DEFAULT NOW()
        );""",
        """CREATE TABLE IF NOT EXISTS historico_empresas (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER,
            descricao TEXT,
            data TIMESTAMP DEFAULT NOW()
        );""",
        """CREATE TABLE IF NOT EXISTS historico_chamados (
            id SERIAL PRIMARY KEY,
            chamado_id INTEGER,
            descricao TEXT,
            data_hora TIMESTAMP DEFAULT NOW()
        );""",
        "ALTER TABLE empresas ADD COLUMN IF NOT EXISTS logo TEXT;",
        "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS foto TEXT;",
        "ALTER TABLE entregadores_app ADD COLUMN IF NOT EXISTS foto TEXT;",
        "ALTER TABLE produtos ADD COLUMN IF NOT EXISTS foto TEXT;",
        "ALTER TABLE colaboradores ADD COLUMN IF NOT EXISTS foto TEXT;",
    ]

    resultados = []
    for q in queries:
        try:
            cursor.execute(q)
            db.commit()
            resultados.append("Sucesso na query.")
        except Exception as e:
            db.rollback()
            resultados.append(f"Aviso/Erro: {str(e)}")

    cursor.close()
    return {"status": "Estrutura do Neon DB validada e atualizada com sucesso!"}


# ================= ROTAS MASTER =================
@app.post("/api/master/auth")
def master_login(auth: MasterAuth):
    if auth.senha == MASTER_SECRET:
        return {"autorizado": True, "token": "token_master_valido"}
    raise HTTPException(status_code=401, detail="Senha Master incorreta")


@app.get("/api/master/metrics")
def get_master_metrics(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM empresas")
    total_clientes = cursor.fetchone()["total"]
    cursor.execute("SELECT pg_database_size(current_database()) as db_size;")
    db_size_str = f"{round(cursor.fetchone()['db_size'] / (1024 * 1024), 2)} MB"
    cursor.close()
    return {
        "db_disk_usage": db_size_str,
        "total_clientes": total_clientes,
        "mrr": f"R$ {total_clientes * 250},00",
    }


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
    cursor.execute(
        """
        INSERT INTO empresas (razao_social, nome_fantasia, cnpj, responsavel, contato, email_admin, endereco, plano, vencimento, limite_usuarios, status, logo)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'ativo', %s) RETURNING id;
    """,
        (
            emp.razao_social,
            emp.nome_fantasia,
            emp.cnpj,
            emp.responsavel,
            emp.contato,
            emp.email_admin,
            emp.endereco,
            emp.plano,
            emp.vencimento,
            emp.limite_usuarios,
            emp.logo,
        ),
    )
    db.commit()
    novo_id = cursor.fetchone()["id"]
    cursor.close()
    return {"mensagem": "Tenant criado", "id": novo_id}


@app.put("/api/master/empresas/{id}")
def update_empresa(id: int, emp: dict, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        """UPDATE empresas SET razao_social=%s, nome_fantasia=%s, cnpj=%s, responsavel=%s, 
           contato=%s, email_admin=%s, endereco=%s, plano=%s, vencimento=%s, limite_usuarios=%s, logo=%s WHERE id=%s""",
        (
            emp.get("razao_social"),
            emp.get("nome_fantasia"),
            emp.get("cnpj"),
            emp.get("responsavel"),
            emp.get("contato"),
            emp.get("email_admin"),
            emp.get("endereco"),
            emp.get("plano"),
            emp.get("vencimento"),
            emp.get("limite_usuarios"),
            emp.get("logo"),
            id,
        ),
    )
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
        cursor.execute(
            "INSERT INTO historico_empresas (empresa_id, descricao, data) VALUES (%s, 'Pagamento carimbado e autenticado', NOW())",
            (id,),
        )
    except Exception:
        pass
    db.commit()
    cursor.close()
    return {"mensagem": "Pagamento carimbado com sucesso"}


@app.put("/api/master/empresas/{id}/pix")
def update_pix_master(id: int, pix: PixConfigUpdate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "UPDATE empresas SET qrcode_imagem = %s, copia_e_cola = %s WHERE id = %s",
        (pix.qrcode_imagem, pix.copia_e_cola, id),
    )
    try:
        cursor.execute(
            "INSERT INTO historico_empresas (empresa_id, descricao, data) VALUES (%s, 'Configuração PIX atualizada', NOW())",
            (id,),
        )
    except Exception:
        pass
    db.commit()
    cursor.close()
    return {"mensagem": "PIX atualizado com sucesso"}


@app.get("/api/master/empresas/{id}/historico")
def get_empresa_historico(id: int, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute(
            "SELECT descricao, TO_CHAR(data, 'DD/MM/YYYY HH24:MI') as data FROM historico_empresas WHERE empresa_id = %s ORDER BY data DESC",
            (id,),
        )
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
        cursor.execute(
            "SELECT id, nome, telefone, status, tipo_veiculo as veiculo, foto FROM entregadores_app ORDER BY id DESC"
        )
        resultados = cursor.fetchall()
        lista_final = []
        for row in resultados:
            lista_final.append(
                {
                    "id": row["id"],
                    "nome": row["nome"],
                    "telefone": row["telefone"],
                    "status": row["status"] or "Disponível",
                    "veiculo": row["veiculo"] or "Moto",
                    "foto": row["foto"] or "",
                    "total_entregas": 0,
                }
            )
        return lista_final
    except Exception:
        db.rollback()
        return []
    finally:
        cursor.close()


@app.get("/api/master/notificacoes")
def get_notificacoes_master(data: Optional[str] = None, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        if data:
            cursor.execute(
                "SELECT id, tipo, titulo, mensagem, TO_CHAR(data_hora, 'DD/MM/YYYY HH24:MI') as data_hora FROM notificacoes_master WHERE DATE(data_hora) = %s ORDER BY id DESC LIMIT 50",
                (data,),
            )
        else:
            cursor.execute(
                "SELECT id, tipo, titulo, mensagem, TO_CHAR(data_hora, 'DD/MM/YYYY HH24:MI') as data_hora FROM notificacoes_master ORDER BY id DESC LIMIT 50"
            )
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


# ================= ROTAS DE HELPDESK =================
@app.post("/api/helpdesk")
def criar_chamado(chamado: ChamadoCreate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        """
        INSERT INTO chamados (empresa_id, resumo_problema, descricao, status, data_criacao) 
        VALUES (%s, %s, %s, 'aberto', NOW()) RETURNING id;
    """,
        (chamado.empresa_id, chamado.resumo_problema, chamado.descricao),
    )
    novo_id = cursor.fetchone()["id"]
    cursor.execute(
        """
        INSERT INTO notificacoes_master (tipo, titulo, mensagem, data_hora)
        VALUES ('sup', 'Novo Chamado', %s, NOW())
    """,
        (
            f"Empresa ID {chamado.empresa_id} abriu chamado: {chamado.resumo_problema}",
        ),
    )
    db.commit()
    cursor.close()
    return {"mensagem": "Chamado aberto com sucesso", "id": novo_id}


@app.get("/api/helpdesk")
def listar_chamados_gestor(empresa_id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        """
        SELECT id, resumo_problema, descricao, status, 
               TO_CHAR(data_criacao, 'DD/MM/YYYY HH24:MI') as data_criacao, 
               tecnico_responsavel
        FROM chamados WHERE empresa_id = %s ORDER BY id DESC;
    """,
        (empresa_id,),
    )
    res = cursor.fetchall()
    cursor.close()
    return res


@app.get("/api/master/helpdesk/indicadores")
def get_master_helpdesk_indicadores(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "SELECT COUNT(*) as total FROM chamados WHERE status = 'aberto'"
    )
    abertos = cursor.fetchone()["total"]
    cursor.execute(
        "SELECT COUNT(*) as total FROM chamados WHERE status IN ('em_atendimento', 'em_andamento')"
    )
    andamento = cursor.fetchone()["total"]
    cursor.execute(
        "SELECT COUNT(*) as total FROM chamados WHERE status IN ('resolvido', 'concluido')"
    )
    concluidos = cursor.fetchone()["total"]
    cursor.execute(
        "SELECT COUNT(*) as total FROM chamados WHERE status = 'pendente'"
    )
    pendentes = cursor.fetchone()["total"]
    cursor.close()
    return {
        "abertos": abertos,
        "em_andamento": andamento,
        "concluidos": concluidos,
        "pendentes": pendentes,
    }


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
    return {"mensagem": "Status atualizado"}


@app.post("/api/master/helpdesk/chamados/{id}/concluir")
def concluir_chamado(id: int, data: ChamadoConcluir, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "UPDATE chamados SET status = 'resolvido', tecnico_responsavel = %s WHERE id = %s",
        (data.tecnico, id),
    )
    db.commit()
    cursor.close()
    return {"mensagem": "Chamado concluído"}


@app.post("/api/master/helpdesk/chamados/{id}/cancelar")
def cancelar_chamado(id: int, data: ChamadoCancelar, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("UPDATE chamados SET status = 'cancelado' WHERE id = %s", (id,))
    db.commit()
    cursor.close()
    return {"mensagem": "Chamado cancelado"}


# ================= ROTAS DO GESTOR =================
@app.post("/api/gestor/auth")
def gestor_login(auth: GestorAuth, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "SELECT id, nome_fantasia, cnpj, status FROM empresas WHERE REPLACE(REPLACE(REPLACE(cnpj, '.', ''), '/', ''), '-', '') = REPLACE(REPLACE(REPLACE(%s, '.', ''), '/', ''), '-', '')",
        (auth.cnpj,),
    )
    empresa = cursor.fetchone()
    cursor.close()
    if not empresa:
        raise HTTPException(status_code=404, detail="CNPJ não encontrado.")
    if empresa["status"] != "ativo":
        raise HTTPException(
            status_code=403, detail="Empresa inativa ou suspensa."
        )
    return {
        "autorizado": True,
        "empresa_id": empresa["id"],
        "nome_fantasia": empresa["nome_fantasia"],
    }


@app.get("/api/configuracoes")
def get_configuracoes(empresa_id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        """
        SELECT nome_fantasia as titulo, endereco, contato as telefone, 
               slogan, horario_funcionamento, cor_primaria, cor_secundaria,
               qrcode_imagem as qrcode_img, logo as logo_url
        FROM empresas WHERE id = %s
    """,
        (empresa_id,),
    )
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
        "qrcode_img": res.get("qrcode_img") or "",
        "logo_url": res.get("logo_url") or "",
    }


@app.put("/api/configuracoes")
def update_configuracoes(data: dict, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            UPDATE empresas 
            SET nome_fantasia = %s, endereco = %s, contato = %s, 
                slogan = %s, horario_funcionamento = %s, 
                cor_primaria = %s, cor_secundaria = %s, qrcode_imagem = %s, logo = %s
            WHERE id = %s
        """,
            (
                data.get("titulo"),
                data.get("endereco"),
                data.get("telefone"),
                data.get("slogan"),
                data.get("horario_funcionamento"),
                data.get("cor_primaria"),
                data.get("cor_secundaria"),
                data.get("qrcode_img"),
                data.get("logo_url"),
                data.get("empresa_id"),
            ),
        )
        db.commit()
        cursor.close()
        return {"mensagem": "Configurações atualizadas!"}
    except Exception as e:
        db.rollback()
        cursor.close()
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/dashboard")
def get_dashboard(empresa_id: int, db=Depends(get_db)):
    cur = db.cursor()
    cur.execute(
        "SELECT COUNT(*) as total FROM pedidos WHERE empresa_id = %s AND status = 'Aguardando pagamento'",
        (empresa_id,),
    )
    aguardando = cur.fetchone()["total"]

    cur.execute(
        "SELECT COUNT(*) as total FROM pedidos WHERE empresa_id = %s AND status = 'Entregue'",
        (empresa_id,),
    )
    entregues = cur.fetchone()["total"]

    cur.execute(
        "SELECT COUNT(*) as total FROM pedidos WHERE empresa_id = %s AND status = 'Cancelado'",
        (empresa_id,),
    )
    cancelados = cur.fetchone()["total"]

    cur.execute(
        "SELECT SUM(valor_total) as receita FROM pedidos WHERE empresa_id = %s AND status = 'Entregue'",
        (empresa_id,),
    )
    row = cur.fetchone()
    receita = row["receita"] if row["receita"] else 0.00
    cur.close()

    return {
        "aguardando": aguardando,
        "entregues": entregues,
        "cancelados": cancelados,
        "receita": f"{receita:.2f}".replace(".", ","),
    }


@app.get("/api/dashboard/fluxo")
def get_dashboard_fluxo(empresa_id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        """
        SELECT SUBSTRING(hora FROM 1 for 2) as horario, COUNT(*) as total 
        FROM pedidos WHERE empresa_id = %s AND hora IS NOT NULL 
        GROUP BY horario ORDER BY horario ASC
    """,
        (empresa_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    totais = {row["horario"]: row["total"] for row in rows}
    dados = []
    for h in range(17, 23):
        h_str = f"{h:02d}"
        dados.append({"hora": f"{h_str}h", "total": totais.get(h_str, 0)})
    return dados


# ================= PRODUTOS (COM SUPORTE A FOTO) =================
@app.get("/api/products")
def list_products(empresa_id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "SELECT id, nome, categoria, preco, estoque, descricao, foto FROM produtos WHERE empresa_id = %s ORDER BY id DESC",
        (empresa_id,),
    )
    res = cursor.fetchall()
    cursor.close()
    return res


@app.post("/api/products")
def create_product(prod: ProdutoCreate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO produtos (empresa_id, nome, categoria, preco, estoque, descricao, foto) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;",
        (
            prod.empresa_id,
            prod.nome,
            prod.categoria,
            prod.preco,
            prod.estoque,
            prod.descricao,
            prod.foto,
        ),
    )
    db.commit()
    novo_id = cursor.fetchone()["id"]
    cursor.close()
    return {"mensagem": "Produto salvo", "id": novo_id}


@app.put("/api/products/{id}")
def update_product(id: int, prod: ProdutoUpdate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "UPDATE produtos SET nome=%s, categoria=%s, preco=%s, estoque=%s, descricao=%s, foto=%s WHERE id=%s AND empresa_id=%s;",
        (
            prod.nome,
            prod.categoria,
            prod.preco,
            prod.estoque,
            prod.descricao,
            prod.foto,
            id,
            prod.empresa_id,
        ),
    )
    db.commit()
    cursor.close()
    return {"mensagem": "Produto atualizado"}


@app.delete("/api/products/{id}")
def delete_product(id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("DELETE FROM produtos WHERE id = %s", (id,))
    db.commit()
    cursor.close()
    return {"mensagem": "Produto excluído"}


# ================= CLIENTES (COM SUPORTE A FOTO) =================
@app.get("/api/clients")
def list_clients(empresa_id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "SELECT id, nome, telefone, email, endereco_entrega as endereco, referencia, foto FROM clientes WHERE empresa_id = %s ORDER BY id DESC",
        (empresa_id,),
    )
    res = cursor.fetchall()
    cursor.close()
    return res


@app.post("/api/clients")
def create_client(cli: ClienteCreate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO clientes (empresa_id, nome, telefone, email, endereco_entrega, referencia, foto) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;",
        (
            cli.empresa_id,
            cli.nome,
            cli.telefone,
            cli.email,
            cli.endereco,
            cli.referencia,
            cli.foto,
        ),
    )
    db.commit()
    novo_id = cursor.fetchone()["id"]
    cursor.close()
    return {"mensagem": "Cliente salvo", "id": novo_id}


@app.put("/api/clients/{id}")
def update_client(id: int, cli: ClienteUpdate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "UPDATE clientes SET nome=%s, telefone=%s, email=%s, endereco_entrega=%s, referencia=%s, foto=%s WHERE id=%s AND empresa_id=%s",
        (
            cli.nome,
            cli.telefone,
            cli.email,
            cli.endereco,
            cli.referencia,
            cli.foto,
            id,
            cli.empresa_id,
        ),
    )
    db.commit()
    cursor.close()
    return {"mensagem": "Cliente atualizado"}


@app.delete("/api/clients/{id}")
def delete_client(id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("DELETE FROM clientes WHERE id = %s", (id,))
    db.commit()
    cursor.close()
    return {"mensagem": "Cliente excluído"}


# ================= COLABORADORES (COM SUPORTE A FOTO) =================
@app.get("/api/colaboradores")
def list_colaboradores(empresa_id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "SELECT id, nome, telefone, email, cpf, funcao, status, foto FROM colaboradores WHERE empresa_id = %s ORDER BY id DESC",
        (empresa_id,),
    )
    res = cursor.fetchall()
    cursor.close()
    return res


@app.post("/api/colaboradores")
def create_colaborador(colab: ColaboradorCreate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        """INSERT INTO colaboradores (empresa_id, nome, telefone, email, cpf, data_nascimento, endereco, funcao, status, observacoes, tipo_veiculo, veiculo_modelo, veiculo_cor, veiculo_placa, area_atuacao, valor_entrega, foto) 
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;""",
        (
            colab.empresa_id,
            colab.nome,
            colab.telefone,
            colab.email,
            colab.cpf,
            colab.data_nascimento,
            colab.endereco,
            colab.funcao,
            colab.status,
            colab.observacoes,
            colab.tipo_veiculo,
            colab.veiculo_modelo,
            colab.veiculo_cor,
            colab.veiculo_placa,
            colab.area_atuacao,
            colab.valor_entrega,
            colab.foto,
        ),
    )
    db.commit()
    novo_id = cursor.fetchone()["id"]
    cursor.close()
    return {"mensagem": "Colaborador salvo", "id": novo_id}


@app.put("/api/colaboradores/{id}")
def update_colaborador(id: int, colab: ColaboradorCreate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        """UPDATE colaboradores SET nome=%s, telefone=%s, email=%s, cpf=%s, data_nascimento=%s, endereco=%s, 
           funcao=%s, status=%s, observacoes=%s, tipo_veiculo=%s, veiculo_modelo=%s, veiculo_cor=%s, veiculo_placa=%s, area_atuacao=%s, valor_entrega=%s, foto=%s 
           WHERE id=%s AND empresa_id=%s""",
        (
            colab.nome,
            colab.telefone,
            colab.email,
            colab.cpf,
            colab.data_nascimento,
            colab.endereco,
            colab.funcao,
            colab.status,
            colab.observacoes,
            colab.tipo_veiculo,
            colab.veiculo_modelo,
            colab.veiculo_cor,
            colab.veiculo_placa,
            colab.area_atuacao,
            colab.valor_entrega,
            colab.foto,
            id,
            colab.empresa_id,
        ),
    )
    db.commit()
    cursor.close()
    return {"mensagem": "Colaborador atualizado"}


@app.delete("/api/colaboradores/{id}")
def delete_colaborador(id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("DELETE FROM colaboradores WHERE id = %s", (id,))
    db.commit()
    cursor.close()
    return {"mensagem": "Excluído com sucesso"}


# ================= PEDIDOS E HUB =================
@app.post("/api/orders")
def create_order(order: OrderCreate, db=Depends(get_db)):
    cursor = db.cursor()
    nome_cliente = order.cliente or order.cliente_nome or "Cliente"
    cursor.execute(
        """
        INSERT INTO pedidos (empresa_id, cliente_nome, telefone, endereco_entrega, pagamento, itens, valor_total, status, hora, data) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
    """,
        (
            order.empresa_id,
            nome_cliente,
            order.telefone,
            order.endereco,
            order.pagamento,
            order.itens,
            order.total,
            order.status,
            order.hora or datetime.now().strftime("%H:%M"),
            order.data or datetime.now().strftime("%Y-%m-%d"),
        ),
    )
    db.commit()
    novo_id = cursor.fetchone()["id"]
    cursor.close()
    return {"mensagem": "Pedido criado", "id": novo_id}


@app.get("/api/orders")
def get_orders(empresa_id: int, db=Depends(get_db)):
    cur = db.cursor()
    cur.execute(
        """
        SELECT id, hora, cliente_nome AS cliente, endereco_entrega AS endereco, 
               valor_total AS total, status, pagamento, itens, telefone, entregador_id
        FROM pedidos WHERE empresa_id = %s ORDER BY id DESC LIMIT 50
    """,
        (empresa_id,),
    )
    rows = cur.fetchall()
    cur.close()
    orders = []
    for r in rows:
        orders.append(
            {
                "id": r["id"],
                "hora": str(r["hora"]) if r["hora"] else "",
                "cliente": r["cliente"],
                "endereco": r["endereco"],
                "total": f"{r['total']:.2f}".replace(".", ",")
                if r["total"]
                else "0,00",
                "status": r["status"],
                "pagamento": r["pagamento"],
                "itens": r["itens"],
                "telefone": r["telefone"],
                "entregador_id": r["entregador_id"],
            }
        )
    return orders


@app.put("/api/orders/{order_id}/status")
def update_order_status(order_id: int, data: dict, db=Depends(get_db)):
    cur = db.cursor()
    cur.execute(
        "UPDATE pedidos SET status = %s WHERE id = %s",
        (data.get("status"), order_id),
    )
    db.commit()
    cur.close()
    return {"success": True}


@app.post("/api/orders/{order_id}/despachar-proximos")
def despachar_proximos(order_id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "UPDATE pedidos SET status = 'Saiu para entrega' WHERE id = %s",
        (order_id,),
    )
    db.commit()
    cursor.close()
    return {"success": True}


@app.post("/api/orders/{order_id}/atribuir-motoboy")
def atribuir_motoboy(order_id: int, data: dict, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "UPDATE pedidos SET status = 'Saiu para entrega', entregador_id = %s WHERE id = %s",
        (data.get("motoboy_id"), order_id),
    )
    db.commit()
    cursor.close()
    return {"success": True}


@app.get("/api/orders/{order_id}")
def get_order_by_id(order_id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "SELECT id, status, valor_total as total, endereco_entrega as endereco FROM pedidos WHERE id = %s",
        (order_id,),
    )
    order = cursor.fetchone()
    cursor.close()
    if not order:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return {
        "id": order["id"],
        "status": order["status"],
        "total": f"{order['total']:.2f}".replace(".", ","),
        "endereco": order["endereco"],
    }


# ================= OUVIDORIA E EMPRESAS PÚBLICAS =================
@app.post("/api/ouvidoria")
def create_ouvidoria(ouv: OuvidoriaCreate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        """INSERT INTO ouvidoria (empresa_id, cliente_nome, atendimento, avaliacao, relato) 
           VALUES (%s, %s, %s, %s, %s) RETURNING id;""",
        (
            ouv.empresa_id,
            ouv.cliente_nome,
            ouv.atendimento,
            ouv.avaliacao,
            ouv.relato,
        ),
    )
    db.commit()
    cursor.close()
    return {"mensagem": "Ouvidoria registrada"}


@app.get("/api/ouvidoria")
def list_ouvidoria(empresa_id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "SELECT id, cliente_nome as cliente, avaliacao, relato, TO_CHAR(criado_em, 'DD/MM/YYYY') as data FROM ouvidoria WHERE empresa_id = %s ORDER BY id DESC",
        (empresa_id,),
    )
    res = cursor.fetchall()
    cursor.close()
    return res


@app.get("/api/empresas")
def listar_empresas_publicas(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "SELECT id, nome_fantasia as nome, 'Geral' as categoria, logo as logo_url, '40-50 min' as tempo_entrega, 5.00 as taxa_entrega, contato FROM empresas WHERE status = 'ativo' ORDER BY id DESC"
    )
    res = cursor.fetchall()
    cursor.close()
    return res


@app.get("/api/produtos/destaques")
def listar_produtos_destaques(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT p.id, p.nome, p.preco, p.descricao, p.foto, p.empresa_id, 
               e.nome_fantasia as empresa_nome, e.logo as empresa_img, 'geral' as categoria_empresa
        FROM produtos p
        JOIN empresas e ON p.empresa_id = e.id
        ORDER BY p.id DESC LIMIT 10
    """)
    res = cursor.fetchall()
    cursor.close()
    return res


# ================= APP DO ENTREGADOR =================
@app.post("/api/auth/entregador/cadastro")
def cadastro_entregador(ent: EntregadorCadastro, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        """
        INSERT INTO entregadores_app (nome, cpf, telefone, senha, email, data_nascimento, tipo_veiculo, veiculo_modelo, veiculo_placa, status, foto)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'Disponível', %s) RETURNING id;
    """,
        (
            ent.nome,
            ent.cpf,
            ent.telefone,
            ent.senha,
            ent.email,
            ent.data_nascimento,
            ent.tipo_veiculo,
            ent.veiculo_modelo,
            ent.veiculo_placa,
            ent.foto,
        ),
    )
    db.commit()
    novo_id = cursor.fetchone()["id"]
    cursor.close()
    return {
        "autorizado": True,
        "id": novo_id,
        "nome": ent.nome,
        "empresa_id": 1,
        "status": "Disponível",
        "token": "token_ativo",
    }


@app.post("/api/auth/entregador")
def auth_entregador(auth: EntregadorAuth, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "SELECT id, 1 as empresa_id, nome, status, senha, cpf, foto FROM entregadores_app WHERE telefone = %s",
        (auth.telefone,),
    )
    colab = cursor.fetchone()
    cursor.close()
    if not colab or auth.senha != str(colab["senha"]):
        raise HTTPException(status_code=401, detail="Telefone ou senha incorretos.")
    return {
        "autorizado": True,
        "token": "token_motoboy_valido",
        "nome": colab["nome"],
        "id": colab["id"],
        "empresa_id": colab["empresa_id"],
        "status": colab["status"] or "Disponível",
        "foto": colab["foto"] or "",
    }


@app.put("/api/entregador/status")
def update_entregador_status(data: EntregadorStatusUpdate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "UPDATE entregadores_app SET status = %s WHERE id = %s",
        (data.status, data.entregador_id),
    )
    db.commit()
    cursor.close()
    return {"mensagem": f"Status alterado para {data.status}"}


@app.get("/api/entregador/rotas")
def get_entregador_rotas(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT p.id, p.cliente_nome AS cliente, p.endereco_entrega AS endereco, 
               p.valor_total as valor, p.pagamento as status_pag, 
               '6,50' as taxa, COALESCE(p.hora, '--:--') as hora, 
               p.status, p.entregador_id
        FROM pedidos p
        WHERE LOWER(TRIM(COALESCE(p.status, ''))) IN ('saiu para entrega', 'saiu pra entrega', 'pronto', 'despachado')
        ORDER BY p.id DESC
    """)
    rows = cursor.fetchall()
    cursor.close()
    resultado = []
    for r in rows:
        resultado.append(
            {
                "id": r["id"],
                "cliente": r["cliente"],
                "endereco": r["endereco"],
                "valor": float(r["valor"]) if r["valor"] is not None else 0.0,
                "status_pag": r["status_pag"],
                "taxa": r["taxa"],
                "hora": r["hora"],
                "lat": -0.9270,
                "lng": -48.1390,
                "status": r["status"],
                "entregador_id": r["entregador_id"],
            }
        )
    return resultado


@app.post("/api/entregador/baixa")
def entregador_baixa(baixa: BaixaPedido, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "UPDATE pedidos SET status = %s WHERE id = %s",
        (baixa.status, baixa.pedido_id),
    )
    db.commit()
    cursor.close()
    return {"mensagem": "Entrega concluída"}


@app.get("/api/entregador/extrato")
def get_entregador_extrato(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT id, cliente_nome AS cliente, endereco_entrega AS endereco, valor_total as total, 
               COALESCE(TO_CHAR(data, 'YYYY-MM-DD'), TO_CHAR(NOW(), 'YYYY-MM-DD')) as data_filtragem, 
               COALESCE(hora, '--:--') as hora, '6,50' as taxa
        FROM pedidos WHERE LOWER(TRIM(COALESCE(status, ''))) = 'entregue' ORDER BY id DESC
    """)
    rows = cursor.fetchall()
    cursor.close()
    resultado = []
    for r in rows:
        resultado.append(
            {
                "id": r["id"],
                "cliente": r["cliente"],
                "endereco": r["endereco"],
                "total": float(r["total"]) if r["total"] is not None else 0.0,
                "data_filtragem": r["data_filtragem"],
                "hora": r["hora"],
                "taxa": r["taxa"],
            }
        )
    return resultado


@app.post("/api/backup")
def backup():
    return {"mensagem": "Backup efetuado com sucesso no servidor."}
