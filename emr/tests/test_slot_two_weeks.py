"""La agenda de dos semanas no mezcla los turnos de las dos semanas."""
from datetime import date, datetime, time, timedelta

from pytz import timezone, utc

from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestTwoWeekSlotGeneration(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tz = timezone("America/Buenos_Aires")
        cls.lau = cls._practitioner("Lau", morning_week="0")
        cls.poly = cls._practitioner("Poly", morning_week="1")
        cls.Slot = cls.env["emr.slot"]

    @classmethod
    def _practitioner(cls, name, morning_week):
        afternoon_week = "1" if morning_week == "0" else "0"
        attendances = [
            Command.create({
                "name": "Semana 1",
                "dayofweek": "0",
                "week_type": "0",
                "hour_from": 0,
                "hour_to": 0,
                "day_period": "morning",
                "display_type": "line_section",
                "sequence": 0,
            }),
            Command.create({
                "name": "Semana 2",
                "dayofweek": "0",
                "week_type": "1",
                "hour_from": 0,
                "hour_to": 0,
                "day_period": "morning",
                "display_type": "line_section",
                "sequence": 25,
            }),
        ]
        for day in range(5):
            attendances.append(Command.create({
                "name": "Mañana",
                "dayofweek": str(day),
                "week_type": morning_week,
                "hour_from": 9.0,
                "hour_to": 14.0,
                "day_period": "morning",
                "slot_duration": 60,
                "slot_type": "scheduled",
            }))
            attendances.append(Command.create({
                "name": "Tarde",
                "dayofweek": str(day),
                "week_type": afternoon_week,
                "hour_from": 14.0,
                "hour_to": 20.0,
                "day_period": "afternoon",
                "slot_duration": 60,
                "slot_type": "scheduled",
            }))
        calendar = cls.env["resource.calendar"].with_context(
            resource_skip_inverse_two_weeks=True
        ).create({
            "name": "Agenda %s" % name,
            "tz": "America/Buenos_Aires",
            "two_weeks_calendar": True,
            "attendance_ids": attendances,
        })
        partner = cls.env["res.partner"].create({
            "name": name,
            "is_practitioner": True,
            "scheduling_method": "slots",
        })
        partner.resource_id.calendar_id = calendar
        return partner

    def _hours(self, practitioner, day):
        slots = self.Slot.search([
            ("practitioner_id", "=", practitioner.id),
            ("start", ">=", datetime.combine(day, time.min)),
            ("start", "<=", datetime.combine(day, time.max)),
        ])
        return sorted(
            utc.localize(slot.start).astimezone(self.tz).hour for slot in slots
        )

    def test_alternating_weeks_do_not_stack_both_shifts(self):
        week_even = date(2026, 11, 23)
        week_odd = date(2026, 11, 30)
        self.assertEqual(
            str(self.env["resource.calendar.attendance"].get_week_type(week_even)),
            "0",
        )
        self.assertEqual(
            str(self.env["resource.calendar.attendance"].get_week_type(week_odd)),
            "1",
        )
        self.Slot._generate_for_practitioner(self.lau, week_even, week_odd)
        self.Slot._generate_for_practitioner(self.poly, week_even, week_odd)

        self.assertEqual(self._hours(self.lau, week_even), [9, 10, 11, 12, 13])
        self.assertEqual(self._hours(self.poly, week_even), [14, 15, 16, 17, 18, 19])
        self.assertEqual(self._hours(self.lau, week_odd), [14, 15, 16, 17, 18, 19])
        self.assertEqual(self._hours(self.poly, week_odd), [9, 10, 11, 12, 13])

        before = self.Slot.search_count([
            ("practitioner_id", "in", (self.lau.id, self.poly.id)),
        ])
        booked = self.Slot.search([
            ("practitioner_id", "=", self.lau.id),
        ], order="start", limit=1)
        booked.block_reason = "holiday"
        self.Slot._generate_for_practitioner(self.lau, week_even, week_odd)
        self.Slot._generate_for_practitioner(self.poly, week_even, week_odd)
        self.assertEqual(
            self.Slot.search_count([
                ("practitioner_id", "in", (self.lau.id, self.poly.id)),
            ]),
            before,
        )
        self.assertEqual(booked.block_reason, "holiday")

    def test_plain_calendar_still_repeats_every_week(self):
        calendar = self.env["resource.calendar"].create({
            "name": "Agenda simple",
            "tz": "America/Buenos_Aires",
            "attendance_ids": [Command.create({
                "name": "Lunes",
                "dayofweek": "0",
                "hour_from": 9.0,
                "hour_to": 12.0,
                "day_period": "morning",
                "slot_duration": 60,
                "slot_type": "scheduled",
            })],
        })
        partner = self.env["res.partner"].create({
            "name": "Fijo",
            "is_practitioner": True,
            "scheduling_method": "slots",
        })
        partner.resource_id.calendar_id = calendar
        first = date(2026, 11, 23)
        second = date(2026, 11, 30)
        self.Slot._generate_for_practitioner(partner, first, second)
        self.assertEqual(self._hours(partner, first), [9, 10, 11])
        self.assertEqual(self._hours(partner, second), [9, 10, 11])
