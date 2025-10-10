from django.contrib import admin
from .models import Hostel, Participant, Domain, SelfRating, Game, Round, Action

admin.site.register(Hostel)
admin.site.register(Participant)
admin.site.register(Domain)
admin.site.register(SelfRating)
admin.site.register(Game)
admin.site.register(Round)
admin.site.register(Action)