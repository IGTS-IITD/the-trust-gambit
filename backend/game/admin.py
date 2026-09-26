from django.contrib import admin
from django import forms
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.shortcuts import get_object_or_404

from .round_flow import start_game
from .models import Hostel, Participant, Domain, SelfRating, Game, Lobby, Round, Action, GameMembership

@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ["user", "hostel"]
    search_fields = ["user__username", "user__email"]
    list_filter = ["hostel"]

@admin.action(description="Start selected games")
def start_selected_games(modeladmin, request, queryset):
    for game in queryset:
        if Game.objects.filter(state=Game.State.RUNNING).exists():
            messages.error(request, f"Cannot start '{game.name}': Another game is already running!")
            continue
            
        if game.state == Game.State.REGISTRATION:
            started = start_game(game)
            if started:
                messages.success(request, f"Game '{game.name}' started. Round {started.round_number} is now active.")
            else:
                messages.error(request, f"Could not start '{game.name}'. No round 1 exists.")
        else:
            messages.warning(request, f"Game '{game.name}' is not in REGISTRATION state.")

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ["name", "state", "lambda_param", "beta_param", "player_limit", "start_button"]
    list_filter = ["state"]
    search_fields = ["name"]
    actions = [start_selected_games]

    def start_button(self, obj):
        if obj.state == Game.State.REGISTRATION:
            url = reverse('admin:game_game_start_game', args=[obj.pk])
            return format_html('<a class="button" href="{}" style="padding: 4px 8px; background-color: #28a745; color: white; border-radius: 4px; text-decoration: none;">Start Game</a>', url)
        return ""
    start_button.short_description = "Start Action"

    def get_urls(self):
        return [
            path(
                "<int:game_id>/start-game/",
                self.admin_site.admin_view(self.start_game_view),
                name="game_game_start_game",
            ),
        ] + super().get_urls()

    def start_game_view(self, request, game_id):
        game = get_object_or_404(Game, pk=game_id)
        if Game.objects.filter(state=Game.State.RUNNING).exists():
            messages.error(request, "Another game is already running! Wait for it to complete.")
        elif game.state == Game.State.REGISTRATION:
            started = start_game(game)
            if started:
                messages.success(request, f"Game '{game.name}' started. Round {started.round_number} is now active.")
            else:
                messages.error(request, f"Could not start '{game.name}'. No round 1 exists.")
        else:
            messages.warning(request, f"Game '{game.name}' is not in REGISTRATION state.")
        return HttpResponseRedirect(reverse("admin:game_game_changelist"))


@admin.register(Round)
class RoundAdmin(admin.ModelAdmin):
    list_display = [
        "round_number", "game", "domain", "duration_seconds",
        "starts_at", "is_completed",
    ]
    readonly_fields = ["starts_at", "is_completed"]
    list_filter = ["game", "is_completed", "domain"]
    ordering = ["game", "round_number"]

@admin.register(Lobby)
class LobbyAdmin(admin.ModelAdmin):
    list_display = ["name", "game", "sequence_number", "is_active"]
    list_filter = ["game", "is_active"]
    search_fields = ["name"]
    
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        # Prevent manual deletion from the Lobby admin page,
        # but allow it to return True during a Game cascade delete
        if request.path and '/admin/game/lobby/' in request.path:
            return False
        return True

class GameMembershipForm(forms.ModelForm):
    class Meta:
        model = GameMembership
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        lobby = cleaned_data.get('lobby')
        game = cleaned_data.get('game')
        
        if lobby and game:
            if lobby.game != game:
                raise forms.ValidationError("Lobby must belong to the same game.")
            
            if self.instance.lobby != lobby:
                if lobby.members.count() >= game.player_limit:
                    raise forms.ValidationError(f"Cannot assign to {lobby.name}: it is already at or above the player limit ({game.player_limit}).")
                    
        return cleaned_data


@admin.register(GameMembership)
class GameMembershipAdmin(admin.ModelAdmin):
    form = GameMembershipForm
    list_display = ["participant", "game", "lobby", "eligible_from_round"]
    list_filter = ["game", "lobby"]
    search_fields = ["participant__user__username"]

admin.site.register(Hostel)
admin.site.register(Domain)
admin.site.register(SelfRating)
admin.site.register(Action)
