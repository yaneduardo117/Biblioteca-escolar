from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        try:
            # busca o usuário pelo email
            user = UserModel.objects.get(email=username)
        except UserModel.DoesNotExist:
            return None

        # Se achou o usuário pelo email, verifica a senha
        if user.check_password(password):
            return user
        return None