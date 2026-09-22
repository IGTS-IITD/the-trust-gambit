from django.contrib import admin
from django import forms
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import path, reverse

from .lobby_utils import assign_participants_to_lobbies
from .round_flow import start_game
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

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    change_list_template = "admin/game/game/change_list.html"
    list_display = ["name", "is_active", "lambda_param", "beta_param"]

    def get_urls(self):
        return [
            path(
                "start-game/",
                self.admin_site.admin_view(self.start_game_view),
                name="game_game_start_game",
            ),
        ] + super().get_urls()

    def start_game_view(self, request):
        active_game = Game.objects.filter(is_active=True).first()
        if not active_game:
            messages.error(request, "No active game to start.")
        else:
            started = start_game(active_game)
            if started:
                messages.success(
                    request,
                    f"Round {started.round_number} started — rounds will now "
                    f"advance automatically on their own timers.",
                )
            else:
                messages.error(
                    request,
                    "Game already started, or there's no Round 1 to start yet.",
                )
        return HttpResponseRedirect(reverse("admin:game_game_changelist"))


@admin.register(Round)
class RoundAdmin(admin.ModelAdmin):
    list_display = [
        "round_number", "game", "domain", "duration_seconds",
        "starts_at", "is_completed",
    ]
    readonly_fields = ["starts_at", "is_completed"]
    ordering = ["game", "round_number"]


admin.site.register(Hostel)
admin.site.register(Domain)
admin.site.register(SelfRating)
admin.site.register(Lobby)
admin.site.register(Action)
