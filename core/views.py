from django.shortcuts import render, redirect, get_object_or_404
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

    # variável separada 'todos_livros' para calcular os totais.
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


@login_required
def editar_livro(request, id):
    # Busca o livro pelo ID ou dá erro 404 se não existir
    livro = get_object_or_404(Livro, id=id)

    if request.method == 'POST':
        # Carrega o formulário com os dados novos (POST) E diz quem estamos editando (instance)
        form = LivroForm(request.POST, instance=livro)

        if form.is_valid():
            livro_editado = form.save(commit=False)

            # --- Lógica do Autor (Mesma do cadastro) ---
            # verificar se o usuário mudou o nome do autor
            nome_digitado = form.cleaned_data['nome_autor']
            autor_obj, created = Autor.objects.get_or_create(nome=nome_digitado)

            livro_editado.autor = autor_obj
            livro_editado.save()

            return redirect('listagem_livros')
    else:
        # Quando abre a tela (GET):
        # Preenchemos o form com os dados do livro (instance=livro)
        # E preenchemos manualmente nosso campo extra 'nome_autor' (initial)
        form = LivroForm(instance=livro, initial={'nome_autor': livro.autor.nome})

    return render(request, 'editar_livro.html', {'form': form})


@login_required
def remover_livro(request, id):
    livro = get_object_or_404(Livro, id=id)
    livro.delete()
    return redirect('listagem_livros')


def fazer_logout(request):
    logout(request)  # Encerra a sessão do usuário
    return redirect('login')