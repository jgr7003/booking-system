"""Entry points of the background processes (`python -m app.workers.<name>`).

Like `app.main`, this is a composition root: it is the only place, besides `app.main`, that
puts several modules together, so it sits outside the module boundaries.
"""
