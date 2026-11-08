from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from .forms import ProfileForm, UserNameForm
from .models import Profile


class ProfileUpdateView(LoginRequiredMixin, View):
    template_name = 'profiles/profile_form.html'
    success_message = 'Perfil atualizado com sucesso.'

    def get_profile(self):
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        return profile

    def render_forms(self, user_form, profile_form):
        context = {
            'user_form': user_form,
            'profile_form': profile_form,
        }
        return render(self.request, self.template_name, context)

    def get(self, request, *args, **kwargs):
        user_form = UserNameForm(instance=request.user)
        profile_form = ProfileForm(instance=self.get_profile())
        return self.render_forms(user_form, profile_form)

    def post(self, request, *args, **kwargs):
        user_form = UserNameForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, instance=self.get_profile())
        if all([user_form.is_valid(), profile_form.is_valid()]):
            user_form.save()
            profile_form.save()
            messages.success(request, self.success_message)
            return redirect('profile')
        return self.render_forms(user_form, profile_form)
