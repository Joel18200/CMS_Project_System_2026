
from django.db.models import Q
from rest_framework import generics

#from .auth import IsReceptionist
from rest_framework.permissions import AllowAny
from .models import Patient
from .serializers import PatientSerializer


class PatientListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = PatientSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = Patient.objects.all().order_by("-created_at")
        search = self.request.query_params.get("search", "").strip()

        if search:
            conditions = (
                Q(patient_number__iexact=search)
                | Q(phone_number__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )

            if search.isdigit():
                conditions |= Q(id=int(search))

            queryset = queryset.filter(conditions)

        return queryset


class PatientDetailUpdateAPIView(generics.RetrieveUpdateAPIView):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [AllowAny]

# from django.shortcuts import render
# from .auth import IsReceptionist
# # Create your views here.

# from rest_framework import generics
# from rest_framework.permissions import IsAuthenticated

# from .models import Patient
# from .serializers import PatientSerializer


# class PatientListCreateAPIView(generics.ListCreateAPIView):
#     queryset = Patient.objects.all().order_by("-created_at")
#     serializer_class = PatientSerializer
#     permission_classes = [IsReceptionist]
# class PatientDetailUpdateAPIView(generics.RetrieveUpdateAPIView):
#     queryset = Patient.objects.all()
#     serializer_class = PatientSerializer
#     permission_classes = [IsReceptionist]