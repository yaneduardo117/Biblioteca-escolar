from django import forms
from .models import Livro
from datetime import date


class LivroForm(forms.ModelForm):
    """
    Formulário responsável pelo cadastro e validação dos livros.
    Herda de ModelForm para facilitar a integração com o banco de dados.
    """

    # --- CAMPO PERSONALIZADO: NOME DO AUTOR ---
    # foi criado o campo 'nome_autor' manualmente porque, no banco de dados,
    # o Autor é uma chave estrangeira (ID). Aqui, queremos permitir que o
    # usuário digite o nome (Texto) livremente para melhorar a usabilidade.
    # A conversão de "Nome Texto" para "ID do Autor" será feita na View.
    nome_autor = forms.CharField(
        label='Nome do Autor',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite o nome do autor'
        }),
        max_length=100
    )

    class Meta:
        # Define qual modelo (tabela) este formulário vai alimentar
        model = Livro

        # Lista de campos que serão exibidos no HTML.
        # Note que removemos o campo 'autor' original (dropdown) e usamos o 'nome_autor' acima.
        fields = ['titulo', 'categoria', 'isbn', 'ano_publicacao', 'quantidade']

        # --- ESTILIZAÇÃO (BOOTSTRAP) ---
        # O dicionário 'widgets' serve para injetar classes CSS nos inputs do HTML.
        # Usamos 'form-control' e 'form-select' para aplicar o visual do Bootstrap.
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'isbn': forms.TextInput(attrs={'class': 'form-control'}),
            'ano_publicacao': forms.NumberInput(attrs={'class': 'form-control'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
        }

    # --- VALIDAÇÕES DE REGRA DE NEGÓCIO ---

    def clean_isbn(self):
        """
        Valida o campo ISBN conforme requisitos do projeto:
        1. Remove formatação (traços e espaços).
        2. Verifica se contém apenas números.
        3. Verifica se tem 10 ou 13 dígitos.
        """
        isbn = self.cleaned_data.get('isbn')

        # Se o campo estiver vazio, retorna vazio (o required=True padrão já trata isso)
        if not isbn: return isbn

        # Sanitização: Remove caracteres especiais que o usuário possa ter digitado
        isbn = isbn.replace('-', '').replace(' ', '')

        # Regra 1: Apenas números
        if not isbn.isdigit():
            raise forms.ValidationError("ISBN deve conter apenas números.")

        # Regra 2: Tamanho exato (Desafio do PDF)
        if len(isbn) not in [10, 13]:
            raise forms.ValidationError("ISBN deve ter 10 ou 13 números.")

        return isbn  # Retorna o dado limpo para ser salvo

    def clean_ano_publicacao(self):
        """
        Valida o Ano de Publicação.
        Impede o cadastro de livros com datas futuras (ex: ano 2050).
        """
        ano = self.cleaned_data.get('ano_publicacao')

        # Compara o ano digitado com o ano atual do sistema
        if ano and ano > date.today().year:
            raise forms.ValidationError("Ano inválido (futuro).")

        return ano