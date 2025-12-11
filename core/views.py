from datetime import date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum, Q
from django.contrib import messages
from .models import Livro, Autor, Emprestimo, Usuario
from .forms import LivroForm, CadastroUsuarioForm, EmprestimoForm, FormAdicionarUsuario, FormEditarUsuario
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout


@login_required
def listagem_livros(request):
    """
    Dashboard principal: Lista livros e mostra estatísticas do acervo.
    """
    livros = Livro.objects.select_related('autor', 'categoria').all().order_by('-id')

    # --- LÓGICA DE PESQUISA ---
    # Se o usuário digitou algo na barra de busca, filtro aqui
    query = request.GET.get('q')
    if query:
        livros = livros.filter(
            Q(titulo__icontains=query) |
            Q(autor__nome__icontains=query) |
            Q(isbn__icontains=query)
        )

    # --- ESTATÍSTICAS DO DASHBOARD ---
    # Pego todos os livros para garantir que os cards mostrem o total real da biblioteca,
    # independente do filtro de pesquisa atual.
    todos_livros = Livro.objects.all()
    total_livros = todos_livros.count()
    total_exemplares = todos_livros.aggregate(Sum('quantidade'))['quantidade__sum'] or 0
    total_categorias = todos_livros.values('categoria').distinct().count()

    context = {
        'livros': livros,
        'total_livros': total_livros,
        'total_exemplares': total_exemplares,
        'total_categorias': total_categorias,
    }
    return render(request, 'listagem_livros.html', context)


@login_required
def cadastro_livro(request):
    if request.method == 'POST':
        form = LivroForm(request.POST)
        if form.is_valid():
            livro = form.save(commit=False)

            # Lógica para criar Autor se não existir
            nome_digitado = form.cleaned_data['nome_autor']
            autor_obj, created = Autor.objects.get_or_create(nome=nome_digitado)
            livro.autor = autor_obj
            # Associo o autor ao livro e salvo tudo
            livro.save()
            return redirect('listagem_livros')
    else:
        form = LivroForm()

    return render(request, 'cadastro_livro.html', {'form': form})


@login_required
def editar_livro(request, id):
    # Tento buscar o livro, se não achar dou erro 404
    livro = get_object_or_404(Livro, id=id)

    if request.method == 'POST':
        form = LivroForm(request.POST, instance=livro)
        if form.is_valid():
            livro_editado = form.save(commit=False)

            nome_digitado = form.cleaned_data['nome_autor']
            autor_obj, created = Autor.objects.get_or_create(nome=nome_digitado)
            livro_editado.autor = autor_obj

            livro_editado.save()
            return redirect('listagem_livros')
    else:
        # Quando abro a tela, preencho o form com os dados atuais
        # e coloco o nome do autor manualmente no campo de texto
        form = LivroForm(instance=livro, initial={'nome_autor': livro.autor.nome})

    return render(request, 'editar_livro.html', {'form': form})


@login_required
def remover_livro(request, id):
    livro = get_object_or_404(Livro, id=id)
    livro.delete()
    return redirect('listagem_livros')


def fazer_logout(request):
    logout(request)
    return redirect('login')


def cadastrar_usuario(request):
    # Se o cara já tá logado, não deixo ele ver a tela de cadastro
    if request.user.is_authenticated:
        return redirect('listagem_livros')

    if request.method == 'POST':
        form = CadastroUsuarioForm(request.POST)
        if form.is_valid():
            usuario = form.save(commit=False)
            usuario.username = usuario.email
            usuario.save()
            return redirect('login')
    else:
        form = CadastroUsuarioForm()

    return render(request, 'cadastro_usuario.html', {'form': form})


# --- LÓGICA DE EMPRÉSTIMOS ---

@login_required
def listar_emprestimos(request):
    # Busco os empréstimos trazendo os dados do livro e do usuário para não pesar o banco
    emprestimos = Emprestimo.objects.select_related('livro', 'usuario').all().order_by('-id')

    # Filtro da barra de busca (procura por nome do aluno, título do livro ou matrícula)
    query = request.GET.get('q')
    if query:
        emprestimos = emprestimos.filter(
            Q(usuario__first_name__icontains=query) |
            Q(livro__titulo__icontains=query) |
            Q(usuario__matricula__icontains=query)
        )

    # Contadores
    total_emprestimos = emprestimos.count()
    # Em andamento: não devolvido ainda e a data prevista é hoje ou futuro

    em_andamento = emprestimos.filter(data_devolucao_real__isnull=True,
                                      data_devolucao_prevista__gte=date.today()).count()
    atrasados = emprestimos.filter(data_devolucao_real__isnull=True, data_devolucao_prevista__lt=date.today()).count()
    # Devolvidos: campo data_devolucao_real está preenchido
    devolvidos = emprestimos.filter(data_devolucao_real__isnull=False).count()

    context = {
        'emprestimos': emprestimos,
        'total_emprestimos': total_emprestimos,
        'em_andamento': em_andamento,
        'atrasados': atrasados,
        'devolvidos': devolvidos,
        'hoje': date.today(),
        'usuarios_list': Usuario.objects.filter(is_active=True),
        'livros_disponiveis': Livro.objects.filter(quantidade__gt=0),
    }
    return render(request, 'emprestimos.html', context)


@login_required
def criar_emprestimo(request):
    if request.method == 'POST':
        form = EmprestimoForm(request.POST)
        if form.is_valid():
            emprestimo = form.save(commit=False)

            # Regras: Data devolução (+14 dias) e Estoque (-1)
            emprestimo.data_devolucao_prevista = date.today() + timedelta(days=14)

            # Regra 2: Controle de Estoque
            # Se tiver livro disponível, tiro um do estoque e salvo o empréstimo
            livro = emprestimo.livro
            if livro.quantidade > 0:
                livro.quantidade -= 1
                livro.save()
                emprestimo.save()

            return redirect('listar_emprestimos')

    return redirect('listar_emprestimos')


@login_required
def devolver_livro(request, id):
    emprestimo = get_object_or_404(Emprestimo, id=id)

    # Só faço a devolução se ainda não tiver sido devolvido
    if not emprestimo.data_devolucao_real:
        emprestimo.data_devolucao_real = date.today()
        emprestimo.save()

        # Devolvo o livro para o estoque (aumento a quantidade)
        livro = emprestimo.livro
        livro.quantidade += 1
        livro.save()

    return redirect('listar_emprestimos')


# --- LÓGICA DE USUÁRIOS (ADM) ---

@login_required
def listar_usuarios(request):
    """
    Lista todos os usuários e mostra estatísticas administrativas.
    """
    usuarios = Usuario.objects.all().order_by('-date_joined')

    # Filtro de Busca (Nome ou Email)
    query = request.GET.get('q')
    if query:
        usuarios = usuarios.filter(
            Q(first_name__icontains=query) |
            Q(email__icontains=query)
        )

    # Estatísticas do Dashboard
    total_usuarios = Usuario.objects.count()

    # Calcula 'usuarios_ativos'
    usuarios_ativos = Usuario.objects.filter(is_active=True).count()

    # Conta Admins (inclui quem é superuser)
    total_admins = Usuario.objects.filter(Q(tipo_usuario='ADMIN') | Q(is_superuser=True)).count()

    context = {
        'usuarios': usuarios,
        'total_usuarios': total_usuarios,
        'usuarios_ativos': usuarios_ativos,  # Nome corrigido aqui
        'total_admins': total_admins,
        # Enviamos o formulário vazio para ser usado no Modal de Adicionar
        'form_adicionar': FormAdicionarUsuario()
    }

    return render(request, 'usuarios.html', context)


@login_required
def adicionar_usuario(request):
    """
    Processa o formulário do Modal para criar um novo usuário (Adm/Bibliotecário).
    """
    if request.method == 'POST':
        form = FormAdicionarUsuario(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Usuário adicionado com sucesso!")
            return redirect('listar_usuarios')
        else:
            messages.error(request, "Erro ao adicionar. Verifique os campos.")

    return redirect('listar_usuarios')


@login_required
def editar_usuario(request, id):
    """
    Tela para editar dados e alterar status (Ativo/Inativo) de um usuário.
    """
    usuario = get_object_or_404(Usuario, id=id)

    if request.method == 'POST':
        form = FormEditarUsuario(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, "Dados do usuário atualizados!")
            return redirect('listar_usuarios')
    else:
        form = FormEditarUsuario(instance=usuario)

    return render(request, 'editar_usuario.html', {'form': form, 'usuario': usuario})