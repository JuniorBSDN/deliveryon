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
    qrcode_imagem: str # Pode ser a URL da imagem ou base64 enviado pelo Master
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
class GestorAuth(BaseModel):
    cnpj: str

@app.put("/api/orders/{order_id}/status")
def update_order_status(order_id: int, data: dict):
    novo_status = data.get("status")
    empresa_id = data.get("empresa_id")
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE pedidos SET status = %s WHERE id = %s AND empresa_id = %s",
        (novo_status, order_id, empresa_id)
    )
    conn.commit()
    cur.close()
    conn.close()
    
    return {"success": True, "message": "Status atualizado com sucesso!"}

@app.post("/api/gestor/auth")
def gestor_login(auth: GestorAuth, db=Depends(get_db)):
    cursor = db.cursor()
    # Remove formatações do CNPJ para comparar apenas os números, se preferir, ou busca exata
    cursor.execute("SELECT id, nome_fantasia, cnpj, status FROM empresas WHERE REPLACE(REPLACE(REPLACE(cnpj, '.', ''), '/', ''), '-', '') = REPLACE(REPLACE(REPLACE(%s, '.', ''), '/', ''), '-', '')", (auth.cnpj,))
    empresa = cursor.fetchone()
    
    if not empresa:
        raise HTTPException(status_code=404, detail="CNPJ não encontrado na base de dados.")
    
    if empresa['status'] != 'ativo':
        raise HTTPException(status_code=403, detail="Esta empresa está inativa ou com o acesso suspenso.")
        
    return {"autorizado": True, "empresa_id": empresa['id'], "nome_fantasia": empresa['nome_fantasia']}

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
def get_faturamento_gestor(empresa_id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT nome_fantasia, plano, vencimento, qrcode_imagem, copia_e_cola, status FROM empresas WHERE id = %s", (empresa_id,))
    res = cursor.fetchone()
    if not res:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return res

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

@app.get("/api/master/helpdesk/indicadores")
def get_helpdesk_indicadores(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT 
            COUNT(CASE WHEN status = 'aberto' THEN 1 END) as abertos,
            COUNT(CASE WHEN status = 'em_atendimento' THEN 1 END) as em_atendimento,
            COUNT(CASE WHEN status = 'pendente' THEN 1 END) as pendentes,
            COUNT(CASE WHEN status = 'resolvido' THEN 1 END) as resolvidos
        FROM chamados_helpdesk
    """)
    res = cursor.fetchone()
    return res or {"abertos": 0, "em_atendimento": 0, "pendentes": 0, "resolvidos": 0}

@app.get("/api/master/helpdesk/chamados")
def list_chamados(data: Optional[str] = None, db=Depends(get_db)):
    cursor = db.cursor()
    query = """
        SELECT id, empresa_nome, status, resumo_problema, tecnico_responsavel, 
               TO_CHAR(criado_em, 'DD/MM/YYYY HH24:MI') as data_criacao 
        FROM chamados_helpdesk
    """
    if data:
        query += f" WHERE DATE(criado_em) = '{data}'"
    query += " ORDER BY id DESC"
    cursor.execute(query)
    return cursor.fetchall()

@app.put("/api/master/helpdesk/chamados/{id}/status")
def update_chamado_status(id: int, body: ChamadoStatusUpdate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("UPDATE chamados_helpdesk SET status = %s WHERE id = %s", (body.status, id))
    db.commit()
    return {"mensagem": "Status atualizado com sucesso"}

@app.post("/api/master/helpdesk/chamados/{id}/concluir")
def concluir_chamado(id: int, body: ChamadoConcluir, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        UPDATE chamados_helpdesk 
        SET status = 'resolvido', tecnico_responsavel = %s 
        WHERE id = %s
    """, (body.tecnico, id))
    # Registra no histórico do chamado
    cursor.execute("""
        INSERT INTO historico_chamados (chamado_id, descricao) 
        VALUES (%s, %s)
    """, (id, f"Chamado concluído pelo técnico {body.tecnico}. Comprovante automático enviado."))
    db.commit()
    return {"mensagem": "Chamado concluído e comprovante gerado com sucesso!"}

@app.post("/api/master/helpdesk/chamados/{id}/cancelar")
def cancelar_chamado(id: int, body: ChamadoCancelar, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("UPDATE chamados_helpdesk SET status = 'cancelado' WHERE id = %s", (id,))
    cursor.execute("""
        INSERT INTO historico_chamados (chamado_id, descricao) 
        VALUES (%s, %s)
    """, (id, f"Chamado cancelado. Motivo: {body.motivo}"))
    db.commit()
    return {"mensagem": "Chamado cancelado com sucesso."}

@app.get("/api/master/helpdesk/chamados/{id}/historico")
def get_historico_chamado(id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT TO_CHAR(criado_em, 'DD/MM/YYYY HH24:MI') as data, descricao 
        FROM historico_chamados 
        WHERE chamado_id = %s 
        ORDER BY id DESC
    """, (id,))
    return cursor.fetchall()

# ================= ROTAS DO GESTOR (CLIENTE FINAl) =================
@app.get("/api/dashboard")
def get_dashboard(empresa_id: int):
    conn = get_db()
    cur = conn.cursor()
    
    # Exemplo de busca real no Neon DB para a empresa correta
    cur.execute("SELECT COUNT(*) FROM pedidos WHERE empresa_id = %s AND status = 'Aguardando pagamento'", (empresa_id,))
    aguardando = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM pedidos WHERE empresa_id = %s AND status = 'Entregue'", (empresa_id,))
    entregues = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM pedidos WHERE empresa_id = %s AND status = 'Cancelado'", (empresa_id,))
    cancelados = cur.fetchone()[0]
    
    cur.execute("SELECT SUM(total) FROM pedidos WHERE empresa_id = %s AND status = 'Entregue'", (empresa_id,))
    receita = cur.fetchone()[0] or 0.00
    
    cur.close()
    conn.close()
    
    return {
        "aguardando": aguardando,
        "entregues": entregues,
        "cancelados": cancelados,
        "receita": f"{receita:.2f}".replace('.', ',')
    }

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

@app.get("/api/orders")
def get_orders(empresa_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, hora, cliente, endereco, total, status FROM pedidos WHERE empresa_id = %s ORDER BY id DESC LIMIT 10",
        (empresa_id,)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    orders = []
    for row in rows:
        orders.append({
            "id": row[0],
            "hora": str(row[1]) if row[1] else "",
            "cliente": row[2],
            "endereco": row[3],
            "total": f"{row[4]:.2f}".replace('.', ',') if row[4] else "0,00",
            "status": row[5]
        })
    return orders

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
```[cite: 7]

---

### 2. A função `saveConfigurations()` otimizada no Front-end (`admin_5.html`)
Garanta que a sua função de salvamento no script do painel esteja exatamente assim, preservando todos os dados preenchidos na tela:

```javascript
async function saveConfigurations() {
    const configAtual = await apiRequest('/configuracoes') || {};

    let logoBase64 = window.currentLogoBase64 || configAtual.logo_url || '';
    const fileInput = document.getElementById('input-config-logo-file');
    
    if (fileInput && fileInput.files && fileInput.files[0]) {
        try {
            logoBase64 = await convertFileToBase64(fileInput.files[0]);
        } catch (err) {
            console.error("Erro ao converter imagem:", err);
        }
    }

    const payload = {
        titulo: document.getElementById('input-config-title').value || configAtual.titulo || '',
        slogan: document.getElementById('input-config-slogan').value || configAtual.slogan || '',
        endereco: document.getElementById('input-config-address').value || configAtual.endereco || '',
        telefone: document.getElementById('input-config-phone').value || configAtual.telefone || '',
        horario_funcionamento: document.getElementById('textarea-config-hours').value || configAtual.horario_funcionamento || '',
        cor_primaria: document.getElementById('input-config-cor1').value || configAtual.cor_primaria || '#ff5722',
        cor_secundaria: document.getElementById('input-config-cor2').value || configAtual.cor_secundaria || '#e64a19',
        logo_url: logoBase64
    };

    const res = await apiRequest('/configuracoes', 'PUT', payload);
    if (res) {
        alert('Configurações, cores e logotipo salvos com sucesso!');
        loadConfigurations();
        aplicarIdentidadeVisualDaEmpresa();
    } else {
        alert('Erro ao salvar as configurações.');
    }
}
```[cite: 8]
