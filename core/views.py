from datetime import date, timedelta
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum, Q
from django.contrib import messages
from .models import Livro, Autor, Emprestimo, Usuario, Reserva
from .forms import LivroForm, CadastroUsuarioForm, EmprestimoForm, FormAdicionarUsuario, FormEditarUsuario
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout


# --- DASHBOARD E LIVROS ---

@login_required
def listagem_livros(request):
    """
    Dashboard principal: Lista livros e mostra estatísticas do acervo.
    """
    livros = Livro.objects.select_related('autor', 'categoria').all().order_by('-id')

    # Filtro de Pesquisa
    query = request.GET.get('q')
    if query:
        livros = livros.filter(
            Q(titulo__icontains=query) |
            Q(autor__nome__icontains=query) |
            Q(isbn__icontains=query)
        )

    # Estatísticas
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
    # Bloqueio: Aluno não cadastra livro
    if request.user.tipo_usuario == 'ALUNO':
        return redirect('listagem_livros')

    if request.method == 'POST':
        form = LivroForm(request.POST)
        if form.is_valid():
            livro = form.save(commit=False)

            nome_digitado = form.cleaned_data['nome_autor']
            autor_obj, created = Autor.objects.get_or_create(nome=nome_digitado)
            livro.autor = autor_obj

            livro.save()
            return redirect('listagem_livros')
    else:
        form = LivroForm()

    return render(request, 'cadastro_livro.html', {'form': form})


@login_required
def editar_livro(request, id):
    # Bloqueio: Aluno não edita livro
    if request.user.tipo_usuario == 'ALUNO':
        return redirect('listagem_livros')

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
        form = LivroForm(instance=livro, initial={'nome_autor': livro.autor.nome})

    return render(request, 'editar_livro.html', {'form': form})


@login_required
def remover_livro(request, id):
    # Bloqueio: Aluno não remove livro
    if request.user.tipo_usuario == 'ALUNO':
        return redirect('listagem_livros')

    livro = get_object_or_404(Livro, id=id)
    livro.delete()
    return redirect('listagem_livros')


def fazer_logout(request):
    logout(request)
    return redirect('login')


def cadastrar_usuario(request):
    """Tela de auto-cadastro (pública)"""
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
    # 1. FILTRAGEM POR TIPO DE USUÁRIO
    if request.user.tipo_usuario == 'ALUNO':
        # Aluno: Vê apenas os SEUS empréstimos
        emprestimos = Emprestimo.objects.select_related('livro', 'usuario').filter(usuario=request.user).order_by('-id')
    else:
        # Staff: Vê TODOS os empréstimos
        emprestimos = Emprestimo.objects.select_related('livro', 'usuario').all().order_by('-id')

    # Filtro de Busca
    query = request.GET.get('q')
    if query:
        emprestimos = emprestimos.filter(
            Q(usuario__first_name__icontains=query) |
            Q(livro__titulo__icontains=query) |
            Q(usuario__matricula__icontains=query)
        )

    # Cálculos dos Cards (Baseados na lista filtrada)
    total_emprestimos = emprestimos.count()
    em_andamento = emprestimos.filter(data_devolucao_real__isnull=True,
                                      data_devolucao_prevista__gte=date.today()).count()
    atrasados = emprestimos.filter(data_devolucao_real__isnull=True, data_devolucao_prevista__lt=date.today()).count()
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
    # Bloqueio: Aluno não cria empréstimo manualmente
    if request.user.tipo_usuario == 'ALUNO':
        return redirect('listar_emprestimos')

    if request.method == 'POST':
        form = EmprestimoForm(request.POST)
        if form.is_valid():
            emprestimo = form.save(commit=False)

            # Regras: Data devolução (+14 dias) e Estoque (-1)
            emprestimo.data_devolucao_prevista = date.today() + timedelta(days=14)

            livro = emprestimo.livro
            if livro.quantidade > 0:
                livro.quantidade -= 1
                livro.save()
                emprestimo.save()

            return redirect('listar_emprestimos')

    return redirect('listar_emprestimos')


@login_required
def devolver_livro(request, id):
    # Bloqueio: Aluno não devolve livro no sistema
    if request.user.tipo_usuario == 'ALUNO':
        return redirect('listar_emprestimos')

    emprestimo = get_object_or_404(Emprestimo, id=id)

    if not emprestimo.data_devolucao_real:
        emprestimo.data_devolucao_real = date.today()
        emprestimo.save()

        # Devolve ao estoque
        livro = emprestimo.livro
        livro.quantidade += 1
        livro.save()

    return redirect('listar_emprestimos')


# --- LÓGICA DE USUÁRIOS (APENAS ADMIN) ---

@login_required
def listar_usuarios(request):
    # 1. BLOQUEIO DE SEGURANÇA: Apenas ADMIN ou Superuser
    if request.user.tipo_usuario != 'ADMIN' and not request.user.is_superuser:
        messages.error(request, "Acesso negado. Área restrita a administradores.")
        return redirect('listagem_livros')

    usuarios = Usuario.objects.all().order_by('-date_joined')

    query = request.GET.get('q')
    if query:
        usuarios = usuarios.filter(
            Q(first_name__icontains=query) |
            Q(email__icontains=query)
        )

    # Estatísticas
    total_usuarios = Usuario.objects.count()
    usuarios_ativos = Usuario.objects.filter(is_active=True).count()
    total_admins = Usuario.objects.filter(Q(tipo_usuario='ADMIN') | Q(is_superuser=True)).count()

    context = {
        'usuarios': usuarios,
        'total_usuarios': total_usuarios,
        'usuarios_ativos': usuarios_ativos,
        'total_admins': total_admins,
        'form_adicionar': FormAdicionarUsuario()
    }

    return render(request, 'usuarios.html', context)


@login_required
def adicionar_usuario(request):
    # Bloqueio: Apenas Admin
    if request.user.tipo_usuario != 'ADMIN' and not request.user.is_superuser:
        return redirect('listagem_livros')

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
    # Bloqueio: Apenas Admin
    if request.user.tipo_usuario != 'ADMIN' and not request.user.is_superuser:
        return redirect('listagem_livros')

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


# --- LÓGICA DE RESERVAS ---

@login_required
def reservar_livro(request, id):
    livro = get_object_or_404(Livro, id=id)
    usuario = request.user

    if Reserva.objects.filter(usuario=usuario, livro=livro, status='AGUARDANDO').exists():
        messages.error(request, "Você já reservou este livro.")
        return redirect('listagem_livros')

    if livro.quantidade > 0:
        livro.quantidade -= 1
        livro.save()

        Reserva.objects.create(usuario=usuario, livro=livro)
        messages.success(request, "Livro reservado! Você tem 24h para retirar na biblioteca.")
    else:
        messages.error(request, "Livro indisponível no momento.")

    return redirect('listagem_livros')


@login_required
def gerenciar_reservas(request):
    # Bloqueio: Aluno não gerencia reservas
    if request.user.tipo_usuario == 'ALUNO':
        return redirect('listagem_livros')

    agora = timezone.now()
    reservas_vencidas = Reserva.objects.filter(status='AGUARDANDO', data_expiracao__lt=agora)

    count_vencidas = 0
    for reserva in reservas_vencidas:
        livro = reserva.livro
        livro.quantidade += 1
        livro.save()

        reserva.status = 'CANCELADA'
        reserva.save()
        count_vencidas += 1

    if count_vencidas > 0:
        messages.info(request, f"{count_vencidas} reservas expiradas foram canceladas.")

    reservas = Reserva.objects.filter(status='AGUARDANDO').order_by('data_expiracao')

    return render(request, 'gerenciar_reservas.html', {'reservas': reservas})


@login_required
def validar_reserva(request, id):
    # Bloqueio: Aluno não valida reserva
    if request.user.tipo_usuario == 'ALUNO':
        return redirect('listagem_livros')

    reserva = get_object_or_404(Reserva, id=id)

    if reserva.status == 'AGUARDANDO':
        Emprestimo.objects.create(
            usuario=reserva.usuario,
            livro=reserva.livro,
            data_devolucao_prevista=date.today() + timedelta(days=14)
        )

        reserva.status = 'CONCLUIDA'
        reserva.save()

        messages.success(request, "Empréstimo confirmado com sucesso!")

    return redirect('gerenciar_reservas')