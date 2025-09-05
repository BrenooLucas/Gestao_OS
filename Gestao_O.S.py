import tkinter as tk
from tkinter import ttk, messagebox, filedialog, Menu
import sqlite3
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import random
import errno

########################################################################################################################

DB_NAME = "ordens_servico.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("PRAGMA journal_mode=WAL;")  # Ativa WAL

        ############Nova tabela com constraints###########
        c.execute('''
            CREATE TABLE IF NOT EXISTS ordens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_profissional TEXT NOT NULL,
                nome_cliente TEXT NOT NULL,
                servico TEXT NOT NULL,
                valor REAL NOT NULL CHECK (valor >= 0),
                detalhes TEXT,
                peca_substituida TEXT,
                numero_ordem TEXT NOT NULL UNIQUE,
                status TEXT DEFAULT 'PENDENTE' CHECK (status IN ('PENDENTE', 'EM ANDAMENTO', 'FINALIZADA')),
                data_finalizacao TEXT
            )
        ''')
    conn.commit()
    conn.close()

###########FUNÇÕES#######################################################

def mostrar_relatorio_financeiro():
    relatorio_win = tk.Toplevel(root)
    relatorio_win.withdraw()  # Oculta a janela inicialmente

    relatorio_win.title("Relatório Financeiro")
    relatorio_win.geometry("700x450")
    relatorio_win.resizable(False, False)
    relatorio_win.configure(bg="#808080")
    relatorio_win.iconbitmap("pc.ico")

    relatorio_win.transient(root)

    ############Executa a carga do banco de dados###########

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM ordens WHERE status = 'FINALIZADA'")
        finalizadas = c.fetchall()

        c.execute("SELECT * FROM ordens WHERE status != 'FINALIZADA'")
        pendentes = c.fetchall()

    def somar_valores(ordens):
        return sum(float(o[4]) for o in ordens)

    total_faturado = somar_valores(finalizadas)
    total_pendente = somar_valores(pendentes)

    estilo = ttk.Style()
    estilo.configure("Treeview", background="#f0f0f0", fieldbackground="#f0f0f0", foreground="black")

    frame_faturado = tk.Frame(relatorio_win, bg="#C0C0C0") #Altera a cor da faixa
    frame_faturado.pack(fill="x")

    lbl_faturado = tk.Label(
        frame_faturado,
        text=f"✅ Total Faturado: R$ {total_faturado:,.2f} ".replace(",", "X").replace(".", ",").replace("X", "."),
        bg="#C0C0C0", fg="green", font=("Roboto", 11, "bold"))
    lbl_faturado.pack(pady=(10, 0))

    frame_pendente = tk.Frame(relatorio_win, bg="#C0C0C0") #altera cor da outra faixa
    frame_pendente.pack(fill="x")

    lbl_pendente = tk.Label(
        frame_pendente,
        text=f"⌛ Total a Receber: R$ {total_pendente:,.2f} ".replace(",", "X").replace(".", ",").replace("X", "."),
        bg="#C0C0C0", fg="red", font=("Roboto", 11, "bold"))
    lbl_pendente.pack(pady=(0, 10))

    # Frame que conterá a Treeview + Scrollbar
    frame_tree = tk.Frame(relatorio_win, bg="#808080")
    frame_tree.pack(fill="both", expand=True, padx=10, pady=10)

    scrollbar_y = ttk.Scrollbar(frame_tree, orient="vertical")
    scrollbar_y.pack(side="right", fill="y")

    tree_relatorio = ttk.Treeview(
        frame_tree,
        columns=("numero", "cliente", "valor", "status", "data"),
        show="headings",
        yscrollcommand=scrollbar_y.set
    )
    scrollbar_y.config(command=tree_relatorio.yview)

    tree_relatorio.heading("numero", text="Nº Ordem")
    tree_relatorio.heading("cliente", text="Cliente")
    tree_relatorio.heading("valor", text="Valor (R$)")
    tree_relatorio.heading("status", text="Status")
    tree_relatorio.heading("data", text="Finalizado em")

    tree_relatorio.column("numero", width=80, anchor="center")
    tree_relatorio.column("cliente", width=150)
    tree_relatorio.column("valor", width=100, anchor="center")
    tree_relatorio.column("status", width=100, anchor="center")
    tree_relatorio.column("data", width=100, anchor="center")

    tree_relatorio.pack(side="left", fill="both", expand=True)

    for ordem in finalizadas + pendentes:
        _, _, cliente, _, valor, _, _, numero, status, data = ordem
        data = data if data else "-"
        icone_status = "✅" if status == "FINALIZADA" else "⌛"

        tree_relatorio.insert("", "end", values=(
            numero,
            cliente,
            f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            f"{icone_status} {status.capitalize()}",
            data
        ))

    frame_botoes = tk.Frame(relatorio_win, bg="#808080")
    frame_botoes.pack(pady=(5, 15))

    btn_pdf = tk.Button(
        frame_botoes, text="Gerar PDF do Relatório", bg="green", fg="white",
        relief="flat", highlightthickness=0, cursor="hand2",
        command=lambda: gerar_pdf_relatorio(relatorio_win)
    )
    btn_pdf.pack(side="left", padx=10)

    btn_fechar = tk.Button(
        frame_botoes, text="Fechar ❌", bg="red", fg="white",
        relief="flat", highlightthickness=0, cursor="hand2",
        command=relatorio_win.destroy
    )
    btn_fechar.pack(side="left", padx=10)

    def click_relatorio(event):
        widget = event.widget
        if widget == tree_relatorio:
            region = tree_relatorio.identify("region", event.x, event.y)
            if region not in ("cell", "tree"):
                tree_relatorio.selection_remove(tree_relatorio.selection())
            return
        if isinstance(widget, tk.Button):
            return
        tree_relatorio.selection_remove(tree_relatorio.selection())

    relatorio_win.bind("<Button-1>", click_relatorio)
    relatorio_win.deiconify()
    relatorio_win.grab_set()
def gerar_pdf_relatorio(janela):

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM ordens WHERE status = 'FINALIZADA'")
        finalizadas = c.fetchall()
        c.execute("SELECT * FROM ordens WHERE status != 'FINALIZADA'")
        pendentes = c.fetchall()

    total_faturado = sum(float(o[4]) for o in finalizadas)
    total_pendente = sum(float(o[4]) for o in pendentes)

    file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
    if not file_path:
        return

    doc = SimpleDocTemplate(file_path, pagesize=A4)
    estilos = getSampleStyleSheet()
    elementos = []

    # Cabeçalho do relatório
    elementos.append(Paragraph("Relatório Financeiro", estilos["Title"]))
    elementos.append(Spacer(1, 10))
    elementos.append(Paragraph(
        f"💰 Total Faturado: R$ {total_faturado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        estilos["Normal"]))
    elementos.append(Paragraph(
        f"🕓 Total a Receber: R$ {total_pendente:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        estilos["Normal"]))
    elementos.append(Spacer(1, 12))

    # Dados da tabela com cabeçalho e ícone na primeira coluna
    dados = [["✔", "Nº OS", "Cliente", "Valor (R$)", "Status", "Finalizado em"]]

    for ordem in finalizadas + pendentes:
        _, _, cliente, _, valor, _, _, numero, status, data = ordem
        data = data if data else "-"
        dados.append([
            "✔" if status == "FINALIZADA" else "⌛",
            numero,
            cliente,
            f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            status,
            data
        ])

    tabela = Table(dados, repeatRows=1, hAlign='LEFT')
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))

    elementos.append(tabela)

    try:
        doc.build(elementos)
        messagebox.showinfo("PDF Gerado", f"Relatório salvo em:\n{file_path}", parent=janela)
        janela.destroy()

    except PermissionError:
        messagebox.showerror("Permissão Negada","Você não tem permissão para salvar neste local ou o arquivo já está aberto em outro local.",parent=janela)



    except FileNotFoundError:
        messagebox.showerror("Caminho Inválido",
                             "O local de destino não foi encontrado. Verifique se a pasta ainda existe.",
                             parent=janela)

    except OSError as e:
        if e.errno == errno.EACCES:
            messagebox.showerror("Acesso Negado",
                                 "Permissão negada. Verifique as permissões da pasta ou se o arquivo está em uso.",
                                 parent=janela)
        elif e.errno == errno.ENOSPC:
            messagebox.showerror("Sem Espaço",
                                 "Sem espaço suficiente em disco. Libere espaço e tente novamente.",
                                 parent=janela)
        elif e.errno == errno.ENAMETOOLONG:
            messagebox.showerror("Nome Muito Longo",
                                 "O nome do arquivo é muito longo. Use um nome mais curto ou salve em outro local.",
                                 parent=janela)
        else:
            messagebox.showerror("Erro do Sistema",
                                 f"Ocorreu um erro ao salvar o PDF: {e.strerror}",
                                 parent=janela)

    except ValueError as e:
        messagebox.showerror("Erro de Dados",
                             f"Dados inválidos ao montar o PDF:\n{e}",
                             parent=janela)

    except Exception as e:
        messagebox.showerror("Erro Desconhecido",
                             f"Ocorreu um erro inesperado ao gerar o PDF:\n{e}",
                             parent=janela)

def inserir_ordem(nome_profissional, nome_cliente, servico, valor, detalhes, peca_substituida, numero_ordem):
    campos = {
        "Nome do Profissional": nome_profissional,
        "Nome do Cliente": nome_cliente,
        "Serviço": servico,
        "Número da Ordem": numero_ordem,
        "Valor": valor,
        "Detalhes": detalhes,
        "Peça Trocada": peca_substituida
    }

    # Verifica se todos os campos estão vazios (None ou string em branco)
    if all((v is None or str(v).strip() == "") for v in campos.values()):
        messagebox.showwarning("Aviso", "Todos os campos estão vazios. Por favor, preencha-os!")
        return

    # Verifica se algum campo individual está vazio
    for nome_campo, valor_campo in campos.items():
        if valor_campo is None or str(valor_campo).strip() == "":
            messagebox.showwarning("Aviso", f"Preencha o campo: {nome_campo}")
            return

    # Validação do valor numérico
    try:
        valor = float(valor)
        if valor < 0:
            raise ValueError
    except ValueError:
        messagebox.showerror("Erro", "Valor deve ser um número positivo.")
        return

    # Inserção no banco
    try:
        with sqlite3.connect(DB_NAME, timeout=10) as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO ordens (
                    nome_profissional, nome_cliente, servico, valor, detalhes,
                    peca_substituida, numero_ordem, status, data_finalizacao
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDENTE', NULL)
            ''', (nome_profissional, nome_cliente, servico, valor, detalhes, peca_substituida, numero_ordem))

        for entry in entries:
            entry.delete(0, tk.END)

        carregar_ordens(entry_busca.get())
        messagebox.showinfo("Sucesso", f"Ordem Nº {numero_ordem} adicionada.")

    except sqlite3.IntegrityError:
        messagebox.showerror("Erro", f"Já existe uma ordem com o número {numero_ordem}.")
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            messagebox.showerror("Erro", "Banco de dados está bloqueado. Tente novamente.")
        else:
            messagebox.showerror("Erro", f"Erro operacional: {str(e)}")
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao inserir no banco: {str(e)}")
def carregar_ordens(filtro=""):
    # Limpa as linhas atuais da treeview
    for row in tree.get_children():
        tree.delete(row)

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        if filtro:
            c.execute("SELECT * FROM ordens WHERE nome_cliente LIKE ? OR numero_ordem LIKE ?",
                      (f"{filtro}%", f"{filtro}%"))
        else:
            c.execute("SELECT * FROM ordens")

        resultados = c.fetchall()

        # Mostrar mensagem só se o filtro NÃO estiver vazio
        if filtro:
            if not resultados:
                label_aviso_busca.config(text="Nenhuma O.S ou cliente encontrada(s).", fg="#FF0000")  # vermelho
            else:
                label_aviso_busca.config(text="Registro(s) encontrado(s).", fg="#008000")  # verde
        else:
            # Se filtro vazio, limpa mensagem (não mostra nada)
            label_aviso_busca.config(text="")

        for row in resultados:
            id_, prof, cliente, servico, valor, detalhes, peca, numero, status, data = row
            status_icone = "✅" if status == "FINALIZADA" else "⏳"
            tree.insert("", "end", values=(
                status_icone, numero, cliente, servico,
                formatar_valor(valor), prof, peca, detalhes, data or "-"
            ))

def excluir_ordem():
    item = tree.selection()
    if not item:
        messagebox.showwarning("Aviso", "Selecione uma ordem para excluir!")
        return

    item_selecionado = item[0]
    numero_ordem = tree.item(item_selecionado)["values"][1]

    confirmar = messagebox.askyesno(title="Confirmação", message=f"Deseja excluir Ordem Nº {numero_ordem}?")
    if not confirmar:
        return

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM ordens WHERE numero_ordem = ?", (numero_ordem,))
        conn.commit()
    carregar_ordens(entry_busca.get())

def finalizar_ordem():
    item = tree.selection()
    if not item:
        messagebox.showwarning("Aviso", "Selecione uma ordem para finalizar.")
        return

    item_selecionado = item[0]
    numero_ordem = tree.item(item_selecionado)["values"][1]

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT status FROM ordens WHERE numero_ordem = ?", (numero_ordem,))
        status = c.fetchone()

        if status and status[0] == "FINALIZADA":
            messagebox.showwarning("Aviso", "Essa ordem já está finalizada!")
            return  # aqui a conexão será fechada automaticamente pelo 'with'

        data = datetime.now().strftime("%d/%m/%Y")
        c.execute("UPDATE ordens SET status = 'FINALIZADA', data_finalizacao = ? WHERE numero_ordem = ?", (data, numero_ordem))
        conn.commit()

    carregar_ordens(entry_busca.get())

def desfazer_finalizacao():
    item = tree.selection()
    if not item:
        messagebox.showwarning("Aviso", "Selecione uma ordem para desfazer a finalização.")
        return

    item_selecionado = item[0]
    valores = tree.item(item_selecionado)["values"]
    numero_ordem = valores[1]

    # Conecta ao banco usando 'with' (fecha automaticamente)
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT status FROM ordens WHERE numero_ordem = ?", (numero_ordem,))
        resultado = c.fetchone()

        if not resultado:
            messagebox.showerror("Erro", "Número de ordem não encontrado no banco de dados.")
            return

        status_real = resultado[0]

        if status_real != "FINALIZADA":
            messagebox.showwarning("Aviso", "Essa ordem não está finalizada. Não há o que desfazer.")
            return

        # Se estiver finalizada, desfaz a finalização
        c.execute("UPDATE ordens SET status = 'PENDENTE', data_finalizacao = NULL WHERE numero_ordem = ?", (numero_ordem,))
        conn.commit()

    carregar_ordens(entry_busca.get())

def gerar_pdf():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM ordens WHERE status = 'FINALIZADA'")
        ordens = c.fetchall()

    if not ordens:
        messagebox.showwarning("Aviso", "Nenhuma ordem FINALIZADA para gerar PDF.")
        return

    file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
    if not file_path:
        return

    doc = SimpleDocTemplate(file_path, pagesize=A4, leftMargin=20, rightMargin=20)
    elementos = []

    estilos = getSampleStyleSheet()

    estilo_celula = ParagraphStyle(
        name='ConteudoPadrao',
        parent=estilos["Normal"],
        fontSize=8,
        leading=10,
        alignment=0  # LEFT
    )

    estilo_celula_centralizado = ParagraphStyle(
        name='ConteudoCentralizado',
        parent=estilos["Normal"],
        fontSize=8,
        leading=10,
        alignment=1  # CENTER
    )

    titulo = Paragraph("Ordens de Serviço Finalizadas", estilos['Title'])
    elementos.append(titulo)
    elementos.append(Spacer(1, 12))

    # Cabeçalho da tabela
    dados = [[
        Paragraph("✔", estilo_celula_centralizado),
        Paragraph("Nº OS", estilo_celula_centralizado),
        Paragraph("Cliente", estilo_celula_centralizado),
        Paragraph("Serviço", estilo_celula_centralizado),
        Paragraph("Valor (R$)", estilo_celula_centralizado),
        Paragraph("Profissional", estilo_celula_centralizado),
        Paragraph("Peça Trocada", estilo_celula_centralizado),
        Paragraph("Detalhes", estilo_celula_centralizado),
        Paragraph("Finalizado em", estilo_celula_centralizado),
    ]]

    for ordem in ordens:
        _, prof, cliente, servico, valor, detalhes, peca, numero, _, data_final = ordem
        data_final = data_final if data_final else "-"

        dados.append([
            Paragraph("✔", estilo_celula_centralizado),
            Paragraph(str(numero), estilo_celula_centralizado),  # Nº OS centralizado
            Paragraph(cliente, estilo_celula_centralizado),
            Paragraph(servico, estilo_celula_centralizado),
            Paragraph(f"{valor:.2f}", estilo_celula_centralizado),  # Valor centralizado
            Paragraph(prof, estilo_celula_centralizado),
            Paragraph(peca or "-", estilo_celula_centralizado),
            Paragraph(detalhes or "-", estilo_celula_centralizado),
            Paragraph(data_final, estilo_celula_centralizado),
        ])

    tabela = Table(dados, repeatRows=1, hAlign='LEFT')

    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
    ]))

    elementos.append(tabela)

    try:
        doc.build(elementos)
        messagebox.showinfo("PDF Gerado", f"PDF gerado com sucesso em:\n{file_path}")

    except PermissionError:
        messagebox.showerror("Permissão Negada",
                             "Permissão negada. Feche o arquivo se ele estiver aberto ou escolha outro local.")
    except FileNotFoundError:
        messagebox.showerror("Erro de Caminho", "O caminho do arquivo não foi encontrado. Tente novamente.")
    except IOError as e:
        if e.errno == errno.ENOSPC:
            messagebox.showerror("Erro de Espaço", "Sem espaço em disco para salvar o arquivo.")
        else:
            messagebox.showerror("Erro de Escrita", f"Erro ao salvar o arquivo:\n{e}")
    except Exception as e:
        messagebox.showerror("Erro Desconhecido", f"Ocorreu um erro inesperado ao gerar o PDF:\n{str(e)}")

def editar_ordem_existente():
    item = tree.selection()
    if not item:
        messagebox.showwarning("Aviso", "Selecione uma ordem para editar.")
        return

    item_id = item[0]
    valores = tree.item(item_id)['values']
    numero_ordem = valores[1]

    ############Criar nova janela de edição###########

    janela_edicao = tk.Toplevel(root,bg="#A9A9A9") #Altera cor da janela principal
    janela_edicao.title(f"Ordem Nº {numero_ordem}")
    janela_edicao.geometry("475x245")
    janela_edicao.transient(root)
    janela_edicao.grab_set()
    janela_edicao.resizable(False,False)
    janela_edicao.iconbitmap("pc.ico")

    labels_inline = ["Profissional", "Cliente", "Serviço", "Valor (R$)", "Peça trocada", "Detalhes"]
    entradas_inline = []

    for i, texto in enumerate(labels_inline):
        lbl = tk.Label(janela_edicao, text=texto, bg="#A9A9A9") #Altera cor de fundo do texto
        lbl.grid(row=i, column=0, sticky="e", padx=5, pady=5)
        ent = tk.Entry(janela_edicao, width=50, bg="#DCDCDC") #Altera cor do campo de entrada
        ent.grid(row=i, column=1, padx=5, pady=5)
        entradas_inline.append(ent)

    # Preenche os dados atuais
    entradas_inline[0].insert(0, valores[5])  # Profissional
    entradas_inline[1].insert(0, valores[2])  # Cliente
    entradas_inline[2].insert(0, valores[3])  # Serviço
    entradas_inline[3].insert(0, valores[4])  # Valor
    entradas_inline[4].insert(0, valores[6])  # Peça
    entradas_inline[5].insert(0, valores[7])  # Detalhes

    def salvar_edicao():
        novo_prof = entradas_inline[0].get()
        novo_cli = entradas_inline[1].get()
        novo_serv = entradas_inline[2].get()
        novo_valor = entradas_inline[3].get()
        nova_peca = entradas_inline[4].get()
        novos_detalhes = entradas_inline[5].get()

        if not novo_prof.strip() or not novo_cli.strip() or not novo_serv.strip():
            messagebox.showerror("Erro", "Campos obrigatórios não preenchidos.")
            return

        try:
            valor_tratado = novo_valor.replace(".", "").replace(",", ".")
            novo_valor_float = float(valor_tratado)
        except:
            messagebox.showerror("Erro", "Valor inválido.")
            return

        # Pega os valores antigos
        antigo_prof = valores[5]
        antigo_cli = valores[2]
        antigo_serv = valores[3]
        antigo_valor = float(str(valores[4]).replace(".", "").replace(",", "."))
        antiga_peca = valores[6]
        antigos_detalhes = valores[7]

        # Verifica se houve de fato alteração dos campos na janela de edição
        if (
                novo_prof == antigo_prof and
                novo_cli == antigo_cli and
                novo_serv == antigo_serv and
                novo_valor_float == antigo_valor and
                nova_peca == antiga_peca and
                novos_detalhes == antigos_detalhes
        ):
            messagebox.showwarning("Aviso", "Nenhuma alteração foi feita.")
            janela_edicao.destroy()
            return

        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute('''UPDATE ordens SET
                                nome_profissional = ?, nome_cliente = ?, servico = ?,
                                valor = ?, peca_substituida = ?, detalhes = ?
                            WHERE numero_ordem = ?''',
                      (novo_prof, novo_cli, novo_serv, novo_valor_float, nova_peca, novos_detalhes, numero_ordem))
            conn.commit()


        carregar_ordens(entry_busca.get())
        janela_edicao.destroy()

    frame_botoes = tk.Frame(janela_edicao, bg="#A9A9A9") #Altera cor de fundo frame botões
    frame_botoes.grid(row=len(labels_inline), column=0, columnspan=2, pady=20)

    btn_salvar = tk.Button(frame_botoes, text="Salvar Alterações", bg="green", fg="white",relief="flat", highlightthickness=0 ,command=salvar_edicao, cursor="hand2")
    btn_salvar.pack(side="left", padx=10)

    btn_fechar = tk.Button(frame_botoes, text="Fechar ❌", bg="red", fg="white", relief="flat", highlightthickness=0,command=janela_edicao.destroy, cursor="hand2")
    btn_fechar.pack(side="left", padx=10)

def gerar_numero_ordem():
    numero = random.randint(1, 99999)

    # Preenche o campo "Nº Ordem" (último campo dos entries)
    entries[-1].delete(0, tk.END)
    entries[-1].insert(0, str(numero))
def deletar_todos_registros():
    try:
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM ordens")
            total = c.fetchone()[0]

            if total == 0:
                messagebox.showwarning("Aviso", "Não há registros para excluir.")
                return

            resposta = messagebox.askyesno("Excluir", "Deseja deletar TODOS os registros?")
            if resposta:
                c.execute("DELETE FROM ordens")
                conn.commit()
                carregar_ordens(entry_busca.get())
                messagebox.showinfo("Sucesso", "Todos os registros foram excluídos com sucesso.")
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao excluir registros: {e}")

def formatar_valor(valor):
    try:
        valor_float = float(valor)
        return f"{valor_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return valor  # Retorna como está se falhar

def pdf_cliente():
    item = tree.selection()
    if not item:
        messagebox.showwarning("Aviso", "Selecione uma O.S para gerar o PDF.")
        return

    item_id = item[0]
    valores = tree.item(item_id)["values"]
    numero_ordem = valores[1]

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM ordens WHERE numero_ordem = ?", (numero_ordem,))
        ordem = c.fetchone()

    if not ordem:
        messagebox.showerror("Erro", f"Ordem Nº {numero_ordem} não encontrada.")
        return

    if ordem[8] != "FINALIZADA":
        messagebox.showwarning("Aviso", "FINALIZE a ORDEM para gerar o PDF ao cliente.")
        return

    _, profissional, cliente, servico, valor, detalhes, peca, numero, status, data_finalizacao = ordem

    janela_edicao = tk.Toplevel(root, bg="#A9A9A9")
    janela_edicao.title(f"Ordem Nº {numero}")
    janela_edicao.geometry("620x320")
    janela_edicao.transient(root)
    janela_edicao.grab_set()
    janela_edicao.resizable(False, False)
    janela_edicao.iconbitmap("pc.ico")

    # Flag para detectar se houve qualquer edição
    edicao_realizada = tk.BooleanVar(value=False)

    campos = {
        "Notebook / Desktop – Modelo": "",
        "Finalizado em": data_finalizacao or "",
        "Profissional": profissional,
        "Cliente": cliente,
        "Serviço": servico,
        "Valor": formatar_valor(valor),
        "N° Ordem de Serviço": numero,
    }

    entries_pdf = {}
    valores_originais = {}

    def marcar_edicao(*args):
        edicao_realizada.set(True)

    for i, (label_text, valor) in enumerate(campos.items()):
        lbl = tk.Label(janela_edicao, text=label_text + ":", bg="#A9A9A9")
        lbl.grid(row=i, column=0, sticky="e", padx=5, pady=2)
        ent = tk.Entry(janela_edicao, width=45, bg="#DCDCDC", fg="black")
        ent.insert(0, valor)
        ent.grid(row=i, column=1, padx=5, pady=2)

        if label_text == "Notebook / Desktop – Modelo":
            ent.config(state="normal")
        else:
            ent.config(state="readonly", readonlybackground="#DCDCDC", fg="black")

        # Detecta alterações no Entry
        ent.bind("<KeyRelease>", marcar_edicao)

        entries_pdf[label_text] = ent
        valores_originais[label_text] = valor.strip()

    lbl_parecer = tk.Label(janela_edicao, text="Parecer Técnico:", bg="#A9A9A9")
    lbl_parecer.grid(row=len(campos), column=0, sticky="ne", padx=5, pady=5)

    txt_parecer = tk.Text(janela_edicao, width=45, height=5, bg="#DCDCDC")
    txt_parecer.grid(row=len(campos), column=1, padx=5, pady=5)
    parecer_original = txt_parecer.get("1.0", tk.END).strip()

    # Detecta alterações no Text
    txt_parecer.bind("<KeyRelease>", lambda e: edicao_realizada.set(True))

    def habilitar_edicao():
        for ent in entries_pdf.values():
            ent.config(state="normal", bg="yellow")
        txt_parecer.config(state="normal", bg="yellow")

    def salvar_edicao():

        if not edicao_realizada.get():
            messagebox.showwarning("Aviso", "Nenhuma alteração foi feita.")
            return

        # Bloqueia novamente os campos, mas só mantém alguns liberados

        for campo, ent in entries_pdf.items():
            if campo == "Notebook / Desktop – Modelo":
                ent.config(state="normal", bg="#DCDCDC")  # Mantém habilitado
            else:
                ent.config(state="readonly", readonlybackground="#DCDCDC", fg="black", bg="#DCDCDC")

        txt_parecer.config(state="normal", bg="#DCDCDC")  # Mantém Parecer Técnico habilitado

        messagebox.showinfo("Edição Salva", "Informações atualizadas com sucesso.")

        edicao_realizada.set(False)  # Reset após salvar

    def fechar():
        janela_edicao.destroy()

    def gerar_pdf_cliente():
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.lib.enums import TA_JUSTIFY

        file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if not file_path:
            return

        try:
            doc = SimpleDocTemplate(
                file_path,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72,
            )

            estilo_titulo = ParagraphStyle(
                name="Titulo",
                fontName="Times-Roman",
                fontSize=14,
                alignment=1,
                spaceAfter=24,
                leading=16,
            )

            estilo_texto = ParagraphStyle(
                name="TextoNormal",
                fontName="Times-Roman",
                fontSize=12,
                leading=18,
                alignment=TA_JUSTIFY,
                leftIndent=0,
                rightIndent=0,
                firstLineIndent=1.25 * cm,
                spaceBefore=0,
                spaceAfter=12,
            )

            estilo_label = ParagraphStyle(
                name="Label",
                fontName="Times-Roman",
                fontSize=12,
                leading=18,
                leftIndent=0,
                spaceAfter=12,
            )

            elementos = []
            elementos.append(Paragraph("Informativo Sobre a Intervenção Realizada", estilo_titulo))
            elementos.append(Spacer(1, 12))

            for campo, ent in entries_pdf.items():
                valor = ent.get()
                elementos.append(Paragraph(f"<b>{campo}:</b> {valor}", estilo_label))

            elementos.append(Spacer(1, 6))
            elementos.append(Paragraph("<b>Parecer Técnico¹:</b>", estilo_label))

            parecer = txt_parecer.get("1.0", tk.END).strip()
            if not parecer:
                messagebox.showwarning("Aviso", "Digite o parecer técnico antes de gerar o PDF.")
                return
            elementos.append(Paragraph(parecer, estilo_texto))
            elementos.append(Spacer(1, 30))

            def rodape(canvas, doc):
                canvas.saveState()
                canvas.setFont("Times-Roman", 9)
                texto = ("¹ A fim de promover clareza ao cliente, esse arquivo serve exclusivamente "
                         "para informá-lo o que foi realizado em sua máquina.")
                canvas.drawString(doc.leftMargin, 1.7 * cm, texto)
                canvas.restoreState()

            doc.build(elementos, onFirstPage=rodape, onLaterPages=rodape)
            messagebox.showinfo("PDF Gerado", f"PDF gerado com sucesso:\n{file_path}")
            janela_edicao.destroy()

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao gerar PDF: {e}")

    ############# Botões #############

    tk.Button(janela_edicao, text="Gerar PDF", bg="green", fg="white", relief="flat", highlightthickness=0,
              cursor="hand2", command=gerar_pdf_cliente).place(x=230, y=275)
    tk.Button(janela_edicao, text="Editar", bg="blue", fg="white", relief="flat", highlightthickness=0,
              cursor="hand2", command=habilitar_edicao).place(x=300, y=275)
    tk.Button(janela_edicao, text="Salvar Edição", bg="black", fg="white", relief="flat", highlightthickness=0,
              cursor="hand2", command=salvar_edicao).place(x=350, y=275)
    tk.Button(janela_edicao, text="Fechar", bg="red", fg="white", relief="flat", highlightthickness=0,
              cursor="hand2", command=fechar).place(x=438, y=275)


############Interface###########

root = tk.Tk()
root.title("Gestão O.S")
root.geometry("1280x620")
# root.resizable(False,False)
root.configure(bg='#808080')
root.attributes("-fullscreen", True)
root.attributes("-fullscreen", False)
root.iconbitmap("pc.ico")

############ALTERA COR DA TREE VIEW###########

style = ttk.Style()
style.theme_use("default")
style.configure("Treeview",
                background="#d9d9d9", #Altera cor da TABELA treeview
                fieldbackground="#d9d9d9", #Altera cor DE FUNDO da TABELA treeview
                foreground="black")
style.map("Treeview", background=[("selected", "#0000FF")]) #Altera cor da linha selecionada

###########Barra de Menu###########

menubar = Menu(root)
root.config(menu=menubar)
menubar.add_command(label="Gerar PDF", command=gerar_pdf)
menubar.add_command(label="Editar Ordem", command=editar_ordem_existente)
menubar.add_command(label="Deletar Todos Registros", command=deletar_todos_registros)
menubar.add_command(label="Gerar PDF - Cliente", command=pdf_cliente)
menubar.add_command(label="Relatório Financeiro", command=mostrar_relatorio_financeiro)

###########Formulário###########

frame_form = tk.Frame(root, bg="#d9d9d9")
frame_form.pack(pady=10, padx=3, anchor="w", fill="x")
labels = ["Profissional", "Cliente", "Serviço", "Valor (R$)", "Peça trocada", "Detalhes", "Nº Ordem"]
entries = []

for i, texto in enumerate(labels):
    lbl = tk.Label(frame_form, text=texto, bg="#d9d9d9", fg="blue") #TEXTO DA MESMA COR DO FRAME, ALTERA COR DA FONTE
    lbl.grid(row=0, column=i, padx=5, pady=2, sticky="w")

    largura = 18
    if texto == "Detalhes":
        largura = 40
    elif texto == "Serviço":
        largura = 30  # Aumente para 30 ou mais, conforme preferir

    ent = tk.Entry(frame_form, width=largura, bg="#A9A9A9")  #Cor entrada Formulario
    ent.grid(row=1, column=i, padx=5, pady=2)
    entries.append(ent)


btn_adicionar = tk.Button(frame_form, text="Adicionar Ordem", bg="green", relief="flat", highlightthickness=0,fg="white", cursor="hand2",command=lambda: inserir_ordem(
    entries[0].get(), entries[1].get(), entries[2].get(),
    float(entries[3].get().replace(",", ".")) if entries[3].get().replace(",", ".").replace(".", "", 1).isdigit() else None,
    entries[5].get(), entries[4].get(), entries[6].get()))

btn_adicionar.grid(row=1, column=len(labels)+1, padx=5, pady=2)

btn_gerar_os = tk.Button(frame_form, text="Gerar Nº O.S", bg="black", fg="yellow", relief="flat", highlightthickness=0,cursor="hand2", command=lambda: gerar_numero_ordem())
btn_gerar_os.grid(row=1, column=len(labels), padx=5, pady=2)

###########Campo de Busca###########

frame_busca = tk.Frame(root, bg="#d9d9d9")  # Cor do Frame
frame_busca.pack(pady=5, anchor="w", fill="x")

label_busca = tk.Label(frame_busca, text="Pesq. OS / Cliente:", bg="#d9d9d9", fg="blue")  # Cor do texto
label_busca.pack(side="left", padx=(10, 5))

entry_busca = tk.Entry(frame_busca, width=50, bg="#A9A9A9")
entry_busca.pack(side="left")
entry_busca.bind("<KeyRelease>", lambda e: carregar_ordens(entry_busca.get()))

label_aviso_busca = tk.Label(frame_busca, text="", fg="red",bg="#d9d9d9")
label_aviso_busca.pack(side="left", padx=10)

###########Treeview Estilização###########

frame_tree = tk.Frame(root, bg="#696969")  #Altera Cor de fundo do Frame da TreeView
frame_tree.pack(fill="both", expand=True, padx=20, pady=15)  # apenas largura

scroll_y = ttk.Scrollbar(frame_tree, orient="vertical", style="Vertical.TScrollbar")
scroll_x = ttk.Scrollbar(frame_tree, orient="horizontal", style="Horizontal.TScrollbar")

cols = ("status", "numero_ordem", "cliente", "servico", "valor", "profissional", "peca", "detalhes", "data")
tree = ttk.Treeview(frame_tree,columns=cols,show="headings",
                    height=18,  # ← ALTURA DA TREEVIEW PARA EXIBIR LINHAS
                    yscrollcommand=scroll_y.set,
                    xscrollcommand=scroll_x.set)

scroll_y.config(command=tree.yview)
scroll_x.config(command=tree.xview)

scroll_y.pack(side="right", fill="y")
scroll_x.pack(side="bottom", fill="x")
tree.pack(fill="x", padx=20, pady=10)  # apenas largura

###########ESTILIZAÇÃO DAS BARRAS DE ROLAGEM###########

style.configure("Vertical.TScrollbar", background="#1C1C1C", troughcolor="#808080", arrowcolor="white",relief="raised")
style.configure("Horizontal.TScrollbar", background="#1C1C1C", troughcolor="#808080", arrowcolor="white",relief="raised")

style.map("Vertical.TScrollbar", background=[("active", "#363636")])
style.map("Horizontal.TScrollbar",background=[("active", "#363636")])

###########Cabeçalhos e larguras personalizadas###########

tree.heading("status", text="⏳")
tree.column("status", width=50, anchor="center")

tree.heading("numero_ordem", text="Nº Ordem")
tree.column("numero_ordem", width=100, anchor="center")

tree.heading("cliente", text="Cliente")
tree.column("cliente", width=200, anchor="w")

tree.heading("servico", text="Serviço")
tree.column("servico", width=200, anchor="w")

tree.heading("valor", text="Valor (R$)")
tree.column("valor", width=100, anchor="center")

tree.heading("profissional", text="Profissional")
tree.column("profissional", width=150, anchor="center")

tree.heading("peca", text="Peça Trocada")
tree.column("peca", width=150, anchor="center")

tree.heading("detalhes", text="Detalhes")
tree.column("detalhes", width=250, anchor="w")

tree.heading("data", text="Finalizado em")
tree.column("data", width=120, anchor="center")

###########FUNÇÃO PARA DESMARCAR LINHA SELECIONADA TREEVIEW###########
def click_geral(event):
    widget = event.widget
    if widget == tree:
        region = tree.identify("region", event.x, event.y)
        if region not in ("cell", "tree"):
            tree.selection_remove(tree.selection())
        return
    if isinstance(widget, tk.Button):
        return
    tree.selection_remove(tree.selection())

root.bind("<Button-1>", click_geral)

###########Botões###########

frame_botoes = tk.Frame(root, bg='#808080')
frame_botoes.pack(pady=10)

btn_excluir = tk.Button(frame_botoes, text="Excluir", bg="red", fg="white", relief="flat", highlightthickness=0, command=excluir_ordem, cursor="hand2")
btn_finalizar = tk.Button(frame_botoes, text="Finalizar", bg="green", fg="white", relief="flat", highlightthickness=0, command=finalizar_ordem, cursor="hand2")
btn_desfazer = tk.Button(frame_botoes, text="Desfazer Finalização", bg="blue", fg="white", relief="flat", highlightthickness=0, command=desfazer_finalizacao, cursor="hand2")
btn_sair = tk.Button(frame_botoes, text="Sair", bg="black", fg="white", relief="flat", highlightthickness=0, command=root.quit, cursor="hand2")

btn_finalizar.grid(row=0, column=0, padx=5)
btn_desfazer.grid(row=0, column=1, padx=5)
btn_excluir.grid(row=0, column=2, padx=5)
btn_sair.grid(row=0, column=3, padx=5)

############Início###########
init_db()
carregar_ordens()
root.mainloop()
