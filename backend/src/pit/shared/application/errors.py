class ConcurrencyConflict(Exception):
    """Someone else changed the aggregate since it was loaded (optimistic locking).

    Not a business error: the message bus retries the handler with fresh state.
    """
