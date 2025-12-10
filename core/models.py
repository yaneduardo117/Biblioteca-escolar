from django.db import models
from django.contrib.auth.models import AbstractUser
from datetime import date, timedelta

class Categoria(models.Model):
    nome = models.CharField(max_length=50, unique=True)
    def __str__(self): return self.nome

class Autor(models.Model):
    nome = models.CharField(max_length=100)
    def __str__(self): return self.nome

class Livro(models.Model):
    titulo = models.CharField(max_length=200)
    isbn = models.CharField(max_length=13, unique=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT)
    autor = models.ForeignKey(Autor, on_delete=models.PROTECT)
    ano_publicacao = models.IntegerField()
    quantidade = models.IntegerField(default=1)

    def __str__(self): return self.titulo

class Usuario(AbstractUser):
    """
    Modelo de usuário personalizado para suportar campos extras
    e controle de níveis de acesso.
    """
    # Opções de Turno
    TURNO_CHOICES = [
        ('M', 'Matutino'),
        ('V', 'Vespertino'),
        ('N', 'Noturno'),
        ('I', 'Integral'),
    ]

    # Níveis de Acesso
    TIPO_ALUNO = 'ALUNO'
    TIPO_BIBLIOTECARIO = 'BIBLIOTECARIO'
    TIPO_ADMIN = 'ADMIN'

    TIPO_USUARIO_CHOICES = [
        (TIPO_ALUNO, 'Aluno'),
        (TIPO_BIBLIOTECARIO, 'Bibliotecário'),
        (TIPO_ADMIN, 'Administrador'),
    ]

    # Campos extras exigidos no layout
    matricula = models.CharField('Matrícula Escolar', max_length=20, blank=True, null=True)
    data_nascimento = models.DateField('Data de Nascimento', blank=True, null=True)
    curso = models.CharField('Curso / Modalidade', max_length=100, blank=True, null=True)
    turno = models.CharField('Turno', max_length=1, choices=TURNO_CHOICES, blank=True, null=True)
    telefone = models.CharField('Telefone / WhatsApp', max_length=20, blank=True, null=True)

    # Define o nível de acesso (Padrão é ALUNO)
    tipo_usuario = models.CharField(
        'Tipo de Usuário',
        max_length=20,
        choices=TIPO_USUARIO_CHOICES,
        default=TIPO_ALUNO
    )

    # Forçar o login por e-mail (opcional, mas recomendado pelo seu layout)
    email = models.EmailField('Endereço de E-mail', unique=True)

    # Configurações para logar com email ao invés de username
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    def __str__(self):
        return f"{self.first_name} ({self.tipo_usuario})"


class Emprestimo(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    livro = models.ForeignKey(Livro, on_delete=models.PROTECT)
    data_emprestimo = models.DateField(auto_now_add=True)
    data_devolucao_prevista = models.DateField()
    data_devolucao_real = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.usuario} - {self.livro}"

    @property
    def status(self):
        if self.data_devolucao_real:
            return 'Devolvido'
        if date.today() > self.data_devolucao_prevista:
            return 'Atrasado'
        return 'Em andamento'