import datetime

from django.db import models


class API(models.Model):
    """
    A model that tracks external API address_dict.

    This model exists so that the API key and request delay can be updated from the admin site. Otherwise,
    the project would need to be updated for each change.
    """
    name = models.CharField(max_length=100, unique=True)  # Cannot edit because views fetch by name.
    description = models.TextField(max_length=500, blank=True)
    api_url = models.URLField()
    api_key = models.TextField()  # Specific implementation of the key will be handled by each view.
    request_delay = models.DecimalField(default=0.5, max_digits=5, decimal_places=4)
    num_request_attempts = models.PositiveIntegerField(default=2)

    def __str__(self):
        return "{}".format(self.name)


class APIRequest(models.Model):
    """
    A model that tracks requests to each external API. Use this to prevent overburdening their API using the
    API foreign table's "request_delay" attribute.
    """
    CONST_STATUS_CHOICES = (
        ("waiting", "waiting"),
        ("finished", "finished"),
        ("error", "error"),
    )

    api = models.ForeignKey(API, on_delete=models.CASCADE)
    time = models.DateTimeField(default=datetime.datetime.utcnow, blank=True)
    status = models.CharField(max_length=20, choices=CONST_STATUS_CHOICES, default="waiting")

    def __str__(self):
        return "{}, {}  |  {}, {}".format(self.id, self.api, self.status, self.time)
