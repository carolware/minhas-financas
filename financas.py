import json
import os
import time
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "financas_data.json")

CATEGORIAS = [
    "Moradia", "Contas fixas", "Cartão de crédito",
    "Assinaturas", "Transporte", "Saúde", "Outros",
]

DEFAULT_DATA = {
    "bills": [],
    "partner_name": "Hanna",
    "budget": None,
}


def load_data():
    if not os.path.exists(DATA_FILE):
        return dict(DEFAULT_DATA)
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("bills", [])
        data.setdefault("partner_name", "Hanna")
        data.setdefault("budget", None)
        return data
    except (json.JSONDecodeError, OSError):
        backup = DATA_FILE + f".bak-{int(time.time())}"
        try:
            os.rename(DATA_FILE, backup)
        except OSError:
            pass
        return dict(DEFAULT_DATA)


def save_data(data):
    tmp_path = DATA_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, DATA_FILE)  # gravação atômica, evita corromper o arquivo


def fmt_money(v):
    s = f"{v:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def effective_amount(bill):
    total_parc = bill.get("installments_total", 1) or 1
    return bill["amount"] / total_parc


def your_share(bill):
    base = effective_amount(bill)
    if bill.get("split"):
        return base * (bill["split_percent"] / 100.0)
    return base


def partner_share(bill):
    base = effective_amount(bill)
    if bill.get("split"):
        return base * ((100 - bill["split_percent"]) / 100.0)
    return 0.0


def is_fully_paid(bill):
    if bill.get("split"):
        return bill.get("paid_you", False) and bill.get("paid_partner", False)
    return bill.get("paid_you", False)


def build_status_text(bill, partner_name):
    if bill.get("split"):
        you_txt = "pago" if bill.get("paid_you") else "pendente"
        partner_txt = "pago" if bill.get("paid_partner") else "pendente"
        status = (
            f"Dividida — Você ({you_txt}) {fmt_money(your_share(bill))} · "
            f"{partner_name} ({partner_txt}) {fmt_money(partner_share(bill))}"
        )
    else:
        status = "Paga" if bill.get("paid_you") else "Pendente"

    tags = []
    if bill.get("fixed"):
        tags.append("Fixa")
    total_parc = bill.get("installments_total", 1)
    if total_parc and total_parc > 1:
        cur_parc = bill.get("installment_current", 1)
        tags.append(
            f"Parcela {cur_parc}/{total_parc} de {fmt_money(bill['amount'])} "
            f"(parcela: {fmt_money(effective_amount(bill))})"
        )

    if tags:
        status = " · ".join(tags) + " · " + status
    return status


# --------------------------------------------------------------------------
# aplicativo
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# cores
# --------------------------------------------------------------------------
BG = "#f4f5f7"
CARD_BG = "#ffffff"
BORDER = "#e0e1e6"
TEXT = "#1a1d23"
TEXT_MUTED = "#6b7280"
ACCENT = "#4f46e5"
ACCENT_DARK = "#4338ca"
GREEN = "#059669"
RED = "#dc2626"


class FinancasApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Minhas Finanças")
        self.geometry("800x700")
        self.minsize(700, 600)
        self.configure(bg=BG)

        self.data = load_data()
        self.editing_id = None
        self.filter_var = tk.StringVar(value="all")

        self._build_style()
        self._build_ui()
        self.refresh_all()

    # -- estilo -----------------------------------------------------------
    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(".", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("TLabelframe", background=BG, bordercolor=BORDER)
        style.configure("TLabelframe.Label", background=BG, foreground=TEXT,
                         font=("Segoe UI", 10, "bold"))
        style.configure("TRadiobutton", background=BG)
        style.configure("TCheckbutton", background=BG)

        style.configure("Treeview", rowheight=27, font=("Segoe UI", 10),
                         background=CARD_BG, fieldbackground=CARD_BG, bordercolor=BORDER)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

        style.configure("Title.TLabel", font=("Segoe UI", 15, "bold"), background=BG)
        style.configure("Sub.TLabel", foreground=TEXT_MUTED, background=BG)
        style.configure("Big.TLabel", font=("Segoe UI", 17, "bold"), background=CARD_BG)
        style.configure("CardTitle.TLabel", foreground=TEXT_MUTED, background=CARD_BG,
                         font=("Segoe UI", 9))
        style.configure("Pending.TLabel", foreground=RED, background=CARD_BG,
                         font=("Segoe UI", 17, "bold"))
        style.configure("Paid.TLabel", foreground=GREEN, background=CARD_BG,
                         font=("Segoe UI", 17, "bold"))
        style.configure("Total.TLabel", foreground=ACCENT, background=CARD_BG,
                         font=("Segoe UI", 17, "bold"))

        style.configure("TButton", padding=6, font=("Segoe UI", 9))
        style.configure("Accent.TButton", background=ACCENT, foreground="white",
                         padding=(12, 8), font=("Segoe UI", 10, "bold"))
        style.map("Accent.TButton", background=[("active", ACCENT_DARK)])

        style.configure("Budget.TLabelframe", background=BG, bordercolor=BORDER)
        style.configure("Budget.TLabelframe.Label", background=BG, foreground=TEXT,
                         font=("Segoe UI", 13, "bold"))
        style.configure("BudgetInfo.TLabel", background=BG, foreground=TEXT,
                         font=("Segoe UI", 13))
        style.configure("Horizontal.TProgressbar", background=ACCENT,
                         troughcolor=BORDER, thickness=24)

    def _build_ui(self):
        outer = ttk.Frame(self, padding=14)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Minhas Finanças", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            outer, text=f"Dados salvos em: {DATA_FILE}", style="Sub.TLabel"
        ).pack(anchor="w", pady=(0, 10))

        # ---- resumo -------------------------------------------------
        summary = ttk.Frame(outer)
        summary.pack(fill="x", pady=(0, 10))
        for i in range(3):
            summary.columnconfigure(i, weight=1)

        self.lbl_pending = self._summary_card(summary, "A pagar", 0, "Pending.TLabel")
        self.lbl_paid = self._summary_card(summary, "Pago", 1, "Paid.TLabel")
        self.lbl_total = self._summary_card(summary, "Total", 2, "Total.TLabel")

        # ---- parceiro(a) ---------------------------------------------
        partner_bar = ttk.Frame(outer)
        partner_bar.pack(fill="x", pady=(0, 6))
        self.partner_label = ttk.Label(partner_bar, text="", style="Sub.TLabel")
        self.partner_label.pack(side="left")
        ttk.Button(partner_bar, text="Editar nome", command=self.edit_partner_name).pack(
            side="left", padx=8
        )

        # ---- orçamento --------------------------------------------------
        budget_box = ttk.LabelFrame(
            outer, text="Seu orçamento", padding=16, style="Budget.TLabelframe"
        )
        budget_box.pack(fill="x", pady=(0, 14))
        self.budget_info = ttk.Label(budget_box, text="", style="BudgetInfo.TLabel")
        self.budget_info.pack(anchor="w")
        self.budget_bar = ttk.Progressbar(budget_box, maximum=100, value=0)
        self.budget_bar.pack(fill="x", pady=(10, 10))
        ttk.Button(
            budget_box, text="Definir orçamento", command=self.edit_budget,
            style="Accent.TButton",
        ).pack(anchor="w")

        # ---- formulário de conta -----------------------------------------
        form = ttk.LabelFrame(outer, text="Nova conta", padding=10)
        form.pack(fill="x", pady=(0, 12))
        self.form = form

        row1 = ttk.Frame(form)
        row1.pack(fill="x", pady=3)
        ttk.Label(row1, text="Descrição:", width=12).pack(side="left")
        self.entry_name = ttk.Entry(row1)
        self.entry_name.pack(side="left", fill="x", expand=True)

        row2 = ttk.Frame(form)
        row2.pack(fill="x", pady=3)
        ttk.Label(row2, text="Valor (R$):", width=12).pack(side="left")
        self.entry_amount = ttk.Entry(row2)
        self.entry_amount.pack(side="left", fill="x", expand=True)
        self.entry_amount.bind("<KeyRelease>", lambda e: self.update_split_preview())

        row3 = ttk.Frame(form)
        row3.pack(fill="x", pady=3)
        ttk.Label(row3, text="Categoria:", width=12).pack(side="left")
        self.combo_category = ttk.Combobox(
            row3, values=CATEGORIAS, state="readonly"
        )
        self.combo_category.current(len(CATEGORIAS) - 1)
        self.combo_category.pack(side="left", fill="x", expand=True)

        row4 = ttk.Frame(form)
        row4.pack(fill="x", pady=3)
        self.split_var = tk.BooleanVar(value=False)
        self.split_check = ttk.Checkbutton(
            row4, text="Dividir esta conta", variable=self.split_var,
            command=self.on_split_toggle,
        )
        self.split_check.pack(side="left")

        self.split_frame = ttk.Frame(form)
        self.percent_var = tk.IntVar(value=50)
        self.split_scale = ttk.Scale(
            self.split_frame, from_=0, to=100, orient="horizontal",
            variable=self.percent_var, command=lambda e: self.update_split_preview(),
        )
        self.split_scale.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.split_preview_label = ttk.Label(self.split_frame, text="")
        self.split_preview_label.pack(side="left")

        # ---- conta fixa (sempre exibida, ex.: aluguel) -----------------
        row5 = ttk.Frame(form)
        row5.pack(fill="x", pady=3)
        self.fixed_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            row5, text="Conta fixa (sempre exibida, ex: aluguel)",
            variable=self.fixed_var,
        ).pack(side="left")

        # ---- parcelas ---------------------------------------------------
        row6 = ttk.Frame(form)
        row6.pack(fill="x", pady=3)
        ttk.Label(row6, text="Parcelas:", width=12).pack(side="left")
        self.entry_installments = ttk.Entry(row6, width=6)
        self.entry_installments.insert(0, "1")
        self.entry_installments.pack(side="left")
        ttk.Label(
            row6,
            text="  (o valor acima é o total da compra e será dividido pelas parcelas; deixe 1 se não houver parcelamento)",
            style="Sub.TLabel",
        ).pack(side="left")

        btn_row = ttk.Frame(form)
        btn_row.pack(fill="x", pady=(8, 0))
        self.submit_btn = ttk.Button(
            btn_row, text="+ Adicionar conta", command=self.on_submit,
            style="Accent.TButton",
        )
        self.submit_btn.pack(side="left")
        self.cancel_btn = ttk.Button(
            btn_row, text="Cancelar edição", command=self.cancel_edit
        )
        # cancel_btn só é exibido durante edição (pack feito em start_edit)

        # ---- filtros ------------------------------------------------
        filt = ttk.Frame(outer)
        filt.pack(fill="x", pady=(0, 6))
        for label, value in [("Todas", "all"), ("A pagar", "pending"), ("Pagas", "paid")]:
            ttk.Radiobutton(
                filt, text=label, value=value, variable=self.filter_var,
                command=self.refresh_list,
            ).pack(side="left", padx=(0, 10))
        ttk.Label(
            filt, text="  Contas fixas aparecem sempre, em qualquer filtro.",
            style="Sub.TLabel",
        ).pack(side="left")

        # ---- lista de contas ------------------------------------------
        list_frame = ttk.Frame(outer)
        list_frame.pack(fill="both", expand=True)

        columns = ("nome", "categoria", "valor", "status")
        self.tree = ttk.Treeview(
            list_frame, columns=columns, show="headings", selectmode="browse"
        )
        self.tree.heading("nome", text="Descrição")
        self.tree.heading("categoria", text="Categoria")
        self.tree.heading("valor", text="Valor (parcela)")
        self.tree.heading("status", text="Status")
        self.tree.column("nome", width=220)
        self.tree.column("categoria", width=130)
        self.tree.column("valor", width=110, anchor="e")
        self.tree.column("status", width=260)
        self.tree.pack(side="left", fill="both", expand=True)

        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        scroll.pack(side="left", fill="y")
        self.tree.configure(yscrollcommand=scroll.set)

        # ---- ações da conta selecionada --------------------------------
        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(8, 0))
        ttk.Button(actions, text="Marcar/desmarcar Você pago", command=self.toggle_you).pack(
            side="left", padx=(0, 6)
        )
        self.toggle_partner_btn = ttk.Button(
            actions, text="Marcar/desmarcar parceiro(a) pago",
            command=self.toggle_partner,
        )
        self.toggle_partner_btn.pack(side="left", padx=(0, 6))
        ttk.Button(actions, text="Avançar parcela", command=self.advance_installment).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(actions, text="Editar", command=self.edit_selected).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(actions, text="Excluir", command=self.delete_selected).pack(
            side="left"
        )

        self.on_split_toggle()

    def _summary_card(self, parent, title, col, value_style="Big.TLabel"):
        card = tk.Frame(parent, bg=CARD_BG, highlightbackground=BORDER,
                         highlightthickness=1, bd=0)
        card.grid(row=0, column=col, sticky="nsew", padx=4)
        inner = tk.Frame(card, bg=CARD_BG)
        inner.pack(fill="both", expand=True, padx=12, pady=10)
        ttk.Label(inner, text=title, style="CardTitle.TLabel").pack(anchor="w")
        value_label = ttk.Label(inner, text="R$ 0,00", style=value_style)
        value_label.pack(anchor="w")
        return value_label

    # -- split preview ------------------------------------------------
    def on_split_toggle(self):
        if self.split_var.get():
            self.split_frame.pack(fill="x", pady=3, after=self.split_check.master)
        else:
            self.split_frame.pack_forget()
        self.update_split_preview()

    def update_split_preview(self):
        try:
            amount = float(self.entry_amount.get().replace(",", "."))
        except ValueError:
            amount = 0.0
        pct = self.percent_var.get()
        partner = self.data["partner_name"]
        your = amount * pct / 100.0
        theirs = amount * (100 - pct) / 100.0
        self.split_preview_label.configure(
            text=f"{pct}%  ·  Você: {fmt_money(your)}  ·  {partner}: {fmt_money(theirs)}"
        )

    # -- formulário: adicionar / salvar edição -------------------------
    def on_submit(self):
        name = self.entry_name.get().strip()
        try:
            amount = float(self.entry_amount.get().replace(",", "."))
        except ValueError:
            amount = None
        if not name or amount is None or amount <= 0:
            messagebox.showwarning(
                "Dados incompletos", "Preencha uma descrição e um valor válido."
            )
            return

        category = self.combo_category.get()
        split = self.split_var.get()
        split_percent = self.percent_var.get()
        fixed = self.fixed_var.get()

        try:
            installments_total = int(self.entry_installments.get().strip())
            if installments_total < 1:
                installments_total = 1
        except ValueError:
            installments_total = 1

        if self.editing_id:
            bill = self._find_bill(self.editing_id)
            if bill:
                bill["name"] = name
                bill["amount"] = amount
                bill["category"] = category
                bill["split"] = split
                bill["split_percent"] = split_percent if split else 100
                bill["fixed"] = fixed
                bill["installments_total"] = installments_total
                # Mantém a parcela atual, só ajustando se o novo total for menor.
                bill["installment_current"] = min(
                    bill.get("installment_current", 1), installments_total
                )
                if not split:
                    bill["paid_partner"] = True
            self.cancel_edit()
        else:
            self.data["bills"].append({
                "id": str(int(time.time() * 1000)),
                "name": name,
                "amount": amount,
                "category": category,
                "split": split,
                "split_percent": split_percent if split else 100,
                "paid_you": False,
                "paid_partner": not split,
                "fixed": fixed,
                "installments_total": installments_total,
                "installment_current": 1,
            })
            self._reset_form()

        save_data(self.data)
        self.refresh_all()

    def _reset_form(self):
        self.entry_name.delete(0, "end")
        self.entry_amount.delete(0, "end")
        self.combo_category.current(len(CATEGORIAS) - 1)
        self.split_var.set(False)
        self.percent_var.set(50)
        self.fixed_var.set(False)
        self.entry_installments.delete(0, "end")
        self.entry_installments.insert(0, "1")
        self.on_split_toggle()

    def start_edit(self, bill):
        self.editing_id = bill["id"]
        self.entry_name.delete(0, "end")
        self.entry_name.insert(0, bill["name"])
        self.entry_amount.delete(0, "end")
        self.entry_amount.insert(0, str(bill["amount"]))
        if bill["category"] in CATEGORIAS:
            self.combo_category.set(bill["category"])
        self.split_var.set(bool(bill.get("split")))
        self.percent_var.set(bill.get("split_percent", 50) if bill.get("split") else 50)
        self.fixed_var.set(bool(bill.get("fixed", False)))
        self.entry_installments.delete(0, "end")
        self.entry_installments.insert(0, str(bill.get("installments_total", 1)))
        self.on_split_toggle()
        self.submit_btn.configure(text="Salvar alterações")
        self.cancel_btn.pack(side="left", padx=(8, 0))
        self.form.configure(text="Editando conta")

    def cancel_edit(self):
        self.editing_id = None
        self._reset_form()
        self.submit_btn.configure(text="+ Adicionar conta")
        self.cancel_btn.pack_forget()
        self.form.configure(text="Nova conta")

    # -- ações sobre a conta selecionada -----------------------------
    def _selected_bill(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return self._find_bill(sel[0])

    def _find_bill(self, bill_id):
        for b in self.data["bills"]:
            if b["id"] == bill_id:
                return b
        return None

    def toggle_you(self):
        bill = self._selected_bill()
        if not bill:
            messagebox.showinfo("Selecione uma conta", "Clique em uma conta na lista primeiro.")
            return
        bill["paid_you"] = not bill.get("paid_you", False)
        save_data(self.data)
        self.refresh_all()

    def toggle_partner(self):
        bill = self._selected_bill()
        if not bill:
            messagebox.showinfo("Selecione uma conta", "Clique em uma conta na lista primeiro.")
            return
        if not bill.get("split"):
            messagebox.showinfo("Conta não dividida", "Essa conta não está marcada como dividida.")
            return
        bill["paid_partner"] = not bill.get("paid_partner", False)
        save_data(self.data)
        self.refresh_all()

    def advance_installment(self):
        bill = self._selected_bill()
        if not bill:
            messagebox.showinfo("Selecione uma conta", "Clique em uma conta na lista primeiro.")
            return
        total = bill.get("installments_total", 1)
        current = bill.get("installment_current", 1)
        if total <= 1:
            messagebox.showinfo(
                "Sem parcelas", "Essa conta não está configurada com parcelas (defina o total em 'Parcelas' ao editá-la)."
            )
            return
        if current >= total:
            messagebox.showinfo(
                "Parcelas concluídas",
                f'"{bill["name"]}" já está na última parcela ({current}/{total}).',
            )
            return
        bill["installment_current"] = current + 1
        bill["paid_you"] = False
        if bill.get("split"):
            bill["paid_partner"] = False
        save_data(self.data)
        self.refresh_all()

    def edit_selected(self):
        bill = self._selected_bill()
        if not bill:
            messagebox.showinfo("Selecione uma conta", "Clique em uma conta na lista primeiro.")
            return
        self.start_edit(bill)

    def delete_selected(self):
        bill = self._selected_bill()
        if not bill:
            messagebox.showinfo("Selecione uma conta", "Clique em uma conta na lista primeiro.")
            return
        if messagebox.askyesno("Excluir conta", f'Excluir "{bill["name"]}"?'):
            self.data["bills"] = [b for b in self.data["bills"] if b["id"] != bill["id"]]
            if self.editing_id == bill["id"]:
                self.cancel_edit()
            save_data(self.data)
            self.refresh_all()

    # -- parceiro(a) e orçamento --------------------------------------
    def edit_partner_name(self):
        novo = simpledialog.askstring(
            "Nome da pessoa", "Com quem você divide as contas?",
            initialvalue=self.data["partner_name"], parent=self,
        )
        if novo and novo.strip():
            self.data["partner_name"] = novo.strip()
            save_data(self.data)
            self.refresh_all()

    def edit_budget(self):
        atual = self.data.get("budget")
        novo = simpledialog.askstring(
            "Orçamento",
            "Quanto você quer gastar (R$)? Deixe em branco para remover.",
            initialvalue="" if atual is None else str(atual),
            parent=self,
        )
        if novo is None:
            return
        novo = novo.strip()
        if novo == "":
            self.data["budget"] = None
        else:
            try:
                valor = float(novo.replace(",", "."))
                if valor <= 0:
                    raise ValueError
                self.data["budget"] = valor
            except ValueError:
                messagebox.showwarning("Valor inválido", "Digite um número válido maior que zero.")
                return
        save_data(self.data)
        self.refresh_all()

    # -- atualização de telas ------------------------------------------
    def refresh_all(self):
        self.refresh_summary()
        self.refresh_partner()
        self.refresh_budget()
        self.refresh_list()
        self.update_split_preview()

    def refresh_summary(self):
        bills = self.data["bills"]
        pending = sum(effective_amount(b) for b in bills if not is_fully_paid(b))
        paid = sum(effective_amount(b) for b in bills if is_fully_paid(b))
        self.lbl_pending.configure(text=fmt_money(pending))
        self.lbl_paid.configure(text=fmt_money(paid))
        self.lbl_total.configure(text=fmt_money(pending + paid))

    def refresh_partner(self):
        self.partner_label.configure(text=f"Dividindo com: {self.data['partner_name']}")

    def refresh_budget(self):
        budget = self.data.get("budget")
        if not budget:
            self.budget_info.configure(text="Nenhum orçamento definido ainda.")
            self.budget_bar.configure(value=0)
            return
        paid_out = sum(your_share(b) for b in self.data["bills"] if b.get("paid_you"))
        remaining = budget - paid_out
        pct = min(100, (paid_out / budget) * 100) if budget else 0
        self.budget_bar.configure(value=pct)
        if remaining >= 0:
            self.budget_info.configure(
                text=f"Restam {fmt_money(remaining)} de {fmt_money(budget)}  ·  já pago: {fmt_money(paid_out)}"
            )
        else:
            self.budget_info.configure(
                text=f"Você passou o orçamento em {fmt_money(abs(remaining))} (orçamento: {fmt_money(budget)})"
            )

    def refresh_list(self):
        prev_selection = self.tree.selection()
        prev_id = prev_selection[0] if prev_selection else None

        self.tree.delete(*self.tree.get_children())
        bills = list(self.data["bills"])

        # Contas fixas (ex.: aluguel) aparecem sempre, independente do filtro.
        f = self.filter_var.get()
        if f == "pending":
            bills = [b for b in bills if (not is_fully_paid(b)) or b.get("fixed")]
        elif f == "paid":
            bills = [b for b in bills if is_fully_paid(b) or b.get("fixed")]

        # Contas fixas ficam sempre no topo da lista.
        bills.sort(key=lambda b: (not b.get("fixed", False), is_fully_paid(b), b["id"]))

        partner = self.data["partner_name"]
        for b in bills:
            status = build_status_text(b, partner)
            self.tree.insert(
                "", "end", iid=b["id"],
                values=(b["name"], b["category"], fmt_money(effective_amount(b)), status),
            )

        if prev_id and self.tree.exists(prev_id):
            self.tree.selection_set(prev_id)
            self.tree.focus(prev_id)


if __name__ == "__main__":
    app = FinancasApp()
    app.mainloop()
