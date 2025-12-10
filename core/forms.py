from django import forms
from .models import Livro, Usuario, Emprestimo
from datetime import date


# FORMULÁRIO DE LIVROS
class LivroForm(forms.ModelForm):
    """
    Formulário para cadastro e edição de livros.
    """

    # Campo 'nome_autor' criado manualmente.
    # No banco, Autor é um ID (ForeignKey), mas na tela o usuário
    # digite o nome. A conversão de Texto -> ID é feita na View.
    nome_autor = forms.CharField(
        label='Nome do Autor',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite o nome do autor'
        }),
        max_length=100
    )

    class Meta:
        model = Livro
        fields = ['titulo', 'categoria', 'isbn', 'ano_publicacao', 'quantidade']

        # Widgets aplicam classes CSS (Bootstrap) e atributos HTML (min, max)
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'isbn': forms.TextInput(attrs={'class': 'form-control'}),
            'ano_publicacao': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1000',  # Bloqueia anos muito antigos no front-end
                'max': str(date.today().year),  # Bloqueia anos futuros no front-end
                'placeholder': f'Ex: {date.today().year}'
            }),
            'quantidade': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',  # Bloqueia números negativos no front-end
                'placeholder': 'Ex: 1'
            }),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
        }

    # --- VALIDAÇÕES (BACKEND) ---

    def clean_isbn(self):
        """Valida se o ISBN contém apenas números e tem 10 ou 13 dígitos."""
        isbn = self.cleaned_data.get('isbn')
        if not isbn: return isbn

        # Remove traços e espaços antes de validar
        isbn = isbn.replace('-', '').replace(' ', '')

        if not isbn.isdigit():
            raise forms.ValidationError("ISBN deve conter apenas números.")
        if len(isbn) not in [10, 13]:
            raise forms.ValidationError("ISBN deve ter 10 ou 13 números.")
        return isbn

    def clean_ano_publicacao(self):
        """Valida se o ano não é futuro nem muito antigo."""
        ano = self.cleaned_data.get('ano_publicacao')
        if ano is not None:
            ano_atual = date.today().year
            if ano > ano_atual:
                raise forms.ValidationError(f"Ano inválido (não pode ser maior que {ano_atual}).")
            if ano < 1000:
                raise forms.ValidationError("Ano inválido (muito antigo).")
        return ano

    def clean_quantidade(self):
        """Impede estoque negativo."""
        qtd = self.cleaned_data.get('quantidade')
        if qtd is not None and qtd < 0:
            raise forms.ValidationError("A quantidade não pode ser negativa.")
        return qtd



# FORMULÁRIO DE USUÁRIOS (ALUNOS/ADMINS)
class CadastroUsuarioForm(forms.ModelForm):
    """
    Formulário personalizado para registro de usuários.
    Gerencia a senha manualmente para garantir a criptografia correta.
    """
    senha1 = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True
    )
    senha2 = forms.CharField(
        label='Confirmar Senha',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True
    )

    class Meta:
        model = Usuario
        fields = [
            'first_name', 'last_name', 'data_nascimento',
            'matricula', 'telefone', 'turno', 'curso', 'email'
        ]

    def clean_email(self):
        """Verifica se o e-mail já existe no banco de dados."""
        email = self.cleaned_data.get('email')
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError("Este e-mail já está cadastrado.")
        return email

    def clean(self):
        """Validação geral: Verifica se as duas senhas conferem."""
        cleaned_data = super().clean()
        senha1 = cleaned_data.get("senha1")
        senha2 = cleaned_data.get("senha2")

        if senha1 and senha2 and senha1 != senha2:
            self.add_error('senha2', "As senhas não conferem.")
        return cleaned_data

    def save(self, commit=True):
        """
        Sobrescreve o salvamento para:
        1. Criptografar a senha (hash).
        2. Definir o username igual ao email (para compatibilidade com Django Auth).
        """
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["senha1"])
        user.username = user.email
        if commit:
            user.save()
        return user


# FORMULÁRIO DE EMPRÉSTIMOS
class EmprestimoForm(forms.ModelForm):
    """
    Formulário para registrar a saída de livros.
    """

    class Meta:
        model = Emprestimo
        fields = ['usuario', 'livro']

        widgets = {
            'usuario': forms.Select(attrs={'class': 'form-select'}),
            'livro': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        """
        Ao iniciar o formulário, filtramos a lista de livros
        para exibir APENAS aqueles que têm estoque disponível (quantidade > 0).
        """
        super().__init__(*args, **kwargs)
        self.fields['livro'].queryset = Livro.objects.filter(quantidade__gt=0)