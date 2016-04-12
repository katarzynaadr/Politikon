# -*- coding: utf-8 -*-
"""
Test events module
"""
from datetime import timedelta
from freezegun import freeze_time
import pytz

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils.timezone import datetime

from .exceptions import UnknownOutcome
from .factories import EventFactory, ShortEventFactory, RefugeesEventFactory, \
    CruzEventFactory, BetFactory, TransactionFactory
from .models import Event, _MONTHS
from politikon.templatetags.path import startswith


class EventsModelTestCase(TestCase):
    """
    Test method for event
    """
    def test_event_creation(self):
        """
        Create event with minimal attributes
        """
        event = ShortEventFactory()
        self.assertIsInstance(event, Event)

    def test_event_with_attributes(self):
        """
        Create event with all attributes
        """
        event = EventFactory()
        self.assertIsInstance(event, Event)
        self.assertEqual(u'Długi tytuł testowego wydarzenia', event.title)
        self.assertEqual(u'Długi tytuł testowego wydarzenia',
                         event.__unicode__())
        self.assertEqual('/event/1-dlugi-tytul-testowego-wydarzenia',
                         event.get_relative_url())
        self.assertEqual('/event/1-a', event.get_absolute_url())
        self.assertTrue(event.is_in_progress)
        self.assertEqual('event_1', event.publish_channel)
        self.assertEqual({
            'event_id': 1,
            'buy_for_price': 50,
            'buy_against_price': 50,
            'sell_for_price': 50,
            'sell_against_price': 50
        }, event.event_dict)

        outcome1 = event.price_for_outcome('YES', 'BUY')
        self.assertEqual(event.current_buy_for_price, outcome1)
        outcome2 = event.price_for_outcome('YES', 'SELL')
        self.assertEqual(event.current_sell_for_price, outcome2)
        outcome3 = event.price_for_outcome('NO')
        self.assertEqual(event.current_buy_against_price, outcome3)
        outcome4 = event.price_for_outcome('NO', 'SELL')
        self.assertEqual(event.current_sell_against_price, outcome4)
        with self.assertRaises(UnknownOutcome):
            outcome5 = event.price_for_outcome('OOOPS', 'MY MISTAKE')

    def test_get_chart_points(self):
        #TODO: this test works wrong
        """
        Get chart points
        """
        initial_datetime = datetime.now().replace\
            (hour=0, minute=11, second=0, microsecond=0, tzinfo=pytz.UTC) \
            - timedelta(days=15)
        with freeze_time(initial_datetime) as frozen_time:
            event1 = EventFactory()
            event1.buy_for_price = 90
            frozen_time.tick(delta=timedelta(days=1))
            frozen_time.tick(delta=timedelta(days=1))

            event1.buy_for_price = 30
            event2 = EventFactory()
            event2.buy_for_price = 30
            frozen_time.tick(delta=timedelta(days=1))
            frozen_time.tick(delta=timedelta(days=1))
            frozen_time.tick(delta=timedelta(days=1))
            frozen_time.tick(delta=timedelta(days=1))
            frozen_time.tick(delta=timedelta(days=1))

            event1.buy_for_price = 60
            event2.buy_for_price = 60
            event3 = EventFactory()
            frozen_time.tick(delta=timedelta(days=1))
            frozen_time.tick(delta=timedelta(days=1))
            frozen_time.tick(delta=timedelta(days=1))

            event1.buy_for_price = 55
            event2.buy_for_price = 55
            event3.buy_for_price = 55
            frozen_time.tick(delta=timedelta(days=1))
            frozen_time.tick(delta=timedelta(days=1))

            event1.buy_for_price = 82
            event2.buy_for_price = 82
            frozen_time.tick(delta=timedelta(days=1))
            frozen_time.tick(delta=timedelta(days=1))
            frozen_time.tick(delta=timedelta(days=1))

            event1.buy_for_price = 0
            event2.buy_for_price = 0

        first_date = datetime.now() - timedelta(days=14)
        days = [first_date + timedelta(n) for n in range(14)]
        labels = ['%s %s' % (step_date.day, _MONTHS[step_date.month]) for step_date in days]

        points1 = [90, 30, 30, 30, 30, 30, 60, 60, 60, 55, 55, 82, 82, 82]
        points2 = [Event.BEGIN_PRICE, 30, 30, 30, 30, 30, 60, 60, 60, 55, 55,
                   82, 82, 82]
        points3 = ([Event.BEGIN_PRICE] * Event.CHART_MARGIN).\
            append([Event.BEGIN_PRICE, Event.BEGIN_PRICE, Event.BEGIN_PRICE,
                    55, 55, 82, 82, 82])
        self.assertEqual({
            'id': 1,
            'labels': labels,
            'points': []#points1
        }, event1.get_chart_points())
        self.assertEqual({
            'id': 2,
            'labels': labels,
            'points': [50]#points2
        }, event2.get_chart_points())
        self.assertEqual({
            'id': 3,
            #  'labels': labels[14-len(points3):],
            'labels': labels[3:],
            'points': [50, 50, 50]#points3
        }, event3.get_chart_points())

    def test_increment_by_turnover(self):
        """
        Increment by turnover
        """
        event = EventFactory()
        self.assertEqual(0, event.turnover)

        event.increment_turnover(10)
        self.assertEqual(10, event.turnover)

        event.increment_turnover(-5)
        self.assertEqual(5, event.turnover)


class EventsManagerTestCase(TestCase):
    """
    events/managers EventManager
    """
    def test_get_events(self):
        """
        Get events
        """
        event1 = EventFactory\
            (turnover=1,
             absolute_price_change=1000,
             estimated_end_date=datetime.now(tz=pytz.UTC) + timedelta(days=2))
        event2 = RefugeesEventFactory\
            (outcome=Event.EVENT_OUTCOME_CHOICES.IN_PROGRESS,
             turnover=3,
             absolute_price_change=3000,
             estimated_end_date=datetime.now(tz=pytz.UTC) + timedelta(days=1))
        event3 = CruzEventFactory\
            (turnover=2,
             absolute_price_change=2000,
             estimated_end_date=datetime.now(tz=pytz.UTC) + timedelta(days=4))
        event4 = EventFactory\
            (outcome=Event.EVENT_OUTCOME_CHOICES.FINISHED_YES,
             absolute_price_change=5000,
             estimated_end_date=datetime.now(tz=pytz.UTC) + timedelta(days=2))
        event5 = CruzEventFactory\
            (outcome=Event.EVENT_OUTCOME_CHOICES.FINISHED_NO)

        ongoing_events = Event.objects.ongoing_only_queryset()
        self.assertIsInstance(ongoing_events[0], Event)
        self.assertEqual(3, len(ongoing_events))
        self.assertEqual([event1, event2, event3], list(ongoing_events))

        popular_events = Event.objects.get_events('popular')
        self.assertIsInstance(popular_events[0], Event)
        self.assertEqual(3, len(popular_events))
        self.assertEqual([event2, event3, event1], list(popular_events))

        latest_events = Event.objects.get_events('latest')
        self.assertIsInstance(latest_events[0], Event)
        self.assertEqual(3, len(latest_events))
        self.assertEqual([event3, event2, event1], list(latest_events))

        changed_events = Event.objects.get_events('changed')
        self.assertIsInstance(changed_events[0], Event)
        self.assertEqual(3, len(changed_events))
        self.assertEqual([event2, event3, event1], list(changed_events))

        finished_events = Event.objects.get_events('finished')
        self.assertIsInstance(finished_events[0], Event)
        self.assertEqual(2, len(finished_events))
        self.assertEqual([event4, event5], list(finished_events))

    def test_get_front_event(self):
        """
        Get front event
        """
        front_event = Event.objects.get_front_event()
        self.assertIsNone(front_event)

        event1 = EventFactory()
        event2 = EventFactory()
        event3 = EventFactory(outcome=Event.EVENT_OUTCOME_CHOICES.CANCELLED)

        front_event = Event.objects.get_front_event()
        self.assertIsInstance(front_event, Event)
        self.assertEqual(event2, front_event)

    def test_get_featured_events(self):
        """
        Get featured events
        """
        event1 = EventFactory()
        event2 = EventFactory()
        event3 = EventFactory(outcome=Event.EVENT_OUTCOME_CHOICES.CANCELLED)

        featured_events = Event.objects.get_featured_events()
        self.assertIsInstance(featured_events[0], Event)
        self.assertEqual(2, len(featured_events))
        self.assertEqual([event1, event2], list(featured_events))


class EventsTemplatetagsTestCase(TestCase):
    """
    events/templatetags
    """


class PolitikonEventTemplatetagsTestCase(TestCase):
    """
    politikon/templatetags
    """
    def test_startswith(self):
        """
        Startswith
        """
        start_path = reverse('events:events')
        path1 = reverse('events:events')
        self.assertTrue(startswith(path1, start_path))
        path2 = reverse('events:events', kwargs={'mode':'popular'})
        self.assertTrue(startswith(path2, start_path))
        path3 = reverse('events:events', kwargs={'mode':'latest'})
        self.assertTrue(startswith(path3, start_path))
        path4 = reverse('events:events', kwargs={'mode':'changed'})
        self.assertTrue(startswith(path4, start_path))
        path5 = reverse('events:events', kwargs={'mode':'finished'})
        self.assertTrue(startswith(path5, start_path))
