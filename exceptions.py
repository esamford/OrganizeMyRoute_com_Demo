

class NotRoutableException(Exception):
    """
    The provided addresses could not be routed by TrueWay API. This is likely because a person cannot drive
    between them.
    """
    pass


