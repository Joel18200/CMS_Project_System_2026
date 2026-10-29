from django.test import TestCase

# Create your tests here.
"""Receptionist API tests. Run: python manage.py test receptionist"""
from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APITestCase

from doctor.models import DoctorProfile, DoctorSchedule
from .models import Appointment, ConsultationPayment, Patient, QueueToken, ReceptionistProfile


def future_date(days=3):
    return timezone.localdate() + timedelta(days=days)


class BaseAPITest(APITestCase):
    def setUp(self):
        # Receptionist + a non-receptionist user (e.g. a doctor's login).
        self.rec_user = User.objects.create_user("rita", password="pass12345")
        ReceptionistProfile.objects.create(user=self.rec_user)
        self.other_user = User.objects.create_user("outsider", password="pass12345")

        doc_user = User.objects.create_user("drsmith", password="x", first_name="Sam", last_name="Smith")
        self.doctor = DoctorProfile.objects.create(
            user=doc_user, specialization="GP", qualification="MBBS",
            registration_number="REG1", consultation_fee=Decimal("500.00"),
            consultation_duration_minutes=15,
        )
        # Doctor works 09:00-13:00 every weekday of the week, effective well in the past.
        for dow in range(7):
            DoctorSchedule.objects.create(
                doctor=self.doctor, day_of_week=dow, start_time=time(9), end_time=time(13),
                effective_from=timezone.localdate() - timedelta(days=30),
            )
        self.patient = Patient.objects.create(
            first_name="Anu", last_name="K", date_of_birth=date(1990, 1, 1),
            gender="Female", phone_number="9876543210",
        )
        self.login()

    def login(self, username="rita", password="pass12345"):
        resp = self.client.post("/api/receptionist/login/", {"username": username, "password": password})
        if resp.status_code == 200:
            self.client.credentials(HTTP_AUTHORIZATION="Bearer " + resp.data["access"])
        return resp

    def book(self, **over):
        body = {"patient": self.patient.id, "doctor": self.doctor.id,
                "appointment_date": str(future_date()), "appointment_time": "10:00:00",
                "booking_type": "ADVANCE"}
        body.update(over)
        return self.client.post("/api/appointments/", body, format="json")

    def appointment_today(self, status=Appointment.Status.BOOKED, patient=None, t=time(9)):
        # Created through the ORM: the API (correctly) refuses past times for today.
        return Appointment.objects.create(
            patient=patient or self.patient, doctor=self.doctor,
            appointment_date=timezone.localdate(), appointment_time=t, status=status,
        )


class AuthTests(BaseAPITest):
    def test_login_success_returns_tokens(self):
        r = self.login()
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.data)

    def test_login_wrong_password_401(self):
        self.client.credentials()
        self.assertEqual(self.login(password="bad").status_code, 401)

    def test_login_non_receptionist_rejected(self):
        self.client.credentials()
        self.assertIn(self.login("outsider").status_code, (401, 403))

    def test_no_token_401(self):
        self.client.credentials()
        self.assertEqual(self.client.get("/api/patients/").status_code, 401)

    def test_non_receptionist_token_403(self):
        from rest_framework_simplejwt.tokens import AccessToken
        tok = AccessToken.for_user(self.other_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tok}")
        for url in ("/api/patients/", "/api/appointments/", "/api/queue/", "/api/reports/daily/"):
            self.assertEqual(self.client.get(url).status_code, 403, url)


class PatientTests(BaseAPITest):
    payload = {"first_name": "Ravi", "last_name": "M", "date_of_birth": "1985-05-05",
               "gender": "male", "phone_number": "9000000001"}

    def test_register_auto_number(self):
        r = self.client.post("/api/patients/", self.payload, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["patient_number"], "P002")  # setUp created P001
        self.assertEqual(r.data["gender"], "Male")

    def test_missing_fields_400(self):
        r = self.client.post("/api/patients/", {"first_name": "X"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("phone_number", r.data)

    def test_bad_phone_400(self):
        r = self.client.post("/api/patients/", {**self.payload, "phone_number": "123"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_duplicate_patient_400(self):
        dup = {"first_name": "anu", "date_of_birth": "1990-01-01", "gender": "Female",
               "phone_number": "9876543210"}
        r = self.client.post("/api/patients/", dup, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("P001", str(r.data))

    def test_search_and_retrieve_and_update(self):
        self.assertEqual(self.client.get("/api/patients/?search=P001").data["results"][0]["first_name"]
                         if "results" in self.client.get("/api/patients/?search=P001").data
                         else self.client.get("/api/patients/?search=P001").data[0]["first_name"], "Anu")
        self.assertEqual(self.client.get(f"/api/patients/{self.patient.id}/").status_code, 200)
        r = self.client.patch(f"/api/patients/{self.patient.id}/", {"phone_number": "9111111111"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["phone_number"], "9111111111")

    def test_missing_patient_404(self):
        self.assertEqual(self.client.get("/api/patients/9999/").status_code, 404)


class AppointmentTests(BaseAPITest):
    def test_book_valid_starts_payment_pending(self):
        r = self.book()
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["status"], "PAYMENT_PENDING")
        self.assertEqual(r.data["patient_number"], "P001")

    def test_invalid_patient_and_doctor_400(self):
        self.assertEqual(self.book(patient=9999).status_code, 400)
        self.assertEqual(self.book(doctor=9999).status_code, 400)

    def test_past_date_400(self):
        r = self.book(appointment_date=str(timezone.localdate() - timedelta(days=1)))
        self.assertEqual(r.status_code, 400)

    def test_outside_hours_and_misaligned_400(self):
        self.assertEqual(self.book(appointment_time="14:00:00").status_code, 400)
        self.assertEqual(self.book(appointment_time="10:07:00").status_code, 400)

    def test_conflicting_slot_400(self):
        self.assertEqual(self.book().status_code, 201)
        other = Patient.objects.create(first_name="Bina", date_of_birth=date(1991, 2, 2),
                                       gender="Female", phone_number="9222222222")
        r = self.book(patient=other.id)
        self.assertEqual(r.status_code, 400)
        self.assertIn("appointment_time", r.data)

    def test_same_patient_same_doctor_same_day_400(self):
        self.assertEqual(self.book().status_code, 201)
        self.assertEqual(self.book(appointment_time="11:00:00").status_code, 400)

    def test_doctor_not_accepting_400(self):
        self.doctor.accepting_bookings = False
        self.doctor.save()
        self.assertEqual(self.book().status_code, 400)

    def test_list_and_filters(self):
        self.book()
        self.assertEqual(len(self._rows("/api/appointments/")), 1)
        self.assertEqual(len(self._rows(f"/api/appointments/?patient={self.patient.id}&status=PAYMENT_PENDING")), 1)
        self.assertEqual(len(self._rows("/api/appointments/?status=COMPLETED")), 0)
        self.assertEqual(self.client.get("/api/appointments/?status=BOGUS").status_code, 400)
        self.assertEqual(self.client.get("/api/appointments/?date=31-12-2026").status_code, 400)

    def _rows(self, url):
        d = self.client.get(url).data
        return d["results"] if isinstance(d, dict) else d

    def test_reschedule_ok_and_conflict_and_locked_fields(self):
        appt_id = self.book().data["id"]
        r = self.client.patch(f"/api/appointments/{appt_id}/", {"appointment_time": "10:15:00"}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["appointment_time"], "10:15:00")
        # patient cannot be swapped via reschedule
        other = Patient.objects.create(first_name="Cy", date_of_birth=date(1992, 3, 3),
                                       gender="Male", phone_number="9333333333")
        self.client.patch(f"/api/appointments/{appt_id}/", {"patient": other.id}, format="json")
        self.assertEqual(Appointment.objects.get(pk=appt_id).patient_id, self.patient.id)
        # conflict with a second booking
        second = self.book(patient=other.id, appointment_time="11:00:00").data["id"]
        r = self.client.patch(f"/api/appointments/{second}/", {"appointment_time": "10:15:00"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_cancel_requires_reason_then_blocks_rereschedule(self):
        appt_id = self.book().data["id"]
        self.assertEqual(self.client.post(f"/api/appointments/{appt_id}/cancel/", {}, format="json").status_code, 400)
        r = self.client.post(f"/api/appointments/{appt_id}/cancel/", {"cancellation_reason": "Patient request"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["status"], "CANCELLED")
        self.assertEqual(self.client.post(f"/api/appointments/{appt_id}/cancel/", {"cancellation_reason": "x"}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(f"/api/appointments/{appt_id}/", {"appointment_time": "11:00:00"}, format="json").status_code, 400)
        # freed slot can be booked again
        self.assertEqual(self.book().status_code, 201)

    def test_missing_appointment_404(self):
        self.assertEqual(self.client.post("/api/appointments/9999/cancel/", {"cancellation_reason": "x"}, format="json").status_code, 404)
        self.assertEqual(self.client.post("/api/appointments/9999/check-in/").status_code, 404)


class CheckInQueueTests(BaseAPITest):
    def test_checkin_issues_token_and_updates_status(self):
        appt = self.appointment_today()
        r = self.client.post(f"/api/appointments/{appt.id}/check-in/")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["token"]["token"], "T001")
        appt.refresh_from_db()
        self.assertEqual(appt.status, "CHECKED_IN")

    def test_repeat_checkin_returns_same_token_no_duplicate(self):
        appt = self.appointment_today()
        self.client.post(f"/api/appointments/{appt.id}/check-in/")
        r = self.client.post(f"/api/appointments/{appt.id}/check-in/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["token"]["token"], "T001")
        self.assertEqual(QueueToken.objects.count(), 1)

    def test_tokens_increment_per_doctor_queue(self):
        p2 = Patient.objects.create(first_name="Dev", date_of_birth=date(1980, 1, 1),
                                    gender="Male", phone_number="9444444444")
        a1, a2 = self.appointment_today(), self.appointment_today(patient=p2, t=time(9, 15))
        self.client.post(f"/api/appointments/{a1.id}/check-in/")
        r = self.client.post(f"/api/appointments/{a2.id}/check-in/")
        self.assertEqual(r.data["token"]["token"], "T002")

    def test_cancelled_future_and_completed_rejected(self):
        self.assertEqual(self.client.post(f"/api/appointments/{self.appointment_today(Appointment.Status.CANCELLED).id}/check-in/").status_code, 400)
        self.assertEqual(self.client.post(f"/api/appointments/{self.appointment_today(Appointment.Status.COMPLETED, t=time(9, 15)).id}/check-in/").status_code, 400)
        future = Appointment.objects.create(patient=self.patient, doctor=self.doctor,
                                            appointment_date=future_date(), appointment_time=time(9),
                                            status=Appointment.Status.BOOKED)
        self.assertEqual(self.client.post(f"/api/appointments/{future.id}/check-in/").status_code, 400)

    def test_cancel_after_checkin_cancels_token(self):
        appt = self.appointment_today()
        self.client.post(f"/api/appointments/{appt.id}/check-in/")
        self.client.post(f"/api/appointments/{appt.id}/cancel/", {"cancellation_reason": "Left"}, format="json")
        self.assertEqual(QueueToken.objects.get(appointment=appt).status, "CANCELLED")

    def test_queue_view(self):
        appt = self.appointment_today()
        self.client.post(f"/api/appointments/{appt.id}/check-in/")
        d = self.client.get(f"/api/queue/?doctor={self.doctor.id}").data
        rows = d["results"] if isinstance(d, dict) else d
        self.assertEqual(rows[0]["token"], "T001")
        self.assertEqual(rows[0]["patient_number"], "P001")
        self.assertEqual(self.client.get("/api/queue/?date=bad").status_code, 400)


class PaymentTests(BaseAPITest):
    def test_payment_defaults_to_doctor_fee_and_confirms_booking(self):
        appt = self.appointment_today(Appointment.Status.PAYMENT_PENDING)
        r = self.client.post(f"/api/appointments/{appt.id}/payment/", {"payment_method": "CASH"}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(Decimal(r.data["amount"]), Decimal("500.00"))
        appt.refresh_from_db()
        self.assertEqual(appt.status, "BOOKED")
        self.assertEqual(ConsultationPayment.objects.get().received_by, self.rec_user)

    def test_duplicate_success_409_and_failed_retry_ok(self):
        appt = self.appointment_today()
        url = f"/api/appointments/{appt.id}/payment/"
        self.assertEqual(self.client.post(url, {"payment_method": "CARD", "payment_status": "FAILED"}, format="json").status_code, 201)
        self.assertEqual(self.client.post(url, {"payment_method": "CARD"}, format="json").status_code, 201)
        self.assertEqual(self.client.post(url, {"payment_method": "CARD"}, format="json").status_code, 409)
        self.assertEqual(ConsultationPayment.objects.count(), 1)

    def test_validation(self):
        appt = self.appointment_today()
        url = f"/api/appointments/{appt.id}/payment/"
        self.assertEqual(self.client.post(url, {}, format="json").status_code, 400)
        self.assertEqual(self.client.post(url, {"payment_method": "ONLINE"}, format="json").status_code, 400)
        self.assertEqual(self.client.post(url, {"payment_method": "CASH", "amount": "-5"}, format="json").status_code, 400)
        cancelled = self.appointment_today(Appointment.Status.CANCELLED, t=time(9, 15))
        self.assertEqual(self.client.post(f"/api/appointments/{cancelled.id}/payment/", {"payment_method": "CASH"}, format="json").status_code, 400)
        self.assertEqual(self.client.get(f"/api/appointments/{appt.id}/payment/").status_code, 404)


class ReportTests(BaseAPITest):
    def test_empty_day_returns_zeros(self):
        d = str(future_date(30))
        r = self.client.get(f"/api/reports/daily/?date={d}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["total_appointments"], 0)
        self.assertEqual(r.data["appointments_by_status"]["BOOKED"], 0)

    def test_mixed_day(self):
        a = self.appointment_today()
        self.appointment_today(Appointment.Status.CANCELLED, t=time(9, 15))
        self.client.post(f"/api/appointments/{a.id}/check-in/")
        self.client.post(f"/api/appointments/{a.id}/payment/", {"payment_method": "UPI"}, format="json")
        r = self.client.get("/api/reports/daily/").data
        self.assertEqual(r["total_appointments"], 2)
        self.assertEqual(r["appointments_by_status"]["CHECKED_IN"], 1)
        self.assertEqual(r["appointments_by_status"]["CANCELLED"], 1)
        self.assertEqual(r["check_ins"], 1)
        self.assertEqual(r["payments"]["successful_total"], "500.00")
        self.assertEqual(r["payments"]["appointments_awaiting_payment"], 0)
        self.assertEqual(r["doctors"][0]["tokens_issued"], 1)
        self.assertEqual(r["patients_registered"], 1)

    def test_invalid_date_400(self):
        self.assertEqual(self.client.get("/api/reports/daily/?date=2026-13-45").status_code, 400)