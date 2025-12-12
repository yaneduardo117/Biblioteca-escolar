"""
URL configuration for biblioteca project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from core import views
from core.forms import LoginForm

urlpatterns = [
    path('admin/', admin.site.urls),

    # --- ROTAS DE AUTENTICAÇÃO ---
    path('login/', auth_views.LoginView.as_view(template_name='login.html', authentication_form=LoginForm), name='login'),
    path('logout/', views.fazer_logout, name='logout'),
    path('registrar/', views.cadastrar_usuario, name='cadastrar_usuario'),

    # ---  ROTAS DO SISTEMA ---
    # rotas do campo livros:
    path('', views.listagem_livros, name='listagem_livros'),
    path('cadastrar/', views.cadastro_livro, name='cadastro_livro'),
    path('editar/<int:id>/', views.editar_livro, name='editar_livro'),
    path('remover/<int:id>/', views.remover_livro, name='remover_livro'),
    # rotas do campo emprestimos:
    path('emprestimos/', views.listar_emprestimos, name='listar_emprestimos'),
    path('emprestimos/novo/', views.criar_emprestimo, name='criar_emprestimo'),
    path('emprestimos/devolver/<int:id>/', views.devolver_livro, name='devolver_livro'),
    # rotas do campo usuários:
    path('usuarios/', views.listar_usuarios, name='listar_usuarios'),
    path('usuarios/adicionar/', views.adicionar_usuario, name='adicionar_usuario'),
    path('usuarios/editar/<int:id>/', views.editar_usuario, name='editar_usuario'),
    # rotas de reservas:
    path('reservar/<int:id>/', views.reservar_livro, name='reservar_livro'),
    path('reservas/', views.gerenciar_reservas, name='gerenciar_reservas'),
    path('reservas/validar/<int:id>/', views.validar_reserva, name='validar_reserva'),
]
