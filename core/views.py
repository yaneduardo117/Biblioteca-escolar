from django.shortcuts import render, redirect
from django.db.models import Sum
from .models import Livro, Autor
from .forms import LivroForm

def listagem_livros(request):
    # Busca todos os livros
    livros = Livro.objects.select_related('autor', 'categoria').all()

    # Total de Livros (Títulos cadastrados)
    total_livros = livros.count()

    # Total de Exemplares (Soma das quantidades físicas)
    total_exemplares = livros.aggregate(Sum('quantidade'))['quantidade__sum'] or 0

    # Categorias EM USO (Conta direto na tabela Livro)
    total_categorias = Livro.objects.values('categoria').distinct().count()

    context = {
        'livros': livros,
        'total_livros': total_livros,
        'total_exemplares': total_exemplares,
        'total_categorias': total_categorias,
    }

    return render(request, 'listagem_livros.html', context)

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