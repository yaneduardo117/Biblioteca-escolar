from django.db import models

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