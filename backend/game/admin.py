from django.contrib import admin
from django import forms
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import path, reverse

from .lobby_utils import assign_participants_to_lobbies
from .models import Hostel, Participant, Domain, SelfRating, Game, Lobby, Round, Action


class LobbyAssignmentForm(forms.Form):
    lobby_size = forms.IntegerField(min_value=1)


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    change_list_template = "admin/game/participant/change_list.html"

    def get_urls(self):
        return [
            path(
                "assign-lobbies/",
                self.admin_site.admin_view(self.assign_lobbies),
                name="game_participant_assign_lobbies",
            ),
        ] + super().get_urls()

    def assign_lobbies(self, request):
        form = LobbyAssignmentForm(request.POST)
        if form.is_valid():
            result = assign_participants_to_lobbies(form.cleaned_data["lobby_size"])
            if "error" in result:
                messages.error(request, result["error"])
            else:
                messages.success(
                    request,
                    f'{result["participants_assigned"]} participants assigned to '
                    f'{result["lobbies_created"]} lobbies.',
                )
        else:
            messages.error(request, "Lobby size must be a positive integer.")

        return HttpResponseRedirect(reverse("admin:game_participant_changelist"))

admin.site.register(Hostel)
admin.site.register(Domain)
admin.site.register(SelfRating)
admin.site.register(Game)
admin.site.register(Lobby)
admin.site.register(Round)
admin.site.register(Action)
