"""Emails of the flights module: how they look (templates) and when they go (event consumers).

Like `api`, it is a way out to the traveler, so it builds on the public view of a booking
(`api.mappers.bookings.to_booking_response`): an email can never carry the cost or the markup.
"""
