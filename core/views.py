from datetime import date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum, Q
from .models import Livro, Autor, Emprestimo, Usuario
from .forms import LivroForm, CadastroUsuarioForm, EmprestimoForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout, login


@login_required
def listagem_livros(request):
    """
    Essa é a tela principal (Dashboard de Livros).
    Aqui carrego a lista e calculo os números para os cards do topo.
    """

    # Busco os livros otimizando a consulta (trazendo autor e categoria junto)
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

    # Conto quantos títulos diferentes temos
    total_livros = todos_livros.count()

    # Somo a quantidade física de todos os exemplares (campo 'quantidade')
    total_exemplares = todos_livros.aggregate(Sum('quantidade'))['quantidade__sum'] or 0

    # Conto quantas categorias diferentes estamos usando
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
            # Crio o objeto na memória sem salvar ainda
            livro = form.save(commit=False)

            # Aqui está o pulo do gato: pego o nome do autor que foi digitado
            # e verifico se já existe no banco. Se não existir, crio um novo.
            nome_digitado = form.cleaned_data['nome_autor']
            autor_obj, created = Autor.objects.get_or_create(nome=nome_digitado)

            # Associo o autor ao livro e salvo tudo
            livro.autor = autor_obj
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

            # Mesma lógica do autor: verifico ou crio um novo na hora da edição
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
    # Simplesmente apago o livro e volto pra lista
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
            # Garanto que o username seja igual ao email para evitar confusão no login
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

    # --- CÁLCULOS DOS CARDS (STATUS) ---
    total_emprestimos = emprestimos.count()

    # Em andamento: não devolvido ainda e a data prevista é hoje ou futuro
    em_andamento = emprestimos.filter(
        data_devolucao_real__isnull=True,
        data_devolucao_prevista__gte=date.today()
    ).count()

    # Atrasados: não devolvido e a data prevista já passou
    atrasados = emprestimos.filter(
        data_devolucao_real__isnull=True,
        data_devolucao_prevista__lt=date.today()
    ).count()

    # Devolvidos: campo data_devolucao_real está preenchido
    devolvidos = emprestimos.filter(data_devolucao_real__isnull=False).count()

    context = {
        'emprestimos': emprestimos,
        'total_emprestimos': total_emprestimos,
        'em_andamento': em_andamento,
        'atrasados': atrasados,
        'devolvidos': devolvidos,
        'hoje': date.today(),
        # Esses dados vão para o dropdown do Modal de Novo Empréstimo
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

            # Regra 1: Defino a data de devolução para 14 dias a partir de hoje
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


@login_required
def listar_usuarios(request):
    # Apenas superusuários ou admins deveriam ver isso, mas por enquanto vamos liberar para login_required
    usuarios = Usuario.objects.all().order_by('-date_joined')

    # Filtro de Busca
    query = request.GET.get('q')
    if query:
        usuarios = usuarios.filter(
            Q(first_name__icontains=query) |
            Q(email__icontains=query) |
            Q(matricula__icontains=query)
        )

    # Estatísticas
    total_usuarios = Usuario.objects.count()
    usuarios_ativos = Usuario.objects.filter(is_active=True).count()
    # Filtra pelo tipo ADMIN (certifique-se que no model o value é 'ADMIN')
    total_admins = Usuario.objects.filter(tipo_usuario='ADMIN').count()

    context = {
        'usuarios': usuarios,
        'total_usuarios': total_usuarios,
        'usuarios_ativos': usuarios_ativos,
        'total_admins': total_admins,
    }

    return render(request, 'usuarios.html', context)