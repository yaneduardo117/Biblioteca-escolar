from django import forms
from .models import Livro, Usuario
from datetime import date
from django.contrib.auth.forms import UserCreationForm


class LivroForm(forms.ModelForm):
    """
    Formulário responsável pelo cadastro e validação dos livros.
    """

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

        # --- ESTILIZAÇÃO E RESTRIÇÕES VISUAIS (WIDGETS) ---
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'isbn': forms.TextInput(attrs={'class': 'form-control'}),

            # ATUALIZAÇÃO: Adicionado min, max e placeholder para o Ano
            'ano_publicacao': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1000',  # Bloqueia visualmente anos antigos
                'max': str(date.today().year),  # Bloqueia visualmente anos futuros
                'placeholder': f'Ex: {date.today().year}'
            }),

            # Adicionado min para Quantidade
            'quantidade': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',  # Bloqueia visualmente números negativos
                'placeholder': 'Ex: 1'
            }),

            'categoria': forms.Select(attrs={'class': 'form-select'}),
        }

    # --- VALIDAÇÕES DE REGRA DE NEGÓCIO (BACKEND) ---

    def clean_isbn(self):
        isbn = self.cleaned_data.get('isbn')
        if not isbn: return isbn

        isbn = isbn.replace('-', '').replace(' ', '')

        if not isbn.isdigit():
            raise forms.ValidationError("ISBN deve conter apenas números.")

        if len(isbn) not in [10, 13]:
            raise forms.ValidationError("ISBN deve ter 10 ou 13 números.")

        return isbn

    def clean_ano_publicacao(self):
        """
        Valida se o ano é futuro ou muito antigo.
        """
        ano = self.cleaned_data.get('ano_publicacao')

        if ano is not None:
            ano_atual = date.today().year

            # Erro se for maior que o ano atual
            if ano > ano_atual:
                raise forms.ValidationError(f"Ano inválido (não pode ser maior que {ano_atual}).")

            # Erro se for menor que 1000 (evita erros de digitação como '20')
            if ano < 1000:
                raise forms.ValidationError("Ano inválido (muito antigo).")

        return ano

    def clean_quantidade(self):
        """
        Impede cadastro de quantidade negativa.
        """
        qtd = self.cleaned_data.get('quantidade')

        if qtd is not None and qtd < 0:
            raise forms.ValidationError("A quantidade não pode ser negativa.")

        return qtd


class CadastroUsuarioForm(forms.ModelForm):
    # Defini os campos de senha explicitamente para validação
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
        # Incluí todos os campos do formulário
        fields = [
            'first_name', 'last_name', 'data_nascimento',
            'matricula', 'telefone', 'turno', 'curso', 'email'
        ]

    def clean_email(self):
        # Validação extra para verificar se o email já existe
        email = self.cleaned_data.get('email')
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError("Este e-mail já está cadastrado.")
        return email

    def clean(self):
        # Validação geral (comparar senhas)
        cleaned_data = super().clean()
        senha1 = cleaned_data.get("senha1")
        senha2 = cleaned_data.get("senha2")

        if senha1 and senha2 and senha1 != senha2:
            # Adiciona o erro especificamente ao campo 'senha2'
            self.add_error('senha2', "As senhas não conferem.")

        return cleaned_data

    def save(self, commit=True):
        # Sobrescrever o save para criptografar a senha corretamente
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["senha1"])
        user.username = user.email  # Garante que username seja igual ao email
        if commit:
            user.save()
        return user