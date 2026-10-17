"""Celery fon vazifalari.

Modullar:
  * scheduled     — davriy (beat): auksion yopish, auto-complete.
  * notifications — push yetkazish (queue).
  * email         — email yuborish (queue).
  * dispatch      — enqueue() yordamchisi (broker yo'q bo'lsa inline zaxira).
"""
