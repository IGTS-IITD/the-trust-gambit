from django.urls import path
from .views import (
    DelegationGraphView, RegisterUserView, CustomAuthToken, 
    ParticipantProfileView, DomainListView, RoundListView, 
    SelfRatingCreateListView, HostelListView,
    CurrentRoundView, SubmitActionView,
    LeaderboardView, AdminEndRoundView, AllRatingsListView,
    AdminAssignLobbiesView
)

urlpatterns = [
    path('register/', RegisterUserView.as_view(), name='register'),
    path('login/', CustomAuthToken.as_view(), name='login'),
    path('profile/', ParticipantProfileView.as_view(), name='participant-profile'),
    path('domains/', DomainListView.as_view(), name='domain-list'),
    path('hostels/', HostelListView.as_view(), name='hostel-list'),
    path('self-ratings/', SelfRatingCreateListView.as_view(), name='self-rating-list-create'),
    path('all-ratings/', AllRatingsListView.as_view(), name='all-ratings-list'),

    path('current-round/', CurrentRoundView.as_view(), name='current-round'),
    path('submit-action/', SubmitActionView.as_view(), name='submit-action'),
    path('leaderboard/', LeaderboardView.as_view(), name='leaderboard'),

    path('rounds/', RoundListView.as_view(), name='round-list'),
    path('rounds/<int:round_id>/delegation-graph/', DelegationGraphView.as_view(), name='delegation-graph'),
    # path('lobbies/<int:lobby_id>/leaderboard/', LobbyLeaderboardView.as_view(), name='lobby-leaderboard'),

    path('admin/end-round/', AdminEndRoundView.as_view(), name='admin-end-round'),
    path('admin/assign-lobbies/', AdminAssignLobbiesView.as_view(), name='admin-assign-lobbies'),
]