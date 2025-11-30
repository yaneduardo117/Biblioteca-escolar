from django.shortcuts import render, redirect
from django.db.models import Sum, Q
from .models import Livro, Autor
from .forms import LivroForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout


@login_required
def listagem_livros(request):
    # 1. Busca inicial de todos os livros
    livros = Livro.objects.select_related('autor', 'categoria').all()

    # --- LÓGICA DE PESQUISA ---
    query = request.GET.get('q')  # Pega o texto da barra de busca

    if query:
        # Se tiver busca, filtra a lista 'livros' por Título, Autor ou ISBN
        livros = livros.filter(
            Q(titulo__icontains=query) |
            Q(autor__nome__icontains=query) |
            Q(isbn__icontains=query)
        )


    # --- ESTATÍSTICAS (Cards do Topo) ---
    # Criamos uma variável separada 'todos_livros' para calcular os totais.
    # Assim, os cards mostram o total da BIBLIOTECA INTEIRA, e não só da busca.
    todos_livros = Livro.objects.all()

    # Total de Livros (Títulos cadastrados)
    total_livros = todos_livros.count()

    # Total de Exemplares (Soma das quantidades físicas)
    total_exemplares = todos_livros.aggregate(Sum('quantidade'))['quantidade__sum'] or 0

    # Categorias EM USO (Conta direto na tabela Livro)
    total_categorias = todos_livros.values('categoria').distinct().count()

    context = {
        'livros': livros,  # Lista (pode estar filtrada ou não)
        'total_livros': total_livros,  # Sempre o total geral
        'total_exemplares': total_exemplares,
        'total_categorias': total_categorias,
    }

    return render(request, 'listagem_livros.html', context)


@login_required
def cadastro_livro(request):
    if request.method == 'POST':
        form = LivroForm(request.POST)
        if form.is_valid():
            # Cria o objeto livro na memória, mas não salva ainda
            livro = form.save(commit=False)

            # Pega o nome do autor digitado
            nome_digitado = form.cleaned_data['nome_autor']

            # Busca ou cria o Autor
            autor_obj, created = Autor.objects.get_or_create(nome=nome_digitado)

            # Associa o autor ao livro
            livro.autor = autor_obj

            # Salva tudo no banco
            livro.save()

            return redirect('listagem_livros')
    else:
        form = LivroForm()

    return render(request, 'cadastro_livro.html', {'form': form})


def fazer_logout(request):
    logout(request)  # Encerra a sessão do usuário
    return redirect('login')