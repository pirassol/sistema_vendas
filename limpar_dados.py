from app import app, db, Evento, Barraca, Produto, Empresa, Usuario, Venda, ItemVenda

def limpar_dados():
    with app.app_context():
        try:
            # Remover todos os itens de venda
            ItemVenda.query.delete()
            # Remover todas as vendas
            Venda.query.delete()
            # Remover todos os produtos
            Produto.query.delete()
            # Remover todas as barracas
            Barraca.query.delete()
            # Remover todos os eventos
            Evento.query.delete()
            # Remover todos os usuários (exceto admin)
            Usuario.query.filter(Usuario.email != 'admin@admin.com').delete()
            # Remover todas as empresas (exceto a de administração)
            Empresa.query.filter(Empresa.cnpj != '00000000000000').delete()
            # Commit das alterações
            db.session.commit()
            print("Todos os dados foram removidos com sucesso!")
        except Exception as e:
            print(f"Erro ao limpar dados: {e}")
            db.session.rollback()

if __name__ == '__main__':
    limpar_dados() 