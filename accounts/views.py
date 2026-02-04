
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.tokens import RefreshToken
from .utils import extract_text_from_resume
from .serializers import UserSerializer, ResumeSerializer
from .models import Resume
import pdfplumber
import docx
import re

# ------ SIGNUP ---------
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

    if user is not None:
        
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "Login successful",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "is_admin": user.is_staff,
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
        return Response({"error": "No resume uploaded"}, status=404)

    if not resume.extracted_text:
        return Response({"error": "Resume text not extracted"}, status=400)


    if resume.ats_score is not None:
        return Response({
            "ATS_score": resume.ats_score,
            "message": "Already analyzed"
        })
    

    text = resume.extracted_text.lower()

    score = 0


    # skill score------
    skills_db = [
        "python","django","java","spring",
        "javascript","react","node",
        "mongodb","sql","docker","aws"
    ]

    found_skills = [skill for skill in skills_db if skill in text]
    skills_score = min(30, len(found_skills) * 5)
    score += skills_score


    # Section Check-------------
    sections = ["education", "experience", "skills", "projects"]
    found_sections = [sec for sec in sections if sec in text]

    section_score = len(found_sections) * 6
    score += section_score


    # Contact Info-------

    email_regex = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    phone_regex = r"\b\d{10}\b"

    if re.search(email_regex, text):
        score += 8

    if re.search(phone_regex, text):
        score += 7


    # Resume Length-----------

    word_count = len(text.split())

    if 400 <= word_count <= 1200:
        score += 10
    elif 250 <= word_count < 400:
        score += 5


    # Action Verbs -------

    verbs = ["developed","built","designed","implemented","created"]
    found_verbs = [v for v in verbs if v in text]

    if found_verbs:
        score += 10


    final_score = min(score, 100)

    resume.ats_score = final_score
    resume.save()


    return Response({
        "ATS_score": final_score,
        "skills_found": found_skills,
        "sections_found": found_sections,
        "word_count": word_count,
        "message": "ATS analysis complete"
    })


# job matcher--------

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

        matched_skills = [skill for skill in skills if skill in text]

        score = int((len(matched_skills) / len(skills)) * 100)

        if score >= 40:  
            matches.append({
                "role": role,
                "match_percentage": score,
                "matched_skills": matched_skills
            })

    # sort by highest match ------------
    matches.sort(key=lambda x: x['match_percentage'], reverse=True)

    if not matches:
        return Response({
            "message": "No strong job matches found. Consider adding more skills."
        })

    return Response({
        "recommended_roles": matches,
        "message": "Job matching completed successfully"
    })

# skill gap analyze --------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def skill_gap_analyzer(request):
    resume = Resume.objects.filter(user=request.user).order_by('-uploaded_at').first()

    if not resume or not resume.extracted_text:
        return Response(
            {"error": "Resume not ready"},
            status=status.HTTP_400_BAD_REQUEST
        )

    text = resume.extracted_text.lower()

    job_roles = {
        "Backend Developer": ["python", "django", "sql", "docker", "aws"],
        "Frontend Developer": ["javascript", "react", "html", "css"],
        "Full Stack Developer": ["python", "django", "react", "sql", "docker"],
        "Java Developer": ["java", "spring", "hibernate", "microservices"],
        "DevOps Engineer": ["docker", "aws", "kubernetes", "ci/cd"]
    }

    best_role = None
    highest_score = 0
    missing_skills_output = []

    for role, skills in job_roles.items():

        matched = [skill for skill in skills if skill in text]
        score = len(matched)

        if score > highest_score:
            highest_score = score
            best_role = role
            missing_skills_output = [skill for skill in skills if skill not in text]

    if not best_role:
        return Response({
            "message": "Could not determine a suitable role."
        })

    return Response({
        "recommended_role": best_role,
        "skills_you_have": highest_score,
        "missing_skills": missing_skills_output,
        "message": "Skill gap analysis completed"
    })

# job description ---------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def job_description_matcher(request):
    resume = Resume.objects.filter(user=request.user).last()
    
    if not resume or not resume.extracted_text:
        return Response(
            {"error": "Resume not ready or not uploaded"},
            status=status.HTTP_400_BAD_REQUEST
        )

    job_description = request.data.get('job_description', '')
    if not job_description:
        return Response(
            {"error": "Job description is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    resume_text = re.sub(r'\s+', ' ', resume.extracted_text.lower())
    job_text = re.sub(r'\s+', ' ', job_description.lower())

    # extracting keyword
    job_skills = set(re.findall(r'\b\w+\b', job_text))
    resume_skills = set(re.findall(r'\b\w+\b', resume_text))

    matched_skills = list(resume_skills & job_skills)
    missing_skills = list(job_skills - resume_skills)

    #scoring
    if job_skills:
        match_score = round(len(matched_skills) / len(job_skills) * 100)
    else:
        match_score = 0

    return Response({
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "match_score": match_score,
        "message": "Job description analyzed successfully"
    })
