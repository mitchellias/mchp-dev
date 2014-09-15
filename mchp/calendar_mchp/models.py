from django.conf import settings
from django.db import models
from django.utils import timezone

from calendar_mchp.exceptions import TimeOrderError, CalendarExpiredError, BringingUpThePastError
from calendar_mchp.signals import calendar_event_created, calendar_event_edited, subscription

class ClassCalendarManager(models.Manager):
    def default(self, student):
        calendar, created = ClassCalendar.objects.get_or_create(
            owner=student,
            title='default',
        )
        return calendar

class ClassCalendar(models.Model):
    owner = models.ForeignKey('user_profile.Student', related_name="calendars")
    subscribers = models.ManyToManyField('user_profile.Student', through='Subscription')

    title = models.CharField(max_length=150)
    description = models.CharField(max_length=2000, blank=True)
    course = models.ForeignKey('schedule.Course', related_name="calendar_courses")

    private = models.BooleanField(default=True)
    price = models.PositiveIntegerField(default=0)
    accuracy = models.FloatField(default=-1)

    create_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    expire_date = models.DateTimeField()

    color = models.CharField(max_length=7, blank=True, default="#FFFFFF")

    objects = ClassCalendarManager()

    class Meta:
        unique_together = (('owner', 'course'))

    def save(self, *args, **kwargs):
        # object is new
        if not self.pk:
            # object is new and doesn't have a title
            if not self.title: 
                self.title = str(self.course.dept) + " " + str(self.course.course_number)
            # give this calendar a max lifetime
            self.expire_date = timezone.now() + settings.MCHP_PRICING['calendar_expiration']

        # don't let end date go past six months from calendar creation
        if self.end_date > self.expire_date:
            self.end_date = self.expire_date

        if(self.end_date > timezone.now()):
            super().save()
        else:
            raise TimeOrderError("Start date must come before end date")

        # set accuracy 
        subs = Subscription.objects.filter(
            calendar = self
        )
        accuracies = list(map(lambda sub: sub.accuracy, subs))
        accuracies = list(filter(lambda score: score != -1, accuracies))
        if(len(accuracies)):
            accuracy = sum(accuracies) / len(accuracies)
            # convert acc to a percentage
            accuracy = round(accuracy * 10, 0)
            # format to no decimal places
            self.accuracy = '{:3.0f}'.format(accuracy)

        super(ClassCalendar, self).save(*args, **kwargs)

    def __str__(self):
        return self.title

class Subscription(models.Model):
    student = models.ForeignKey('user_profile.Student')
    calendar = models.ForeignKey(ClassCalendar)

    price = models.PositiveIntegerField(default=1)
    payment_date = models.DateTimeField()
    subscribe_date = models.DateTimeField(auto_now_add=True)
    enabled = models.BooleanField(default=True)

    accuracy = models.SmallIntegerField(default=-1)

    def save(self, *args, **kwargs):
        # object is new
        if not self.pk:
            # not allowed to follow private calendars
            # this should raise an exception
            if self.calendar.private:
                return
            # set first payment date
            self.subscribe_date = timezone.now()
            self.payment_date = self.subscribe_date + settings.MCHP_PRICING['subscription_length']
            subscription.send(sender=self.__class__, subscription=self)
        # fix up accuracy ratings 
        # this should be a validator instead, but this is more simple 
        if self.accuracy < -1:
            self.accuracy = 0
        if self.accuracy > 10:
            self.accuracy = 10
        super(Subscription, self).save(*args, **kwargs)

    def __str__(self):
        return "subscribed to {} on {}".format(self.calendar.title, self.subscribe_date)

class CalendarEvent(models.Model):
    calendar = models.ForeignKey(ClassCalendar)

    title = models.CharField(max_length=30)
    description = models.CharField(max_length=200)

    all_day = models.BooleanField(default=False)
    start = models.DateTimeField(blank=True, null=True)
    end = models.DateTimeField(blank=True, null=True)
    url = models.URLField(blank=True)

    is_recurring = models.BooleanField(default=False)
    
    create_date = models.DateTimeField(auto_now_add=True)
    last_edit = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.pk:
            # first time
            edit = False
        else:
            edit = True

        # don't let end date go past six months from calendar creation
        if self.end > self.calendar.end_date:
            end_date = timezone.localtime(
                self.calendar.end_date, 
                timezone.get_current_timezone()
            ).strftime('%B %d, %Y')
            raise CalendarExpiredError(
                "You can not add events after this calendar's end date: {}"\
                .format(end_date)
            )

        if self.start < timezone.now():
            raise BringingUpThePastError(
                "You can not change the past. Give it up, Gatsby."
            )

        if(self.end > self.start):
            super().save()
        else:
            raise TimeOrderError("Start date must come before end date")
        self.last_edit = timezone.now()
        super(CalendarEvent, self).save(*args, **kwargs)

        if edit:
            calendar_event_edited.send(sender=self.__class__, event=self)
        else:
            calendar_event_created.send(sender=self.__class__, event=self)

    def __str__(self):
        return self.title
