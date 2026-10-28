"""Builds the public schemas from the domain, one file per topic.

This is the only place that decides what of a domain object reaches clients: the schemas only
declare the shape, and they have no field for the cost or the markup.
"""
