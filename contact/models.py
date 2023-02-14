from django.db import models


class Message(models.Model):
    CONST_PURPOSE_CHOICES = (
        ("Requesting a feature", "Requesting a feature"),
        ("Reporting an error", "Reporting an error"),
        ("Other", "Other")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    read = models.BooleanField(default=False)
    subject = models.CharField(max_length=200)
    reason = models.CharField(max_length=50, choices=CONST_PURPOSE_CHOICES)
    message = models.TextField(max_length=3000)

    def subject_snip(self):
        snip_length = 20
        if len(str(self.subject)) > snip_length:
            return str(self.subject)[:snip_length] + "..."
        else:
            return self.subject

    def message_snip(self):
        snip_length = 30
        if len(str(self.message)) > snip_length:
            return str(self.message)[:snip_length] + "..."
        else:
            return self.message

    def __str__(self):
        return "{}: {}".format(self.subject_snip(), self.message_snip())
