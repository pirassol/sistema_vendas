from app import app, db, Venda, ItemVenda, Pagamento

with app.app_context():
    print("Limpando dados de vendas...")
    try:
        # Remover itens de venda
        num_itens = db.session.query(ItemVenda).delete()
        print(f"- {num_itens} itens de venda removidos")
        
        # Remover pagamentos
        num_pagamentos = db.session.query(Pagamento).delete()
        print(f"- {num_pagamentos} pagamentos removidos")
        
        # Remover vendas
        num_vendas = db.session.query(Venda).delete()
        print(f"- {num_vendas} vendas removidas")
        
        # Commit das alterações
        db.session.commit()
        print("Limpeza concluída com sucesso!")
    except Exception as e:
        db.session.rollback()
        print(f"Erro durante a limpeza: {str(e)}")

if __name__ == '__main__':
    limpar_vendas() 