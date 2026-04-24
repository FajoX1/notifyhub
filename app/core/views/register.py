from allauth.account.views import SignupView


class RegisterView(SignupView):
    template_name = "auth/register.html"
