
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .utils import extract_text_from_resume
from .serializers import UserSerializer, ResumeSerializer
from .models import Resume
import pdfplumber
import docx


# ---------- SIGNUP ----------
@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(
            {"message": "User created successfully"},
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------- LOGIN ----------
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(username=username, password=password)

    if user:
        return Response(
            {
                "message": "Login successful",
                "username": user.username,
                "email": user.email
            },
            status=status.HTTP_200_OK
        )

    return Response(
        {"error": "Invalid username or password"},
        status=status.HTTP_401_UNAUTHORIZED
    )


# ---------- TEST JWT ----------
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def test_auth(request):
    return Response({"message": "Auth working"})

# Utility function to extract text
def extract_text_from_resume(file):
    text = ""
    file.open('rb')  # Ensure file is opened
    try:
        if file.name.endswith('.pdf'):
            with pdfplumber.open(file) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
        elif file.name.endswith('.docx'):
            doc = docx.Document(file)
            for para in doc.paragraphs:
                text += para.text + "\n"
        else:
            raise ValueError("Unsupported file type. Only PDF and DOCX are allowed.")
    finally:
        file.close()
    return text

# ---------- UPLOAD RESUME ----------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_resume(request):
    serializer = ResumeSerializer(data=request.data)

    if serializer.is_valid():
        resume = serializer.save(user=request.user)

        try:
            extracted_text = extract_text_from_resume(resume.file)
            resume.extracted_text = extracted_text
            resume.save()
        except Exception as e:
            return Response(
                {"error": f"Text extraction failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {
                "message": "Resume uploaded & text extracted successfully",
                "text_length": len(extracted_text)
            },
            status=status.HTTP_201_CREATED
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)





@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analyze_resume(request):
    resume = Resume.objects.filter(user=request.user).last()

    if not resume:
        return Response(
            {"error": "No resume uploaded"},
            status=status.HTTP_404_NOT_FOUND
        )

    if not resume.extracted_text:
        return Response(
            {"error": "Resume text not extracted"},
            status=status.HTTP_400_BAD_REQUEST
        )

    text = resume.extracted_text.lower()

    skills_db = [
        "python", "django", "java", "spring",
        "javascript", "react", "node",
        "mongodb", "sql", "docker", "aws"
    ]

    found_skills = [skill for skill in skills_db if skill in text]

    score = min(100, 50 + len(found_skills) * 5)

    return Response({
        "skills_found": found_skills,
        "resume_score": score,
        "message": "Resume analyzed successfully"
    })




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def job_matcher(request):
    resume = Resume.objects.filter(user=request.user).last()

    if not resume or not resume.extracted_text:
        return Response(
            {"error": "Resume not ready"},
            status=status.HTTP_400_BAD_REQUEST
        )

    text = resume.extracted_text.lower()

    job_roles = {
        "Backend Developer": ["python", "django", "sql", "api"],
        "Frontend Developer": ["javascript", "react", "html", "css"],
        "Full Stack Developer": ["python", "django", "react", "sql"],
        "Java Developer": ["java", "spring", "hibernate"],
        "DevOps Engineer": ["docker", "aws", "kubernetes"]
    }

    matches = []

    for role, skills in job_roles.items():
        score = sum(1 for skill in skills if skill in text)
        if score >= 2:
            matches.append({
                "role": role,
                "match_score": score * 20
            })

    return Response({
        "recommended_roles": matches,
        "message": "Job matching completed"
    })

